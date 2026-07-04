# minato-voice-chatbot — Claude Code 向けプロジェクト指示

日本語ボイスチャットボット。LoRA微調整した0.5B LLM（ペルソナ「ミナト」）+ VOICEVOX TTS。完全ローカル動作の個人学習プロジェクト。

## 🔒 最重要: PIIゼロ方針（Publicリポジトリ）

- 実在の個人名・ハンドル名・社名・メールアドレスを、コード/データ/コミット/PRに**絶対に入れない**
- コミット前に `git config user.email` が noreply アドレスであることを確認
- `data/train.jsonl` へ追加する学習データも同様（架空の設定のみ可）

## 開発フロー（AIも人間と同じ）

- **mainへ直接pushしない**（ルールセットでブロックされる）。ブランチ → PR → CI green → マージ
- ブランチ名: `feat/*`, `fix/*`, `chore/*`
- コミットメッセージ: 英語・命令形
- 並行作業時は git worktree で分離すること（他の作業者とコンフリクトさせない）

## コマンド

```bash
pip install -r requirements.txt          # 依存インストール
docker compose up voicevox               # TTSエンジン起動（port 50021）
python src/minato_talk.py                # デスクトップ対話モード
python src/api.py                        # ヘッドレスAPI（port 8080）
python data/make_data.py                 # 学習データ再生成
python finetune_lora.py                  # LoRA再学習（GPU推奨、CPUでも可）
ruff check src/                          # lint（CIと同じ）
python architecture/generate_architecture_diagram.py  # 構成図PNG再生成
```

## アーキテクチャ

ユーザー入力 → LLM（Qwen2.5-0.5B + `out/lora/` のLoRAアダプタ）→ VOICEVOX API（`VOICEVOX_URL`, デフォルト `http://127.0.0.1:50021`）→ WAV。
詳細は `architecture/minato_architecture.drawio` と README参照。

## 注意事項

- `src/minato_talk.py` はクロスプラットフォーム必須（winsound等のOS依存モジュール禁止。音声は sounddevice/soundfile）
- torch は requirements.txt では CPU版。CUDA版をrequirementsに入れないこと（ポータビリティ優先）
- モデルの応答品質は19件学習の範囲が限界。訓練外の質問への誤答は既知の制約であり、バグ扱いしない
- 構成を変えたら `architecture/` の図も更新すること
