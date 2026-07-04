"""
Talk to a character pack by text; the character answers out loud.

Pipeline: your text -> PII mask -> character LLM (base + optional LoRA)
          -> VOICEVOX (or the pack's voice engine) -> speaker playback.

Cross-platform: audio playback uses sounddevice/soundfile (Windows/macOS/Linux).

Usage:
  python src/minato_talk.py                       # default character (minato)
  python src/minato_talk.py --character <name>    # any pack under characters/
  python src/minato_talk.py --list-characters     # discovered packs
  python src/minato_talk.py --list-speakers       # VOICEVOX voice ids

Env vars:
  VOICEVOX_URL   VOICEVOX engine URL (default: http://127.0.0.1:50021)
"""
import argparse
import io
import os
from collections import deque

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import requests  # noqa: E402  (after KMP env var, before torch)
import soundfile as sf  # noqa: E402
import sounddevice as sd  # noqa: E402
import torch  # noqa: E402
from characters import Character, discover, load  # noqa: E402
from pii_filter import mask_pii  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
MEMORY_TURNS = 10  # in-session only; nothing is persisted to disk


def list_speakers():
    speakers = requests.get(f"{VOICEVOX_URL}/speakers", timeout=5).json()
    for sp in speakers:
        for style in sp["styles"]:
            print(f"  id={style['id']:<4} {sp['name']} / {style['name']}")


def synthesize_and_play(text: str, character: Character):
    # Non-VOICEVOX engines are resolved to a VOICEVOX fallback by
    # characters.load() when no local voice model is present. Dedicated
    # adapters for sbv2 / gpt-sovits arrive in a later phase.
    query = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": character.voice_speaker},
        timeout=15,
    ).json()
    wav_bytes = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": character.voice_speaker},
        json=query,
        timeout=30,
    ).content

    data, samplerate = sf.read(io.BytesIO(wav_bytes))
    sd.play(data, samplerate)
    sd.wait()


def load_model(character: Character):
    print(f"{character.display_name} を起動中...")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, dtype=torch.bfloat16 if device == "cuda" else torch.float32, device_map=device
    )
    if character.lora_path:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, character.lora_path)
    model.eval()
    return tok, model


def generate_reply(tok, model, character: Character, history: deque, user_text: str) -> str:
    msgs = [{"role": "system", "content": character.persona}]
    for u, a in history:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": user_text})

    prompt = tok.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=120, do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--character", default="minato")
    ap.add_argument("--list-characters", action="store_true")
    ap.add_argument("--list-speakers", action="store_true")
    args = ap.parse_args()

    if args.list_characters:
        for name, c in discover().items():
            lora = "LoRAあり" if c.lora_path else "人格カードのみ"
            print(f"  {name:<16} {c.display_name} / voice={c.voice_engine}:{c.voice_speaker} / {lora}")
        return
    if args.list_speakers:
        list_speakers()
        return

    character = load(args.character)

    try:
        requests.get(f"{VOICEVOX_URL}/version", timeout=3)
    except requests.exceptions.RequestException:
        print(f"VOICEVOXエンジンに接続できません ({VOICEVOX_URL})。")
        print("先にVOICEVOXアプリを起動するか、`docker compose up voicevox` を実行してください。")
        return

    tok, model = load_model(character)
    history: deque = deque(maxlen=MEMORY_TURNS)
    print(f"{character.display_name} 準備完了（直近{MEMORY_TURNS}ターンを記憶・保存はしません）。'exit'で終了。\n")

    while True:
        user_text = input("あなた: ").strip()
        if user_text.lower() in ("exit", "quit", "終了"):
            print(f"{character.display_name}: またね。")
            break
        if not user_text:
            continue
        user_text, pii_found = mask_pii(user_text)
        if pii_found:
            print(f"（入力内の {'/'.join(pii_found)} をマスクしました）")
        reply = generate_reply(tok, model, character, history, user_text)
        history.append((user_text, reply))
        print(f"{character.display_name}: {reply}")
        synthesize_and_play(reply, character)


if __name__ == "__main__":
    main()
