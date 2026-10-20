from decimal import Decimal

import pytest

from app.calculator import Calculator
from app.exceptions import OperationError, ValidationError
from app.history import AutoSaveObserver, HistoryObserver

D = Decimal
HEADER = "operation,operand_a,operand_b,result,timestamp"


@pytest.fixture
def calc(config, app_logger):
    return Calculator(config)


def read_log(config):
    return config.log_file.read_text(encoding="utf-8")


class Recorder(HistoryObserver):
    def __init__(self):
        self.seen = []

    def update(self, calculation):
        self.seen.append(calculation)


def test_save_history_writes_csv(calc, config):
    calc.calculate("add", "1", "2")
    calc.save_history()
    lines = config.history_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == HEADER
    assert lines[1].startswith("add,1,2,3,")


def test_save_then_load_round_trip(calc, config):
    calc.calculate("add", "1", "2")
    calc.calculate("divide", "1", "3")
    calc.save_history()
    fresh = Calculator(config)
    fresh.load_history()
    assert fresh.history == calc.history


def test_load_replaces_history_and_is_undoable(make_config, app_logger):
    saver = Calculator(make_config())
    saver.calculate("add", "1", "1")
    saver.calculate("add", "2", "2")
    saver.save_history()

    session = Calculator(make_config())
    mine = session.calculate("multiply", "3", "3")
    session.load_history()
    assert session.history == saver.history

    session.undo()
    assert session.history == (mine,)
    session.redo()
    assert session.history == saver.history


def test_load_of_header_only_file_clears_history_undoably(calc, config):
    first = calc.calculate("add", "1", "1")
    config.history_file.write_text(HEADER + "\n", encoding="utf-8")
    calc.load_history()
    assert calc.history == ()
    calc.undo()
    assert calc.history == (first,)


def test_failed_load_leaves_history_and_undo_untouched(calc):
    first = calc.calculate("add", "1", "1")
    with pytest.raises(OperationError, match="not found"):
        calc.load_history()
    assert calc.history == (first,)
    calc.undo()
    assert calc.history == ()
    assert not calc.can_undo


def test_failed_load_is_logged(calc, config):
    config.history_file.write_text("garbage\n", encoding="utf-8")
    with pytest.raises(ValidationError, match="missing columns"):
        calc.load_history()
    assert "ERROR | Load failed" in read_log(config)


def test_load_keeps_only_most_recent_entries(make_config, app_logger):
    big = Calculator(make_config())
    for i in range(5):
        big.calculate("add", str(i), "1")
    big.save_history()
    small = Calculator(make_config(CALCULATOR_MAX_HISTORY_SIZE="3"))
    small.load_history()
    assert [c.operand_a for c in small.history] == [D(2), D(3), D(4)]


def test_load_does_not_notify_observers(calc):
    calc.calculate("add", "1", "1")
    calc.save_history()
    recorder = Recorder()
    calc.register_observer(recorder)
    calc.load_history()
    assert recorder.seen == []


def test_autosave_observer_persists_each_calculation(calc, config):
    calc.register_observer(AutoSaveObserver(calc))
    calc.calculate("add", "1", "2")
    fresh = Calculator(config)
    fresh.load_history()
    assert len(fresh.history) == 1


def test_save_failure_is_logged_and_raised(make_config, config, app_logger, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    broken = Calculator(make_config(CALCULATOR_HISTORY_DIR=str(blocker / "sub")))
    with pytest.raises(OperationError, match="Could not save"):
        broken.save_history()
    assert "ERROR | Save failed" in read_log(config)


def test_successful_save_and_load_are_logged(calc, config):
    calc.calculate("add", "1", "2")
    calc.save_history()
    calc.load_history()
    content = read_log(config)
    assert "History saved to" in content
    assert "History loaded from" in content