"""
Character pack discovery and loading.

A character pack is a directory under characters/ owned by exactly one
contributor:

    characters/<name>/
    ├── persona.md      (required)  personality card -> system prompt
    ├── config.json     (required)  name / voice engine / optional lora
    ├── lora/           (optional)  LoRA adapter dir for the shared base model
    └── voice/          (optional)  personal voice model — NEVER committed

There is deliberately no central registry file: packs are auto-discovered by
scanning the directory, so parallel contributors never edit a shared file.
"""
import json
import os
from dataclasses import dataclass

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHARACTERS_DIR = os.path.join(REPO_ROOT, "characters")

SUPPORTED_ENGINES = ("voicevox", "sbv2", "gpt-sovits")


class CharacterError(ValueError):
    pass


@dataclass
class Character:
    name: str
    display_name: str
    persona: str
    voice_engine: str
    voice_speaker: int
    lora_path: str | None  # absolute path, or None


def _load_one(pack_dir: str) -> Character:
    name = os.path.basename(pack_dir)
    config_path = os.path.join(pack_dir, "config.json")
    persona_path = os.path.join(pack_dir, "persona.md")

    if not os.path.exists(config_path):
        raise CharacterError(f"{name}: config.json がありません")
    if not os.path.exists(persona_path):
        raise CharacterError(f"{name}: persona.md がありません")

    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)

    if cfg.get("name") != name:
        raise CharacterError(f"{name}: config.json の name はディレクトリ名と一致させてください")

    voice = cfg.get("voice") or {}
    engine = voice.get("engine", "voicevox")
    if engine not in SUPPORTED_ENGINES:
        raise CharacterError(f"{name}: 未対応の voice.engine '{engine}'")

    # Voice-clone engines (sbv2 / gpt-sovits) need a local model that is never
    # committed. If it's absent on this machine, fall back to VOICEVOX.
    speaker = int(voice.get("speaker", voice.get("fallback_speaker", 3)))
    if engine != "voicevox":
        model_dir = os.path.join(pack_dir, "voice")
        has_model = any(
            f not in (".gitkeep", "README.md") for f in os.listdir(model_dir)
        ) if os.path.isdir(model_dir) else False
        if not has_model:
            engine = "voicevox"
            speaker = int(voice.get("fallback_speaker", 3))

    with open(persona_path, encoding="utf-8") as f:
        persona = f.read().strip()
    if not persona:
        raise CharacterError(f"{name}: persona.md が空です")

    lora_path = None
    if cfg.get("lora"):
        candidate = os.path.join(pack_dir, cfg["lora"])
        if os.path.isdir(candidate):
            lora_path = candidate

    return Character(
        name=name,
        display_name=cfg.get("display_name", name),
        persona=persona,
        voice_engine=engine,
        voice_speaker=speaker,
        lora_path=lora_path,
    )


def discover() -> dict[str, Character]:
    """Scan characters/ and return {name: Character} for all valid packs."""
    found: dict[str, Character] = {}
    if not os.path.isdir(CHARACTERS_DIR):
        return found
    for entry in sorted(os.listdir(CHARACTERS_DIR)):
        pack_dir = os.path.join(CHARACTERS_DIR, entry)
        if os.path.isdir(pack_dir):
            found[entry] = _load_one(pack_dir)
    return found


def load(name: str) -> Character:
    pack_dir = os.path.join(CHARACTERS_DIR, name)
    if not os.path.isdir(pack_dir):
        available = ", ".join(sorted(os.listdir(CHARACTERS_DIR))) if os.path.isdir(CHARACTERS_DIR) else "(なし)"
        raise CharacterError(f"キャラクター '{name}' が見つかりません。利用可能: {available}")
    return _load_one(pack_dir)
