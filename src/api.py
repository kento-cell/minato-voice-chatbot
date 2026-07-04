"""
Headless HTTP API for a character pack -- generation + speech synthesis.

The response body is raw WAV bytes; the caller decides how to play or store it.

Endpoints:
  GET  /health                     -> {"status": "ok", "character": "<name>"}
  POST /chat  {"text": "..."}      -> WAV audio bytes (audio/wav)
                                       X-Minato-Reply-Text: generated reply (URL-encoded)
                                       X-Minato-PII-Masked: masked labels, if any

Env vars:
  API_HOST          bind address. Defaults to 127.0.0.1 (loopback only) so that
                    running this on a laptop does NOT expose an unauthenticated
                    API to the whole LAN. The Docker image sets API_HOST=0.0.0.0
                    because binding beyond loopback is required inside a container.
  MINATO_CHARACTER  character pack to serve (default: minato)
  VOICEVOX_URL      VOICEVOX engine base URL (default: http://127.0.0.1:50021)
"""
import os
from urllib.parse import quote

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import requests  # noqa: E402
import torch  # noqa: E402
from characters import load as load_character  # noqa: E402
from flask import Flask, Response, jsonify, request  # noqa: E402
from pii_filter import mask_pii  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
CHARACTER = load_character(os.environ.get("MINATO_CHARACTER", "minato"))

app = Flask(__name__)
_tok = None
_model = None


def get_model():
    global _tok, _model
    if _model is None:
        _tok = AutoTokenizer.from_pretrained(BASE_MODEL)
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL, dtype=torch.bfloat16 if device == "cuda" else torch.float32, device_map=device
        )
        if CHARACTER.lora_path:
            from peft import PeftModel
            _model = PeftModel.from_pretrained(_model, CHARACTER.lora_path)
        _model.eval()
    return _tok, _model


def generate_reply(user_text: str) -> str:
    tok, model = get_model()
    msgs = [
        {"role": "system", "content": CHARACTER.persona},
        {"role": "user", "content": user_text},
    ]
    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=120, do_sample=False, pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def synthesize(text: str, speaker: int) -> bytes:
    query = requests.post(f"{VOICEVOX_URL}/audio_query", params={"text": text, "speaker": speaker}, timeout=15).json()
    resp = requests.post(f"{VOICEVOX_URL}/synthesis", params={"speaker": speaker}, json=query, timeout=30)
    resp.raise_for_status()
    return resp.content


@app.get("/health")
def health():
    return jsonify({"status": "ok", "character": CHARACTER.name})


@app.post("/chat")
def chat():
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    requested = body.get("character")
    if requested and requested != CHARACTER.name:
        return jsonify({
            "error": f"this server is running character '{CHARACTER.name}'. "
                     f"Set MINATO_CHARACTER={requested} and restart to switch."
        }), 400

    # PII is masked BEFORE the text reaches the LLM (and thus before any
    # downstream logging or synthesis can see it).
    text, pii_found = mask_pii(text)

    reply = generate_reply(text)
    wav = synthesize(reply, CHARACTER.voice_speaker)
    headers = {"X-Minato-Reply-Text": quote(reply)}
    if pii_found:
        headers["X-Minato-PII-Masked"] = quote(",".join(pii_found))
    return Response(wav, mimetype="audio/wav", headers=headers)


if __name__ == "__main__":
    # 127.0.0.1 by default: never expose an auth-less API to the LAN unless
    # explicitly asked to (API_HOST=0.0.0.0, e.g. inside Docker).
    app.run(host=os.environ.get("API_HOST", "127.0.0.1"), port=8080)
