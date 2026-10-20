import logging
from decimal import Decimal

import pytest

from app.calculation import Calculation
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError
from app.history import AutoSaveObserver, HistoryObserver, LoggingObserver
from app.logger import LOGGER_NAME, Logger

D = Decimal
CALC = Calculation("add", D(2), D(3), D(5))


@pytest.fixture
def config(tmp_path):
    return CalculatorConfig.from_env({"CALCULATOR_LOG_DIR": str(tmp_path / "logs")})


@pytest.fixture(autouse=True)
def configured_logger(config):
    Logger.setup(config)
    yield
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


class FakeSaver:
    def __init__(self, error=None):
        self.calls = 0
        self.error = error

    def save_history(self):
        self.calls += 1
        if self.error:
            raise self.error


def read_log(config):
    return config.log_file.read_text(encoding="utf-8")


def test_observer_interface_is_abstract():
    with pytest.raises(TypeError):
        HistoryObserver()


def test_logging_observer_records_all_details(config):
    LoggingObserver().update(CALC)
    content = read_log(config)
    assert "INFO" in content
    assert "operation=add" in content
    assert "operands=(2, 3)" in content
    assert "result=5" in content


def test_autosave_calls_saver_when_enabled(config):
    saver = FakeSaver()
    AutoSaveObserver(saver, enabled=True).update(CALC)
    assert saver.calls == 1
    assert "auto-saved" in read_log(config)


def test_autosave_skips_when_disabled():
    saver = FakeSaver()
    AutoSaveObserver(saver, enabled=False).update(CALC)
    assert saver.calls == 0


@pytest.mark.parametrize("error", [OperationError("disk full"), OSError("locked")])
def test_autosave_failure_is_logged_not_raised(config, error):
    saver = FakeSaver(error=error)
    AutoSaveObserver(saver).update(CALC)  # must not raise
    assert "ERROR | Auto-save failed" in read_log(config)


def test_autosave_does_not_swallow_unexpected_errors():
    with pytest.raises(RuntimeError):
        AutoSaveObserver(FakeSaver(error=RuntimeError("bug"))).update(CALC)