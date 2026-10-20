from dataclasses import dataclass

from app.calculation import Calculation


@dataclass(frozen=True)
class CalculatorMemento:
    """Immutable snapshot of the calculator's history (Memento pattern)."""

    history: tuple[Calculation, ...]