import logging
from typing import Callable, Optional

from app.calculator import Calculator
from app.calculator_config import CalculatorConfig
from app.exceptions import CalculatorError, ConfigurationError, ValidationError
from app.history import AutoSaveObserver, LoggingObserver
from app.logger import Logger
from app.operations import OperationFactory

PROMPT = "calc> "

OPERATION_HELP = {
    "add": "Add two numbers",
    "subtract": "Subtract the second number from the first",
    "multiply": "Multiply two numbers",
    "divide": "Divide the first number by the second",
    "power": "Raise the first number to the power of the second",
    "root": "Take the nth root: root <number> <n>",
    "modulus": "Remainder of dividing the first number by the second",
    "int_divide": "Integer quotient, discarding the fractional part",
    "percent": "First number as a percentage of the second",
    "abs_diff": "Absolute difference between two numbers",
}

COMMAND_HELP = {
    "history": "Show calculation history",
    "clear": "Clear calculation history",
    "undo": "Undo the last change to history",
    "redo": "Redo the last undone change",
    "save": "Save history to the CSV file",
    "load": "Load history from the CSV file (replaces current history)",
    "help": "Show this help",
    "exit": "Exit the calculator",
}


class Repl:
    """Read-Eval-Print Loop. Input and output are injected so tests can script a session."""

    def __init__(
        self,
        calculator: Calculator,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self._calc = calculator
        self._input = input_fn
        self._print = output_fn
        self._logger = logger or Logger.get()
        self._commands: dict[str, Callable[[], None]] = {
            "history": self._cmd_history,
            "clear": self._cmd_clear,
            "undo": self._cmd_undo,
            "redo": self._cmd_redo,
            "save": self._cmd_save,
            "load": self._cmd_load,
            "help": self._cmd_help,
        }

    def run(self) -> None:
        """Loop until the user exits (or input ends)."""
        self._print("Advanced Calculator. Type 'help' for commands, 'exit' to quit.")
        while True:
            try:
                line = self._input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                self._print("")
                self._print("Goodbye!")
                return
            if not self.handle(line):
                return

    def handle(self, line: str) -> bool:
        """Process one input line. Returns False when the session should end."""
        parts = line.split()
        if not parts:
            return True
        command, args = parts[0].lower(), parts[1:]
        if command == "exit":
            self._print("Goodbye!")
            return False
        try:
            self._dispatch(command, args)
        except CalculatorError as exc:
            self._print(f"Error: {exc}")
        except Exception:
            # Last line of defence: a bug must never kill the session.
            self._logger.exception("Unexpected error while running '%s'", command)
            self._print("Unexpected error. Details were written to the log.")
        return True

    def _dispatch(self, command: str, args: list[str]) -> None:
        if command in self._commands:
            if args:
                raise ValidationError(f"'{command}' takes no arguments")
            self._commands[command]()
        elif command in OperationFactory.available_operations():
            if len(args) != 2:
                raise ValidationError(f"Usage: {command} <a> <b>")
            self._cmd_calculate(command, args[0], args[1])
        else:
            self._logger.warning("Unknown command: %s", command)
            raise ValidationError(f"Unknown command '{command}'. Type 'help' to see available commands")

    # ---- commands ----
    def _cmd_calculate(self, name: str, raw_a: str, raw_b: str) -> None:
        calculation = self._calc.calculate(name, raw_a, raw_b)
        self._print(f"Result: {format(calculation.result, 'f')}")

    def _cmd_history(self) -> None:
        history = self._calc.history
        if not history:
            self._print("No history yet.")
            return
        for index, calculation in enumerate(history, start=1):
            self._print(f"{index}. {calculation}")

    def _cmd_clear(self) -> None:
        self._calc.clear_history()
        self._print("History cleared.")

    def _cmd_undo(self) -> None:
        self._calc.undo()
        self._print(f"Undone. History now has {len(self._calc.history)} entries.")

    def _cmd_redo(self) -> None:
        self._calc.redo()
        self._print(f"Redone. History now has {len(self._calc.history)} entries.")

    def _cmd_save(self) -> None:
        self._calc.save_history()
        self._print("History saved.")

    def _cmd_load(self) -> None:
        self._calc.load_history()
        self._print(f"History loaded ({len(self._calc.history)} entries).")

    def _cmd_help(self) -> None:
        self._print("Operations (usage: <operation> <a> <b>):")
        for name in OperationFactory.available_operations():
            self._print(f"  {name.ljust(12)}{OPERATION_HELP.get(name, 'Custom operation')}")
        self._print("Commands:")
        for name, description in COMMAND_HELP.items():
            self._print(f"  {name.ljust(12)}{description}")


def main(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Application entry point. Returns a process exit code."""
    try:
        config = CalculatorConfig.from_env()
        Logger.setup(config)
    except ConfigurationError as exc:
        output_fn(f"Configuration error: {exc}")
        return 1

    calculator = Calculator(config)
    calculator.register_observer(LoggingObserver())
    calculator.register_observer(AutoSaveObserver(calculator, enabled=config.auto_save))
    Repl(calculator, input_fn, output_fn).run()
    return 0