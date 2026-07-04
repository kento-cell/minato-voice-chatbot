"""
Give the fine-tuned "ミナト" persona (Qwen2.5-0.5B + LoRA) a voice.

Pipeline: your text -> ミナト generates a reply -> VOICEVOX synthesizes it -> plays out loud.

Cross-platform: audio playback uses sounddevice/soundfile (works on Windows, macOS,
Linux) instead of the Windows-only `winsound` module.

Prereqs:
  - out/lora/ must exist (run finetune_lora.py first)
  - A VOICEVOX engine must be reachable (local app, or `docker compose up voicevox`)

Usage:
  python src/minato_talk.py                    # interactive chat loop
  python src/minato_talk.py --speaker 3         # use a different VOICEVOX voice
  python src/minato_talk.py --list-speakers     # show all available voice IDs

Env vars:
  VOICEVOX_URL   override the VOICEVOX engine URL (default: http://127.0.0.1:50021)
"""
import argparse
import io
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import requests  # noqa: E402  (after KMP env var, before torch)
import soundfile as sf  # noqa: E402
import sounddevice as sd  # noqa: E402
import torch  # noqa: E402
from peft import PeftModel  # noqa: E402
from pii_filter import mask_pii  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"
ADAPTER_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "out", "lora")
VOICEVOX_URL = os.environ.get("VOICEVOX_URL", "http://127.0.0.1:50021")
DEFAULT_SPEAKER = 3  # ずんだもん (ノーマル)


def list_speakers():
    speakers = requests.get(f"{VOICEVOX_URL}/speakers", timeout=5).json()
    for sp in speakers:
        for style in sp["styles"]:
            print(f"  id={style['id']:<4} {sp['name']} / {style['name']}")


def synthesize_and_play(text: str, speaker: int):
    query = requests.post(
        f"{VOICEVOX_URL}/audio_query",
        params={"text": text, "speaker": speaker},
        timeout=15,
    ).json()
    wav_bytes = requests.post(
        f"{VOICEVOX_URL}/synthesis",
        params={"speaker": speaker},
        json=query,
        timeout=30,
    ).content

    data, samplerate = sf.read(io.BytesIO(wav_bytes))
    sd.play(data, samplerate)
    sd.wait()


def load_minato():
    print("ミナトを起動中...")
    tok = AutoTokenizer.from_pretrained(BASE_MODEL)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL, dtype=torch.bfloat16 if device == "cuda" else torch.float32, device_map=device
    )
    model = PeftModel.from_pretrained(model, ADAPTER_DIR)
    model.eval()
    return tok, model


def generate_reply(tok, model, user_text: str) -> str:
    msgs = [{"role": "user", "content": user_text}]
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
    ap.add_argument("--speaker", type=int, default=DEFAULT_SPEAKER)
    ap.add_argument("--list-speakers", action="store_true")
    args = ap.parse_args()

    if args.list_speakers:
        list_speakers()
        return

    try:
        requests.get(f"{VOICEVOX_URL}/version", timeout=3)
    except requests.exceptions.RequestException:
        print(f"VOICEVOXエンジンに接続できません ({VOICEVOX_URL})。")
        print("先にVOICEVOXアプリを起動するか、`docker compose up voicevox` を実行してください。")
        return

    tok, model = load_minato()
    print(f"ミナト準備完了（voicevox speaker id={args.speaker}）。'exit'で終了。\n")

    while True:
        user_text = input("あなた: ").strip()
        if user_text.lower() in ("exit", "quit", "終了"):
            print("ミナト: またね。")
            break
        if not user_text:
            continue
        user_text, pii_found = mask_pii(user_text)
        if pii_found:
            print(f"（入力内の {'/'.join(pii_found)} をマスクしました）")
        reply = generate_reply(tok, model, user_text)
        print(f"ミナト: {reply}")
        synthesize_and_play(reply, args.speaker)


if __name__ == "__main__":
    main()
