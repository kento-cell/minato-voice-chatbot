"""
Repository PII scanner — used by both pre-commit (changed files) and CI (--all).

Two detection layers:
  1. Generic structured-PII patterns (real emails, JP phone numbers, long digit
     runs). Known-safe addresses (noreply / example.com) are allowlisted.
  2. A personal-name denylist that is deliberately NOT stored in this public
     repo (that would itself leak the PII). Sources, in priority order:
       - env var PII_DENYLIST   (comma-separated terms; set as a GitHub Actions
         secret so it is available in CI but never visible in the repo/logs)
       - .pii-denylist.txt      (one term per line; gitignored, each
         contributor keeps their own local copy)

Findings are reported as  path:line  [label]  only — the matched text itself
is never printed, so the scanner cannot leak what it finds.

Exit code: 0 = clean, 1 = findings (blocks commit / fails CI).
"""
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Files the scanner must not scan: its own sources / tests contain pattern
# examples by necessity, and model artifacts are binary.
EXCLUDE_PREFIXES = ("out/", "tests/", ".git/")
EXCLUDE_FILES = {"scripts/check_pii.py", "src/pii_filter.py", ".pre-commit-config.yaml"}
EXCLUDE_SUFFIXES = (".safetensors", ".png", ".bin", ".ico", ".wav", ".pyc")

EMAIL_ALLOWLIST = re.compile(
    r"@(users\.noreply\.github\.com|example\.(com|org|net)|localhost)\b", re.IGNORECASE
)

# Digit-boundary lookarounds instead of \b: kanji/kana count as word chars in
# Python's re, so \b silently fails to match at Japanese-text/digit boundaries.
GENERIC_RULES: list[tuple[str, re.Pattern]] = [
    ("email", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("jp-phone", re.compile(r"(?<!\d)0\d{1,3}[-ー‐ ]\d{1,4}[-ー‐ ]\d{4}(?!\d)")),
    ("long-digit-run", re.compile(r"(?<!\d)\d{4}[ -]\d{4}[ -]\d{4}(?:[ -]\d{4})?(?!\d)")),
]


def load_denylist() -> list[str]:
    terms: list[str] = []
    env = os.environ.get("PII_DENYLIST", "")
    terms += [t.strip() for t in env.replace("\n", ",").split(",") if t.strip()]
    local = os.path.join(REPO_ROOT, ".pii-denylist.txt")
    if os.path.exists(local):
        with open(local, encoding="utf-8") as f:
            terms += [line.strip() for line in f if line.strip() and not line.startswith("#")]
    return terms


def iter_target_files(args: list[str]) -> list[str]:
    if "--all" in args:
        out = subprocess.run(
            ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT, check=True
        ).stdout
        files = out.splitlines()
    else:
        files = args
    result = []
    for f in files:
        rel = os.path.relpath(f, REPO_ROOT) if os.path.isabs(f) else f
        rel = rel.replace("\\", "/")
        if rel.startswith(EXCLUDE_PREFIXES) or rel in EXCLUDE_FILES or rel.endswith(EXCLUDE_SUFFIXES):
            continue
        result.append(rel)
    return result


def scan_file(rel_path: str, denylist: list[str]) -> list[str]:
    findings = []
    path = os.path.join(REPO_ROOT, rel_path)
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except (OSError, UnicodeError):
        return findings
    lowered_terms = [t.lower() for t in denylist]
    for i, line in enumerate(lines, 1):
        for label, pattern in GENERIC_RULES:
            for m in pattern.finditer(line):
                if label == "email" and EMAIL_ALLOWLIST.search(m.group(0)):
                    continue
                findings.append(f"{rel_path}:{i}  [{label}]")
        low = line.lower()
        for term in lowered_terms:
            if term in low:
                findings.append(f"{rel_path}:{i}  [denylist]")
    return findings


def main() -> int:
    args = sys.argv[1:]
    denylist = load_denylist()
    if "--all" in args and not denylist:
        print("note: no denylist loaded (PII_DENYLIST unset and no .pii-denylist.txt) "
              "— running generic patterns only")
    all_findings: list[str] = []
    for rel in iter_target_files(args):
        all_findings += scan_file(rel, denylist)
    if all_findings:
        print("PII scan FAILED — remove or mask the following before committing:")
        for f in sorted(set(all_findings)):
            print("  " + f)
        return 1
    print("PII scan passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
