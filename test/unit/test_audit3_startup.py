# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Starting up off-screen, and user plugins (audit 3).

- An off-screen run (tests, screenshot checks) stays off the PC: no keyboard
  or mouse hook, no Windows message box, no closing another copy, no HidHide,
  no tray icon. One check decides, joystick_gremlin.running_offscreen().
- A user plugin can't take the name of a built-in QML element (Deadzone, the
  conditions, the comparators): QML would create the plugin's class instead.

Nothing here shows a real message box or installs a real hook: the Windows
calls are replaced by recorders.
"""

from __future__ import annotations

import contextlib
import ctypes
import os
import pathlib
import subprocess
import sys
import textwrap
import uuid
from collections.abc import Iterator
from typing import NoReturn

sys.path.append(".")

import pytest

import joystick_gremlin as jg
from gremlin import plugin_manager, windows_event_hook

_ROOT = pathlib.Path(__file__).parents[2]

# The real one: test/conftest.py replaces it for every test.
_REAL_MESSAGE_BOX = jg._message_box


@contextlib.contextmanager
def _no_qt_yet(
    monkeypatch: pytest.MonkeyPatch, argv: list[str], env: str
) -> Iterator[None]:
    """As before Qt starts: no application object. Undone inside the test:
    Qt's test teardown asks for the real instance."""
    with monkeypatch.context() as patch:
        patch.setattr(jg.QtCore.QCoreApplication, "instance", lambda: None)
        patch.setattr(sys, "argv", ["joystick_gremlin.py", *argv])
        patch.setenv("QT_QPA_PLATFORM", env)
        yield


@pytest.fixture
def message_boxes(monkeypatch: pytest.MonkeyPatch) -> list[tuple]:
    """The real _message_box, with MessageBoxW recorded (answering Yes)."""
    shown: list[tuple] = []
    monkeypatch.setattr(jg, "_message_box", _REAL_MESSAGE_BOX)
    monkeypatch.setattr(
        ctypes.windll.user32,
        "MessageBoxW",
        lambda *a: shown.append(a) or 6,
    )
    return shown


# --- The off-screen check ---------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("offscreen", True),
        ("offscreen:configfile=screen.json", True),
        (" OffScreen ", True),
        ("windows", False),
        ("windows:darkmode=2", False),
        ("", False),
        # Qt's fallback list: the first entry is the one Qt starts on.
        ("offscreen;minimal", True),
        ("offscreen:configfile=screen.json;windows", True),
        ("windows;offscreen", False),
        ("minimal;offscreen", False),
    ],
)
def test_before_qt_the_platform_part_of_the_variable_decides(
    monkeypatch: pytest.MonkeyPatch, value: str, expected: bool
) -> None:
    with _no_qt_yet(monkeypatch, [], value):
        assert jg.running_offscreen() is expected


def test_before_qt_the_platform_argument_wins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _no_qt_yet(monkeypatch, ["-platform", "offscreen"], "windows"):
        assert jg.running_offscreen()
    with _no_qt_yet(monkeypatch, ["--platform", "windows"], "offscreen"):
        assert not jg.running_offscreen()
    with _no_qt_yet(monkeypatch, ["-platform", "offscreen;windows"], "windows"):
        assert jg.running_offscreen()
    with _no_qt_yet(monkeypatch, ["-platform", "windows;offscreen"], "offscreen"):
        assert not jg.running_offscreen()


def test_once_qt_runs_its_platform_decides(monkeypatch: pytest.MonkeyPatch) -> None:
    class _App:
        platform = "offscreen"

        def platformName(self) -> str:
            return self.platform

    app = _App()
    # Undone straight away: Qt's test teardown asks for the real instance.
    with monkeypatch.context() as patch:
        patch.setattr(jg.QtGui, "QGuiApplication", _App)
        patch.setattr(jg.QtCore.QCoreApplication, "instance", lambda: app)
        patch.setenv("QT_QPA_PLATFORM", "windows")
        assert jg.running_offscreen()
        app.platform = "windows"
        patch.setenv("QT_QPA_PLATFORM", "offscreen")
        assert not jg.running_offscreen()


def test_the_tray_icon_uses_the_shared_check() -> None:
    import inspect

    source = inspect.getsource(jg.JoystickGremlinApp)
    assert "if not running_offscreen():" in source
    assert "platformName()" not in source


# --- Message boxes and the second copy ---------------------------------------


def test_off_screen_a_message_box_is_logged_and_answers_cancel(
    message_boxes: list[tuple], caplog: pytest.LogCaptureFixture
) -> None:
    assert jg._message_box("Some text", "Title", 0x33) == 2
    assert message_boxes == []
    assert "Some text" in caplog.text


def test_off_screen_could_not_start_shows_no_box(message_boxes: list[tuple]) -> None:
    jg.tell_could_not_start("Broken", "details")
    assert message_boxes == []


def test_off_screen_a_second_copy_quits_and_closes_nothing(
    monkeypatch: pytest.MonkeyPatch, message_boxes: list[tuple]
) -> None:
    closed: list[list[int]] = []
    monkeypatch.setattr(jg, "acquire_instance_lock", lambda: None)
    monkeypatch.setattr(jg, "_gremlin_window_titles", lambda: ["Gremlin-Platforms R1"])
    monkeypatch.setattr(jg, "_other_gremlin_pids", lambda: [999_999])
    monkeypatch.setattr(jg, "_terminate_other_gremlin", closed.append)
    assert jg._check_second_copy() == (None, False)
    assert message_boxes == []
    assert closed == []


def test_off_screen_another_process_is_never_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    class _Kernel32:
        def OpenProcess(self, *_a: object) -> int:
            calls.append("open")
            return 1

        def TerminateProcess(self, *_a: object) -> int:
            calls.append("terminate")
            return 1

        def CloseHandle(self, *_a: object) -> int:
            return 1

    monkeypatch.setattr(ctypes.windll, "kernel32", _Kernel32())
    monkeypatch.setattr(jg.subprocess, "run", lambda *a, **k: calls.append("taskkill"))
    monkeypatch.setattr(jg.time, "sleep", lambda _s: None)
    monkeypatch.setattr(jg, "_this_process_tree", lambda: {os.getpid()})
    jg._terminate_other_gremlin([999_999])
    assert calls == []


# --- Keyboard and mouse hooks ------------------------------------------------


class _AppStarted(BaseException):
    """Start-up reached; not an Exception, so main() lets it through."""


def test_main_turns_the_hooks_off_before_the_app_starts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(windows_event_hook, "enabled", True)
    monkeypatch.setattr(jg, "acquire_instance_lock", lambda: "lock")
    monkeypatch.setattr(jg, "_gremlin_window_titles", lambda: [])
    seen: list[bool] = []

    def fake_app(*_a: object) -> NoReturn:
        seen.append(windows_event_hook.enabled)
        raise _AppStarted

    monkeypatch.setattr(jg, "JoystickGremlinApp", fake_app)
    with pytest.raises(_AppStarted):
        jg.main()
    assert seen == [False]


def test_the_app_built_off_screen_installs_no_hook_hidhide_or_tray(
    tmp_path: pathlib.Path,
) -> None:
    """As the smoke scripts do: JoystickGremlinApp built in its own process,
    without test/conftest.py. The hook's thread body, HidHide and message
    boxes are recorders, so nothing reaches the PC even on the old code."""
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    code = textwrap.dedent("""
        import ctypes, importlib.util, os, sys
        from pathlib import Path
        ROOT = Path.cwd()
        sys.path.insert(0, str(ROOT))
        spec = importlib.util.spec_from_file_location(
            "fake_hardware", ROOT / "test" / "fake_hardware.py")
        fake_hardware = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fake_hardware)
        fake_hardware.install()

        from gremlin import windows_event_hook
        windows_event_hook._Hook._listen = lambda self: print("HOOK", flush=True)
        ctypes.windll.user32.MessageBoxW = lambda *a: print("BOX", flush=True) or 2
        import gremlin.ui.hidhide
        gremlin.ui.hidhide.apply_on_start = lambda: print("HIDHIDE", flush=True)
        import gremlin.ui.update_model as um
        um.UpdateModel.startup = lambda self, *a, **k: None

        import joystick_gremlin
        app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
        print("ENABLED", windows_event_hook.enabled, flush=True)
        print("TRAY", app.tray_icon, flush=True)
        print("DONE", flush=True)
        os._exit(0)
    """)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    out = result.stdout
    assert "DONE" in out, out[-2000:] + result.stderr[-2000:]
    assert "HOOK" not in out
    assert "ENABLED False" in out
    assert "HIDHIDE" not in out
    assert "BOX" not in out
    assert "TRAY None" in out


# --- User plugins and built-in QML elements -----------------------------------

_PLUGIN = """
from PySide6 import QtCore
from gremlin.types import InputType


class {cls}Data:
    name = {name!r}
    tag = {name!r}
    model = type({model!r}, (QtCore.QObject,), {{}})
    properties = ()
    input_types = (InputType.JoystickButton,)

    @classmethod
    def can_create(cls):
        return True


create = {cls}Data
"""


def test_the_core_qml_elements_are_known() -> None:
    import action_plugins.condition  # noqa: F401
    import action_plugins.response_curve  # noqa: F401

    names = plugin_manager.core_qml_names("action_plugins")
    assert {
        "Deadzone",
        "KeyboardCondition",
        "JoystickCondition",
        "VJoyCondition",
        "RangeComparatorModel",
        "PressedComparatorModel",
    } <= names


@pytest.mark.parametrize(
    "model", ["Deadzone", "KeyboardCondition", "RangeComparatorModel"]
)
def test_a_user_plugin_cant_replace_a_built_in_qml_element(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, model: str
) -> None:
    registered: list[tuple[str, str]] = []

    def register(cls: type, uri: str, major: int, minor: int, name: str) -> int:
        registered.append((cls.__module__, name))
        return len(registered)

    monkeypatch.setattr(plugin_manager.QtQml, "qmlRegisterType", register)
    monkeypatch.setattr(sys, "path", list(sys.path))

    module = f"audit3_clash_{uuid.uuid4().hex[:8]}"
    folder = tmp_path / module
    folder.mkdir()
    (folder / "__init__.py").write_text(
        _PLUGIN.format(cls="Clash", name=module, model=model), encoding="utf-8"
    )

    # Patched on the class: patching the shared instance left a copy of the
    # method on it after the test, which hid later class patches (test_modes).
    settings = type(plugin_manager.config.Configuration())
    real_value = settings.value

    def value(self: object, *key: str) -> object:
        if key == ("global", "files", "plugin-directory"):
            return str(tmp_path)
        return real_value(self, *key)

    monkeypatch.setattr(settings, "value", value)
    # Not the shared manager: a fresh one through the real start-up path.
    manager = object.__new__(plugin_manager.PluginManager)
    plugin_manager.PluginManager.__init__(manager)

    assert module not in manager.repository
    assert (module, model) not in registered
    # The built-in actions still load.
    assert manager.repository
