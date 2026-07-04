# voice-chat-bot — 分身たちの声の遊び場

![CI](https://github.com/kento-cell/voice-chat-bot/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/kento-cell/voice-chat-bot/actions/workflows/cd.yml/badge.svg)

**自分の「分身キャラ」を作って持ち寄り、声で会話して遊ぶ、完全ローカルの音声チャットボット。**
LoRA微調整した軽量LLM（0.5B）＋ [VOICEVOX](https://voicevox.hiroshiba.jp/) 音声合成。
クラウドAPI不使用・推論時の外部通信ゼロ・低スペックPC（GPU無し）でも動きます。

A fully-local voice-chatbot playground: bring your own AI alter-ego
(persona card + optional LoRA + voice). No cloud APIs, no external calls at
inference time. This repo intentionally contains no company or personal names.

## 🚀 クイックスタート（3ステップ・5分）

```bash
# 1. 取得と依存インストール
git clone https://github.com/kento-cell/voice-chat-bot.git
cd voice-chat-bot
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 2. 音声エンジン起動（どちらか。Dockerが楽）
docker compose up voicevox        # または VOICEVOXデスクトップアプリを起動

# 3. 話す（初回はLLMを自動ダウンロード、以降オフライン可）
python src/minato_talk.py
```

テキストを打つとキャラが**声で**返事します。`exit`で終了。GPU不要（あれば自動で使用）。

```bash
python src/minato_talk.py --list-characters   # いるキャラの一覧
python src/minato_talk.py --character minato  # キャラを指定して会話
```

## 🎭 遊び方と運用ルール（参加したい人へ）

**自分のキャラを作るのに必要なのはMarkdown 1枚**（プログラミング不要・5分）。
手順は [CONTRIBUTING.md](CONTRIBUTING.md) の「自分のキャラクターを作る」参照。

| ルール | 内容 | 強制方法 |
|---|---|---|
| 自分の部屋だけ | 触ってよいのは `characters/<自分のキャラ>/` のみ。1PR=1キャラ | CI（repo-guard）が自動判定 |
| 承認は不要 | 自分のキャラのPRは、CI緑になれば**自分でマージしてOK** | ルールセット設定済み |
| コアは立入禁止 | `src/`等の変更はオーナーのみ。提案はIssueへ | CI（repo-guard） |
| 声は持ち込まない | 声モデル（生体情報）はコミット禁止・各自ローカル保管 | .gitignore＋CI（pack-lint） |
| 個人情報ゼロ | 実名・社名・連絡先をリポジトリに入れない | CI（pii-check） |

ルール違反のPRは**マージボタンが物理的に押せなくなる**ので、壊す心配なく気軽にどうぞ。

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
python src/minato_talk.py --list-characters   # discovered character packs
python src/minato_talk.py --list-speakers     # available VOICEVOX voices
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

## Known limitations / Roadmap

- マイク入力は未実装（テキスト入力→音声出力のみ）。**Phase 2**で対応予定（faster-whisper・CPU可）
- 会話記憶はセッション内のみ（直近10ターン・ディスク保存なし）
- キャラ同士の自動会話（デュエットモード）は**Phase 3**、本人声クローン対応（Style-Bert-VITS2等）は**Phase 4**で予定
- ミナトの学習データは19件のみ — その範囲外の質問には、もっともらしい誤答をすることがあります（小型モデルの既知の限界であり仕様です）
- Linuxでデスクトップ再生する場合、`libportaudio2` のインストールが必要なことがあります（`sudo apt install libportaudio2`）

## License

MIT — see [LICENSE](LICENSE).
