"""
LoRA fine-tuning of a small instruction model on data/train.jsonl (chat format).

Robust across recent TRL versions:
  - model passed as a string -> SFTTrainer loads model+tokenizer internally
    (avoids tokenizer/processing_class arg-name churn)
  - chat-format dataset ("messages" column) -> chat template applied automatically
  - sequence-length kwarg omitted (defaults are fine for these short examples)

Output: out/lora  (the LoRA adapter; base weights stay untouched)
"""
import os
# Windows: torch + pyarrow(datasets) clash over OpenMP/native runtimes and segfault
# if torch is imported first. Import datasets BEFORE torch, and allow duplicate OpenMP.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from datasets import load_dataset  # must come before torch on Windows
import torch
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer

# 0.5B fits comfortably in 8GB VRAM during training (1.5B spilled to system RAM
# via Windows CUDA fallback -> ~100x slower). Same learning demo, far faster.
BASE = "Qwen/Qwen2.5-0.5B-Instruct"
OUT = "out/lora"

def main():
    assert torch.cuda.is_available(), "CUDA GPU not available — check the torch install"
    print("GPU:", torch.cuda.get_device_name(0))

    ds = load_dataset("json", data_files="data/train.jsonl", split="train")
    print(f"train examples: {len(ds)}")

    lora = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )

    cfg = SFTConfig(
        output_dir=OUT,
        num_train_epochs=10,          # small dataset -> many passes to learn it
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        warmup_ratio=0.05,
        max_length=256,               # examples are short; keep sequences tight
        logging_steps=1,              # show loss every optimizer step
        disable_tqdm=True,            # print loss lines instead of a buffered bar
        dataloader_num_workers=0,     # Windows: avoid worker-process startup cost
        save_strategy="no",
        bf16=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        report_to="none",
        model_init_kwargs={"torch_dtype": "bfloat16"},
    )

    trainer = SFTTrainer(
        model=BASE,
        args=cfg,
        train_dataset=ds,
        peft_config=lora,
    )
    trainer.train()
    trainer.save_model(OUT)
    print(f"\nLoRA adapter saved -> {OUT}")
    print("次: python chat.py --adapter out\\lora  で訓練後を確認")


if __name__ == "__main__":
    main()
