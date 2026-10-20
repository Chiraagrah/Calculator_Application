import codecs
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Mapping, Optional

from dotenv import load_dotenv

from app.exceptions import ConfigurationError

MAX_PRECISION = 28  # Decimal's default context precision; quantizing beyond it raises


def _read(env: Mapping[str, str], key: str, default: str) -> str:
    """Return the stripped env value, or the default if unset or blank."""
    value = env.get(key)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _parse_int(key: str, raw: str, minimum: int, maximum: Optional[int] = None) -> int:
    try:
        value = int(raw)
    except ValueError:
        raise ConfigurationError(f"{key} must be an integer, got '{raw}'") from None
    if value < minimum or (maximum is not None and value > maximum):
        bound = f"between {minimum} and {maximum}" if maximum is not None else f"at least {minimum}"
        raise ConfigurationError(f"{key} must be {bound}, got {value}")
    return value


def _parse_bool(key: str, raw: str) -> bool:
    lowered = raw.lower()
    if lowered not in ("true", "false"):
        raise ConfigurationError(f"{key} must be 'true' or 'false', got '{raw}'")
    return lowered == "true"


def _parse_positive_decimal(key: str, raw: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation:
        raise ConfigurationError(f"{key} must be a number, got '{raw}'") from None
    if not value.is_finite() or value <= 0:
        raise ConfigurationError(f"{key} must be a finite number greater than 0, got '{raw}'")
    return value


def _parse_encoding(key: str, raw: str) -> str:
    try:
        codecs.lookup(raw)
    except LookupError:
        raise ConfigurationError(f"{key} is not a known encoding: '{raw}'") from None
    return raw


@dataclass(frozen=True)
class CalculatorConfig:
    """Validated application settings loaded from environment / .env."""

    log_dir: Path
    history_dir: Path
    log_file: Path
    history_file: Path
    max_history_size: int
    auto_save: bool
    precision: int
    max_input_value: Decimal
    default_encoding: str

    @classmethod
    def from_env(cls, env: Optional[Mapping[str, str]] = None) -> "CalculatorConfig":
        """Load settings. Pass `env` in tests; otherwise reads .env and os.environ."""
        if env is None:
            load_dotenv()
            env = os.environ

        log_dir = Path(_read(env, "CALCULATOR_LOG_DIR", "logs"))
        history_dir = Path(_read(env, "CALCULATOR_HISTORY_DIR", "history"))
        return cls(
            log_dir=log_dir,
            history_dir=history_dir,
            log_file=log_dir / _read(env, "CALCULATOR_LOG_FILE", "calculator.log"),
            history_file=history_dir / _read(env, "CALCULATOR_HISTORY_FILE", "calculator_history.csv"),
            max_history_size=_parse_int(
                "CALCULATOR_MAX_HISTORY_SIZE", _read(env, "CALCULATOR_MAX_HISTORY_SIZE", "100"), 1),
            auto_save=_parse_bool("CALCULATOR_AUTO_SAVE", _read(env, "CALCULATOR_AUTO_SAVE", "true")),
            precision=_parse_int(
                "CALCULATOR_PRECISION", _read(env, "CALCULATOR_PRECISION", "10"), 0, MAX_PRECISION),
            max_input_value=_parse_positive_decimal(
                "CALCULATOR_MAX_INPUT_VALUE", _read(env, "CALCULATOR_MAX_INPUT_VALUE", "1000000")),
            default_encoding=_parse_encoding(
                "CALCULATOR_DEFAULT_ENCODING", _read(env, "CALCULATOR_DEFAULT_ENCODING", "utf-8")),
        )

    def ensure_directories(self) -> None:
        """Create log and history directories. Kept separate so loading has no side effects."""
        for directory in (self.log_dir, self.history_dir):
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise ConfigurationError(f"Cannot create directory '{directory}': {exc}") from exc