import logging
from typing import Callable, Optional

import colorama

from app.calculator import Calculator
from app.calculator_config import CalculatorConfig
from app.colors import colorize, should_use_color
from app.commands import ExitCommand, parse_command
from app.exceptions import CalculatorError, ConfigurationError
from app.history import AutoSaveObserver, LoggingObserver
from app.logger import Logger

PROMPT = "calc> "


class Repl:
    """Read-Eval-Print Loop. Acts as the Command invoker: parse, execute, print.

    Input, output, and color are injected so tests can script a whole session.
    """

    def __init__(
        self,
        calculator: Calculator,
        input_fn: Callable[[str], str] = input,
        output_fn: Callable[[str], None] = print,
        logger: Optional[logging.Logger] = None,
        use_color: bool = False,
    ) -> None:
        self._calc = calculator
        self._input = input_fn
        self._print = output_fn
        self._logger = logger or Logger.get()
        self._color = use_color

    def _emit(self, text: str, style: str) -> None:
        self._print(colorize(text, style, self._color))

    def run(self) -> None:
        """Loop until the user exits (or input ends)."""
        self._emit("Advanced Calculator. Type 'help' for commands, 'exit' to quit.", "info")
        while True:
            try:
                line = self._input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                self._print("")
                self._emit("Goodbye!", "info")
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
            self._emit(f"Error: {exc}", "error")
            return True
        except Exception:
            # Last line of defence: a bug must never kill the session.
            self._logger.exception("Unexpected error while running '%s'", parts[0].lower())
            self._emit("Unexpected error. Details were written to the log.", "error")
            return True
        self._emit(output, command.style)
        return not isinstance(command, ExitCommand)


def main(
    input_fn: Callable[[str], str] = input,
    output_fn: Callable[[str], None] = print,
) -> int:
    """Application entry point. Returns a process exit code."""
    use_color = should_use_color()
    try:
        config = CalculatorConfig.from_env()
        Logger.setup(config)
    except ConfigurationError as exc:
        output_fn(colorize(f"Configuration error: {exc}", "error", use_color))
        return 1

    if use_color:
        colorama.just_fix_windows_console()  # no-op on Linux/macOS, enables ANSI on old Windows consoles
    calculator = Calculator(config)
    calculator.register_observer(LoggingObserver())
    calculator.register_observer(AutoSaveObserver(calculator, enabled=config.auto_save))
    Repl(calculator, input_fn, output_fn, use_color=use_color).run()
    return 0