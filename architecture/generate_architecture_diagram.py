"""
Render the ミナト voice-chatbot architecture as a PNG, purely from code
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

    ax.text(0.3, 7.7, "音声AIチャットボット「ミナト」アーキテクチャ図", fontsize=16, fontweight="bold")
    ax.text(0.3, 7.4, "個人学習プロジェクト（完全ローカル動作・外部通信なし）", fontsize=10, color="#666666")

    fill, edge = COLORS["io"]
    _, user_bottom = box(ax, (3.7, 6.55), 2.6, 0.6, "ユーザー\n（テキスト入力）", fill, edge)

    fill, edge = COLORS["guard"]
    box(ax, (3.55, 5.78), 2.9, 0.5, "PIIフィルター（src/pii_filter.py）\nメール・電話・番号列等を正規表現でマスク", fill, edge, fontsize=8)

    fill, edge = COLORS["llm_box"]
    box(ax, (3.3, 3.8), 3.4, 1.8, "", fill, edge)
    ax.text(5.0, 5.35, "ミナト（キャラクターLLM）", fontsize=11, fontweight="bold", ha="center")

    fill, edge = COLORS["base"]
    box(ax, (3.45, 4.65), 3.1, 0.6, "ベースモデル: Qwen2.5-0.5B-Instruct\n（オープンソース／パラメータは凍結）", fill, edge, fontsize=8.5)

    fill, edge = COLORS["lora"]
    box(ax, (3.45, 3.95), 3.1, 0.6, "LoRAアダプタ\n自作ファインチューニング（約35MB）", fill, edge, fontsize=8.5)

    fill, edge = COLORS["tts"]
    _, tts_top = box(ax, (3.3, 2.4), 3.4, 1.0, "VOICEVOX\nローカル音声合成API（port 50021）\n話者：ずんだもん", fill, edge, fontsize=9)

    fill, edge = COLORS["io"]
    _, out_top = box(ax, (3.7, 1.1), 2.6, 0.7, "音声出力\n（クロスプラットフォーム再生）", fill, edge)

    arrow(ax, user_bottom, (5.0, 6.28), "① テキスト入力")
    arrow(ax, (5.0, 5.78), (5.0, 5.6), "①' マスク済みテキスト")
    arrow(ax, (5.0, 3.8), (5.0, 3.4), "② 応答テキストを生成")
    arrow(ax, (5.0, 2.4), (5.0, 1.8), "③ audio_query → synthesis（wav）")

    fill, edge = COLORS["future"]
    box(ax, (7.6, 3.6), 3.0, 2.6, "", fill, edge, dashed=True)
    ax.text(9.1, 5.9, "拡張予定（未実装）", fontsize=10, fontweight="bold", ha="center")
    for i, item in enumerate([
        "マイク入力（音声認識／STT）",
        "簡易GUI",
        "通話連携（一般的な音声通話API）",
        "会話履歴の保持（マルチターン対応）",
    ]):
        ax.text(7.75, 5.5 - i * 0.4, f"・{item}", fontsize=8.5, va="center")

    ax.text(0.3, 0.3, "※完全ローカル動作。外部インターネット通信なし。個人の学習用プロトタイプ。",
            fontsize=8, color="#999999")

    plt.tight_layout()
    plt.savefig(OUT, dpi=160, bbox_inches="tight")
    print(f"saved -> {OUT}")


if __name__ == "__main__":
    main()
