from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

from app.exceptions import OperationError


class Operation(ABC):
    """Base class: every operation takes exactly two numbers."""
    description: str = "Custom operation"

    @abstractmethod
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Compute the result for operands a and b."""

    def __str__(self) -> str:
        return self.__class__.__name__
    
def describe(text: str):
    """Class decorator that attaches help text to an Operation subclass."""

    def decorator(operation_class: type[Operation]) -> type[Operation]:
        """Attach the help text to the operation class and return it."""
        operation_class.description = text
        return operation_class

    return decorator

@describe("Add two numbers")   
class Addition(Operation):
    """Adds two numbers."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a + b."""
        return a + b

@describe("Subtract the second number from the first")
class Subtraction(Operation):
    """Subtracts the second number from the first."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a - b."""
        return a - b

@describe("Multiply two numbers") 
class Multiplication(Operation):
    """Multiplies two numbers."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a * b."""
        return a * b

@describe("Divide the first number by the second") 
class Division(Operation):
    """Divides the first number by the second."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a / b. Raises OperationError on division by zero."""
        if b == 0:
            raise OperationError("Division by zero is not allowed")
        return a / b

@describe("Raise the first number to the power of the second")
class Power(Operation):
    """Raises the first number to the power of the second."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a ** b. Raises OperationError for 0 ** negative or an invalid power."""
        if a == 0 and b < 0:
            raise OperationError("Zero cannot be raised to a negative power")
        try:
            return a ** b
        except InvalidOperation:
            raise OperationError("Invalid power: negative base with non-integer exponent")

@describe("Take the nth root: root <number> <n>")
class Root(Operation):
    """nth root: a is the number, b is the degree n."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return the nth root of a. Raises OperationError for an undefined root."""
        if b == 0:
            raise OperationError("Root degree cannot be zero")
        if a < 0:
            if b != b.to_integral_value() or b % 2 == 0:
                raise OperationError("Even or fractional root of a negative number is undefined")
            return -((-a) ** (Decimal(1) / b))
        return a ** (Decimal(1) / b)

@describe("Remainder of dividing the first number by the second")
class Modulus(Operation):
    """Remainder of dividing the first number by the second."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a % b (sign follows the dividend). Raises OperationError if b is zero."""
        if b == 0:
            raise OperationError("Modulus by zero is not allowed")
        return a % b

@describe("Integer quotient, discarding the fractional part")
class IntegerDivision(Operation):
    """Integer quotient of the first number divided by the second."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return a // b, truncated toward zero. Raises OperationError if b is zero."""
        if b == 0:
            raise OperationError("Integer division by zero is not allowed")
        return a // b

@describe("First number as a percentage of the second")  
class Percentage(Operation):
    """Percentage(a, b) = (a / b) * 100."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return (a / b) * 100. Raises OperationError if b is zero."""
        if b == 0:
            raise OperationError("Percentage with zero denominator is not allowed")
        return (a / b) * 100

@describe("Absolute difference between two numbers") 
class AbsoluteDifference(Operation):
    """Absolute difference between two numbers."""
    def execute(self, a: Decimal, b: Decimal) -> Decimal:
        """Return abs(a - b)."""
        return abs(a - b)


class OperationFactory:
    """Creates Operation instances from REPL command names (Factory pattern)."""

    _operations: dict[str, type[Operation]] = {
        "add": Addition,
        "subtract": Subtraction,
        "multiply": Multiplication,
        "divide": Division,
        "power": Power,
        "root": Root,
        "modulus": Modulus,
        "int_divide": IntegerDivision,
        "percent": Percentage,
        "abs_diff": AbsoluteDifference,
    }

    @classmethod
    def register_operation(cls, name: str, operation_class: type[Operation]) -> None:
        """Register a new operation so the factory (and help menu) pick it up."""
        if not (isinstance(operation_class, type) and issubclass(operation_class, Operation)):
            raise TypeError("Operation class must inherit from Operation")
        cls._operations[name.lower()] = operation_class

    @classmethod
    def create_operation(cls, name: str) -> Operation:
        """Return an instance for the given command name."""
        operation_class = cls._operations.get(name.lower())
        if operation_class is None:
            raise OperationError(f"Unknown operation: '{name}'")
        return operation_class()

    @classmethod
    def available_operations(cls) -> list[str]:
        """Return the names of all registered operations, sorted."""
        return sorted(cls._operations)

    @classmethod
    def describe_operations(cls) -> dict[str, str]:
        """Map each registered operation name to its help text, sorted by name."""
        return {name: cls._operations[name].description for name in cls.available_operations()}