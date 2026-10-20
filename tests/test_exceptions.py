import pytest
from app.exceptions import (CalculatorError, ValidationError,
                            OperationError, ConfigurationError)

@pytest.mark.parametrize("exc", [ValidationError, OperationError, ConfigurationError])
def test_exceptions_inherit_from_base(exc):
    with pytest.raises(CalculatorError):
        raise exc("boom")