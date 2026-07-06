"""
Render the voice-chat-bot architecture as a PNG, purely from code
(no GUI diagram tool required -> reproducible, CI-friendly, no PII).

Usage: python generate_architecture_diagram.py [output.png]
"""
import sys

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

plt.rcParams["font.family"] = ["Yu Gothic", "MS Gothic", "Meiryo", "sans-serif"]

OUT = sys.argv[1] if len(sys.argv) > 1 else "minato_architecture.png"

COLORS = {
    "io": ("#DAE8FC", "#6C8EBF"),
    "guard": ("#FFE6CC", "#D79B00"),
    "llm_box": ("#FFF2CC", "#D6B656"),
    "base": ("#F5F5F5", "#666666"),
    "lora": ("#D5E8D4", "#82B366"),
    "tts": ("#E1D5E7", "#9673A6"),
    "future": ("none", "#999999"),
}


def box(ax, xy, w, h, text, fill, edge, fontsize=10, dashed=False, boxstyle="round,pad=0.02"):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle=boxstyle,
        linewidth=1.4, edgecolor=edge, facecolor=fill,
        linestyle="dashed" if dashed else "solid",
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, wrap=True)
    return (x + w / 2, y), (x + w / 2, y + h)  # (bottom-center, top-center)


def arrow(ax, start, end, label=""):
    a = FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=15, color="#333333", linewidth=1.2)
    ax.add_patch(a)
    if label:
        mx, my = (start[0] + end[0]) / 2, (start[1] + end[1]) / 2
        ax.text(mx + 0.3, my, label, fontsize=8.5, color="#333333", va="center")


def main():
    fig, ax = plt.subplots(figsize=(11, 8))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 8)
    ax.axis("off")

    ax.text(0.3, 7.72, "voice-chat-bot アーキテクチャ図", fontsize=16, fontweight="bold")
    ax.text(0.3, 7.44, "分身キャラと声で会話する、完全ローカルの音声チャットボット（外部通信なし）", fontsize=10, color="#666666")

    fill, edge = COLORS["io"]
    box(ax, (3.7, 6.75), 2.6, 0.5, "ユーザー\n（マイク音声／テキスト）", fill, edge, fontsize=9)

    fill, edge = COLORS["io"]
    box(ax, (3.55, 5.98), 2.9, 0.44, "音声認識 faster-whisper（サイズはマシン別設定・CPU可）", fill, edge, fontsize=8)

    fill, edge = COLORS["guard"]
    box(ax, (3.55, 5.42), 2.9, 0.44, "PIIフィルター（src/pii_filter.py）正規表現マスク", fill, edge, fontsize=8)

    fill, edge = COLORS["llm_box"]
    box(ax, (3.3, 3.55), 3.4, 1.7, "", fill, edge)
    ax.text(5.0, 5.02, "キャラクターLLM", fontsize=11, fontweight="bold", ha="center")

    fill, edge = COLORS["base"]
    box(ax, (3.45, 4.35), 3.1, 0.55, "ベースモデル（マシン別に選択可）\nデフォルト: Qwen2.5-0.5B / GPU機は大型化可", fill, edge, fontsize=8)

    fill, edge = COLORS["lora"]
    box(ax, (3.45, 3.68), 3.1, 0.55, "人格カード（persona.md）＋LoRA（任意・ベース一致時のみ）", fill, edge, fontsize=8)

    fill, edge = COLORS["lora"]
    box(ax, (0.4, 3.9), 2.5, 1.2,
        "characters/<name>/\nキャラパック（1人1ディレクトリ）\npersona.md＋LoRA(任意)\n＋声設定（voiceは非コミット）",
        fill, edge, fontsize=8)
    arrow(ax, (2.9, 4.5), (3.3, 4.5), "")

    fill, edge = COLORS["tts"]
    box(ax, (3.3, 2.35), 3.4, 0.95, "音声合成（エンジン差し替え式）\nVOICEVOXデフォルト／SBV2等はPhase 4", fill, edge, fontsize=9)

    fill, edge = COLORS["io"]
    box(ax, (3.7, 1.15), 2.6, 0.7, "音声出力\n（ブラウザ再生／スピーカー）", fill, edge, fontsize=9)

    arrow(ax, (5.0, 6.75), (5.0, 6.42), "① 音声／テキスト入力")
    arrow(ax, (5.0, 5.98), (5.0, 5.86), "")
    arrow(ax, (5.0, 5.42), (5.0, 5.25), "①' マスク済みテキスト")
    arrow(ax, (5.0, 3.55), (5.0, 3.30), "② 応答を生成（記憶10ターン）")
    arrow(ax, (5.0, 2.35), (5.0, 1.85), "③ 合成（wav）")

    fill, edge = COLORS["future"]
    box(ax, (7.6, 4.0), 3.0, 2.0, "", fill, edge, dashed=True)
    ax.text(9.1, 5.75, "拡張予定", fontsize=10, fontweight="bold", ha="center")
    for i, item in enumerate([
        "デュエットモード（Phase 3）",
        "本人声クローン SBV2等（Phase 4）",
        "通話連携（将来）",
        "マルチデバイス対応（将来）",
    ]):
        ax.text(7.75, 5.35 - i * 0.4, f"・{item}", fontsize=8.5, va="center")

    ax.text(0.3, 0.3, "※完全ローカル動作。外部インターネット通信なし。個人の学習用プロジェクト。",
            fontsize=8, color="#999999")

    plt.tight_layout()
    plt.savefig(OUT, dpi=160, bbox_inches="tight")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
