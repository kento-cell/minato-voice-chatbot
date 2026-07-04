"""
Core-area access gate — the rule that guards all other rules.

Run from the BASE branch's workflow (pull_request_target), so a PR cannot
modify this script or its workflow to bypass it.

Policy:
  - A PR that touches CORE paths is allowed only when its author is the
    repository owner. Everyone else gets an actionable error.
  - A non-core PR must confine its changes to exactly ONE characters/<name>/
    subtree ("stay in your own room") — this is what makes simultaneous
    contributors structurally conflict-free.

Inputs (args/env):
  --files   newline-separated changed file list (stdin if omitted)
  --author  PR author login
  env GITHUB_REPOSITORY_OWNER  repository owner login
"""
import argparse
import os
import sys

CORE_PREFIXES = (
    ".github/",
    ".claude/",
    "scripts/",
    "src/",
    "tests/",
    "data/",
    "architecture/",
)
CORE_FILES = {
    "Dockerfile",
    "docker-compose.yml",
    "requirements.txt",
    "requirements-dev.txt",
    ".pre-commit-config.yaml",
    ".gitignore",
    "finetune_lora.py",
    "README.md",
    "CONTRIBUTING.md",
    "CLAUDE.md",
    "AGENTS.md",
    "LICENSE",
}


def classify(path: str) -> str:
    p = path.replace("\\", "/")
    if p.startswith("characters/"):
        return "characters"
    if p.startswith(CORE_PREFIXES) or p in CORE_FILES:
        return "core"
    return "core"  # default-deny: anything unrecognized counts as core


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--files", default=None, help="newline-separated changed files")
    ap.add_argument("--author", required=True)
    args = ap.parse_args()

    raw = args.files if args.files is not None else sys.stdin.read()
    files = [f.strip() for f in raw.splitlines() if f.strip()]
    owner = os.environ.get("GITHUB_REPOSITORY_OWNER", "")

    if not files:
        print("repo-guard: 変更ファイルなし — pass")
        return 0

    core_touched = [f for f in files if classify(f) == "core"]
    char_touched = [f for f in files if classify(f) == "characters"]

    if core_touched:
        if args.author == owner:
            print(f"repo-guard: コア変更 {len(core_touched)}件 — オーナー({owner})によるものなので許可")
            return 0
        print("repo-guard FAILED: コア領域はオーナーのみ変更できます。")
        print("あなたのPRで変更できるのは characters/<あなたのキャラ名>/ 配下だけです。")
        print("コアに提案がある場合は Issue を立ててください。対象ファイル:")
        for f in core_touched:
            print("  " + f)
        return 1

    # characters-only PR: must stay inside exactly one pack
    packs = {f.split("/")[1] for f in char_touched if len(f.split("/")) >= 2}
    if len(packs) > 1:
        print(f"repo-guard FAILED: 1つのPRで複数のキャラディレクトリ({', '.join(sorted(packs))})を変更しています。")
        print("他人のキャラに触らない・自分のキャラは1PRで1つ、が原則です。")
        return 1

    print(f"repo-guard: characters/{next(iter(packs))}/ のみの変更 — pass")
    return 0


if __name__ == "__main__":
    sys.exit(main())
