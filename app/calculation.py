from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from app.exceptions import ValidationError


@dataclass(frozen=True)
class Calculation:
    """Immutable record of one calculation. Holds results, never computes them."""

    operation: str
    operand_a: Decimal
    operand_b: Decimal
    result: Decimal
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, str]:
        """Serialize to plain strings (safe for CSV, no float precision loss)."""
        return {
            "operation": self.operation,
            "operand_a": str(self.operand_a),
            "operand_b": str(self.operand_b),
            "result": str(self.result),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Calculation":
        """Rebuild from a dict, raising ValidationError on malformed data."""
        try:
            values = {key: Decimal(str(data[key])) for key in ("operand_a", "operand_b", "result")}
            if not all(value.is_finite() for value in values.values()):
                raise ValueError("operands and result must be finite numbers")
            return cls(
                operation=str(data["operation"]),
                timestamp=datetime.fromisoformat(str(data["timestamp"])),
                **values,
            )
        except (KeyError, InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError(f"Malformed calculation record: {exc!r}") from exc

    def __str__(self) -> str:
        return f"{self.operation}({self.operand_a}, {self.operand_b}) = {self.result}"