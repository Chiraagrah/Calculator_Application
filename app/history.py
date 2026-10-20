import logging
from abc import ABC, abstractmethod
from typing import Optional, Protocol

from app.calculation import Calculation
from app.exceptions import CalculatorError
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
        self._logger.info(
            "Calculation performed: operation=%s, operands=(%s, %s), result=%s",
            calculation.operation,
            calculation.operand_a,
            calculation.operand_b,
            calculation.result,
        )


class SupportsSaveHistory(Protocol):
    def save_history(self) -> None: ...


class AutoSaveObserver(HistoryObserver):
    """Saves history after every calculation when auto-save is enabled."""

    def __init__(self, saver: SupportsSaveHistory, enabled: bool = True,
                 logger: Optional[logging.Logger] = None) -> None:
        self._saver = saver
        self._enabled = enabled
        self._logger = logger or Logger.get()

    def update(self, calculation: Calculation) -> None:
        if not self._enabled:
            return
        try:
            self._saver.save_history()
        except (CalculatorError, OSError) as exc:
            # A failed save must not undo or hide a valid calculation.
            self._logger.error("Auto-save failed: %s", exc)
        else:
            self._logger.info("History auto-saved after: %s", calculation)