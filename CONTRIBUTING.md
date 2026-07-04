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

## テスト

PRを出す前にローカルで最低限:

```bash
ruff check src/                          # lint
python src/api.py &                     # APIが起動するか
curl -sf http://localhost:8080/health    # healthが返るか
```

CIでは実際にVOICEVOXコンテナ＋LLM推論を含むエンドツーエンドテストが走ります（約3分）。
