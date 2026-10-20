class CalculatorError(Exception):
    """Base class for all calculator errors."""

class ValidationError(CalculatorError):
    """Raised when user input is invalid."""

class OperationError(CalculatorError):
    """Raised when an operation cannot be performed."""

class ConfigurationError(CalculatorError):
    """Raised when configuration is invalid."""