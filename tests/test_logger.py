import logging
from logging.handlers import RotatingFileHandler

import pytest

from app.calculator_config import CalculatorConfig
from app.logger import LOGGER_NAME, Logger
from app import logger as logger_module


@pytest.fixture
def config(tmp_path):
    return CalculatorConfig.from_env({"CALCULATOR_LOG_DIR": str(tmp_path / "logs")})


@pytest.fixture(autouse=True)
def reset_logger():
    yield
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def read_log(config):
    return config.log_file.read_text(encoding="utf-8")


def test_setup_creates_directory_and_file(config):
    Logger.setup(config)
    Logger.get().info("hello")
    assert config.log_file.exists()
    assert "hello" in read_log(config)


def test_levels_are_recorded(config):
    Logger.setup(config)
    log = Logger.get()
    log.info("a")
    log.warning("b")
    log.error("c")
    content = read_log(config)
    assert "INFO | a" in content
    assert "WARNING | b" in content
    assert "ERROR | c" in content


def test_debug_is_filtered_out(config):
    Logger.setup(config)
    Logger.get().debug("hidden")
    assert "hidden" not in read_log(config)


def test_setup_twice_does_not_duplicate_lines(config):
    Logger.setup(config)
    Logger.setup(config)
    Logger.get().info("once")
    assert read_log(config).count("once") == 1


def test_logger_does_not_propagate_to_console(config):
    assert Logger.setup(config).propagate is False


def test_get_returns_shared_logger(config):
    assert Logger.get() is Logger.setup(config)




def test_setup_uses_a_rotating_handler(config):
    logger = Logger.setup(config)
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], RotatingFileHandler)


def test_log_rotates_and_keeps_only_the_configured_backups(config, monkeypatch):
    monkeypatch.setattr(logger_module, "MAX_LOG_BYTES", 200)
    monkeypatch.setattr(logger_module, "LOG_BACKUP_COUNT", 2)
    Logger.setup(config)
    for i in range(60):
        Logger.get().info("entry %d with some padding text to fill the file", i)
    names = {path.name for path in config.log_file.parent.iterdir()}
    base = config.log_file.name
    assert {base, f"{base}.1", f"{base}.2"} <= names
    assert f"{base}.3" not in names