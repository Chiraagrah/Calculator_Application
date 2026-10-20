from abc import ABC, abstractmethod
from decimal import Decimal

from app.exceptions import OperationError


class Operation(ABC):
    """Base class: every operation takes exactly two numbers."""

    @abstractmethod
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Compute the result for operands a and b."""

    def __str__(self) -> str:
        return self.__class__.__name__


class Addition(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        return a + b


class Subtraction(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        return a - b


class Multiplication(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        return a * b


class Division(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            raise OperationError("Division by zero is not allowed")
        return a / b