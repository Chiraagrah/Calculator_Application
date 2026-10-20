import sys

import pytest
from colorama import Fore, Style

from app.colors import STYLES, colorize, should_use_color


class FakeStream:
    def __init__(self, tty):
        self._tty = tty

    def isatty(self):
        return self._tty


def test_terminal_enables_color():
    assert should_use_color(FakeStream(True), {}) is True


def test_pipe_or_file_disables_color():
    assert should_use_color(FakeStream(False), {}) is False


def test_no_color_env_disables_color_even_on_a_terminal():
    assert should_use_color(FakeStream(True), {"NO_COLOR": "1"}) is False


def test_empty_no_color_is_ignored():
    assert should_use_color(FakeStream(True), {"NO_COLOR": ""}) is True


def test_stream_without_isatty_disables_color():
    assert should_use_color(object(), {}) is False


def test_defaults_read_sys_stdout_and_os_environ(monkeypatch):
    monkeypatch.setattr(sys, "stdout", FakeStream(True))
    monkeypatch.delenv("NO_COLOR", raising=False)
    assert should_use_color() is True
    monkeypatch.setenv("NO_COLOR", "1")
    assert should_use_color() is False


@pytest.mark.parametrize("style, code", [
    ("success", Fore.GREEN),
    ("error", Fore.RED),
    ("warning", Fore.YELLOW),
    ("info", Fore.CYAN),
])
def test_colorize_wraps_text_when_enabled(style, code):
    assert colorize("hi", style, True) == f"{code}hi{Style.RESET_ALL}"


@pytest.mark.parametrize("style", list(STYLES))
def test_colorize_returns_text_unchanged_when_disabled(style):
    assert colorize("hi", style, False) == "hi"


def test_plain_style_is_never_colored():
    assert colorize("hi", "plain", True) == "hi"


@pytest.mark.parametrize("enabled", [True, False])
def test_unknown_style_raises_regardless_of_enabled(enabled):
    with pytest.raises(ValueError, match="Unknown style 'purple'"):
        colorize("hi", "purple", enabled)