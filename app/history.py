import contextlib
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Optional, Protocol

import pandas as pd

from app.calculation import Calculation
from app.exceptions import CalculatorError, OperationError, ValidationError
from app.logger import Logger


class HistoryObserver(ABC):
    """Observer interface: notified whenever a new calculation is recorded."""

    @abstractmethod
    def update(self, calculation: Calculation) -> None:
        """React to a new calculation."""


class LoggingObserver(HistoryObserver):
    """Writes each calculation (operation, operands, result) to the log file."""

    def __init__(self, logger: Optional[logging.Logger] = None) -> None:
        self._logger = logger or Logger.get()

    def update(self, calculation: Calculation) -> None:
        """Log the calculation's operation, operands, and result."""
        self._logger.info(
            "Calculation performed: operation=%s, operands=(%s, %s), result=%s",
            calculation.operation,
            calculation.operand_a,
            calculation.operand_b,
            calculation.result,
        )


class SupportsSaveHistory(Protocol):
    """Anything that can persist its history; satisfied by Calculator."""

    def save_history(self) -> None:
        """Persist the current history."""


class AutoSaveObserver(HistoryObserver):
    """Saves history after every calculation when auto-save is enabled."""

    def __init__(self, saver: SupportsSaveHistory, enabled: bool = True,
                 logger: Optional[logging.Logger] = None) -> None:
        self._saver = saver
        self._enabled = enabled
        self._logger = logger or Logger.get()

    def update(self, calculation: Calculation) -> None:
        """Save history when auto-save is enabled; failures are logged, not raised."""
        if not self._enabled:
            return
        try:
            self._saver.save_history()
        except (CalculatorError, OSError) as exc:
            # A failed save must not undo or hide a valid calculation.
            self._logger.error("Auto-save failed: %s", exc)
        else:
            self._logger.info("History auto-saved after: %s", calculation)

CSV_COLUMNS = ["operation", "operand_a", "operand_b", "result", "timestamp"]


class HistoryStore:
    """Reads and writes calculation history as CSV using pandas."""

    def __init__(self, path: Path, encoding: str = "utf-8") -> None:
        self._path = Path(path)
        self._encoding = encoding

    @property
    def path(self) -> Path:
        """Location of the CSV file."""
        return self._path

    def save(self, calculations: Iterable[Calculation]) -> None:
        """Write history to CSV. Writes a temp file first so a crash cannot corrupt the old file."""
        frame = pd.DataFrame([c.to_dict() for c in calculations], columns=CSV_COLUMNS)
        temp = self._path.with_name(self._path.name + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(temp, index=False, encoding=self._encoding)
            os.replace(temp, self._path)
        except OSError as exc:
            with contextlib.suppress(OSError):
                temp.unlink()
            raise OperationError(f"Could not save history to '{self._path}': {exc}") from exc

    def load(self) -> tuple[Calculation, ...]:
        """Read history from CSV, raising a clear error for missing or malformed files."""
        if not self._path.exists():
            raise OperationError(f"History file not found: '{self._path}'")
        try:
            # dtype=str keeps "0.10" as text so Decimal precision is never lost to float.
            frame = pd.read_csv(
                self._path, dtype=str, keep_default_na=False, encoding=self._encoding
            ).fillna("")  # short rows are padded with NaN; turn them into "" so they fail validation
        except pd.errors.EmptyDataError:
            raise ValidationError(f"History file is empty: '{self._path}'") from None
        except (pd.errors.ParserError, UnicodeDecodeError) as exc:
            raise ValidationError(f"History file is malformed: '{self._path}' ({exc})") from exc
        except OSError as exc:
            raise OperationError(f"Could not read history file '{self._path}': {exc}") from exc

        missing = [column for column in CSV_COLUMNS if column not in frame.columns]
        if missing:
            raise ValidationError(f"History file is missing columns: {', '.join(missing)}")

        calculations = []
        for line, row in enumerate(frame[CSV_COLUMNS].to_dict("records"), start=2):  # line 1 is the header
            try:
                calculations.append(Calculation.from_dict(row))
            except ValidationError as exc:
                raise ValidationError(f"Row {line}: {exc}") from exc
        return tuple(calculations)