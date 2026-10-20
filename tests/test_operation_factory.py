import pytest

from app.exceptions import OperationError
from app.operations import (Operation, OperationFactory, Addition, Subtraction,
                            Multiplication, Division, Power, Root, Modulus,
                            IntegerDivision, Percentage, AbsoluteDifference)


@pytest.mark.parametrize("name, expected_class", [
    ("add", Addition),
    ("subtract", Subtraction),
    ("multiply", Multiplication),
    ("divide", Division),
    ("power", Power),
    ("root", Root),
    ("modulus", Modulus),
    ("int_divide", IntegerDivision),
    ("percent", Percentage),
    ("abs_diff", AbsoluteDifference),
])
def test_create_operation(name, expected_class):
    assert isinstance(OperationFactory.create_operation(name), expected_class)


def test_create_operation_is_case_insensitive():
    assert isinstance(OperationFactory.create_operation("ADD"), Addition)


def test_unknown_operation_raises():
    with pytest.raises(OperationError, match="Unknown operation"):
        OperationFactory.create_operation("sqrt")


def test_register_custom_operation():
    class Dummy(Operation):
        def execute(self, a, b):
            return a

    OperationFactory.register_operation("dummy", Dummy)
    try:
        assert isinstance(OperationFactory.create_operation("dummy"), Dummy)
        assert "dummy" in OperationFactory.available_operations()
    finally:
        OperationFactory._operations.pop("dummy")  # keep tests isolated


@pytest.mark.parametrize("bad", [str, int, "not a class", None])
def test_register_invalid_class_raises(bad):
    with pytest.raises(TypeError):
        OperationFactory.register_operation("bad", bad)


def test_available_operations_lists_all_ten():
    assert len(OperationFactory.available_operations()) >= 10