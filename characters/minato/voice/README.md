# voice/ — 本人声モデル置き場（コミット禁止）

このディレクトリに置いた声モデル（.pth / .safetensors 等）は **絶対にコミットされません**
（.gitignore + CI の pack-lint が二重にブロックします）。

- 声は生体情報です。公開リポジトリに置くと、誰でもあなたの声で任意の文章を喋らせられるようになります
- 声モデルが無い場合は `config.json` の `fallback_speaker`（VOICEVOX話者）が使われます
- クローンしてよいのは **自分自身の声だけ** です（CONTRIBUTING.md 参照）
