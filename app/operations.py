from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

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

class Power(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        if a == 0 and b < 0:
            raise OperationError("Zero cannot be raised to a negative power")
        try:
            return a ** b
        except InvalidOperation:
            raise OperationError("Invalid power: negative base with non-integer exponent")


class Root(Operation):
    """nth root: a is the number, b is the degree n."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            raise OperationError("Root degree cannot be zero")
        if a < 0:
            if b != b.to_integral_value() or b % 2 == 0:
                raise OperationError("Even or fractional root of a negative number is undefined")
            return -((-a) ** (Decimal(1) / b))
        return a ** (Decimal(1) / b)


class Modulus(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            raise OperationError("Modulus by zero is not allowed")
        return a % b


class IntegerDivision(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            raise OperationError("Integer division by zero is not allowed")
        return a // b


class Percentage(Operation):
    """Percentage(a, b) = (a / b) * 100."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        if b == 0:
            raise OperationError("Percentage with zero denominator is not allowed")
        return (a / b) * 100


class AbsoluteDifference(Operation):
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        return abs(a - b)