from decimal import Decimal
import pytest

from app.exceptions import OperationError
from app.operations import Operation, Addition, Subtraction, Multiplication, Division

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
])
def test_basic_operations(op, a, b, expected):
    assert op.execute(a, b) == expected


def test_division_by_zero():
    with pytest.raises(OperationError, match="Division by zero"):
        Division().execute(D(1), D(0))


def test_str_returns_class_name():
    assert str(Addition()) == "Addition"