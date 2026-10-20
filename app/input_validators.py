import re
from decimal import Decimal
from typing import Sequence

from app.exceptions import ValidationError

# ASCII digits only: Python's \d and Decimal both accept other Unicode digits.
_NUMBER_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")


def validate_number(raw: str, max_value: Decimal) -> Decimal:
    """Convert raw text to Decimal, or raise ValidationError with a fix-it message."""
    if not isinstance(raw, str) or not raw.strip():
        raise ValidationError("Input cannot be empty")
    text = raw.strip()
    if not _NUMBER_PATTERN.fullmatch(text):
        raise ValidationError(
            f"'{text}' is not a valid number (use digits with an optional sign and decimal point)"
        )
    value = Decimal(text)
    if abs(value) > max_value:
        raise ValidationError(f"{text} exceeds the maximum allowed value of {max_value}")
    return value


def validate_operands(args: Sequence[str], max_value: Decimal) -> tuple[Decimal, Decimal]:
    """Validate exactly two operands from REPL input."""
    if len(args) != 2:
        raise ValidationError(f"Expected exactly 2 numbers, got {len(args)}")
    return validate_number(args[0], max_value), validate_number(args[1], max_value)