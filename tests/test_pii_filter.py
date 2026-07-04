import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from pii_filter import mask_pii  # noqa: E402


def test_email_masked():
    masked, found = mask_pii("連絡先は taro@example.com です")
    assert "taro@example.com" not in masked
    assert "[メールアドレス]" in masked
    assert "メールアドレス" in found


def test_phone_masked():
    masked, found = mask_pii("電話は090-1234-5678にください")
    assert "090-1234-5678" not in masked
    assert "[電話番号]" in masked


def test_phone_with_spaces_masked():
    masked, _ = mask_pii("固定は03 1234 5678です")
    assert "1234" not in masked


def test_twelve_digit_number_masked():
    masked, found = mask_pii("番号は 1234 5678 9012 です")
    assert "9012" not in masked
    assert "12桁の番号" in found


def test_card_number_masked_as_card_not_partial():
    masked, found = mask_pii("カードは 4111 1111 1111 1111")
    assert "1111" not in masked
    assert "カード番号" in found


def test_postal_code_masked():
    masked, _ = mask_pii("住所は〒160-0023 東京都新宿区")
    assert "160-0023" not in masked


def test_clean_text_unchanged():
    text = "今日はいい天気ですね。VOICEVOXのポートは50021です。"
    masked, found = mask_pii(text)
    assert masked == text
    assert found == []


def test_version_numbers_not_masked():
    text = "torch 2.6.0 と transformers 5.12.1 を使う"
    masked, _ = mask_pii(text)
    assert masked == text


def test_multiple_pii_types():
    masked, found = mask_pii("a@b.co へ連絡、電話は0312345678")
    assert len(found) == 2
