from decimal import Decimal

import pytest

from app.exceptions import ValidationError
from app.input_validators import validate_number, validate_operands

D = Decimal
MAX = D("1000000")


@pytest.mark.parametrize("raw, expected", [
    ("5", D(5)),
    ("-5", D(-5)),
    ("+5", D(5)),
    ("3.14", D("3.14")),
    (".5", D("0.5")),
    ("5.", D(5)),
    ("  7  ", D(7)),
    ("0", D(0)),
    ("1000000", D(1000000)),     # boundary is inclusive
    ("-1000000", D(-1000000)),
])
def test_valid_numbers(raw, expected):
    assert validate_number(raw, MAX) == expected


@pytest.mark.parametrize("raw", [
    "abc", "1e3", "1E3", "NaN", "Infinity", "-inf", "1_000", "1,000",
    "--5", "5-", "1.2.3", "0x10", "\u0663",   # last one is an Arabic-Indic digit
])
def test_invalid_format_rejected(raw):
    with pytest.raises(ValidationError, match="not a valid number"):
        validate_number(raw, MAX)


@pytest.mark.parametrize("raw", ["", "   ", None])
def test_empty_input_rejected(raw):
    with pytest.raises(ValidationError, match="empty"):
        validate_number(raw, MAX)


@pytest.mark.parametrize("raw", ["1000000.01", "-1000000.01", "99999999"])
def test_out_of_range_rejected(raw):
    with pytest.raises(ValidationError, match="exceeds"):
        validate_number(raw, MAX)


def test_validate_operands_returns_two_decimals():
    assert validate_operands(["2", "3.5"], MAX) == (D(2), D("3.5"))


@pytest.mark.parametrize("args", [[], ["1"], ["1", "2", "3"]])
def test_wrong_operand_count_rejected(args):
    with pytest.raises(ValidationError, match="exactly 2"):
        validate_operands(args, MAX)


def test_operand_errors_propagate():
    with pytest.raises(ValidationError, match="not a valid number"):
        validate_operands(["1", "x"], MAX)