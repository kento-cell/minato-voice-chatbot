# Contributing / 開発ルール

人間の作業者もAIエージェント（Claude Code, Codex等）も、**全員このルールで作業します**。

## 🔒 絶対ルール: PII（個人情報）

このリポジトリは**Public**です。以下を絶対に含めないでください:

- 実在の個人名・ハンドルネーム・社名・メールアドレス・住所・電話番号
- コード、学習データ（`data/train.jsonl`）、コミットメッセージ、Issue/PR本文すべてが対象
- コミットは **GitHubのnoreplyメール**で行うこと:
  ```bash
  git config user.email "<GitHubID>+<username>@users.noreply.github.com"
  ```

### PIIガード（3層・自動）

| 層 | 仕組み | 強制力 |
|---|---|---|
| ランタイム | `src/pii_filter.py` がチャット入力のメール/電話/番号列等をLLMに渡る前にマスク | コード組込み（常時） |
| CI | `pii-check` ジョブがリポジトリ全体をスキャン。検出時はマージ不可 | ルールセットで強制 |
| pre-commit | コミット時にローカルで同じスキャンを実行（早期警告） | 要インストール（下記） |

**pre-commitのセットアップ（初回のみ・推奨）:**
```bash
pip install -r requirements-dev.txt
pre-commit install
```

**自分の名前を検出対象に足す:** リポジトリ直下に `.pii-denylist.txt`（gitignore済み）を作り、1行1語で自分の本名・ハンドル名を書いてください。このファイルはコミットされず、あなたのマシン上でのみスキャンに使われます。CI側は同じ内容をリポジトリSecret `PII_DENYLIST` で保持しています（新しい作業者が入ったらSecretにも追記）。

## 開発フロー

`main` への直接pushは**ルールセットでブロック**されています。必ず:

```
1. ブランチを切る        git switch -c feat/mic-input
2. 作業してコミット       （小さく、意味の単位で）
3. push & PR作成        gh pr create --fill
4. CIがグリーンになるのを待つ（自動でLLM+TTSのスモークテストが走ります）
5. レビュー後マージ       （squash推奨）
```

### ブランチ命名

| プレフィックス | 用途 |
|---|---|
| `feat/` | 新機能（例: `feat/mic-input`） |
| `fix/` | バグ修正 |
| `chore/` | 設定・ドキュメント・雑務 |

- コミットメッセージは英語・命令形（例: `Add microphone input via Whisper`）

## セットアップ（初回のみ）

```bash
git clone https://github.com/kento-cell/minato-voice-chatbot.git
cd minato-voice-chatbot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
docker compose up voicevox   # TTSエンジン起動（初回はイメージDL）
python src/minato_talk.py    # 動作確認
```

GPUがなくても動きます（CPU推論）。詳細は [README.md](README.md)。

## AIエージェントとして参加する場合

- Claude Code: リポジトリ直下の `CLAUDE.md` を読むこと（自動で読まれます）
- Codex: リポジトリ直下の `AGENTS.md` を読むこと（自動で読まれます）
- 人間と同じフロー（ブランチ→PR→CI→マージ）に従うこと。mainへの直接pushは人間同様ブロックされます

## 🎭 自分のキャラクターを作る（メインの参加方法）

**5分で参戦できます。** プログラミング不要、必要なのはMarkdown1枚:

```bash
mkdir -p characters/<あなたのキャラ名>/voice
# 1. persona.md を書く（口調・性格・口癖・サンプル台詞）
# 2. config.json を書く（最小例↓）
```

```json
{ "name": "<キャラ名>", "display_name": "表示名",
  "voice": { "engine": "voicevox", "speaker": 8, "fallback_speaker": 8 } }
```

```bash
python src/minato_talk.py --character <キャラ名>   # 動作確認
git switch -c feat/<キャラ名>                       # ブランチ → PR → CI緑 → 自分でマージOK
```

こだわりたい人の追加オプション（すべて任意）:
- **LoRA学習**でより強い人格再現（`finetune_lora.py`参照。GPUが無ければGoogle Colab無料枠で可）
- **自分の声モデル**（Style-Bert-VITS2等）を `voice/` に配置 → 自分の声で喋る（後述の注意必読）

### 領域ルール（サーバー側で強制されます — 破りたくても破れません）

| 領域 | 誰が触れるか | 強制手段 |
|---|---|---|
| `characters/<自分のキャラ>/` | あなた（PR→CI緑→**自分でマージ可、承認不要**） | repo-guard CI |
| 他人のキャラディレクトリ | 触れない（1PR=1キャラ厳守） | repo-guard CI |
| コア（`src/` `.github/` `scripts/` 等） | リポジトリオーナーのみ。提案はIssueで | repo-guard CI（改ざん不能なpull_request_target方式） |
| `characters/*/voice/` へのコミット | 全員禁止（声は生体情報） | .gitignore + pack-lint CI |

### 声モデルの絶対ルール

1. **クローンしてよいのは自分自身の声だけ**。他人・有名人の声の学習は禁止（肖像権・パブリシティ権侵害のリスク）
2. 声モデルは**絶対にコミットしない**（CIが物理的にブロックしますが、フォーク先では自衛してください）
3. Google Colabで声学習する場合、**録音データをGoogleに渡すことになる**点は理解した上で使ってください

## テスト

PRを出す前にローカルで最低限:

```bash
ruff check src/                          # lint
python src/api.py &                     # APIが起動するか
curl -sf http://localhost:8080/health    # healthが返るか
```

CIでは実際にVOICEVOXコンテナ＋LLM推論を含むエンドツーエンドテストが走ります（約3分）。
