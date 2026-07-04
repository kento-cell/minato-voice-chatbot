"""
Shared LLM inference engine for character packs.

The base model is a MACHINE-LOCAL choice (like the STT model size), not a
pack choice: low-spec machines run the 0.5B default, GPU machines can set
MINATO_BASE_MODEL to a bigger instruct model for real conversational quality.

A pack's LoRA adapter only applies when the running base model matches the
base the adapter was trained on (checked against adapter_config.json);
otherwise the persona card alone drives the character.
"""
import json
import os

os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import torch  # noqa: E402
from characters import Character  # noqa: E402
from transformers import AutoModelForCausalLM, AutoTokenizer  # noqa: E402

DEFAULT_BASE_MODEL = "Qwen/Qwen2.5-0.5B-Instruct"


def resolve_base_model() -> str:
    return os.environ.get("MINATO_BASE_MODEL", DEFAULT_BASE_MODEL)


def lora_compatible(character: Character, base_model: str) -> bool:
    """A LoRA adapter is usable only on the base model it was trained on."""
    if not character.lora_path:
        return False
    cfg_path = os.path.join(character.lora_path, "adapter_config.json")
    if not os.path.exists(cfg_path):
        return False
    with open(cfg_path, encoding="utf-8") as f:
        adapter_cfg = json.load(f)
    return adapter_cfg.get("base_model_name_or_path") == base_model


def load_model(character: Character, base_model: str | None = None):
    """Return (tokenizer, model, used_lora)."""
    base = base_model or resolve_base_model()
    tok = AutoTokenizer.from_pretrained(base)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = AutoModelForCausalLM.from_pretrained(
        base, dtype=torch.bfloat16 if device == "cuda" else torch.float32, device_map=device
    )
    used_lora = False
    if lora_compatible(character, base):
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, character.lora_path)
        used_lora = True
    model.eval()
    return tok, model, used_lora


def build_messages(character: Character, history, user_text: str) -> list[dict]:
    msgs = [{"role": "system", "content": character.persona}]
    for u, a in history:
        msgs.append({"role": "user", "content": u})
        msgs.append({"role": "assistant", "content": a})
    msgs.append({"role": "user", "content": user_text})
    return msgs


def generate(tok, model, messages: list[dict], max_new_tokens: int = 120) -> str:
    prompt = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tok(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(
            **inputs, max_new_tokens=max_new_tokens, do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
    return tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()

def finalize_reply(character: Character, reply: str) -> str:
    """Cut the reply after the first occurrence of the character's signature.

    Small models drift or loop AFTER emitting their closing phrase
    ("— ミナトでした。 — ミナトでした。…"); token-level penalties can't fix
    this without corrupting the phrase itself (HF processors also penalize
    prompt/history tokens). Truncating at the signature is loop-proof and
    persona-preserving.
    """
    if character.signature:
        idx = reply.find(character.signature)
        if idx >= 0:
            return reply[: idx + len(character.signature)]
    return reply
