import logging

import pytest

from app import calculator_config
from app.calculator import Calculator
from app.logger import LOGGER_NAME
from app.operations import Operation, OperationFactory, describe
from app.commands import registered_commands
from app.repl import Repl, main


def make_input(lines):
    """Scripted stdin: yields each line, then behaves like end-of-input."""
    iterator = iter(lines)

    def _input(prompt=""):
        try:
            return next(iterator)
        except StopIteration:
            raise EOFError from None

    return _input


def read_log(config):
    return config.log_file.read_text(encoding="utf-8")


@pytest.fixture
def run(config, app_logger):
    def _run(*lines, calculator=None):
        calculator = calculator or Calculator(config)
        out = []
        Repl(calculator, make_input(lines), out.append).run()
        return "\n".join(out)
    return _run


# ---- session basics ----
def test_welcome_message_is_shown(run):
    assert "Type 'help'" in run("exit")


def test_exit_ends_session_immediately(run):
    output = run("exit", "add 1 2")
    assert "Goodbye!" in output
    assert "Result" not in output


def test_end_of_input_exits_gracefully(run):
    assert "Goodbye!" in run("add 1 2")


def test_ctrl_c_exits_gracefully(config, app_logger):
    def interrupting(prompt=""):
        raise KeyboardInterrupt

    out = []
    Repl(Calculator(config), interrupting, out.append).run()
    assert "Goodbye!" in "\n".join(out)


def test_blank_lines_are_ignored(run):
    output = run("", "   ", "exit")
    assert "Error" not in output


# ---- calculations ----
@pytest.mark.parametrize("command, expected", [
    ("add 2 3", "5"),
    ("subtract 2 3", "-1"),
    ("multiply 2 3", "6"),
    ("divide 1 4", "0.25"),
    ("power 2 3", "8"),
    ("root 27 3", "3"),
    ("modulus 7 3", "1"),
    ("int_divide 7 2", "3"),
    ("percent 1 4", "25"),
    ("abs_diff 3 10", "7"),
])
def test_every_operation_command(run, command, expected):
    assert f"Result: {expected}" in run(command)


@pytest.mark.parametrize("line", ["ADD 1 2", "  add   1    2  ", "Add 1 2"])
def test_commands_are_case_and_whitespace_insensitive(run, line):
    assert "Result: 3" in run(line)


@pytest.mark.parametrize("line", ["add", "add 1", "add 1 2 3"])
def test_wrong_argument_count_shows_usage(run, line):
    assert "Error: Usage: add <a> <b>" in run(line)


def test_invalid_number_shows_error_and_continues(run):
    output = run("add x 1", "add 1 1")
    assert "Error:" in output and "not a valid number" in output
    assert "Result: 2" in output


def test_division_by_zero_shows_error(run):
    assert "Error: Division by zero" in run("divide 1 0")


def test_unknown_command_is_reported_and_logged(run, config):
    output = run("frobnicate")
    assert "Unknown command 'frobnicate'" in output
    assert "WARNING | Unknown command: frobnicate" in read_log(config)


def test_registered_operation_is_available_without_repl_changes(run):
    class First(Operation):
        def execute(self, a, b):
            return a

    OperationFactory.register_operation("first", First)
    try:
        assert "Result: 5" in run("first 5 6")
        assert "first" in run("help")
    finally:
        OperationFactory._operations.pop("first")


# ---- history, undo, redo, clear ----
def test_empty_history(run):
    assert "No history yet." in run("history")


def test_history_lists_calculations_in_order(run):
    output = run("add 1 2", "multiply 3 4", "history")
    assert "1. add(1, 2) = 3" in output
    assert "2. multiply(3, 4) = 12" in output


def test_clear_then_undo_restores_history(run):
    output = run("add 1 2", "clear", "history", "undo", "history")
    assert "History cleared." in output
    assert output.count("No history yet.") == 1
    assert "1. add(1, 2) = 3" in output.split("Undone.")[-1]


def test_undo_and_redo_report_history_size(run):
    output = run("add 1 2", "undo", "redo")
    assert "Undone. History now has 0 entries." in output
    assert "Redone. History now has 1 entries." in output


@pytest.mark.parametrize("command, message", [("undo", "Nothing to undo"), ("redo", "Nothing to redo")])
def test_empty_undo_redo_are_errors_not_crashes(run, command, message):
    assert f"Error: {message}" in run(command)


@pytest.mark.parametrize("line", ["history now", "undo twice", "help me", "clear all"])
def test_no_argument_commands_reject_arguments(run, line):
    assert "takes no arguments" in run(line)


# ---- save / load ----
def test_save_then_load_round_trip(run):
    output = run("add 1 2", "save", "clear", "load", "history")
    assert "History saved." in output
    assert "History loaded (1 entries)." in output
    assert "1. add(1, 2) = 3" in output.split("History loaded")[-1]


def test_load_missing_file_is_an_error(run):
    assert "Error: History file not found" in run("load")


def test_load_is_undoable(run):
    output = run("add 1 2", "save", "add 5 5", "load", "undo", "history")
    tail = output.split("Undone.")[-1]
    assert "1. add(1, 2) = 3" in tail
    assert "2. add(5, 5) = 10" in tail


# ---- help ----
def test_help_lists_every_operation_and_command(run):
    output = run("help")
    for name in OperationFactory.available_operations():
        assert name in output
    for name in registered_commands():
        assert name in output


# ---- robustness ----
def test_unexpected_error_is_logged_and_session_continues(config, app_logger, run, monkeypatch):
    calculator = Calculator(config)

    def boom(*args):
        raise RuntimeError("bug")

    monkeypatch.setattr(calculator, "calculate", boom)
    output = run("add 1 2", "history", calculator=calculator)
    assert "Unexpected error" in output
    assert "No history yet." in output
    assert "Unexpected error while running 'add'" in read_log(config)


# ---- main() ----
@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(calculator_config, "load_dotenv", lambda: None)
    for key in ("CALCULATOR_MAX_HISTORY_SIZE", "CALCULATOR_AUTO_SAVE", "CALCULATOR_PRECISION",
                "CALCULATOR_MAX_INPUT_VALUE", "CALCULATOR_DEFAULT_ENCODING",
                "CALCULATOR_LOG_FILE", "CALCULATOR_HISTORY_FILE"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("CALCULATOR_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("CALCULATOR_HISTORY_DIR", str(tmp_path / "history"))
    yield tmp_path
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def test_main_runs_session_logs_and_autosaves(env):
    out = []
    assert main(make_input(["add 1 2", "exit"]), out.append) == 0
    assert "Result: 3" in "\n".join(out)
    assert (env / "history" / "calculator_history.csv").exists()
    assert "operation=add" in (env / "logs" / "calculator.log").read_text(encoding="utf-8")


def test_main_respects_auto_save_false(env, monkeypatch):
    monkeypatch.setenv("CALCULATOR_AUTO_SAVE", "false")
    assert main(make_input(["add 1 2", "exit"]), lambda line: None) == 0
    assert not (env / "history" / "calculator_history.csv").exists()


def test_main_exits_with_error_on_invalid_config(env, monkeypatch):
    monkeypatch.setenv("CALCULATOR_PRECISION", "abc")
    out = []
    assert main(make_input(["exit"]), out.append) == 1
    assert "Configuration error" in out[0] and "CALCULATOR_PRECISION" in out[0]


def test_main_exits_with_error_when_log_dir_cannot_be_created(env, monkeypatch):
    blocker = env / "file"
    blocker.write_text("x")
    monkeypatch.setenv("CALCULATOR_LOG_DIR", str(blocker / "sub"))
    out = []
    assert main(make_input(["exit"]), out.append) == 1
    assert "Cannot create directory" in out[0]

def test_help_shows_description_of_newly_registered_operation(run):
    @describe("Return the first number")
    class First(Operation):
        def execute(self, a, b):
            return a

    OperationFactory.register_operation("first", First)
    try:
        assert "Return the first number" in run("help")
    finally:
        OperationFactory._operations.pop("first")

def test_exit_rejects_arguments_and_session_continues(run):
    output = run("exit now", "add 1 2")
    assert "'exit' takes no arguments" in output
    assert "Result: 3" in output