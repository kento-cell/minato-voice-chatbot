"""Regression tests for the repo PII scanner (scripts/check_pii.py).

The scanner is exercised as a subprocess, the same way pre-commit and CI
invoke it. Temp files are created inside the repo root (the scanner resolves
paths relative to it) and removed afterwards.
"""
import os
import subprocess
import sys
import uuid

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(REPO_ROOT, "scripts", "check_pii.py")


def run_scanner_on(content: str) -> int:
    name = f"_scan_test_{uuid.uuid4().hex[:8]}.txt"
    path = os.path.join(REPO_ROOT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    try:
        env = {k: v for k, v in os.environ.items() if k != "PII_DENYLIST"}
        result = subprocess.run(
            [sys.executable, SCRIPT, name],
            capture_output=True, text=True, cwd=REPO_ROOT, env=env,
        )
        return result.returncode
    finally:
        os.remove(path)


def test_separated_phone_detected():
    assert run_scanner_on("tel: 090-1234-5678\n") == 1


def test_unseparated_phone_detected():
    # gap originally reported by automated PR review on PR #2
    assert run_scanner_on("tel: 09012345678\n") == 1


def test_unseparated_landline_detected():
    assert run_scanner_on("tel: 0312345678\n") == 1


def test_unseparated_12digit_detected():
    assert run_scanner_on("id: 123456789012\n") == 1


def test_unseparated_16digit_detected():
    assert run_scanner_on("card: 4111111111111111\n") == 1


def test_real_email_detected():
    assert run_scanner_on("contact: someone@gmail.com\n") == 1


def test_noreply_email_allowed():
    assert run_scanner_on("author: 12345+user@users.noreply.github.com\n") == 0


def test_clean_code_passes():
    assert run_scanner_on(
        "torch==2.6.0\nport = 50021\ntimestamp_ms = 1751600000000\n"
    ) == 0
