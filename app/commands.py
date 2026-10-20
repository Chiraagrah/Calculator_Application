from abc import ABC, abstractmethod

from app.calculator import Calculator
from app.exceptions import ValidationError
from app.logger import Logger
from app.operations import OperationFactory

_REGISTRY: dict[str, type["Command"]] = {}


class Command(ABC):
    """A user request packaged as an object (Command pattern).

    Repl is the invoker, Calculator is the receiver, and parse_command is the
    factory that turns a line of text into the right Command.
    """

    name: str = ""
    description: str = ""

    def __init__(self, calculator: Calculator) -> None:
        self._calc = calculator

    @classmethod
    def build(cls, calculator: Calculator, args: list[str]) -> "Command":
        """Create the command from REPL arguments. Default: no arguments allowed."""
        if args:
            raise ValidationError(f"'{cls.name}' takes no arguments")
        return cls(calculator)

    @abstractmethod
    def execute(self) -> str:
        """Run the command and return the text to show the user."""


def command(name: str, description: str):
    """Class decorator: register a Command under a REPL name with its help text."""

    def decorator(command_class: type[Command]) -> type[Command]:
        if not (isinstance(command_class, type) and issubclass(command_class, Command)):
            raise TypeError("@command can only decorate Command subclasses")
        command_class.name = name
        command_class.description = description
        _REGISTRY[name] = command_class
        return command_class

    return decorator


def registered_commands() -> dict[str, type[Command]]:
    """Copy of the registry in registration order, so callers cannot corrupt it."""
    return dict(_REGISTRY)


class CalculateCommand(Command):
    """Runs one arithmetic operation. Operation names come from OperationFactory."""

    def __init__(self, calculator: Calculator, operation_name: str, raw_a: str, raw_b: str) -> None:
        super().__init__(calculator)
        self.name = operation_name
        self._raw_a = raw_a
        self._raw_b = raw_b

    def execute(self) -> str:
        calculation = self._calc.calculate(self.name, self._raw_a, self._raw_b)
        return f"Result: {format(calculation.result, 'f')}"


@command("history", "Show calculation history")
class HistoryCommand(Command):
    def execute(self) -> str:
        history = self._calc.history
        if not history:
            return "No history yet."
        return "\n".join(f"{index}. {calculation}" for index, calculation in enumerate(history, start=1))


@command("clear", "Clear calculation history")
class ClearCommand(Command):
    def execute(self) -> str:
        self._calc.clear_history()
        return "History cleared."


@command("undo", "Undo the last change to history")
class UndoCommand(Command):
    def execute(self) -> str:
        self._calc.undo()
        return f"Undone. History now has {len(self._calc.history)} entries."


@command("redo", "Redo the last undone change")
class RedoCommand(Command):
    def execute(self) -> str:
        self._calc.redo()
        return f"Redone. History now has {len(self._calc.history)} entries."


@command("save", "Save history to the CSV file")
class SaveCommand(Command):
    def execute(self) -> str:
        self._calc.save_history()
        return "History saved."


@command("load", "Load history from the CSV file (replaces current history)")
class LoadCommand(Command):
    def execute(self) -> str:
        self._calc.load_history()
        return f"History loaded ({len(self._calc.history)} entries)."


@command("help", "Show this help")
class HelpCommand(Command):
    """Builds help from the two registries, so new operations and commands appear automatically."""

    def execute(self) -> str:
        lines = ["Operations (usage: <operation> <a> <b>):"]
        for name, description in OperationFactory.describe_operations().items():
            lines.append(f"  {name.ljust(12)}{description}")
        lines.append("Commands:")
        for name, command_class in registered_commands().items():
            lines.append(f"  {name.ljust(12)}{command_class.description}")
        return "\n".join(lines)


@command("exit", "Exit the calculator")
class ExitCommand(Command):
    def execute(self) -> str:
        return "Goodbye!"


def parse_command(calculator: Calculator, line: str) -> Command:
    """Turn one line of REPL input into a Command, or raise ValidationError."""
    parts = line.split()
    if not parts:
        raise ValidationError("Empty command")
    name, args = parts[0].lower(), parts[1:]

    registered = registered_commands()
    if name in registered:
        return registered[name].build(calculator, args)
    if name in OperationFactory.available_operations():
        if len(args) != 2:
            raise ValidationError(f"Usage: {name} <a> <b>")
        return CalculateCommand(calculator, name, args[0], args[1])

    Logger.get().warning("Unknown command: %s", name)
    raise ValidationError(f"Unknown command '{name}'. Type 'help' to see available commands")