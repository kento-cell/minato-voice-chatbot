"""
Headless HTTP API for ミナト -- generation + speech synthesis, no local playback.

Designed to run in a container (no host audio device needed): the response body
is raw WAV bytes; the caller (a native client, curl, another service, etc.)
decides how to play or store it.

Endpoints:
  GET  /health                     -> {"status": "ok"}
  POST /chat  {"text": "..."}      -> WAV audio bytes (audio/wav)
                                       with X-Minato-Reply-Text header = the
                                       generated reply (URL-encoded, may be non-ASCII)

Env vars:
  VOICEVOX_URL   VOICEVOX engine base URL (default: http://127.0.0.1:50021)
  VOICEVOX_SPEAKER  speaker id (default: 3, ずんだもん ノーマル)
"""
import os
from urllib.parse import quote

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import requests  # noqa: E402
import torch  # noqa: E402
from flask import Flask, Response, jsonify, request  # noqa: E402
from peft import PeftModel  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "lora")
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
SPEAKER = int(os.environ.get("VOICEVOX_SPEAKER", "3"))

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
        _model = PeftModel.from_pretrained(_model, ADAPTER_DIR)
        _model.eval()
    return _tok, _model


def generate_reply(user_text: str) -> str:
    tok, model = get_model()
    msgs = [{"role": "user", "content": user_text}]
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
    return jsonify({"status": "ok"})


@app.post("/chat")
def chat():
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    if not text:
        return jsonify({"error": "text is required"}), 400

    reply = generate_reply(text)
    wav = synthesize(reply, SPEAKER)
    return Response(
        wav,
        mimetype="audio/wav",
        headers={"X-Minato-Reply-Text": quote(reply)},
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
