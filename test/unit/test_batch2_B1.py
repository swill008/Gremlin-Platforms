# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 2, program shell and settings (spec page 01).

Settings that can't be written are told once (GL-026); settings changed
from another thread are locked (GL-045); a change made before a new
setting's first save still makes a History entry (GL-311); folders that
can't be reached fall back and say so (GL-033, GL-114); the data and logs
folders stay until the next start (GL-113, GL-193 wording); every setting is
registered before the purge (GL-117); the Live Log Reader finds its folder
once and reads only changed files (GL-118); a second copy that couldn't be
closed is said (GL-116); a failure while the modules load is shown
(GL-034); the tray lets a quit's close pass and saves the window place
(GL-111, GL-112); and the main window's side of GL-098, GL-110, GL-157 and
GL-176, off-screen.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

import gremlin.config
from gremlin import deferred_write, threads, util
from gremlin.common import SingletonMetaclass
from gremlin.types import PropertyType

_ROOT = pathlib.Path(__file__).resolve().parents[2]


class _FakeScheduler:
    """Stands in for the Qt timer: writes wait until flushed by hand."""

    def __init__(self) -> None:
        class _Signal:
            def emit(_self, key: str, delay: int) -> None:  # noqa: N805
                pass

        self.request = _Signal()


@pytest.fixture
def deferred(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: _FakeScheduler())
    deferred_write._pending.clear()
    yield
    deferred_write._pending.clear()


@pytest.fixture
def cfg(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[gremlin.config.Configuration]:
    """A first run: no settings file yet."""
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(tmp_path / "c.json"))
    try:
        yield gremlin.config.Configuration()
    finally:
        SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


# --- GL-026: a settings file that can't be written -------------------------


def test_a_settings_file_that_cannot_be_written_is_told_once(
    cfg: gremlin.config.Configuration, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import module_file
    from gremlin.signal import signal

    def locked(*_args: object, **_kwargs: object) -> None:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(module_file, "write_text", locked)
    monkeypatch.setattr(gremlin.config, "_write_failure_told", False)
    told: list[tuple[str, str]] = []
    signal.showNotification.connect(lambda title, text: told.append((title, text)))
    try:
        cfg.save_now()  # never raises: a quit or an install goes on
        cfg.save_now()
    finally:
        signal.showNotification.disconnect()
    assert told == [
        ("Settings Not Saved", "Settings could not be saved: Permission denied")
    ]


# --- GL-045: settings changed from another thread --------------------------


def test_a_change_from_another_thread_waits_for_the_settings_lock(
    cfg: gremlin.config.Configuration, deferred: None
) -> None:
    cfg.register("t", "g", "n", PropertyType.Int, 1, "", {"min": 0, "max": 99})
    done = threading.Event()

    def change() -> None:
        cfg.set("t", "g", "n", 5)
        done.set()

    with cfg._lock:
        worker = threads.start("settings change test", change)
        # Bounded: the change must still be waiting while the lock is held.
        assert not done.wait(0.2)
        assert cfg.value("t", "g", "n") == 1
    assert done.wait(5)
    worker.join(5)
    assert cfg.value("t", "g", "n") == 5


# --- GL-311: a change in the same write as a first appearance ---------------


def test_a_change_before_a_new_settings_first_save_is_a_history_entry(
    cfg: gremlin.config.Configuration, deferred: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import history

    recorded: list[tuple] = []
    monkeypatch.setattr(history, "record", lambda *args: recorded.append(args))
    cfg.register(
        "global", "general", "dark-mode", PropertyType.Bool, True, "", {}, True
    )
    cfg.register(
        "global", "general", "other", PropertyType.Bool, False, "", {}, True
    )
    cfg.set("global", "general", "dark-mode", False)  # within the same second
    deferred_write.flush_all()  # one write
    assert len(recorded) == 1
    area, _title, detail, before, after = recorded[0]
    assert area == "settings"
    # The changed setting only: a first appearance isn't a change (08 S16).
    assert detail == {"keys": ["global/general/dark-mode"]}
    assert before == {"global/general/dark-mode": "True"}  # stored as text
    assert after == {"global/general/dark-mode": "False"}


# --- GL-114 / GL-033: folders that can't be reached ------------------------


@pytest.fixture
def folders(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, str]:
    chosen: dict[str, str] = {}
    settings = gremlin.config.Configuration
    real_value = settings.value
    real_exists = settings.exists

    def value(self: object, *key: str) -> object:
        if key[:2] == ("global", "files") and key[2] in chosen:
            return chosen[key[2]]
        return real_value(self, *key)  # type: ignore[arg-type]

    def exists(self: object, *key: str) -> bool:
        if key[:2] == ("global", "files") and key[2] in chosen:
            return True
        return real_exists(self, *key)  # type: ignore[arg-type]

    monkeypatch.setattr(settings, "value", value)
    monkeypatch.setattr(settings, "exists", exists)
    monkeypatch.setattr(util, "userprofile_path", lambda: str(tmp_path / "home"))
    monkeypatch.setattr(util, "_fallbacks", {})
    monkeypatch.setattr(util, "_fallbacks_told", set())
    monkeypatch.setattr(util, "_start_folders", {})
    return chosen


def test_a_missing_data_folder_uses_the_default_and_says_so_once(
    folders: dict[str, str], tmp_path: Path
) -> None:
    from gremlin.signal import signal

    blocker = tmp_path / "a file"
    blocker.write_text("x", encoding="utf-8")
    folders["data-folder"] = str(blocker / "data")  # like an unplugged drive
    assert Path(util.data_folder()) == tmp_path / "home"
    told: list[tuple[str, str]] = []
    signal.showNotification.connect(lambda title, text: told.append((title, text)))
    try:
        util.announce_folder_fallbacks()
        util.data_folder()
        util.announce_folder_fallbacks()  # once per session
    finally:
        signal.showNotification.disconnect()
    assert len(told) == 1
    title, text = told[0]
    assert title == "Folder Not Found"
    assert str(blocker / "data") in text and str(tmp_path / "home") in text


def test_a_data_folder_that_cannot_be_written_never_stops_folder_lookups(
    folders: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "a file"
    blocker.write_text("x", encoding="utf-8")
    folders["data-folder"] = str(tmp_path / "data")
    folders["logs-folder"] = ""
    (tmp_path / "data").mkdir()
    # The data folder is there, but its logs folder can't be made (a file).
    (tmp_path / "data" / "logs").write_text("x", encoding="utf-8")
    assert util.logs_dir() == tmp_path / "home" / "logs"


# --- GL-113 / GL-193: folders fixed until the next start -------------------


def test_the_logs_folder_stays_until_the_next_start(
    folders: dict[str, str], tmp_path: Path
) -> None:
    folders["data-folder"] = ""
    folders["logs-folder"] = str(tmp_path / "first logs")
    util.freeze_start_folders()
    folders["logs-folder"] = str(tmp_path / "second logs")
    folders["data-folder"] = str(tmp_path / "second data")
    assert util.logs_dir() == (tmp_path / "first logs").resolve()
    assert Path(util.data_folder()) == tmp_path / "home"


def test_folder_rows_say_when_they_take_effect() -> None:
    import joystick_gremlin

    joystick_gremlin.register_config_options()
    config = gremlin.config.Configuration()
    for key in ("data-folder", "logs-folder", "plugin-directory"):
        assert "Takes effect on the next start." in config.description(
            "global", "files", key
        ), key
    assert "stay in the old folder" in config.description(
        "global", "files", "history-folder"
    )


# --- GL-117: every setting registered before the purge ---------------------


def test_settings_registered_later_are_registered_before_the_purge(
    cfg: gremlin.config.Configuration,
) -> None:
    import joystick_gremlin
    from gremlin.modules import registry
    from gremlin.ui import (
        button_map_options,
        device_names,
        hidhide,
        highlight_option,
        live_debug,
        module_model,
        update_model,
        vjoy_status,
        window_placement,
    )

    joystick_gremlin.register_config_options()
    before = set(cfg._keys())
    # What registers on first use (it must find its setting already there,
    # or purge_unused deleted it at start: AU-47).
    for name in live_debug._CHOICES:
        live_debug._choice_key(name)
    live_debug._start_empty_key()
    update_model._register(cfg)
    highlight_option.ensure_registered()
    device_names._ensure()
    registry._binding_store()
    window_placement._ensure()
    hidhide._ensure_options()
    vjoy_status.register_options()
    button_map_options.register()
    module_model._ensure_display_options()
    assert set(cfg._keys()) - before == set()


# --- GL-118: the Live Log Reader's refresh ---------------------------------


def test_the_live_log_reader_finds_its_folder_once_and_reads_changed_files_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import live_debug

    looked: list[int] = []

    def logs_dir() -> Path:
        looked.append(1)
        return tmp_path

    monkeypatch.setattr(util, "logs_dir", logs_dir)
    for name in live_debug.DEBUG_FILES.values():
        (tmp_path / name).write_text(
            "2026-10-06 09:00:00       INFO start\n", encoding="utf-8"
        )
    log = live_debug.DebugLog()
    log._file = "all"
    log._logging_on = lambda: True  # type: ignore[method-assign]
    reads: list[str] = []
    real_read = log._read

    def counted(path: Path, stamp: tuple[int, int] | None) -> tuple[str, bool]:
        reads.append(path.name)
        return real_read(path, stamp)

    log._read = counted  # type: ignore[method-assign]
    log.refresh()
    names = live_debug.MERGED_NAMES
    assert sorted(reads) == sorted(live_debug.DEBUG_FILES[k] for k in names)
    reads.clear()
    with (tmp_path / "system.log").open("a", encoding="utf-8") as handle:
        handle.write("2026-10-06 09:00:01    WARNING more\n")
    log.refresh()
    log.refresh()
    assert reads == ["system.log"]
    assert len(looked) == 1


# --- GL-116: the other copy could not be closed ----------------------------


def test_a_second_copy_that_could_not_be_closed_is_said_and_asked_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import joystick_gremlin as jg

    asked: list[bool] = []

    def prompt(
        lock_held: bool, wins: list[str], pids: list[int], not_closed: bool = False
    ) -> str:
        asked.append(not_closed)
        return "close_others" if not not_closed else "quit"

    monkeypatch.setattr(jg, "acquire_instance_lock", lambda: None)  # never freed
    monkeypatch.setattr(jg, "_gremlin_window_titles", lambda: ["Gremlin-Platforms R1"])
    monkeypatch.setattr(jg, "_other_gremlin_pids", lambda: [700])
    monkeypatch.setattr(jg, "_confirm_second_instance", prompt)
    monkeypatch.setattr(jg, "_terminate_other_gremlin", lambda pids: None)
    lock, start = jg._check_second_copy()
    assert asked == [False, True]  # said, then Cancel
    assert lock is None and start is False


def test_the_not_closed_box_says_so(_no_message_boxes: list[tuple]) -> None:
    import joystick_gremlin as jg

    jg._confirm_second_instance(True, [], [700], not_closed=True)
    text = _no_message_boxes[-1][0]
    assert text.startswith("The other copy could not be closed.")
    assert "No = Start this copy anyway" in text and "Cancel = Do not start" in text


# --- GL-034: a failure while the modules load ------------------------------


def test_a_failure_while_the_modules_load_is_shown_and_logged(tmp_path: Path) -> None:
    code = (
        "import sys, runpy\n"
        "sys.path.insert(0, '.')\n"
        "sys.argv = ['joystick_gremlin.py']\n"
        "sys.modules['gremlin.watchdog'] = None  # an import that fails\n"
        "runpy.run_path('joystick_gremlin.py', run_name='__main__')\n"
    )
    script = tmp_path / "broken_import.py"
    script.write_text(code, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    result = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 1, result.stderr[-1500:]
    log = tmp_path / "Gremlin Platforms" / "logs" / "system.log"
    assert log.is_file(), result.stderr[-1500:]
    text = log.read_text(encoding="utf-8")
    assert "Could not start: ModuleNotFoundError" in text
    # The could-not-start box (logged off-screen instead of shown).
    assert "Gremlin-Platforms could not start." in text


# --- GL-111 / GL-112: the tray's close filter ------------------------------


class _Close:
    def __init__(self, spontaneous: bool) -> None:
        self._spontaneous = spontaneous
        self.ignored = False

    def type(self) -> object:
        from PySide6 import QtCore

        return QtCore.QEvent.Type.Close

    def spontaneous(self) -> bool:
        return self._spontaneous

    def ignore(self) -> None:
        self.ignored = True


class _Window:
    def __init__(self) -> None:
        self.hidden = False

    def hide(self) -> None:
        self.hidden = True


def _tray(monkeypatch: pytest.MonkeyPatch) -> tuple[object, _Window, list]:
    from gremlin.ui import system_tray

    saved: list[object] = []
    monkeypatch.setattr(system_tray.window_placement, "save_window", saved.append)
    cfg = gremlin.config.Configuration()
    monkeypatch.setattr(
        type(cfg), "value",
        lambda self, *key: True if key[2] == "minimize-to-tray" else False,
    )
    monkeypatch.setattr(type(cfg), "exists", lambda self, *key: True)
    tray = system_tray.SystemTrayIcon.__new__(system_tray.SystemTrayIcon)
    window = _Window()
    tray._window = window  # type: ignore[attr-defined]
    tray._icon_present = True  # type: ignore[attr-defined]
    tray._tell_once_still_running = lambda: None  # type: ignore[method-assign]
    return tray, window, saved


def test_the_x_hides_to_the_tray_and_saves_the_window_place(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tray, window, saved = _tray(monkeypatch)
    event = _Close(spontaneous=True)
    assert tray.eventFilter(window, event) is True  # type: ignore[attr-defined]
    assert event.ignored and window.hidden
    assert saved == [window]


def test_the_close_a_quit_makes_is_not_turned_into_a_hide(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from PySide6 import QtCore

    tray, window, saved = _tray(monkeypatch)
    event = _Close(spontaneous=False)
    monkeypatch.setattr(
        QtCore.QObject, "eventFilter", lambda self, watched, event: False
    )
    assert tray.eventFilter(window, event) is False  # type: ignore[attr-defined]
    assert not event.ignored and not window.hidden and saved == []


# --- Main window, off-screen: GL-098, GL-110, GL-157, GL-176 ---------------

_MAIN = """
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtQml, QtTest
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
quits = []
app.engine.quit.connect(lambda: quits.append(1))
QtTest.QTest.qWait(300)

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), expr.error().toString()
    return value[0] if isinstance(value, tuple) else value

out = {}
# GL-098: the contract tools call; with no pane open it goes straight on.
out['panes'] = run('(function() { var ran = false; '
                   'closeActionPanes(function() { ran = true }); return ran })()')
out['mainWindow'] = run('Helpers.mainWindow() === _root')
# GL-157: a Recent file that didn't open offers Forget It.
run('offerForgetRecent("C:/gone.xml", "The file isn\\'t there any more.")')
out['forget'] = [run('_lastProfileGate.confirmText'),
                 run('_lastProfileGate.cancelText')]
run('_lastProfileGate.close()')
# GL-176: a deleted device's Module Setup closes without asking.
run('_root.configureWin = Qt.createQmlObject("import QtQuick; QtObject { '
    'property string deviceName: \\'Stick\\'; property string deviceGuid: \\'g\\'; '
    'property bool allowClose: false; property bool closed: false; '
    'function hasUnsavedWork() { return !allowClose } '
    'function close() { closed = allowClose } }", _root)')
fake = run('_root.configureWin')
run('closeDeletedDevice({"rawName": "Stick", "guid": "g"})')
out['deleted'] = [fake.property('closed'), run('_notificationDialog.text')]
run('_notificationDialog.close(); _root.configureWin = null')
# GL-110: the X quits even with a tool window open.
run('openTool("DialogAbout.qml")')
QtTest.QTest.qWait(100)
win.close()
QtTest.QTest.qWait(100)
out['quit'] = len(quits) > 0
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


def test_main_window_shell(tmp_path: Path) -> None:
    script = tmp_path / "main_shell.py"
    script.write_text(_MAIN, encoding="utf-8")
    (tmp_path / "Gremlin Platforms").mkdir(exist_ok=True)
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    result = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-1500:] + result.stderr[-3000:]
    out = json.loads(lines[0][len("RESULT "):])
    assert out["panes"] is True
    assert out["mainWindow"] is True
    assert out["forget"] == ["Forget It", "Keep"]
    assert out["deleted"][0] is True
    assert "Stick was deleted" in out["deleted"][1]
    assert out["quit"] is True
