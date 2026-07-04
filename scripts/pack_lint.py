"""
Structure lint for character packs — enforced as a required CI check.

Rules (each maps to a promise in CONTRIBUTING.md):
  1. every characters/<name>/ has persona.md (non-empty) and a valid config.json
     whose "name" matches the directory
  2. voice/ may not contain committed files (voice models are biometric data
     and must stay local; .gitignore alone can be bypassed with `git add -f`,
     this check cannot)
  3. no tracked file over MAX_FILE_MB anywhere in the repo

Exit code: 0 = clean, 1 = violations.
"""
import json
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_DIR = os.path.join(REPO_ROOT, "characters")
SUPPORTED_ENGINES = ("voicevox", "sbv2", "gpt-sovits")
VOICE_ALLOWED = {".gitkeep", "README.md"}
MAX_FILE_MB = 60


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO_ROOT, check=True
    ).stdout
    return out.splitlines()


def main() -> int:
    errors: list[str] = []
    tracked = tracked_files()

    # --- rule 2: committed voice files ---------------------------------
    for f in tracked:
        parts = f.replace("\\", "/").split("/")
        if len(parts) >= 4 and parts[0] == "characters" and parts[2] == "voice":
            if parts[-1] not in VOICE_ALLOWED:
                errors.append(f"[voice-model] {f}: voice/ 配下のファイルはコミット禁止です（声は生体情報）")

    # --- rule 3: oversized files ----------------------------------------
    for f in tracked:
        path = os.path.join(REPO_ROOT, f)
        if os.path.exists(path) and os.path.getsize(path) > MAX_FILE_MB * 1024 * 1024:
            errors.append(f"[size] {f}: {MAX_FILE_MB}MB を超えています")

    # --- rule 1: pack structure -----------------------------------------
    if os.path.isdir(CHARACTERS_DIR):
        for name in sorted(os.listdir(CHARACTERS_DIR)):
            pack = os.path.join(CHARACTERS_DIR, name)
            if not os.path.isdir(pack):
                continue
            persona = os.path.join(pack, "persona.md")
            config = os.path.join(pack, "config.json")
            if not os.path.exists(persona) or os.path.getsize(persona) == 0:
                errors.append(f"[pack] characters/{name}: persona.md がない/空です")
            if not os.path.exists(config):
                errors.append(f"[pack] characters/{name}: config.json がありません")
                continue
            try:
                with open(config, encoding="utf-8") as fp:
                    cfg = json.load(fp)
            except json.JSONDecodeError as e:
                errors.append(f"[pack] characters/{name}: config.json がJSONとして不正 ({e})")
                continue
            if cfg.get("name") != name:
                errors.append(f"[pack] characters/{name}: config.json の name がディレクトリ名と不一致")
            engine = (cfg.get("voice") or {}).get("engine", "voicevox")
            if engine not in SUPPORTED_ENGINES:
                errors.append(f"[pack] characters/{name}: 未対応の voice.engine '{engine}'")

    if errors:
        print("pack-lint FAILED:")
        for e in errors:
            print("  " + e)
        return 1
    print("pack-lint passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
