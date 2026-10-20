from decimal import Decimal
from pathlib import Path

import pytest

from app import calculator_config
from app.calculator_config import CalculatorConfig
from app.exceptions import ConfigurationError


def test_defaults_when_nothing_provided():
    cfg = CalculatorConfig.from_env({})
    assert cfg.log_dir == Path("logs")
    assert cfg.history_dir == Path("history")
    assert cfg.log_file == Path("logs") / "calculator.log"
    assert cfg.history_file == Path("history") / "calculator_history.csv"
    assert cfg.max_history_size == 100
    assert cfg.auto_save is True
    assert cfg.precision == 10
    assert cfg.max_input_value == Decimal("1000000")
    assert cfg.default_encoding == "utf-8"


def test_valid_overrides_are_applied():
    cfg = CalculatorConfig.from_env({
        "CALCULATOR_LOG_DIR": "mylogs",
        "CALCULATOR_HISTORY_DIR": "myhist",
        "CALCULATOR_LOG_FILE": "app.log",
        "CALCULATOR_HISTORY_FILE": "h.csv",
        "CALCULATOR_MAX_HISTORY_SIZE": "5",
        "CALCULATOR_AUTO_SAVE": "false",
        "CALCULATOR_PRECISION": "2",
        "CALCULATOR_MAX_INPUT_VALUE": "99.5",
        "CALCULATOR_DEFAULT_ENCODING": "latin-1",
    })
    assert cfg.log_file == Path("mylogs") / "app.log"
    assert cfg.history_file == Path("myhist") / "h.csv"
    assert cfg.max_history_size == 5
    assert cfg.auto_save is False
    assert cfg.precision == 2
    assert cfg.max_input_value == Decimal("99.5")
    assert cfg.default_encoding == "latin-1"


@pytest.mark.parametrize("value", ["", "   "])
def test_blank_values_fall_back_to_default(value):
    assert CalculatorConfig.from_env({"CALCULATOR_PRECISION": value}).precision == 10


@pytest.mark.parametrize("raw, expected", [("true", True), ("TRUE", True), ("False", False)])
def test_auto_save_is_case_insensitive(raw, expected):
    assert CalculatorConfig.from_env({"CALCULATOR_AUTO_SAVE": raw}).auto_save is expected


@pytest.mark.parametrize("key, raw", [
    ("CALCULATOR_PRECISION", "abc"),
    ("CALCULATOR_PRECISION", "2.5"),
    ("CALCULATOR_PRECISION", "-1"),
    ("CALCULATOR_PRECISION", "29"),
    ("CALCULATOR_MAX_HISTORY_SIZE", "0"),
    ("CALCULATOR_MAX_HISTORY_SIZE", "-5"),
    ("CALCULATOR_MAX_HISTORY_SIZE", "lots"),
    ("CALCULATOR_MAX_INPUT_VALUE", "abc"),
    ("CALCULATOR_MAX_INPUT_VALUE", "0"),
    ("CALCULATOR_MAX_INPUT_VALUE", "-10"),
    ("CALCULATOR_MAX_INPUT_VALUE", "NaN"),
    ("CALCULATOR_MAX_INPUT_VALUE", "Infinity"),
    ("CALCULATOR_AUTO_SAVE", "maybe"),
    ("CALCULATOR_AUTO_SAVE", "yes"),
    ("CALCULATOR_DEFAULT_ENCODING", "not-a-codec"),
])
def test_invalid_values_raise_and_name_the_key(key, raw):
    with pytest.raises(ConfigurationError, match=key):
        CalculatorConfig.from_env({key: raw})


def test_from_env_reads_os_environ_and_dotenv(monkeypatch):
    called = []
    monkeypatch.setattr(calculator_config, "load_dotenv", lambda: called.append(True))
    monkeypatch.setenv("CALCULATOR_PRECISION", "4")
    assert CalculatorConfig.from_env().precision == 4
    assert called == [True]


def test_ensure_directories_creates_them(tmp_path):
    cfg = CalculatorConfig.from_env({
        "CALCULATOR_LOG_DIR": str(tmp_path / "a" / "logs"),
        "CALCULATOR_HISTORY_DIR": str(tmp_path / "b" / "hist"),
    })
    cfg.ensure_directories()
    assert cfg.log_dir.is_dir() and cfg.history_dir.is_dir()


def test_ensure_directories_failure_raises(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    cfg = CalculatorConfig.from_env({"CALCULATOR_LOG_DIR": str(blocker / "sub")})
    with pytest.raises(ConfigurationError, match="Cannot create directory"):
        cfg.ensure_directories()