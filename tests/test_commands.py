import pytest

from app import commands
from app.calculator import Calculator
from app.commands import (CalculateCommand, ClearCommand, Command, ExitCommand, HelpCommand,
                          HistoryCommand, LoadCommand, RedoCommand, SaveCommand, UndoCommand,
                          command, parse_command, registered_commands)
from app.exceptions import OperationError, ValidationError
from app.operations import Operation, OperationFactory, describe
from app.colors import STYLES


@pytest.fixture
def calc(config, app_logger):
    return Calculator(config)


@pytest.fixture
def clean_registry():
    """Restore the command registry after tests that register custom commands."""
    snapshot = dict(commands._REGISTRY)
    yield
    commands._REGISTRY.clear()
    commands._REGISTRY.update(snapshot)


def run(calc, line):
    return parse_command(calc, line).execute()


def read_log(config):
    return config.log_file.read_text(encoding="utf-8")


# ---- parsing ----
@pytest.mark.parametrize("line, expected", [
    ("add 1 2", CalculateCommand),
    ("power 2 3", CalculateCommand),
    ("history", HistoryCommand),
    ("clear", ClearCommand),
    ("undo", UndoCommand),
    ("redo", RedoCommand),
    ("save", SaveCommand),
    ("load", LoadCommand),
    ("help", HelpCommand),
    ("exit", ExitCommand),
])
def test_parse_returns_matching_command(calc, line, expected):
    assert type(parse_command(calc, line)) is expected


@pytest.mark.parametrize("line", ["ADD 1 2", "  add   1    2  ", "Add 1 2"])
def test_parsing_ignores_case_and_extra_whitespace(calc, line):
    assert run(calc, line) == "Result: 3"


@pytest.mark.parametrize("line", ["add", "add 1", "add 1 2 3"])
def test_operations_need_exactly_two_arguments(calc, line):
    with pytest.raises(ValidationError, match="Usage: add <a> <b>"):
        parse_command(calc, line)


@pytest.mark.parametrize("line", ["history now", "clear all", "undo twice", "redo 2",
                                  "save x", "load x", "help me", "exit now"])
def test_registered_commands_reject_arguments(calc, line):
    name = line.split()[0]
    with pytest.raises(ValidationError, match=f"'{name}' takes no arguments"):
        parse_command(calc, line)


def test_empty_line_is_rejected(calc):
    with pytest.raises(ValidationError, match="Empty command"):
        parse_command(calc, "   ")


def test_unknown_command_is_rejected_and_logged(calc, config):
    with pytest.raises(ValidationError, match="Unknown command 'frobnicate'"):
        parse_command(calc, "frobnicate")
    assert "WARNING | Unknown command: frobnicate" in read_log(config)


# ---- executing ----
def test_calculate_formats_result(calc):
    assert run(calc, "divide 1 4") == "Result: 0.25"
    assert run(calc, "divide 1 3") == "Result: 0.3333333333"


def test_calculate_errors_propagate(calc):
    with pytest.raises(OperationError, match="Division by zero"):
        run(calc, "divide 1 0")


def test_history_command(calc):
    assert run(calc, "history") == "No history yet."
    run(calc, "add 1 2")
    run(calc, "multiply 3 4")
    assert run(calc, "history") == "1. add(1, 2) = 3\n2. multiply(3, 4) = 12"


def test_clear_undo_redo_commands(calc):
    run(calc, "add 1 2")
    assert run(calc, "clear") == "History cleared."
    assert run(calc, "undo") == "Undone. History now has 1 entries."
    assert run(calc, "redo") == "Redone. History now has 0 entries."


@pytest.mark.parametrize("name, message", [("undo", "Nothing to undo"), ("redo", "Nothing to redo")])
def test_empty_undo_redo_raise(calc, name, message):
    with pytest.raises(OperationError, match=message):
        run(calc, name)


def test_save_and_load_commands(calc):
    run(calc, "add 1 2")
    assert run(calc, "save") == "History saved."
    run(calc, "clear")
    assert run(calc, "load") == "History loaded (1 entries)."


def test_exit_command_says_goodbye(calc):
    assert run(calc, "exit") == "Goodbye!"


def test_commands_are_objects_that_can_run_later(calc):
    queue = [parse_command(calc, line) for line in ("add 1 2", "multiply 3 4", "history")]
    assert calc.history == ()  # nothing runs until execute() is called
    results = [item.execute() for item in queue]
    assert results == ["Result: 3", "Result: 12", "1. add(1, 2) = 3\n2. multiply(3, 4) = 12"]


def test_command_base_class_is_abstract(calc):
    with pytest.raises(TypeError):
        Command(calc)


# ---- registry and decorator ----
def test_registry_order_matches_declaration_order():
    assert list(registered_commands()) == [
        "history", "clear", "undo", "redo", "save", "load", "help", "exit"]


def test_registered_commands_returns_a_copy():
    registered_commands().pop("history")
    assert "history" in registered_commands()


def test_decorator_sets_name_and_description():
    assert HistoryCommand.name == "history"
    assert HistoryCommand.description == "Show calculation history"


def test_decorator_rejects_non_commands(clean_registry):
    with pytest.raises(TypeError):
        command("bad", "x")(object)
    with pytest.raises(TypeError):
        command("bad", "x")("not a class")
    assert "bad" not in registered_commands()


def test_custom_command_is_available_everywhere_without_other_changes(calc, clean_registry):
    @command("ping", "Reply with pong")
    class Ping(Command):
        def execute(self):
            return "pong"

    assert run(calc, "ping") == "pong"
    help_text = run(calc, "help")
    assert "ping" in help_text and "Reply with pong" in help_text
    with pytest.raises(ValidationError, match="'ping' takes no arguments"):
        run(calc, "ping now")


# ---- help ----
def test_help_lists_every_operation_and_command_with_descriptions(calc):
    text = run(calc, "help")
    for name, description in OperationFactory.describe_operations().items():
        assert name in text and description in text
    for name, command_class in registered_commands().items():
        assert name in text and command_class.description in text


def test_help_includes_new_operations_automatically(calc):
    @describe("Return the first number")
    class First(Operation):
        def execute(self, a, b):
            return a

    OperationFactory.register_operation("first", First)
    try:
        assert "Return the first number" in run(calc, "help")
        assert run(calc, "first 5 6") == "Result: 5"
    finally:
        OperationFactory._operations.pop("first")

@pytest.mark.parametrize("command_class, style", [
    (CalculateCommand, "success"),
    (ClearCommand, "success"),
    (UndoCommand, "success"),
    (RedoCommand, "success"),
    (SaveCommand, "success"),
    (LoadCommand, "success"),
    (HistoryCommand, "plain"),
    (HelpCommand, "plain"),
    (ExitCommand, "info"),
])
def test_command_style_hints(command_class, style):
    assert command_class.style == style


def test_all_command_styles_are_valid_styles():
    for command_class in [CalculateCommand, *registered_commands().values()]:
        assert command_class.style in STYLES