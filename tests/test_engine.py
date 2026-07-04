import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import characters  # noqa: E402
import engine  # noqa: E402


def test_default_base_model():
    assert engine.resolve_base_model() == engine.DEFAULT_BASE_MODEL


def test_base_model_env_override(monkeypatch):
    monkeypatch.setenv("MINATO_BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
    assert engine.resolve_base_model() == "Qwen/Qwen2.5-7B-Instruct"


def test_lora_compatible_with_matching_base():
    c = characters.load("minato")
    assert engine.lora_compatible(c, engine.DEFAULT_BASE_MODEL) is True


def test_lora_skipped_on_different_base():
    # switching to a bigger base must NOT try to load the 0.5B-trained adapter
    c = characters.load("minato")
    assert engine.lora_compatible(c, "Qwen/Qwen2.5-7B-Instruct") is False


def test_lora_incompatible_without_adapter(tmp_path, monkeypatch):
    pack = tmp_path / "dave"
    pack.mkdir()
    (pack / "persona.md").write_text("# デイブ", encoding="utf-8")
    (pack / "config.json").write_text(
        '{"name": "dave", "voice": {"engine": "voicevox", "speaker": 1}}',
        encoding="utf-8",
    )
    monkeypatch.setattr(characters, "CHARACTERS_DIR", str(tmp_path))
    c = characters.load("dave")
    assert engine.lora_compatible(c, engine.DEFAULT_BASE_MODEL) is False


def test_build_messages_includes_persona_and_history():
    c = characters.load("minato")
    msgs = engine.build_messages(c, [("こんにちは", "やあ！")], "元気？")
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == c.persona
    assert msgs[1] == {"role": "user", "content": "こんにちは"}
    assert msgs[2] == {"role": "assistant", "content": "やあ！"}
    assert msgs[-1] == {"role": "user", "content": "元気？"}


def test_minato_signature_loaded():
    c = characters.load("minato")
    assert c.signature == "— ミナトでした。"


def test_finalize_reply_cuts_after_signature():
    c = characters.load("minato")
    looped = "わたしはミナトです。 — ミナトでした。 — ミナトでした。 — ミナトしました。"
    assert engine.finalize_reply(c, looped) == "わたしはミナトです。 — ミナトでした。"


def test_finalize_reply_cuts_trailing_ramble():
    c = characters.load("minato")
    ramble = "2です。 — ミナトでした。「おはよう」を教えて。"
    assert engine.finalize_reply(c, ramble) == "2です。 — ミナトでした。"


def test_finalize_reply_passthrough_without_signature_match():
    c = characters.load("minato")
    assert engine.finalize_reply(c, "こんにちは") == "こんにちは"
