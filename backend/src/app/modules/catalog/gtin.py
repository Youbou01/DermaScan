"""Barcode (GTIN) validation and normalization. Pure functions: no database, no I/O.

Products are stored under their 13-digit form (GTIN-13). A scanner may give us EAN-13,
UPC-A (12 digits) or EAN-8; all of them are the same family of codes and become
13 digits by left-padding with zeros, so one product has exactly one barcode in the database.

Not supported on purpose: GTIN-14 (cartons, not consumer packs) and UPC-E (compressed
UPC-A: an 8-digit UPC-E would be misread as an EAN-8, so it fails the check digit).
"""

import re

from app.modules.catalog.exceptions import InvalidBarcodeError

GTIN13_LENGTH = 13
_ACCEPTED_LENGTHS = (8, 12, 13)
_IGNORED_CHARACTERS = re.compile(r"[\s-]")  # people type "619 1234 ..." or "619-1234-..."


def compute_check_digit(body: str) -> int:
    """GS1 check digit for `body` (every digit except the last).

    Going right to left, digits are weighted 3, 1, 3, 1...; the check digit tops the
    weighted sum up to the next multiple of 10.
    """
    total = sum(
        int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(body))
    )
    return (10 - total % 10) % 10


def normalize_gtin(raw: str) -> str:
    """Return `raw` as a validated GTIN-13, or raise `InvalidBarcodeError`.

    >>> normalize_gtin("036000291452")  # UPC-A
    '0036000291452'
    """
    code = _IGNORED_CHARACTERS.sub("", raw)
    if not code:
        raise InvalidBarcodeError("The barcode is empty.")
    # isascii() matters: str.isdigit() also accepts digits such as "²" or Arabic-Indic numerals.
    if not (code.isascii() and code.isdigit()):
        raise InvalidBarcodeError("The barcode must contain digits only.")
    if len(code) not in _ACCEPTED_LENGTHS:
        raise InvalidBarcodeError("The barcode must have 8, 12 or 13 digits.")
    if compute_check_digit(code[:-1]) != int(code[-1]):
        raise InvalidBarcodeError("The barcode's check digit is wrong (misread or mistyped?).")
    return code.zfill(GTIN13_LENGTH)
