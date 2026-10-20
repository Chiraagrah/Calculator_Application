import pytest

from app.exceptions import OperationError
from app.operations import (Operation, 
                            OperationFactory, 
                            Addition, 
                            Subtraction,
                            Multiplication, 
                            Division, 
                            Power, 
                            Root, 
                            Modulus,
                            IntegerDivision, 
                            Percentage, 
                            AbsoluteDifference, 
                            describe)


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


def test_describe_attaches_text_and_returns_the_class():
    @describe("Return the first operand")
    class First(Operation):
        def execute(self, a, b):
            return a

    assert First.description == "Return the first operand"
    assert First().execute(1, 2) == 1


def test_undecorated_operation_has_default_description():
    class Plain(Operation):
        def execute(self, a, b):
            return a

    assert Plain.description == "Custom operation"


def test_every_builtin_operation_has_a_unique_description():
    descriptions = OperationFactory.describe_operations()
    assert len(descriptions) == 10
    assert "Custom operation" not in descriptions.values()
    assert len(set(descriptions.values())) == len(descriptions)


def test_describe_operations_is_sorted_by_name():
    names = list(OperationFactory.describe_operations())
    assert names == sorted(names)


def test_registered_operation_description_is_picked_up():
    @describe("Return the first operand")
    class First(Operation):
        def execute(self, a, b):
            return a

    OperationFactory.register_operation("first", First)
    try:
        assert OperationFactory.describe_operations()["first"] == "Return the first operand"
    finally:
        OperationFactory._operations.pop("first")