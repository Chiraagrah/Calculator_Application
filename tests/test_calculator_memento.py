from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from app.calculation import Calculation
from app.calculator_memento import CalculatorMemento

CALC = Calculation("add", Decimal(1), Decimal(2), Decimal(3))


def test_memento_stores_history():
    assert CalculatorMemento(history=(CALC,)).history == (CALC,)


def test_memento_is_immutable():
    with pytest.raises(FrozenInstanceError):
        CalculatorMemento(history=()).history = (CALC,)


def test_mementos_with_same_history_are_equal():
    assert CalculatorMemento((CALC,)) == CalculatorMemento((CALC,))