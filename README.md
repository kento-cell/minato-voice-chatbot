# voice-chat-bot — 分身たちの声の遊び場

![CI](https://github.com/kento-cell/voice-chat-bot/actions/workflows/ci.yml/badge.svg)
![CD](https://github.com/kento-cell/voice-chat-bot/actions/workflows/cd.yml/badge.svg)

**自分の「分身キャラ」を作って持ち寄り、声で会話して遊ぶ、完全ローカルの音声チャットボット。**
LoRA微調整した軽量LLM（0.5B）＋ [VOICEVOX](https://voicevox.hiroshiba.jp/) 音声合成。
クラウドAPI不使用・推論時の外部通信ゼロ・低スペックPC（GPU無し）でも動きます。

このリポジトリには実在の個人名・社名を一切含めない方針で運営しています（詳細は後述の安全事項）。

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

## アーキテクチャ

![architecture](architecture/minato_architecture.png)

図の元データ（`architecture/minato_architecture.drawio`）は [draw.io](https://app.diagrams.net) か、VS Codeの
[Draw.io Integration](https://marketplace.visualstudio.com/items?itemName=hediet.vscode-drawio)
拡張機能で開いて編集できます。PNGはいつでも再生成可能:

```bash
python architecture/generate_architecture_diagram.py architecture/minato_architecture.png
```

| コンポーネント | 技術 |
|---|---|
| ベースLLM | [Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)（凍結・全キャラ共通） |
| キャラクター | `characters/<name>/` 配下の自己完結パック（人格カード＋任意のLoRA＋声設定） |
| 音声合成 | [VOICEVOXエンジン](https://github.com/VOICEVOX/voicevox_engine)（ローカルHTTP API）。声クローンエンジンはパック単位で差し替え可能 |
| 音声再生（デスクトップモード） | `sounddevice`＋`soundfile`（Windows / macOS / Linux 対応） |

## キャラクターパック

キャラ1体＝ディレクトリ1つ。**作業者同士が同じファイルを触らない**構造なので、何人同時に開発してもコンフリクトしません:

```
characters/<name>/
├── persona.md      # 必須: 人格カード（これだけで参戦できる）
├── config.json     # 必須: 声エンジン／話者ID／任意のloraパス
├── lora/           # 任意: 人格再現を強化するLoRAアダプタ
└── voice/          # 任意: 本人の声モデル — 絶対にコミットされない（CIが強制）
```

自分のキャラの作り方は [CONTRIBUTING.md](CONTRIBUTING.md) へ。

## 実行方法は2つ

### 1. デスクトップモード（スピーカーから声が出る）

クイックスタートの手順そのままです。補助コマンド:

```
python src/minato_talk.py --list-characters   # キャラパック一覧
python src/minato_talk.py --list-speakers     # VOICEVOXの話者一覧
```

### 2. ヘッドレスAPIモード（コンテナ動作・スピーカー不要）

```bash
docker compose up --build
```

```bash
curl -X POST http://localhost:8080/chat \
  -H "Content-Type: application/json" \
  -d '{"text": "こんにちは"}' \
  -o reply.wav
```

WAVバイナリがそのまま返ります。生成された返答テキストはレスポンスヘッダー
`X-Minato-Reply-Text`（URLエンコード済み）に入っています。

`app`イメージは意図的にCPU専用で作ってあるため、**どのマシンでも同じように動きます**
（NVIDIAドライバ・CUDA不要）。NVIDIA GPU持ちでデスクトップモードを速くしたい場合のみ:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu124
```

## ペルソナの再学習

ミナトのLoRAアダプタ（`characters/minato/lora/`）は `data/train.jsonl`（19件、一般的なGPUで約1分）で学習したものです。再現・改変するには:

```bash
python data/make_data.py       # data/train.jsonl を再生成
python finetune_lora.py        # out/lora/ に学習 → 自分のパックの lora/ にコピー
```

## CI/CD

- **CI**（`.github/workflows/ci.yml`）: push/PRのたびにlint＋本物のエンドツーエンドテスト
  （VOICEVOXコンテナを立ち上げ、APIにリクエストを送り、正しいWAVが返るかまで検証）。
  加えて `pii-check`（個人情報スキャン）と `pack-lint`（パック構造検査）が必須で走ります
- **Guard**（`.github/workflows/guard.yml`）: コア領域の変更権限と「1PR=1キャラ」を、
  PR側から改ざんできない方式（pull_request_target）で強制
- **CD**（`.github/workflows/cd.yml`）: バージョンタグ（`v*.*.*`）のpushで、ヘッドレスAPIの
  Dockerイメージを GitHub Container Registry（ghcr.io）へ自動公開

## 安全に使うために

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

## 既知の制限とロードマップ

- マイク入力は未実装（テキスト入力→音声出力のみ）。**Phase 2**で対応予定（faster-whisper・CPU可）
- 会話記憶はセッション内のみ（直近10ターン・ディスク保存なし）
- キャラ同士の自動会話（デュエットモード）は**Phase 3**、本人声クローン対応（Style-Bert-VITS2等）は**Phase 4**で予定
- ミナトの学習データは19件のみ — その範囲外の質問には、もっともらしい誤答をすることがあります（小型モデルの既知の限界であり仕様です）
- Linuxでデスクトップ再生する場合、`libportaudio2` のインストールが必要なことがあります（`sudo apt install libportaudio2`）

## ライセンス

MIT — [LICENSE](LICENSE) 参照。
