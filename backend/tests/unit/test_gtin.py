import pytest

from app.modules.catalog.exceptions import InvalidBarcodeError
from app.modules.catalog.gtin import compute_check_digit, normalize_gtin

# "4006381333931" written with full-width digits (U+FF10..U+FF19), as some keyboards produce.
FULLWIDTH_DIGITS = "".join(chr(0xFF10 + int(digit)) for digit in "4006381333931")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("4006381333931", "4006381333931"),  # EAN-13 stays as is
        ("3017620422003", "3017620422003"),
        ("036000291452", "0036000291452"),  # UPC-A (12) gets one leading zero
        ("73513537", "0000073513537"),  # EAN-8 gets five leading zeros
        ("0036000291452", "0036000291452"),  # already padded: unchanged (idempotent)
        ("  4006381333931\n", "4006381333931"),  # surrounding whitespace
        ("4006 3813 33931", "4006381333931"),  # spaces typed by a human
        ("4006-3813-33931", "4006381333931"),  # hyphens typed by a human
    ],
)
def test_valid_codes_become_gtin13(raw: str, expected: str) -> None:
    assert normalize_gtin(raw) == expected


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("", "empty"),
        ("   ", "empty"),
        ("4006381333932", "check digit"),  # last digit off by one
        ("4006381333913", "check digit"),  # two digits swapped
        ("40063813339", "8, 12 or 13"),  # 11 digits
        ("40063813339312", "8, 12 or 13"),  # 14 digits (GTIN-14 not supported)
        ("123", "8, 12 or 13"),
        ("40063813339AB", "digits only"),
        ("4006381333931x", "digits only"),
        (FULLWIDTH_DIGITS, "digits only"),  # looks like digits, is not ASCII
        ("٤٠٠٦٣٨١٣٣٣٩٣١", "digits only"),  # Arabic-Indic digits: rejected, not silently accepted
        ("4006381333931; DROP TABLE product", "digits only"),
    ],
)
def test_invalid_codes_are_rejected_with_a_reason(raw: str, reason: str) -> None:
    with pytest.raises(InvalidBarcodeError, match=reason):
        normalize_gtin(raw)


def test_invalid_barcode_error_is_a_422_problem() -> None:
    assert InvalidBarcodeError.status_code == 422
    assert InvalidBarcodeError.code == "invalid-barcode"


@pytest.mark.parametrize(
    ("body", "digit"),
    [("400638133393", 1), ("03600029145", 2), ("7351353", 7), ("619123456789", 7)],
)
def test_check_digit(body: str, digit: int) -> None:
    assert compute_check_digit(body) == digit


def test_a_normalized_code_is_always_accepted_again() -> None:
    once = normalize_gtin("036000291452")
    assert normalize_gtin(once) == once
