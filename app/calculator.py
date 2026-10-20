import logging
from collections import deque
from decimal import Decimal, DecimalException
from typing import Optional

from app.calculation import Calculation
from app.calculator_config import CalculatorConfig
from app.calculator_memento import CalculatorMemento
from app.exceptions import CalculatorError, OperationError
from app.history import HistoryObserver, HistoryStore
from app.input_validators import validate_operands
from app.logger import Logger
from app.operations import Operation, OperationFactory


class Calculator:
    """Runs calculations, owns history, supports undo/redo, and notifies observers.

    Acts as the Memento originator (create_memento/restore) and as the caretaker
    (undo/redo stacks). Rounding to CALCULATOR_PRECISION happens here and only here.
    """

    def __init__(self, config: CalculatorConfig, logger: Optional[logging.Logger] = None) -> None:
        self._config = config
        self._logger = logger or Logger.get()
        self._history: tuple[Calculation, ...] = ()
        # Bounded so a long session cannot grow memory without limit.
        self._undo_stack: deque[CalculatorMemento] = deque(maxlen=config.max_history_size)
        self._redo_stack: list[CalculatorMemento] = []
        self._observers: list[HistoryObserver] = []
        self._store = HistoryStore(config.history_file, config.default_encoding)

    # ---- state ----
    @property
    def history(self) -> tuple[Calculation, ...]:
        return self._history

    @property
    def can_undo(self) -> bool:
        return bool(self._undo_stack)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo_stack)

    # ---- observers ----
    def register_observer(self, observer: HistoryObserver) -> None:
        if not isinstance(observer, HistoryObserver):
            raise TypeError("Observer must inherit from HistoryObserver")
        self._observers.append(observer)

    def remove_observer(self, observer: HistoryObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def _notify(self, calculation: Calculation) -> None:
        for observer in list(self._observers):
            observer.update(calculation)

    # ---- calculations ----
    def calculate(self, operation_name: str, raw_a: str, raw_b: str) -> Calculation:
        """Validate input, run the operation, round, record, and notify observers."""
        name = operation_name.strip().lower()
        try:
            operation = OperationFactory.create_operation(name)
            a, b = validate_operands([raw_a, raw_b], self._config.max_input_value)
            result = self._compute(operation, a, b)
        except CalculatorError as exc:
            self._logger.warning("Calculation rejected (%s): %s", name, exc)
            raise

        calculation = Calculation(name, a, b, result)
        self._remember_current_state()
        self._history = (self._history + (calculation,))[-self._config.max_history_size:]
        self._notify(calculation)
        return calculation

    def _compute(self, operation: Operation, a: Decimal, b: Decimal) -> Decimal:
        try:
            return self._round(operation.execute(a, b))
        except DecimalException as exc:
            raise OperationError(
                "Result is out of range or cannot be represented at the configured precision"
            ) from exc

    def _round(self, value: Decimal) -> Decimal:
        """Round to CALCULATOR_PRECISION places, then drop trailing zeros and negative zero."""
        rounded = value.quantize(Decimal(1).scaleb(-self._config.precision))
        text = format(rounded, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        cleaned = Decimal(text)
        return Decimal(0) if cleaned == 0 else cleaned

    # ---- memento ----
    def create_memento(self) -> CalculatorMemento:
        return CalculatorMemento(history=self._history)

    def restore(self, memento: CalculatorMemento) -> None:
        self._history = memento.history

    def _remember_current_state(self) -> None:
        self._undo_stack.append(self.create_memento())
        self._redo_stack.clear()

    # ---- undo / redo / clear ----
    def undo(self) -> None:
        if not self._undo_stack:
            self._logger.warning("Undo requested with nothing to undo")
            raise OperationError("Nothing to undo")
        self._redo_stack.append(self.create_memento())
        self.restore(self._undo_stack.pop())
        self._logger.info("Undo performed; history size is now %d", len(self._history))

    def redo(self) -> None:
        if not self._redo_stack:
            self._logger.warning("Redo requested with nothing to redo")
            raise OperationError("Nothing to redo")
        self._undo_stack.append(self.create_memento())
        self.restore(self._redo_stack.pop())
        self._logger.info("Redo performed; history size is now %d", len(self._history))

    def clear_history(self) -> None:
        if not self._history:
            return
        self._remember_current_state()
        self._history = ()
        self._logger.info("History cleared")

        # ---- persistence ----
    def save_history(self) -> None:
        """Write history to the configured CSV file."""
        try:
            self._store.save(self._history)
        except CalculatorError as exc:
            self._logger.error("Save failed: %s", exc)
            raise
        self._logger.info("History saved to %s (%d entries)", self._store.path, len(self._history))

    def load_history(self) -> None:
        """Replace history with the CSV contents. Undoable; a failed load changes nothing."""
        try:
            loaded = self._store.load()[-self._config.max_history_size:]
        except CalculatorError as exc:
            self._logger.error("Load failed: %s", exc)
            raise
        self._remember_current_state()  # only after a successful read, so failures never touch undo
        self._history = loaded
        self._logger.info("History loaded from %s (%d entries)", self._store.path, len(loaded))