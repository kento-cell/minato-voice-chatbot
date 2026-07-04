"""
Browser voice-chat server: speak into the mic, the character answers out loud.

Pipeline per turn:
  browser mic (webm/opus) -> faster-whisper STT -> PII mask -> character LLM
  -> VOICEVOX synthesis -> WAV back to the browser for playback.

Run:
  python src/webapp.py            # then open http://127.0.0.1:8080

Env vars (machine-local settings, not pack settings):
  STT_MODEL          faster-whisper size: tiny/base/small/medium (default: small;
                     use tiny/base on weak CPUs)
  MINATO_BASE_MODEL  LLM base model (default: Qwen/Qwen2.5-0.5B-Instruct;
                     GPU machines can point at a bigger instruct model)
  VOICEVOX_URL       VOICEVOX engine URL (default: http://127.0.0.1:50021)
  API_HOST           bind address (default: 127.0.0.1 — loopback only)
  PORT               port (default: 8080)

Conversation memory is in-process only (last 10 turns per character); nothing
is written to disk.
"""
import base64
import io
import os
from collections import defaultdict, deque

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import requests  # noqa: E402
from characters import discover, load as load_character  # noqa: E402
from engine import build_messages, finalize_reply, generate, load_model, resolve_base_model  # noqa: E402
from flask import Flask, jsonify, request, send_from_directory  # noqa: E402
from pii_filter import mask_pii  # noqa: E402

VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
MEMORY_TURNS = 10

app = Flask(__name__, static_folder="static")

_stt = None
_llm_cache: dict[str, tuple] = {}  # character name -> (tok, model, used_lora)
_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=MEMORY_TURNS))


def get_stt():
    global _stt
    if _stt is None:
        from faster_whisper import WhisperModel
        size = os.environ.get("STT_MODEL", "small")
        # int8 keeps CPU inference practical on low-spec machines
        _stt = WhisperModel(size, device="auto", compute_type="int8")
    return _stt


def get_llm(character_name: str):
    if character_name not in _llm_cache:
        # keep at most one model in memory (low-spec friendliness)
        _llm_cache.clear()
        character = load_character(character_name)
        tok, model, used_lora = load_model(character)
        _llm_cache[character_name] = (character, tok, model, used_lora)
    return _llm_cache[character_name]


# Whisper hallucinates these stock phrases on silent / near-silent input
# (YouTube-outro artifacts from its training data). Treat them as "no speech".
_HALLUCINATION_PHRASES = {
    "ご視聴ありがとうございました",
    "ご視聴ありがとうございました。",
    "チャンネル登録お願いします",
    "チャンネル登録お願いします。",
    "おやすみなさい",
    "ありがとうございました。",
}


def transcribe(audio_bytes: bytes) -> str:
    segments, _info = get_stt().transcribe(
        io.BytesIO(audio_bytes),
        language="ja",
        vad_filter=True,  # trim silence -> the main defense against hallucination
        condition_on_previous_text=False,
    )
    text = "".join(s.text for s in segments).strip()
    if text in _HALLUCINATION_PHRASES:
        return ""
    return text


def synthesize(text: str, speaker: int) -> bytes:
    query = requests.post(
        f"{VOICEVOX_URL}/audio_query", params={"text": text, "speaker": speaker}, timeout=15
    ).json()
    resp = requests.post(
        f"{VOICEVOX_URL}/synthesis", params={"speaker": speaker}, json=query, timeout=30
    )
    resp.raise_for_status()
    return resp.content


def run_turn(character_name: str, user_text: str) -> dict:
    user_text, pii_found = mask_pii(user_text)
    character, tok, model, used_lora = get_llm(character_name)
    history = _history[character_name]
    reply = generate(tok, model, build_messages(character, history, user_text))
    reply = finalize_reply(character, reply)
    history.append((user_text, reply))
    wav = synthesize(reply, character.voice_speaker)
    return {
        "you": user_text,
        "reply": reply,
        "character": character.display_name,
        "pii_masked": pii_found,
        "lora": used_lora,
        "audio": base64.b64encode(wav).decode("ascii"),
    }


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/health")
def health():
    return jsonify({"status": "ok", "base_model": resolve_base_model()})


@app.get("/characters")
def characters():
    return jsonify([
        {"name": c.name, "display_name": c.display_name,
         "engine": c.voice_engine, "speaker": c.voice_speaker}
        for c in discover().values()
    ])


@app.post("/chat-json")
def chat_json():
    body = request.get_json(force=True, silent=True) or {}
    text = (body.get("text") or "").strip()
    name = body.get("character") or "minato"
    if not text:
        return jsonify({"error": "text is required"}), 400
    return jsonify(run_turn(name, text))


@app.post("/chat-audio")
def chat_audio():
    if "audio" not in request.files:
        return jsonify({"error": "audio file is required"}), 400
    name = request.form.get("character") or "minato"
    recognized = transcribe(request.files["audio"].read())
    if not recognized:
        return jsonify({"error": "声を検出できませんでした。マイクの入力デバイス設定（ブラウザのアドレスバーのマイクアイコン→使用デバイス）を確認し、はっきり話してみてください"}), 422
    return jsonify(run_turn(name, recognized))


@app.post("/reset")
def reset():
    body = request.get_json(force=True, silent=True) or {}
    name = body.get("character") or "minato"
    _history[name].clear()
    return jsonify({"status": "reset", "character": name})


if __name__ == "__main__":
    host = os.environ.get("API_HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8080"))
    print(f"ボイスチャット起動: http://{host}:{port}  (base={resolve_base_model()})")
    app.run(host=host, port=port)
