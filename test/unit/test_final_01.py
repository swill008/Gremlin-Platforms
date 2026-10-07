# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final phase, spec page 01 (app shell and settings): checks for the
section 8 statements that had none. Each test names the statement it checks
(claude/final-test-plan/01-app-shell.md)."""

from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import pathlib
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest
from PySide6 import QtCore, QtNetwork

import gremlin.config
import joystick_gremlin as jg
from gremlin import deferred_write, threads
from gremlin.common import SingletonMetaclass
from gremlin.signal import signal
from gremlin.types import PropertyType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_LOGGERS = ("system", "user", "event")
# The settings file as the settings module found it when it loaded (tests
# below point it elsewhere).
_REAL_CONFIG_PATH = gremlin.config._config_file_path


def _app() -> QtCore.QCoreApplication:
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


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
def no_history(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import history

    monkeypatch.setattr(history, "record", lambda *args, **kwargs: None)


def _settings_file(path: pathlib.Path, entries: dict) -> None:
    data: dict = {}
    for (section, group, name), (kind, value) in entries.items():
        data.setdefault(section, {}).setdefault(group, {})[name] = {
            "data_type": kind, "description": "", "expose": False,
            "properties": {}, "value": value,
        }
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def settings_path(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, deferred: None,
    no_history: None,
) -> Iterator[pathlib.Path]:
    """A settings file of the test's own; Configuration() reads it afresh."""
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    try:
        yield path
    finally:
        SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


@pytest.fixture
def cfg(settings_path: pathlib.Path) -> gremlin.config.Configuration:
    """A first run: no settings file yet."""
    return gremlin.config.Configuration()


@pytest.fixture
def loggers() -> Iterator[None]:
    """The program's loggers are put back as they were."""
    saved = {}
    for name in _LOGGERS:
        logger = logging.getLogger(name)
        saved[name] = (
            logger.level, logger.disabled, list(logger.handlers),
            [(h, h.level) for h in logger.handlers],
        )
    yield
    for name, (level, disabled, handlers, levels) in saved.items():
        logger = logging.getLogger(name)
        for handler in list(logger.handlers):
            if handler not in handlers:
                handler.close()
                logger.removeHandler(handler)
        logger.setLevel(level)
        logger.disabled = disabled
        for handler, handler_level in levels:
            handler.setLevel(handler_level)


# --- S1, S2: Windows scaling read before Qt starts -------------------------


@pytest.mark.parametrize(
    ("content", "expected"),
    [
        (None, False),  # no settings file
        ("{ not json", False),  # can't be read
        ('{"ui": {}}', False),  # no such setting
        ('{"ui": {"general": {"disable-windows-scaling": {"value": true}}}}', True),
        ('{"ui": {"general": {"disable-windows-scaling": {"value": "False"}}}}', False),
    ],
)
def test_s1_s2_windows_scaling_is_read_from_the_settings_file_before_qt(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch,
    content: str | None, expected: bool,
) -> None:
    folder = tmp_path / "Gremlin Platforms"
    folder.mkdir()
    if content is not None:
        (folder / "configuration.json").write_text(content, encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert jg._windows_scaling_disabled() is expected


# --- S3, S78, S81: the quit after exec, and a restart -----------------------


def test_s3_s78_s81_restart_after_the_usual_quit_order_with_the_launch_scaling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    order: list[str] = []

    class _Lock:
        def unlock(self) -> None:
            order.append("unlock")

    app = SimpleNamespace(
        exec=lambda: order.append("exec"),
        backend=SimpleNamespace(restart_on_exit=True),
        updater=SimpleNamespace(start_pending_install=lambda: False),
    )
    monkeypatch.setattr(jg, "_check_second_copy", lambda: (_Lock(), True))
    monkeypatch.setattr(jg.gremlin.qt_log, "install", lambda folder: None)
    monkeypatch.setattr(jg, "JoystickGremlinApp", lambda argv: app)
    monkeypatch.setattr(jg, "shutdown_cleanup", lambda: order.append("cleanup"))
    monkeypatch.setattr(
        jg.gremlin.threads, "shutdown",
        lambda timeout=2.0: order.append("threads") or [],
    )
    monkeypatch.setattr(
        jg.gremlin.deferred_write, "flush_all", lambda: order.append("flush")
    )
    monkeypatch.setattr(jg.gremlin.history, "close", lambda: order.append("history"))
    # Started without the variable; this copy turned Windows scaling off.
    monkeypatch.setattr(jg, "_LAUNCH_HIGHDPI_SCALING", None)
    monkeypatch.setenv("QT_ENABLE_HIGHDPI_SCALING", "0")
    monkeypatch.setattr(jg.sys, "argv", ["joystick_gremlin.py", "--profile", "x.xml"])
    started: list[tuple] = []
    monkeypatch.setattr(
        jg.QtCore.QProcess, "startDetached",
        lambda program, args, folder: started.append(
            (program, list(args), os.environ.get("QT_ENABLE_HIGHDPI_SCALING"))
        ) or True,
    )

    class _Ended(Exception):
        pass

    def _exit(code: int) -> None:
        raise _Ended(code)

    monkeypatch.setattr(jg.os, "_exit", _exit)
    with pytest.raises(_Ended) as ended:
        jg.main()
    assert ended.value.args == (0,)
    # S78: every thread asked to stop, waiting writes written, History
    # closed, then the lock given up.
    assert order == [
        "exec", "cleanup", "threads", "flush", "history", "flush", "unlock"
    ]
    # S81: started again with the same arguments; S3: the new copy reads
    # the scaling setting afresh.
    assert len(started) == 1
    _program, args, scaling = started[0]
    assert args[-2:] == ["--profile", "x.xml"]
    assert scaling is None


# --- S10: --enable and --start-minimized ------------------------------------


@pytest.mark.parametrize(("enable", "minimized"), [(True, True), (False, False)])
def test_s10_enable_runs_after_the_profile_loads_and_start_minimized_minimizes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path,
    enable: bool, minimized: bool,
) -> None:
    profile = tmp_path / "p.xml"
    profile.write_text("<profile/>", encoding="utf-8")
    calls: list[object] = []
    monkeypatch.setattr(jg, "launch_dir", str(tmp_path))
    monkeypatch.setattr(
        jg, "Configuration", lambda: SimpleNamespace(value=lambda *key: "")
    )
    app = SimpleNamespace(
        backend=SimpleNamespace(
            loadProfile=lambda path: calls.append("load"),
            openLastProfile=lambda path: calls.append("last"),
            activate_gremlin=lambda on: calls.append(("run", on)),
            minimize=lambda: calls.append("minimize"),
        ),
        syslog=mock.Mock(),
    )
    args = argparse.Namespace(
        profile="p.xml", enable=enable, start_minimized=minimized
    )
    jg.JoystickGremlinApp.process_cmd_args(app, args)  # type: ignore[arg-type]
    expected: list[object] = ["load"]
    if enable:
        expected.append(("run", True))
    if minimized:
        expected.append("minimize")
    assert calls == expected


# --- S24: the settings file stays in the profile folder --------------------


def test_s24_settings_stay_in_the_profile_folder_when_the_data_folder_moves(
    cfg: gremlin.config.Configuration, tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import util

    moved = tmp_path / "moved data"
    cfg.register(
        "global", "files", "data-folder", PropertyType.String, "", "", {}, True
    )
    cfg.set("global", "files", "data-folder", str(moved))
    monkeypatch.setattr(util, "_start_folders", {})
    assert pathlib.Path(util.data_folder()) == moved.resolve()
    # Where the settings file is read and written does not follow it: it is
    # fixed in the profile folder when the settings module loads.
    assert pathlib.Path(_REAL_CONFIG_PATH) == (
        pathlib.Path(util.userprofile_path()) / "configuration.json"
    )
    cfg.save_now()
    assert not (moved / "configuration.json").exists()


# --- S37: Close to tray becomes Minimize to tray ---------------------------


@pytest.mark.parametrize("old_value", [True, False])
def test_s37_close_to_tray_becomes_minimize_to_tray_then_is_dropped(
    settings_path: pathlib.Path, old_value: bool
) -> None:
    _settings_file(
        settings_path,
        {("global", "general", "close-to-tray"): ("bool", old_value)},
    )
    cfg = gremlin.config.Configuration()
    jg.register_config_options()
    assert cfg.value("global", "general", "minimize-to-tray") is old_value
    cfg.purge_unused()
    assert not cfg.exists("global", "general", "close-to-tray")


# --- S40: the Options sidebar ----------------------------------------------


def test_s40_options_sidebar_sections() -> None:
    from gremlin.ui.option import ConfigSectionModel

    model = ConfigSectionModel()
    role = QtCore.Qt.ItemDataRole.UserRole + 1
    names = [model.data(model.index(row), role) for row in range(model.rowCount())]
    assert names == [
        "General", "Interface", "Actions", "Profiles", "Home", "OSC", "Folders"
    ]


# --- S44: a switch takes effect when changed --------------------------------


def test_s44_a_switch_is_saved_and_announced_when_changed(
    cfg: gremlin.config.Configuration,
) -> None:
    from gremlin.ui.option import ConfigEntryModel

    key = ("ui", "general", "dark-mode")
    cfg.register(*key, PropertyType.Bool, True, "Use the dark mode UI.", {}, True)
    model = ConfigEntryModel("ui", "general", keys=[key])
    told: list[bool] = []

    def note() -> None:
        told.append(True)

    signal.configChanged.connect(note)
    try:
        value_role = QtCore.Qt.ItemDataRole.UserRole + 2
        assert model.setData(model.index(0), False, value_role) is True
    finally:
        signal.configChanged.disconnect(note)
    assert cfg.value(*key) is False
    assert told == [True]
    assert deferred_write.pending("configuration")  # one write, a moment later


# --- S45: real names and US spelling ---------------------------------------


def test_s45_rows_have_real_names_and_groups_us_spelling() -> None:
    from gremlin.ui.option import ConfigEntryModel, entry_title, group_title

    assert entry_title("ui-scale") == "UI scale"
    assert entry_title("plugin-directory") == "Plugins folder"
    assert entry_title("debug") == "Diagnostic logs"
    assert group_title("colours") == "Colors"
    # The row's name is what the model hands the window.
    model = ConfigEntryModel(
        "global", "files", keys=[("global", "files", "plugin-directory")]
    )
    name_role = QtCore.Qt.ItemDataRole.UserRole + 5
    assert model.data(model.index(0), name_role) == "Plugins folder"


# --- S55, S97: Diagnostic logs ---------------------------------------------


def test_s97_diagnostic_logs_default_to_warning(
    cfg: gremlin.config.Configuration, loggers: None
) -> None:
    from gremlin.ui import log_option

    # Nothing stored yet: Warning, and the logs follow it.
    assert log_option.LogLevelModel().level == "Warning"
    assert log_option.apply_log_level() == "Warning"
    assert logging.getLogger("system").level == logging.WARNING
    # And the registered default.
    jg.register_config_options()
    assert cfg.value("global", "general", "log-level") == "Warning"


def test_s55_one_diagnostic_logs_setting_for_options_and_the_live_log_reader(
    cfg: gremlin.config.Configuration, loggers: None
) -> None:
    from gremlin.ui import log_option

    cfg.register(
        "global", "general", "log-level", PropertyType.String, "Warning", "", {},
        False,
    )
    options = log_option.LogLevelModel()
    reader = log_option.LogLevelModel()
    told: list[bool] = []
    reader.levelChanged.connect(lambda: told.append(True))
    options.setLevel("Error")
    assert told == [True]
    assert reader.level == "Error"
    assert cfg.value("global", "general", "log-level") == "Error"
    assert logging.getLogger("user").level == logging.ERROR
    told.clear()
    reader.setLevel("Info")
    assert options.level == "Info" and told == [True]


# --- S93: action timers run on the main thread -----------------------------


def test_s93_a_main_thread_timer_runs_its_function_on_the_main_thread() -> None:
    app = _app()
    ran: list[threading.Thread] = []
    timer = threads.main_timer(
        "final01 main", 0.01, lambda: ran.append(threading.current_thread())
    )
    try:
        assert isinstance(timer, threads.MainTimer)
        deadline = time.monotonic() + 5.0
        while not ran and time.monotonic() < deadline:
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
        assert ran == [threading.main_thread()]
        assert threads.PREFIX + "final01 main" not in threads.running()
    finally:
        timer.cancel()


# --- S96: the log files -------------------------------------------------------


def test_s96_system_and_user_logs_rotate_at_1_mb_and_event_log_is_new_each_session(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, loggers: None
) -> None:
    monkeypatch.setattr(jg.gremlin.util, "logs_dir", lambda: tmp_path)
    (tmp_path / "event.log").write_text("last session\n", encoding="utf-8")
    before = {name: list(logging.getLogger(name).handlers) for name in _LOGGERS}
    jg.configure_loggers()
    added = {
        name: [h for h in logging.getLogger(name).handlers if h not in before[name]]
        for name in _LOGGERS
    }
    for name in ("system", "user"):
        (handler,) = added[name]
        assert isinstance(handler, logging.handlers.RotatingFileHandler)
        assert handler.maxBytes == 1024 * 1024 and handler.backupCount == 1
        assert handler.encoding == "utf-8"
        assert pathlib.Path(handler.baseFilename) == tmp_path / f"{name}.log"
    (event,) = added["event"]
    assert type(event) is logging.FileHandler
    assert event.mode == "w" and event.encoding == "utf-8"
    assert pathlib.Path(event.baseFilename) == tmp_path / "event.log"
    assert (tmp_path / "event.log").read_text(encoding="utf-8") == ""


# --- S105: the activity log -------------------------------------------------


def test_s105_the_activity_log_is_emptied_at_start_and_by_clear_log(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, deferred: None
) -> None:
    from gremlin.ui import live_debug

    path = tmp_path / "logs.txt"
    monkeypatch.setattr(live_debug, "log_path", lambda: path)
    path.write_text("READ | Earlier run | load | old.xml | ok\n", encoding="utf-8")
    live_debug.start()
    live_debug.flush()
    text = path.read_text(encoding="utf-8")
    assert "Earlier run" not in text and "cleared" in text
    log = live_debug.LiveLog()
    log.refresh()
    assert "cleared" in log.text
    live_debug.trace("SAVE", "Final01", "save", tmp_path / "x.xml")
    log.clear()
    assert path.read_text(encoding="utf-8") == "" and log.text == ""
    live_debug.flush()  # the line waiting when Clear Log ran is gone too
    assert path.read_text(encoding="utf-8") == ""


# --- S23, S119, S123: updates ------------------------------------------------


class _Requests:
    """Stands in for the network: records what would have been sent."""

    def __init__(self) -> None:
        self.sent: list[QtNetwork.QNetworkRequest] = []

    def get(self, request: QtNetwork.QNetworkRequest) -> mock.Mock:
        self.sent.append(QtNetwork.QNetworkRequest(request))
        return mock.Mock()


def test_s23_an_offline_run_never_reaches_github() -> None:
    from gremlin.ui import update_model

    _app()
    assert os.environ.get("GREMLIN_OFFLINE")  # set by the test setup
    model = update_model.UpdateModel()
    network = _Requests()
    model._network = network  # type: ignore[assignment]
    model.check(True)
    assert network.sent == []
    assert model.state == "error" and model.errorText.startswith("Offline")


def test_s123_an_update_check_closes_its_connection_with_the_reply(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import update_model

    _app()
    monkeypatch.delenv("GREMLIN_OFFLINE")
    model = update_model.UpdateModel()
    network = _Requests()
    model._network = network  # type: ignore[assignment]
    model.check(True)
    assert len(network.sent) == 1
    request = network.sent[0]
    assert bytes(request.rawHeader("Connection").data()) == b"close"
    http2 = QtNetwork.QNetworkRequest.Attribute.Http2AllowedAttribute
    assert request.attribute(http2) is False
    assert model.state == "checking"


def test_s119_cancelling_a_download_deletes_the_partial_file(
    tmp_path: pathlib.Path,
) -> None:
    from gremlin.ui import update_model

    _app()
    part = tmp_path / "Setup.part"
    part.write_bytes(b"half")
    model = update_model.UpdateModel()
    model._release = SimpleNamespace(  # type: ignore[assignment]
        version="99.0.0", page_url="",
        setup=SimpleNamespace(name="Setup.exe", size=10, sha256="x", url=""),
    )
    reply = mock.Mock()
    reply.readAll.return_value = QtCore.QByteArray()
    reply.error.return_value = (
        QtNetwork.QNetworkReply.NetworkError.OperationCanceledError
    )
    reply.abort.side_effect = lambda: model._on_downloaded()
    model._reply = reply
    model._file = SimpleNamespace(  # type: ignore[assignment]
        write=lambda data: data.size(), flush=lambda: True, close=lambda: None,
        fileName=lambda: str(part), errorString=lambda: "",
    )
    model._write_error = ""
    model._state = "downloading"
    model.cancel()
    reply.abort.assert_called_once()
    assert not part.exists()
    assert model.state == "available"  # Update Now can be chosen again


# --- The main window, off-screen (its own process) --------------------------


def _run_app(tmp_path: pathlib.Path, script: str) -> dict:
    path = tmp_path / "final01_app.py"
    path.write_text(script, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    result = subprocess.run(
        [sys.executable, str(path)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, result.stdout[-2000:] + result.stderr[-4000:]
    return json.loads(lines[0][len("RESULT "):])


_BOOT = """
import json, os, sys, time
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml

def pump(check, limit=10.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if check():
            return True
    return bool(check())
"""


_MAIN_WINDOW = _BOOT + r"""
from gremlin.signal import signal
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
quits = []
app.engine.quit.connect(lambda: quits.append(1))

def run(code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
    value = expr.evaluate()
    assert not expr.hasError(), code + ': ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    if isinstance(value, QtQml.QJSValue):
        value = value.toVariant()
    return value

out = {}
root = os.path.join(os.environ['USERPROFILE'], 'Gremlin Platforms')
out['folders'] = sorted(n for n in os.listdir(root)
                        if os.path.isdir(os.path.join(root, n)))

# S57: the title.
run('_root.profileDirty = false')
out['title'] = run('_root.title')
run('_root.profileDirty = true')
out['titleDirty'] = run('_root.title')
# S64: the footer while stopped (unsaved changes are named only while it runs).
out['footer'] = run('_footer.children[0].children[0].text')
run('_root.profileDirty = false')

# S58, S59, S61: the toolbar.
pump(lambda: run('_manageModesButton.x > _optionsButton.x'))
out['captions'] = run('[_homeButton, _toggleButton, _vjoyViewerButton, '
                      '_xboxViewerButton, _buttonMapButton, _logicalButton, '
                      '_optionsButton].map(function(b) { return b.caption })')
out['order'] = run('(function() { var xs = [_homeButton, _toggleButton, '
                   '_vjoyViewerButton, _xboxViewerButton, _buttonMapButton, '
                   '_logicalButton, _optionsButton, _modeLabel, _modeSelector, '
                   '_manageModesButton].map(function(b) { return b.x }); '
                   'for (var i = 1; i < xs.length; i++) '
                   'if (!(xs[i] > xs[i-1])) return false; '
                   'return true })()')
out['modeLabel'] = run('_modeLabel.text')
out['manageModes'] = run('_manageModesButton.text')
out['homeAccent'] = run('Qt.colorEqual(_homeButton.color, Style.accent)')
out['logicalAccent'] = run('Qt.colorEqual(_logicalButton.color, Style.accent)')

# S65, S66, S67: the menus, from the one command list.
# (A closed menu's rows report visible false; compactNow() gives the rows
# it hides no height.)
out['menus'] = run('(function() { var bar = _root.menuBar; var r = []; '
                   'for (var i = 0; i < bar.count; i++) { var m = bar.menuAt(i); '
                   'm.compactNow(); var rows = []; '
                   'for (var j = 0; j < m.count; j++) { var it = m.itemAt(j); '
                   'if (!it || it.text === undefined || !(it.height > 0)) continue; '
                   'rows.push(it.text + (it.subMenu ? " >" : "") '
                   '+ (it.hint ? " (" + it.hint + ")" : "")) } '
                   'r.push([m.title, rows]) } return r })()')
out['shortcuts'] = run('_root.shortcutCommands.map(function(c) { '
                       'return [c.id, c.shortcut] })')
# S70: Run / Stop is in no menu, the palette or a shortcut.
out['runCommands'] = run('Commands.all().filter(function(c) { '
                         'return /\\b(Run|Stop)\\b/.test(c.text) }).length')
# S68: the palette lists the main window's usable commands, found by words.
out['palette'] = run('Commands.search("", ["main"]).map(function(c) { return c.id })')
out['paletteSave'] = run('Commands.search("save", ["main"])[0].id')
out['paletteFolder'] = run('Commands.search("data folder", ["main"])[0].id')
# S69: a command that can't be used now does nothing.
out['offTrigger'] = run('(function() { var ran = false; Commands.define({ '
                        'id: "final01.off", text: "Off", group: "Test", '
                        'owner: "final01", '
                        'enabled: function() { return false }, '
                        'run: function() { ran = true } }); '
                        'var r = Commands.trigger("final01.off"); '
                        'Commands.removeOwner("final01"); return [r, ran] })()')

# S60: vJoy Viewer opens, then closes.
run('_vjoyViewerButton.clicked()')
out['viewerOpen'] = run('Helpers.windowOf("DialogInputViewer.qml") !== null')
run('_vjoyViewerButton.clicked()')
out['viewerClosed'] = run('Helpers.windowOf("DialogInputViewer.qml") === null')

# S39: one Options window from the toolbar and the menu.
run('_optionsButton.clicked()')
run('Commands.trigger("tools.options")')
run('_optionsButton.clicked()')
out['optionsWindows'] = len([w for w in QtGui.QGuiApplication.allWindows()
                             if w.title() == 'Options' and w.isVisible()])
# S49: closing Options tells the program settings changed.
changed = []
signal.configChanged.connect(lambda: changed.append(1))
run('Helpers.windowOf("DialogOptions.qml").close()')
out['optionsClosedTold'] = len(changed) > 0
out['optionsGone'] = run('Helpers.windowOf("DialogOptions.qml") === null')

# S114: Check for Updates opens the Update window and checks.
run('Commands.trigger("help.updates")')
out['updateWindow'] = run('Helpers.windowOf("DialogUpdate.qml") !== null')
out['updateState'] = [run('updater.state'), run('updater.errorText')]
run('Helpers.windowOf("DialogUpdate.qml").close()')

# S71: New with unsaved changes asks first; Cancel keeps the profile.
profile = app.backend.profile
profile.has_unsaved_changes = lambda: True
run('Commands.trigger("file.new")')
out['newAsks'] = [run('_saveBeforeContinueDialog.pendingAction !== null'),
                  run('_saveBeforeContinueDialog.quitting')]
run('_saveBeforeContinueDialog.cancelled(); _saveBeforeContinueDialog.close()')
out['newCancelled'] = app.backend.profile is profile

# S75: a Module Setup window with unsaved work asks first; the quit stops there.
run('_root.configureWin = Qt.createQmlObject("import QtQuick; QtObject { '
    'property bool visible: true; property bool asked: false; '
    'function hasUnsavedWork() { return true } '
    'function show() {} function raise() {} function requestActivate() {} '
    'function close() { asked = true } }", _root)')
run('quitGremlin()')
out['toolFirst'] = [run('_root.configureWin.asked'),
                    run('_saveBeforeContinueDialog.pendingAction === null'),
                    len(quits)]
run('_root.configureWin = null')
# S76: Cancel calls off the quit and the restart that waited on it.
run('quitGremlin(true)')
out['restartAsked'] = [app.backend.restart_on_exit,
                       run('_saveBeforeContinueDialog.quitting')]
run('_saveBeforeContinueDialog.cancelled(); _saveBeforeContinueDialog.close()')
out['restartCancelled'] = [app.backend.restart_on_exit, len(quits)]
# Discard goes on to quit.
run('quitGremlin()')
run('_saveBeforeContinueDialog.discardChosen(); _saveBeforeContinueDialog.close()')
out['discardQuits'] = len(quits) > 0
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)  # threads started by the app would keep it alive
"""


@pytest.fixture(scope="module")
def main_window(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run_app(tmp_path_factory.mktemp("final01_main"), _MAIN_WINDOW)


def test_s5_the_data_folders_are_made_at_start(main_window: dict) -> None:
    assert {
        "modules", "logs", "profiles", "scripts", "export", "history",
        "deleted devices", "plugins",
    } <= set(main_window["folders"])


def test_s57_the_title_names_the_profile_and_marks_unsaved_changes(
    main_window: dict,
) -> None:
    assert main_window["title"] == "Untitled - Gremlin-Platforms R1"
    assert main_window["titleDirty"] == "* Untitled - Gremlin-Platforms R1"


def test_s58_s59_s61_the_toolbar(main_window: dict) -> None:
    assert main_window["captions"] == [
        "Home", "Run", "vJoy Viewer", "Xbox Viewer", "Button Map",
        "Logical Device", "Options",
    ]
    assert main_window["order"] is True
    assert main_window["modeLabel"] == "Mode"
    assert main_window["manageModes"] == "Manage Modes"
    # Home's page is shown at start; the Logical Device's isn't.
    assert main_window["homeAccent"] is True
    assert main_window["logicalAccent"] is False


def test_s64_the_footer_while_stopped(main_window: dict) -> None:
    assert main_window["footer"] == "<B>Status: </B>Stopped"


def test_s65_s66_s67_menus_come_from_the_command_list(main_window: dict) -> None:
    menus = {title: rows for title, rows in main_window["menus"]}
    assert list(menus) == ["File", "View", "Tools", "Debug", "Help"]
    # Recent shows only once there is a recent profile.
    assert [r for r in menus["File"] if r != "Recent >"] == [
        "New Profile (Ctrl+N)", "Load Profile… (Ctrl+O)", "Save Profile (Ctrl+S)",
        "Save Profile As… (Ctrl+Shift+S)", "Open Program Folder",
        "Open Data Folder", "Exit",
    ]
    # Home is shown: View > Home can't be used, so it isn't listed (S66).
    assert menus["View"] == [
        "Configuration", "Home Layout >", "Scripts", "Profile Settings",
        "Command Palette… (Ctrl+K)",
    ]
    assert menus["Tools"] == [
        "Viewers >", "Device Setup >", "Mapping >", "History", "Options"
    ]
    assert menus["Debug"] == ["Live Log Reader"]
    assert menus["Help"] == ["User Guide (F1)", "Check for Updates", "About"]
    assert dict(main_window["shortcuts"]) == {
        "file.new": "Ctrl+N", "file.load": "Ctrl+O", "file.save": "Ctrl+S",
        "file.saveAs": "Ctrl+Shift+S", "view.palette": "Ctrl+K",
        "help.guide": "F1",
    }


def test_s68_the_palette_lists_usable_commands_found_by_words(
    main_window: dict,
) -> None:
    palette = main_window["palette"]
    assert "file.save" in palette and "tools.options" in palette
    assert "view.palette" not in palette  # the palette itself
    assert "view.home" not in palette  # can't be used on Home
    assert main_window["paletteSave"] == "file.save"
    assert main_window["paletteFolder"] == "file.dataFolder"


def test_s69_a_command_that_cannot_be_used_does_nothing(main_window: dict) -> None:
    assert main_window["offTrigger"] == [False, False]


def test_s70_run_and_stop_are_not_commands(main_window: dict) -> None:
    assert main_window["runCommands"] == 0


def test_s60_the_vjoy_viewer_button_opens_and_closes_it(main_window: dict) -> None:
    assert main_window["viewerOpen"] is True
    assert main_window["viewerClosed"] is True


def test_s39_s49_one_options_window_and_closing_it_announces_changes(
    main_window: dict,
) -> None:
    assert main_window["optionsWindows"] == 1
    assert main_window["optionsClosedTold"] is True
    assert main_window["optionsGone"] is True


def test_s114_check_for_updates_opens_the_window_and_checks(
    main_window: dict,
) -> None:
    assert main_window["updateWindow"] is True
    state, text = main_window["updateState"]
    # Off-screen runs are offline (S23): the check ran and says why.
    assert state == "error" and text.startswith("Offline")


def test_s71_new_with_unsaved_changes_asks_and_cancel_keeps_the_profile(
    main_window: dict,
) -> None:
    assert main_window["newAsks"] == [True, False]
    assert main_window["newCancelled"] is True


def test_s75_s76_quit_order_and_cancel(main_window: dict) -> None:
    # A Module Setup window with unsaved work asks first; nothing else does.
    assert main_window["toolFirst"] == [True, True, 0]
    # The profile asks; Cancel calls off the quit and the restart.
    assert main_window["restartAsked"] == [True, True]
    assert main_window["restartCancelled"] == [False, 0]
    assert main_window["discardQuits"] is True


# --- S12: the start-up failure page -------------------------------------------


_FAILURE = _BOOT + r"""
import gremlin.device_initialization as di
import gremlin.error

def _no_driver():
    raise gremlin.error.GremlinError("The joystick driver could not start.")

di.joystick_devices_initialization = _no_driver
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
quits = []
app.engine.quit.connect(lambda: quits.append(1))
roots = app.engine.rootObjects()
win = roots[0]
out = {'roots': len(roots), 'title': win.title(),
       'main': hasattr(app, 'main_window')}
texts = []
button = None
for child in win.findChildren(QtCore.QObject):
    name = child.metaObject().className()
    text = child.property('text')
    if 'TextArea' in name:
        texts.append(text)
    if 'Button' in name and text:
        button = child
        out['button'] = text
out['reason'] = texts
QtCore.QMetaObject.invokeMethod(button, 'clicked')
out['quit'] = pump(lambda: len(quits) > 0, 5.0)
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)
"""


def test_s12_a_driver_that_cannot_start_shows_the_failure_page(
    tmp_path: pathlib.Path,
) -> None:
    out = _run_app(tmp_path, _FAILURE)
    assert out["roots"] == 1 and out["main"] is False
    assert out["title"] == "Gremlin-Platforms R1"
    assert out["reason"] == ["The joystick driver could not start."]
    assert out["quit"] is True


# --- S16: a user folder that can't be made ----------------------------------


def test_s16_a_user_folder_that_cannot_be_made_is_told_with_the_box(
    tmp_path: pathlib.Path,
) -> None:
    # Something that is not a folder where the user folder belongs.
    (tmp_path / "Gremlin Platforms").write_text("not a folder", encoding="utf-8")
    code = (
        "import sys, runpy\n"
        "sys.path.insert(0, '.')\n"
        "sys.argv = ['joystick_gremlin.py']\n"
        "runpy.run_path('joystick_gremlin.py', run_name='__main__')\n"
    )
    script = tmp_path / "no_user_folder.py"
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
    # No logs folder can be made either: the failure and the box (logged
    # off-screen instead of shown) reach stderr.
    assert "Could not start: GremlinError" in result.stderr, result.stderr[-1500:]
    assert "Gremlin-Platforms could not start." in result.stderr
    assert "Data folder exists but is not a folder" in result.stderr
