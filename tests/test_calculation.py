from dataclasses import FrozenInstanceError
from datetime import datetime
from decimal import Decimal

import pytest

from app.calculation import Calculation
from app.exceptions import ValidationError

D = Decimal
TS = datetime(2026, 1, 2, 3, 4, 5)


def make(**overrides):
    fields = dict(operation="add", operand_a=D(2), operand_b=D(3), result=D(5), timestamp=TS)
    fields.update(overrides)
    return Calculation(**fields)


def test_fields_are_stored():
    calc = make()
    assert (calc.operation, calc.operand_a, calc.operand_b, calc.result) == ("add", D(2), D(3), D(5))


def test_timestamp_defaults_to_now():
    calc = Calculation("add", D(1), D(1), D(2))
    assert isinstance(calc.timestamp, datetime)


def test_calculation_is_immutable():
    with pytest.raises(FrozenInstanceError):
        make().result = D(99)


def test_to_dict_uses_strings():
    assert make().to_dict() == {
        "operation": "add",
        "operand_a": "2",
        "operand_b": "3",
        "result": "5",
        "timestamp": "2026-01-02T03:04:05",
    }


@pytest.mark.parametrize("calc", [
    make(),
    make(operation="divide", operand_a=D(1), operand_b=D(3), result=D("0.3333333333")),
    make(operation="subtract", operand_a=D(-2), operand_b=D("0.5"), result=D("-2.5")),
])
def test_round_trip(calc):
    assert Calculation.from_dict(calc.to_dict()) == calc


@pytest.mark.parametrize("bad", [
    {},                                                    # missing everything
    {"operation": "add", "operand_a": "2", "operand_b": "3", "result": "5"},   # no timestamp
    {"operation": "add", "operand_a": "abc", "operand_b": "3", "result": "5",
     "timestamp": "2026-01-02T03:04:05"},                  # bad decimal
    {"operation": "add", "operand_a": "2", "operand_b": "3", "result": "5",
     "timestamp": "not-a-date"},                           # bad timestamp
])
def test_from_dict_rejects_malformed(bad):
    with pytest.raises(ValidationError, match="Malformed"):
        Calculation.from_dict(bad)


def test_str_format():
    assert str(make()) == "add(2, 3) = 5"