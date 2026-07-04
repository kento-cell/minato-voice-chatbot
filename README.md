# ミナト (Minato) — a tiny voice AI chatbot

![CI](https://github.com/kento-cell/voice-chat-bot/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/kento-cell/voice-chat-bot/actions/workflows/cd.yml/badge.svg)

A personal learning project: a small, fully local voice-chatbot persona built by
LoRA-fine-tuning an open-source 0.5B-parameter LLM and giving it a voice with
[VOICEVOX](https://voicevox.hiroshiba.jp/). No cloud APIs, no external calls at
inference time.

This repo intentionally contains **no company names or personal names** — it's
published as a standalone individual project.

## Architecture

![architecture](architecture/minato_architecture.png)

The diagram source (`architecture/minato_architecture.drawio`) can be opened and
edited in [draw.io](https://app.diagrams.net) or the VS Code
[Draw.io Integration](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio)
extension. Regenerate the PNG anytime with:

```bash
python architecture/generate_architecture_diagram.py architecture/minato_architecture.png
```

| Component | Technology |
|---|---|
| Base LLM | [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct) (frozen, shared by all characters) |
| Characters | Self-contained packs under `characters/<name>/` (persona card + optional LoRA + voice config) |
| Text-to-speech | [VOICEVOX Engine](https://github.com/VOICEVOX/voicevox_engine) (local HTTP API) — voice-clone engines pluggable per pack |
| Playback (desktop mode) | `sounddevice` + `soundfile` (cross-platform: Windows/macOS/Linux) |

## Character packs

Each character is one directory — contributors work in parallel without ever
touching the same files:

```
characters/<name>/
├── persona.md      # required: the personality card (this alone is enough)
├── config.json     # required: voice engine / speaker / optional lora path
├── lora/           # optional: LoRA adapter for stronger persona fidelity
└── voice/          # optional: personal voice model — NEVER committed (CI-enforced)
```

```bash
python src/minato_talk.py --list-characters     # discovered packs
python src/minato_talk.py --character minato    # talk to a specific one
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to create your own character.

## Two ways to run it

### 1. Desktop mode (talks out loud through your speakers)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Start a VOICEVOX engine (either works):
#   a) the desktop app, or
#   b) docker compose up voicevox

python src/minato_talk.py
```

```
python src/minato_talk.py --list-speakers   # see all available voices
python src/minato_talk.py --speaker 3       # pick a different voice
```

### 2. Headless API mode (containerized, no speakers needed)

```bash
docker compose up --build
```

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは"}' \
  -o reply.wav
```

Returns raw WAV bytes; the generated reply text is in the
`X-Minato-Reply-Text` response header (URL-encoded).

The `app` image is CPU-only by design, so `docker compose up` works identically
on any machine — no NVIDIA driver / CUDA toolkit required. If you have an NVIDIA
GPU and run the desktop mode natively, install the CUDA build of torch instead
for faster generation:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## Re-training the persona

Minato's LoRA adapter (`characters/minato/lora/`) was trained on
`data/train.jsonl` (19 examples, ~1 minute on a single consumer GPU).
To reproduce or modify it:

```bash
python data/make_data.py       # regenerate data/train.jsonl
python finetune_lora.py        # trains out/lora/ — copy into your pack's lora/
```

## CI/CD

- **CI** (`.github/workflows/ci.yml`): on every push/PR, lints the code and runs
  a real end-to-end smoke test — spins up the VOICEVOX engine as a service
  container, starts the API, sends a chat request, and asserts a valid WAV comes
  back. Free (GitHub Actions, public repo).
- **CD** (`.github/workflows/cd.yml`): on pushing a version tag (`v*.*.*`),
  builds the headless API image and publishes it to GitHub Container Registry
  (`ghcr.io`) — free for public repos, no external registry account needed.

## 安全に使うために / Safety notes

**プライバシー（設計上の保証）**
- 推論は完全ローカルです。あなたの会話・音声がこのソフトウェアから外部サーバーへ送信されることはありません（通信はモデルのダウンロードのみ）
- 会話ログはデフォルトで保存されません
- 入力テキスト中のメールアドレス・電話番号等はLLMに渡る前に自動マスクされます（`src/pii_filter.py`）
- APIサーバー（`src/api.py`）のデフォルトは `127.0.0.1`（自分のPCからのみアクセス可）です。`API_HOST=0.0.0.0` を明示した場合のみLANに公開されます。**認証機能はないため、信頼できないネットワークで公開しないでください**

**VOICEVOXの利用規約（音声を公開する場合は必須）**
- 合成音声を動画・配信等で公開する場合、[VOICEVOX利用規約](https://voicevox.hiroshiba.jp/term/)により**クレジット表記が必須**です（例: `VOICEVOX:ずんだもん`）
- 加えて**各キャラクター（音声ライブラリ）の個別規約**が適用されます。使用するキャラクターの規約を必ず確認してください
- 商用・非商用とも利用可能ですが、上記の条件に従う必要があります

**声モデル（ボイスクローン）について**
- 学習・使用してよいのは**あなた自身の声だけ**です。他人・有名人の声の無断クローンは、肖像権・パブリシティ権等の侵害となる可能性があります
- 声モデルは `characters/*/voice/` に置き、**コミットしない**でください（.gitignore＋CIで二重にブロックされますが、意図を理解した上で扱ってください）

**このリポジトリをフォークする方へ**
- 本家リポジトリのCI保護・ブランチ保護・Secretは**フォーク先には引き継がれません**。フォークで自分の声モデルや個人データを扱う場合は、フォークをPrivateにするか、同等の保護（Actions有効化等）を自分で設定してください

## Known limitations

- No microphone input yet (text in, voice out only).
- No conversation memory (single-turn only).
- Trained on only 19 examples — outside that narrow scope it can produce
  plausible-sounding but incorrect answers (small-model hallucination), not
  general intelligence.

## License

MIT — see [LICENSE](LICENSE).
