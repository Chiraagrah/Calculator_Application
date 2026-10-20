import pytest

from app.calculator_config import CalculatorConfig
from app.logger import Logger


@pytest.fixture
def make_config(tmp_path):
    """Factory for configs that write into pytest's temp directory."""
    def _make(**overrides):
        env = {
            "CALCULATOR_LOG_DIR": str(tmp_path / "logs"),
            "CALCULATOR_HISTORY_DIR": str(tmp_path / "history"),
        }
        env.update(overrides)
        return CalculatorConfig.from_env(env)
    return _make


@pytest.fixture
def config(make_config):
    return make_config()


@pytest.fixture
def app_logger(config):
    """Configured file logger, fully torn down after each test."""
    logger = Logger.setup(config)
    yield logger
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()