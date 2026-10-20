from decimal import Decimal
import pytest

from app.exceptions import OperationError
from app.operations import (Operation, Addition, Subtraction, Multiplication, Division, Power, Root, Modulus, IntegerDivision,                            Percentage, AbsoluteDifference)

D = Decimal


def test_operation_is_abstract():
    with pytest.raises(TypeError):
        Operation()


@pytest.mark.parametrize("op, a, b, expected", [
    (Addition(), D(2), D(3), D(5)),
    (Addition(), D(-2), D(3), D(1)),
    (Subtraction(), D(2), D(3), D(-1)),
    (Multiplication(), D(2), D(3), D(6)),
    (Multiplication(), D(0), D(3), D(0)),
    (Division(), D(6), D(3), D(2)),
    (Division(), D(1), D(4), D("0.25")),
    (Power(), D(2), D(3), D(8)),
    (Power(), D(2), D(-2), D("0.25")),
    (Power(), D(5), D(0), D(1)),
    (Modulus(), D(7), D(3), D(1)),
    (Modulus(), D(-7), D(3), D(-1)),   # Decimal keeps the sign of the dividend
    (IntegerDivision(), D(7), D(2), D(3)),
    (IntegerDivision(), D(-7), D(2), D(-3)),  # truncates toward zero
    (Percentage(), D(1), D(4), D(25)),
    (Percentage(), D(50), D(200), D(25)),
    (AbsoluteDifference(), D(3), D(10), D(7)),
    (AbsoluteDifference(), D(10), D(3), D(7)),
])
def test_operations(op, a, b, expected):
    assert op.execute(a, b) == expected


def test_division_by_zero():
    with pytest.raises(OperationError, match="Division by zero"):
        Division().execute(D(1), D(0))

@pytest.mark.parametrize("a, b, expected", [
    (D(9), D(2), D(3)),
    (D(27), D(3), D(3)),
    (D(-27), D(3), D(-3)),
])
def test_root_valid(a, b, expected):
    assert Root().execute(a, b) == pytest.approx(expected)

@pytest.mark.parametrize("op, a, b, message", [
    (Power(), D(0), D(-1), "negative power"),
    (Power(), D(-8), D("0.5"), "non-integer exponent"),
    (Root(), D(9), D(0), "cannot be zero"),
    (Root(), D(-9), D(2), "undefined"),
    (Root(), D(-9), D("0.5"), "undefined"),
    (Modulus(), D(1), D(0), "Modulus by zero"),
    (IntegerDivision(), D(1), D(0), "Integer division by zero"),
    (Percentage(), D(1), D(0), "zero denominator"),
])
def test_advanced_operation_errors(op, a, b, message):
    with pytest.raises(OperationError, match=message):
        op.execute(a, b)

def test_str_returns_class_name():
    assert str(Addition()) == "Addition"