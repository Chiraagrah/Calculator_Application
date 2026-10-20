import logging
from logging.handlers import RotatingFileHandler

from app.calculator_config import CalculatorConfig


LOGGER_NAME = "calculator"
_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
MAX_LOG_BYTES = 1_000_000  # rotate when the log reaches about 1 MB
LOG_BACKUP_COUNT = 3       # keep calculator.log.1 to .3; older files are deleted


class Logger:
    """Central logging setup. Writes to the file named in CalculatorConfig, never the console."""

    @staticmethod
    def setup(config: CalculatorConfig) -> logging.Logger:
        """Configure the application logger. Safe to call more than once."""
        config.ensure_directories()
        logger = logging.getLogger(LOGGER_NAME)
        logger.setLevel(logging.INFO)
        logger.propagate = False  # keep log lines out of the REPL output

        for handler in list(logger.handlers):  # avoid duplicate lines on repeat setup
            logger.removeHandler(handler)
            handler.close()

        handler = RotatingFileHandler(
            config.log_file,
            maxBytes=MAX_LOG_BYTES,
            backupCount=LOG_BACKUP_COUNT,
            encoding=config.default_encoding,
        )
        handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        logger.addHandler(handler)
        return logger

    @staticmethod
    def get() -> logging.Logger:
        """Return the shared application logger."""
        return logging.getLogger(LOGGER_NAME)