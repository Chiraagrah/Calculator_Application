import logging
from typing import Callable, Optional

from app.calculator import Calculator
from app.calculator_config import CalculatorConfig
from app.commands import ExitCommand, parse_command
from app.exceptions import CalculatorError, ConfigurationError
from app.history import AutoSaveObserver, LoggingObserver
from app.logger import Logger

PROMPT = "calc> "


class Repl:
    """Read-Eval-Print Loop. Acts as the Command invoker: parse, execute, print.

    Input and output are injected so tests can script a whole session.
    """

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
        try:
            command = parse_command(self._calc, line)
            output = command.execute()
        except CalculatorError as exc:
            self._print(f"Error: {exc}")
            return True
        except Exception:
            # Last line of defence: a bug must never kill the session.
            self._logger.exception("Unexpected error while running '%s'", parts[0].lower())
            self._print("Unexpected error. Details were written to the log.")
            return True
        self._print(output)
        return not isinstance(command, ExitCommand)


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