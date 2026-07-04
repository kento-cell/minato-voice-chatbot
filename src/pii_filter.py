"""
Regex-based PII masking applied to every user input BEFORE it reaches the LLM.

Design notes:
  - Pattern order matters: longer / more specific patterns run first so that a
    16-digit card number is not partially consumed by the 12-digit rule, and a
    phone number is not mislabeled as a postal code.
  - This is a lightweight guard for a hobby project, not a compliance-grade
    redactor: it catches *structured* PII (emails, phone numbers, long digit
    sequences, postal codes). Free-form names cannot be reliably detected by
    regex and are out of scope here (see CONTRIBUTING.md for the repo-level
    denylist that covers that gap at CI time).
"""
import re

# (label, pattern) — evaluated in order, each match replaced with [label].
# NOTE: \b does NOT work as a digit boundary in Japanese text (kanji/kana are
# word characters in Python's re), so digit-boundary lookarounds are used.
_RULES: list[tuple[str, re.Pattern]] = [
    ("メールアドレス", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("カード番号", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),
    ("12桁の番号", re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")),  # マイナンバー等
    ("電話番号", re.compile(r"(?<!\d)0\d{1,3}[-ー‐ ]?\d{1,4}[-ー‐ ]?\d{4}(?!\d)")),
    ("郵便番号", re.compile(r"〒\s?\d{3}[-ー‐]\d{4}|(?<!\d)\d{3}[-ー‐]\d{4}(?!\d)")),
]


def mask_pii(text: str) -> tuple[str, list[str]]:
    """Return (masked_text, list_of_detected_labels).

    The label list is for user feedback ("masked an email address") and never
    contains the matched value itself.
    """
    found: list[str] = []
    for label, pattern in _RULES:
        if pattern.search(text):
            found.append(label)
            text = pattern.sub(f"[{label}]", text)
    return text, found
