import os
import sys
from typing import Mapping, Optional, TextIO

from colorama import Fore, Style

STYLES: dict[str, str] = {
    "success": Fore.GREEN,
    "error": Fore.RED,
    "warning": Fore.YELLOW,
    "info": Fore.CYAN,
    "plain": "",
}


def should_use_color(
    stream: Optional[TextIO] = None, env: Optional[Mapping[str, str]] = None
) -> bool:
    """Color only on a real terminal, and never when NO_COLOR is set (no-color.org)."""
    stream = stream if stream is not None else sys.stdout
    env = os.environ if env is None else env
    if env.get("NO_COLOR"):
        return False
    isatty = getattr(stream, "isatty", None)
    return bool(isatty and isatty())


def colorize(text: str, style: str, enabled: bool) -> str:
    """Wrap text in the style's color codes when enabled; otherwise return it unchanged."""
    if style not in STYLES:  # checked even when disabled, so a typo fails in CI, not on a terminal
        raise ValueError(f"Unknown style '{style}'")
    if not enabled or style == "plain":
        return text
    return f"{STYLES[style]}{text}{Style.RESET_ALL}"