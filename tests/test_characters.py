import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pytest  # noqa: E402

import characters  # noqa: E402


def test_discover_finds_minato():
    packs = characters.discover()
    assert "minato" in packs
    c = packs["minato"]
    assert c.display_name == "ミナト"
    assert c.persona  # non-empty persona card
    assert c.voice_engine == "voicevox"
    assert isinstance(c.voice_speaker, int)


def test_minato_has_lora():
    c = characters.load("minato")
    assert c.lora_path is not None
    assert os.path.exists(os.path.join(c.lora_path, "adapter_config.json"))


def test_unknown_character_raises():
    with pytest.raises(characters.CharacterError):
        characters.load("no_such_character")


def test_invalid_pack_rejected(tmp_path, monkeypatch):
    # name mismatch between directory and config.json must fail validation
    pack = tmp_path / "alice"
    pack.mkdir()
    (pack / "persona.md").write_text("# アリス", encoding="utf-8")
    (pack / "config.json").write_text(
        json.dumps({"name": "bob", "voice": {"engine": "voicevox", "speaker": 1}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(characters, "CHARACTERS_DIR", str(tmp_path))
    with pytest.raises(characters.CharacterError):
        characters.load("alice")


def test_voice_clone_engine_falls_back_without_model(tmp_path, monkeypatch):
    # sbv2 configured but no local voice model -> falls back to VOICEVOX
    pack = tmp_path / "carol"
    pack.mkdir()
    (pack / "voice").mkdir()
    (pack / "persona.md").write_text("# キャロル", encoding="utf-8")
    (pack / "config.json").write_text(
        json.dumps({
            "name": "carol",
            "voice": {"engine": "sbv2", "fallback_speaker": 8},
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(characters, "CHARACTERS_DIR", str(tmp_path))
    c = characters.load("carol")
    assert c.voice_engine == "voicevox"
    assert c.voice_speaker == 8
