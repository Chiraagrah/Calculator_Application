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
            return cls(
                operation=str(data["operation"]),
                operand_a=Decimal(str(data["operand_a"])),
                operand_b=Decimal(str(data["operand_b"])),
                result=Decimal(str(data["result"])),
                timestamp=datetime.fromisoformat(str(data["timestamp"])),
            )
        except (KeyError, InvalidOperation, ValueError, TypeError) as exc:
            raise ValidationError(f"Malformed calculation record: {exc!r}") from exc

    def __str__(self) -> str:
        return f"{self.operation}({self.operand_a}, {self.operand_b}) = {self.result}"