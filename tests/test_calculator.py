from decimal import Decimal

import pytest

from app.calculator import Calculator
from app.exceptions import OperationError, ValidationError
from app.history import HistoryObserver, LoggingObserver

D = Decimal


class Recorder(HistoryObserver):
    def __init__(self):
        self.seen = []

    def update(self, calculation):
        self.seen.append(calculation)


@pytest.fixture
def calc(config, app_logger):
    return Calculator(config)


def add_n(calculator, n):
    for i in range(n):
        calculator.calculate("add", str(i), "1")


def read_log(config):
    return config.log_file.read_text(encoding="utf-8")


# ---- calculations and rounding ----
@pytest.mark.parametrize("name, a, b, expected", [
    ("add", "2", "3", "5"),
    ("subtract", "2", "3", "-1"),
    ("multiply", "2", "3", "6"),
    ("divide", "1", "4", "0.25"),
    ("power", "2", "3", "8"),
    ("root", "27", "3", "3"),
    ("modulus", "7", "3", "1"),
    ("int_divide", "7", "2", "3"),
    ("percent", "1", "4", "25"),
    ("abs_diff", "3", "10", "7"),
])
def test_all_ten_operations_through_calculator(calc, name, a, b, expected):
    calculation = calc.calculate(name, a, b)
    assert calculation.result == D(expected)
    assert calculation.operation == name


def test_result_is_rounded_to_configured_precision(make_config, app_logger):
    calc = Calculator(make_config(CALCULATOR_PRECISION="2"))
    assert calc.calculate("divide", "1", "3").result == D("0.33")


@pytest.mark.parametrize("a, b, expected", [("7", "2", "4"), ("5", "2", "2")])
def test_precision_zero_uses_round_half_even(make_config, app_logger, a, b, expected):
    calc = Calculator(make_config(CALCULATOR_PRECISION="0"))
    assert calc.calculate("divide", a, b).result == D(expected)


def test_trailing_zeros_are_stripped(calc):
    assert str(calc.calculate("percent", "50", "200").result) == "25"
    assert str(calc.calculate("multiply", "2.50", "2").result) == "5"


def test_negative_zero_is_normalised(make_config, app_logger):
    calc = Calculator(make_config(CALCULATOR_PRECISION="2"))
    assert str(calc.calculate("multiply", "-0.001", "0.001").result) == "0"


def test_operation_name_is_normalised(calc):
    assert calc.calculate("  ADD ", "1", "2").operation == "add"


# ---- error handling ----
def test_unknown_operation_rejected(calc):
    with pytest.raises(OperationError, match="Unknown operation"):
        calc.calculate("sqrt", "4", "2")
    assert calc.history == () and not calc.can_undo


def test_invalid_operand_rejected(calc):
    with pytest.raises(ValidationError):
        calc.calculate("add", "abc", "1")
    assert calc.history == () and not calc.can_undo


def test_operation_error_leaves_state_untouched(calc):
    calc.calculate("add", "1", "1")
    with pytest.raises(OperationError, match="Division by zero"):
        calc.calculate("divide", "1", "0")
    assert len(calc.history) == 1
    calc.undo()
    assert calc.history == () and not calc.can_undo


@pytest.mark.parametrize("name, a, b", [
    ("power", "1000", "10"),                                  # 1e30 cannot be quantized
    ("modulus", "1000000", "0.0000000000000000000000000001"),  # quotient exceeds 28 digits
])
def test_unrepresentable_result_raises_operation_error(calc, name, a, b):
    with pytest.raises(OperationError, match="out of range"):
        calc.calculate(name, a, b)
    assert calc.history == ()


def test_rejections_are_logged(calc, config):
    with pytest.raises(ValidationError):
        calc.calculate("add", "abc", "1")
    assert "WARNING | Calculation rejected (add)" in read_log(config)


# ---- history ----
def test_history_records_calculations_in_order(calc):
    first = calc.calculate("add", "1", "2")
    second = calc.calculate("multiply", "3", "4")
    assert calc.history == (first, second)


def test_history_is_an_immutable_tuple(calc):
    assert isinstance(calc.history, tuple)


def test_history_drops_oldest_when_full(make_config, app_logger):
    calc = Calculator(make_config(CALCULATOR_MAX_HISTORY_SIZE="3"))
    add_n(calc, 5)
    assert [c.operand_a for c in calc.history] == [D(2), D(3), D(4)]


# ---- undo / redo / clear ----
def test_undo_then_redo_restores_state(calc):
    first = calc.calculate("add", "1", "1")
    second = calc.calculate("add", "2", "2")
    calc.undo()
    assert calc.history == (first,)
    calc.redo()
    assert calc.history == (first, second)


def test_undo_all_the_way_back(calc):
    add_n(calc, 3)
    for _ in range(3):
        calc.undo()
    assert calc.history == ()
    assert not calc.can_undo and calc.can_redo


@pytest.mark.parametrize("method, message", [("undo", "Nothing to undo"), ("redo", "Nothing to redo")])
def test_empty_stacks_raise(calc, method, message):
    with pytest.raises(OperationError, match=message):
        getattr(calc, method)()


def test_new_calculation_clears_redo_stack(calc):
    add_n(calc, 2)
    calc.undo()
    assert calc.can_redo
    calc.calculate("add", "9", "9")
    assert not calc.can_redo
    with pytest.raises(OperationError, match="Nothing to redo"):
        calc.redo()


def test_clear_history_is_undoable(calc):
    add_n(calc, 2)
    before = calc.history
    calc.clear_history()
    assert calc.history == ()
    calc.undo()
    assert calc.history == before


def test_clear_on_empty_history_is_a_noop(calc):
    calc.clear_history()
    assert not calc.can_undo


def test_undo_stack_is_bounded(make_config, app_logger):
    calc = Calculator(make_config(CALCULATOR_MAX_HISTORY_SIZE="3"))
    add_n(calc, 5)
    for _ in range(3):
        calc.undo()
    with pytest.raises(OperationError, match="Nothing to undo"):
        calc.undo()


def test_undo_redo_and_clear_are_logged(calc, config):
    calc.calculate("add", "1", "1")
    calc.undo()
    calc.redo()
    calc.clear_history()
    content = read_log(config)
    assert "Undo performed" in content
    assert "Redo performed" in content
    assert "History cleared" in content


def test_memento_snapshot_is_unaffected_by_later_calculations(calc):
    calc.calculate("add", "1", "1")
    snapshot = calc.create_memento()
    calc.calculate("add", "2", "2")
    assert len(snapshot.history) == 1
    calc.restore(snapshot)
    assert len(calc.history) == 1


# ---- observers ----
def test_observer_is_notified_with_the_calculation(calc):
    recorder = Recorder()
    calc.register_observer(recorder)
    result = calc.calculate("add", "1", "2")
    assert recorder.seen == [result]


def test_all_observers_are_notified(calc):
    first, second = Recorder(), Recorder()
    calc.register_observer(first)
    calc.register_observer(second)
    calc.calculate("add", "1", "2")
    assert len(first.seen) == len(second.seen) == 1


def test_removed_observer_is_not_notified(calc):
    recorder = Recorder()
    calc.register_observer(recorder)
    calc.remove_observer(recorder)
    calc.remove_observer(recorder)  # removing twice is harmless
    calc.calculate("add", "1", "2")
    assert recorder.seen == []


def test_failed_calculation_does_not_notify(calc):
    recorder = Recorder()
    calc.register_observer(recorder)
    with pytest.raises(OperationError):
        calc.calculate("divide", "1", "0")
    assert recorder.seen == []


def test_undo_and_redo_do_not_notify(calc):
    recorder = Recorder()
    calc.register_observer(recorder)
    calc.calculate("add", "1", "2")
    calc.undo()
    calc.redo()
    assert len(recorder.seen) == 1


def test_register_rejects_non_observers(calc):
    with pytest.raises(TypeError):
        calc.register_observer(object())


def test_logging_observer_integration(calc, config):
    calc.register_observer(LoggingObserver())
    calc.calculate("add", "2", "3")
    content = read_log(config)
    assert "operation=add" in content and "result=5" in content