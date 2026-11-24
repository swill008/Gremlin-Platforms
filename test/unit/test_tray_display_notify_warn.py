"""01 S176: a refused display power report registration warns once."""

import ctypes
import typing

import pytest

from gremlin.ui import system_tray, window_trace


class _Register:
    def __init__(self, result: int) -> None:
        self.result = result

    def __call__(self, *args: object) -> int:
        return self.result


class _User32:
    def __init__(self, result: int) -> None:
        self.RegisterPowerSettingNotification = _Register(result)


@pytest.fixture
def warnings(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []
    monkeypatch.setattr(system_tray, "_display_notify_warned", False, raising=False)
    monkeypatch.setattr(window_trace, "warn", seen.append)
    monkeypatch.setattr(ctypes, "get_last_error", lambda: 1234)
    return seen


def _use(monkeypatch: pytest.MonkeyPatch, result: int) -> None:
    monkeypatch.setattr(system_tray.ctypes, "WinDLL", lambda *a, **k: _User32(result))


def test_failure_warns_once_with_the_windows_error(
    monkeypatch: pytest.MonkeyPatch, warnings: list[str]
) -> None:
    _use(monkeypatch, 0)
    assert system_tray._register_display_notify(1) == 0
    assert len(warnings) == 1
    assert "1234" in warnings[0]
    assert "until the next start" in warnings[0]

    assert system_tray._register_display_notify(1) == 0
    assert len(warnings) == 1


def test_os_error_warns(monkeypatch: pytest.MonkeyPatch, warnings: list[str]) -> None:
    def boom(*a: object, **k: object) -> typing.NoReturn:
        raise OSError("no user32")

    monkeypatch.setattr(system_tray.ctypes, "WinDLL", boom)
    assert system_tray._register_display_notify(1) == 0
    assert len(warnings) == 1


def test_success_does_not_warn(
    monkeypatch: pytest.MonkeyPatch, warnings: list[str]
) -> None:
    _use(monkeypatch, 77)
    assert system_tray._register_display_notify(1) == 77
    assert warnings == []
