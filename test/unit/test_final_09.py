# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final-phase checks for spec page 09 (sound, speech, tray, look). OSC is
parked: no OSC tests here. Plan: claude/final-test-plan/09-osc-sound-misc.md."""

from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterator
from types import SimpleNamespace
from typing import Any
from unittest import mock

import pytest
from PySide6 import QtCore, QtGui

import gremlin.config
from gremlin import audio_player, deferred_write, tts
from gremlin.base_classes import Value
from gremlin.common import SingletonMetaclass
from gremlin.event_handler import Event
from gremlin.types import InputType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_GUID = uuid.UUID("77777777-5555-2222-3333-4444444444f9")


def _wait_for(check: Callable[[], bool], seconds: float = 5.0) -> bool:
    """Polls check (running Qt events) until it is True or time runs out."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents()
        if check():
            return True
        time.sleep(0.01)
    return False


# --- S51: the playback mode chosen in Options applies at once ---------------


@pytest.fixture
def player(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A fresh AudioPlayer (the shared one is put back) reading its mode from
    a stand-in setting, with stand-in samples: nothing plays on the PC."""
    log: list[tuple[str, str]] = []
    samples: dict[str, Any] = {}
    setting = {"mode": "Sequential"}

    class Sample:
        def __init__(self, name: str, _volume: int) -> None:
            self.name = name
            self._done = threading.Event()
            samples[name] = self

        def finish(self) -> None:
            self._done.set()

        @property
        def done(self) -> bool:
            return self._done.is_set()

        def play(self) -> None:
            log.append(("play", self.name))

        def cancel(self) -> None:
            log.append(("cancel", self.name))
            self._done.set()

        def block(self, still_wanted: Callable[[], bool]) -> None:
            while not self._done.wait(0.02):
                if not still_wanted():
                    return

    monkeypatch.setattr(audio_player, "AudioSample", Sample)
    monkeypatch.setattr(
        audio_player,
        "Configuration",
        lambda: SimpleNamespace(value=lambda *_key: setting["mode"]),
    )
    fresh = object.__new__(audio_player.AudioPlayer)
    fresh.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, audio_player.AudioPlayer, fresh)
    yield SimpleNamespace(player=fresh, log=log, samples=samples, setting=setting)
    fresh.stop()


def test_s51_a_new_playback_mode_applies_when_options_closes(
    player: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import backend

    emitted: list[int] = []
    monkeypatch.setattr(
        backend,
        "signal",
        SimpleNamespace(configChanged=SimpleNamespace(emit=lambda: emitted.append(1))),
    )
    player.player.start()
    player.player.enqueue("a.wav", 50)
    assert _wait_for(lambda: ("play", "a.wav") in player.log)
    player.samples["a.wav"].finish()
    # Options: Sequential -> Interrupt, then the window closes (DialogOptions
    # onClosing -> backend.emitConfigChanged), while the Run goes on.
    player.setting["mode"] = "Interrupt"
    backend.Backend.klass.emitConfigChanged(mock.Mock())
    assert emitted == [1]
    player.player.enqueue("b.wav", 50)
    assert _wait_for(lambda: ("play", "b.wav") in player.log)
    player.player.enqueue("c.wav", 50)  # Sequential would wait for b
    assert _wait_for(lambda: ("play", "c.wav") in player.log)
    assert player.log.index(("cancel", "b.wav")) < player.log.index(("play", "c.wav"))


# --- S58, S59, S60: speech voice and the current mode -----------------------


class _Voice:
    def __init__(self, name: str) -> None:
        self._name = name

    def name(self) -> str:
        return self._name


class _Engine:
    State = SimpleNamespace(Ready="ready", Speaking="speaking", Error="error")

    def __init__(self, backend: str) -> None:
        self.backend = backend
        self.said: list[tuple[str, str]] = []  # (text, voice)
        self.voice = ""  # "" = the system's default voice
        self._state = "ready"
        self.stateChanged = mock.MagicMock()

    @classmethod
    def availableEngines(cls) -> list[str]:  # noqa: N802
        return ["winrt"]

    def availableVoices(self) -> list[_Voice]:  # noqa: N802
        return [_Voice("Voice A"), _Voice("Voice B")]

    def setVoice(self, voice: _Voice) -> None:  # noqa: N802
        self.voice = voice.name()

    def state(self) -> str:
        return self._state

    def setRate(self, _v: float) -> None:  # noqa: N802
        pass

    def setPitch(self, _v: float) -> None:  # noqa: N802
        pass

    def setVolume(self, _v: float) -> None:  # noqa: N802
        pass

    def say(self, text: str) -> None:
        self.said.append((text, self.voice))
        self._state = "speaking"

    def stop(self) -> None:
        self._state = "ready"


@pytest.fixture
def speech(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    """A fresh TTSManager (the shared one is put back) with a stand-in engine
    and a stand-in voice setting: nothing is spoken on the PC."""
    from gremlin.ui import option

    monkeypatch.setattr(tts, "QTextToSpeech", _Engine)
    saved = {"voice": ""}
    settings = SimpleNamespace(
        value=lambda *_key: saved["voice"],
        set=lambda *key_and_value: saved.__setitem__("voice", key_and_value[-1]),
    )
    monkeypatch.setattr(tts, "Configuration", lambda: settings)
    monkeypatch.setattr(option.gremlin.config, "Configuration", lambda: settings)
    manager = object.__new__(tts.TTSManager)
    manager.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, tts.TTSManager, manager)
    yield SimpleNamespace(manager=manager, saved=saved)
    manager.stop()


def _say(text: str, mode: str = "queue-back") -> None:
    from action_plugins.text_to_speech import TextToSpeechData, TextToSpeechFunctor

    data = TextToSpeechData(InputType.JoystickButton)
    data.text = text
    data.queue_mode = mode
    event = Event(InputType.JoystickButton, 3, _GUID, "Default", is_pressed=True)
    TextToSpeechFunctor(data)(event, Value(True))


def test_s58_a_voice_changed_while_running_speaks_the_next_text(
    speech: SimpleNamespace,
) -> None:
    from gremlin.ui import option

    speech.saved["voice"] = "Voice A"
    speech.manager.start()  # Run
    _say("one")
    engine = speech.manager._engine
    assert engine.said == [("one", "Voice A")]
    engine.stop()  # finished speaking
    # Options -> Actions -> Text to Speech, while the profile runs.
    model = option.TTSVoiceSelectionModel()
    voices = [model.data(model.index(r, 0), QtCore.Qt.ItemDataRole.UserRole + 1)
              for r in range(model.rowCount())]
    model.currentIndex = voices.index("Voice B")
    assert speech.saved["voice"] == "Voice B"
    _say("two")
    assert speech.manager._engine.said[-1] == ("two", "Voice B")


def test_s59_a_saved_voice_no_longer_installed_speaks_with_the_default(
    speech: SimpleNamespace,
) -> None:
    speech.saved["voice"] = "Uninstalled Voice"
    speech.manager.start()
    _say("hello")
    assert speech.manager._engine.said == [("hello", "")]  # the system default


def test_s60_current_mode_in_the_text_is_the_current_mode_name(
    speech: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    import action_plugins.text_to_speech as tts_action

    current = SimpleNamespace(name="Flight")
    monkeypatch.setattr(
        tts_action,
        "mode_manager",
        SimpleNamespace(ModeManager=lambda: SimpleNamespace(current=current)),
    )
    speech.manager.start()
    _say("Mode ${current_mode}, $other")
    engine = speech.manager._engine
    assert engine.said[-1][0] == "Mode Flight, $other"
    engine.stop()
    current.name = "Landing"
    _say("${current_mode}")
    assert engine.said[-1][0] == "Landing"


# --- S63, S73: the tray, with every Windows call recorded -------------------


class _Window(QtCore.QObject):
    """Stands in for the main window; setVisibility reports the change like
    the real window does."""

    visibilityChanged = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.mode = QtGui.QWindow.Visibility.Windowed
        self.calls: list[object] = []

    def visibility(self) -> QtGui.QWindow.Visibility:
        return self.mode

    def isVisible(self) -> bool:
        return self.mode not in (
            QtGui.QWindow.Visibility.Hidden, QtGui.QWindow.Visibility.Minimized
        )

    def setVisibility(self, mode: QtGui.QWindow.Visibility) -> None:
        self.calls.append(mode)
        self.mode = mode
        self.visibilityChanged.emit(mode)

    def hide(self) -> None:
        self.setVisibility(QtGui.QWindow.Visibility.Hidden)

    def raise_(self) -> None:
        pass

    def requestActivate(self) -> None:
        pass


class _TrayBackend(QtCore.QObject):
    activityChanged = QtCore.Signal()
    quitRequested = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.gremlinActive = False
        self.engine = None


@pytest.fixture
def tray(monkeypatch: pytest.MonkeyPatch) -> Iterator[SimpleNamespace]:
    from gremlin.ui import system_tray

    gui = system_tray.win32gui
    for name, fake in {
        "Shell_NotifyIcon": lambda *a: None,
        "LoadImage": lambda *a: 101,
        "RegisterWindowMessage": lambda _n: 49999,
        "RegisterClass": lambda _wc: 7,
        "CreateWindowEx": lambda *a: 55,
        "DestroyWindow": lambda *a: None,
        "UnregisterClass": lambda *a: None,
        "DestroyIcon": lambda *a: None,
    }.items():
        monkeypatch.setattr(gui, name, fake)
    monkeypatch.setattr(system_tray.win32api, "GetModuleHandle", lambda _n: 3)
    monkeypatch.setattr(system_tray.win32api, "GetSystemMetrics", lambda _n: 16)
    memory = system_tray.tray_memory
    monkeypatch.setattr(memory, "let_hidden_window_release_graphics", lambda w: None)
    monkeypatch.setattr(memory, "enter_tray", lambda w, e: None)
    monkeypatch.setattr(memory, "leave_tray", lambda w: None)
    backend = _TrayBackend()
    monkeypatch.setattr(system_tray, "Backend", lambda: backend)
    values: dict[tuple[str, ...], object] = {
        ("global", "general", "minimize-to-tray"): False,
        ("global", "internal", "tray-notice-shown"): True,
    }
    settings = SimpleNamespace(
        exists=lambda *key: tuple(key) in values,
        value=lambda *key: values[tuple(key)],
        set=lambda *kv: values.__setitem__(tuple(kv[:-1]), kv[-1]),
    )
    monkeypatch.setattr(system_tray, "Configuration", lambda: settings)
    window = _Window()
    icon = system_tray.SystemTrayIcon(window)  # type: ignore[arg-type]
    yield SimpleNamespace(icon=icon, window=window, values=values, module=system_tray)
    icon.release_resources()
    window.removeEventFilter(icon)


@pytest.mark.parametrize(
    "mode", [QtGui.QWindow.Visibility.Maximized, QtGui.QWindow.Visibility.FullScreen]
)
def test_s63_a_left_click_shows_the_window_as_it_was(
    tray: SimpleNamespace, mode: QtGui.QWindow.Visibility
) -> None:
    import win32con

    tray.window.setVisibility(mode)
    tray.window.hide()
    tray.window.calls.clear()
    tray.icon._system_tray_event_cb(55, tray.module._WM_TRAY, 0, win32con.WM_LBUTTONUP)
    assert tray.window.calls == [mode]


def test_s73_start_minimized_minimizes_and_goes_to_the_tray_when_on(
    tray: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    import joystick_gremlin as jg
    from gremlin.ui.backend import Backend

    monkeypatch.setattr(
        jg, "Configuration", lambda: SimpleNamespace(value=lambda *_key: "")
    )
    engine = SimpleNamespace(rootObjects=lambda: [tray.window])
    backend = SimpleNamespace(
        loadProfile=mock.Mock(), openLastProfile=mock.Mock(),
        activate_gremlin=mock.Mock(),
        minimize=lambda: Backend.klass.minimize(SimpleNamespace(engine=engine)),  # type: ignore[arg-type]
    )
    app = SimpleNamespace(backend=backend, syslog=mock.Mock())
    args = SimpleNamespace(profile=None, enable=False, start_minimized=True)

    # Minimize to tray off: minimized, on the taskbar.
    jg.JoystickGremlinApp.process_cmd_args(app, args)  # type: ignore[arg-type]
    assert tray.window.mode == QtGui.QWindow.Visibility.Minimized

    # On: minimized, then hidden to the tray.
    tray.window.setVisibility(QtGui.QWindow.Visibility.Windowed)
    tray.values[("global", "general", "minimize-to-tray")] = True
    tray.window.calls.clear()
    jg.JoystickGremlinApp.process_cmd_args(app, args)  # type: ignore[arg-type]
    assert tray.window.calls == [
        QtGui.QWindow.Visibility.Minimized, QtGui.QWindow.Visibility.Hidden
    ]


# --- S68: the old "Close to tray" becomes Minimize to tray ------------------


@pytest.fixture
def settings_file(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[pathlib.Path]:
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: None)
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    yield path
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


@pytest.mark.parametrize("close_to_tray", [True, False])
def test_s68_close_to_tray_on_gives_minimize_to_tray_on(
    settings_file: pathlib.Path, close_to_tray: bool
) -> None:
    import joystick_gremlin as jg
    from gremlin.types import PropertyType

    old = gremlin.config.Configuration()
    old.register(
        "global", "general", "close-to-tray", PropertyType.Bool, False, "", {}, True
    )
    old.set("global", "general", "close-to-tray", close_to_tray)
    old.save_now(str(settings_file))
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)

    jg.register_config_options()  # the next start
    cfg = gremlin.config.Configuration()
    assert cfg.value("global", "general", "minimize-to-tray") is close_to_tray


# --- S82: Ignore Windows display scaling is read by the next start ----------


@pytest.mark.parametrize("ignore", [True, False])
def test_s82_the_next_start_reads_the_new_windows_scaling_choice(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, ignore: bool
) -> None:
    import joystick_gremlin as jg
    from gremlin.ui import windows_scale_option

    folder = tmp_path / "Gremlin Platforms"
    folder.mkdir()
    path = folder / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: None)
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    try:
        windows_scale_option.register()
        model = windows_scale_option.WindowsScaleModel()
        model.setDisabled(ignore)  # the Options check box
        assert model.disabled is ignore
        gremlin.config.Configuration().save_now(str(path))
    finally:
        SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    # The new process reads the file itself, before Qt loads.
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert jg._windows_scaling_disabled() is ignore


def test_s82_cancel_puts_the_old_choice_back(
    settings_file: pathlib.Path,
) -> None:
    from gremlin.ui import windows_scale_option

    windows_scale_option.register()
    model = windows_scale_option.WindowsScaleModel()
    before = model.disabled
    model.setDisabled(not before)  # clicked
    model.setDisabled(before)  # Cancel (OptionWindowsScale.qml onCancelled)
    assert windows_scale_option.saved_disabled() is before


# --- S74, S76: dark/light switch at once; light mode has no white surfaces -


# Runs in its own process, like test_ui_scale: Qt teardown inside the test
# session can hang.
_LOOK_SCRIPT = r"""
import json, os, sys
from PySide6 import QtCore, QtGui, QtQml

app = QtGui.QGuiApplication(sys.argv)
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(sys.argv[1]), "Gremlin.Style", 1, 0, "Style")
engine = QtQml.QQmlApplicationEngine()
engine.addImportPath(sys.argv[2])
engine.rootContext().setContextProperty("backend", None)
engine.loadData(b'''
import QtQuick
import QtQuick.Controls
import Gremlin.Style
ApplicationWindow {
    function setDark(on) { Style.isDarkMode = on }
    function read() {
        var out = {}
        var tokens = ["background", "bgWell", "bgPage", "bgCard", "bgRaised",
            "bgSelected", "bgHover", "menuBg", "fg", "line"]
        for (var i = 0; i < tokens.length; ++i)
            out[tokens[i]] = String(Style[tokens[i]])
        var controls = {pane: _pane, field: _field, area: _area, bar: _bar,
            tabs: _tabs, popup: _popup}
        for (var name in controls)
            out["control." + name] = String(controls[name].background.color)
        return JSON.stringify(out)
    }
    Column {
        Pane { id: _pane }
        TextField { id: _field }
        TextArea { id: _area }
        ToolBar { id: _bar }
        TabBar { id: _tabs }
    }
    Popup { id: _popup }
}
''')
window = engine.rootObjects()[0]
for dark in (True, False, True):
    QtCore.QMetaObject.invokeMethod(
        window, "setDark", QtCore.Q_ARG("QVariant", dark))
    result = QtCore.QMetaObject.invokeMethod(
        window, "read", QtCore.Q_RETURN_ARG("QVariant"))
    print(result)
sys.stdout.flush()
os._exit(0)
"""


def _looks() -> list[dict[str, str]]:
    env = dict(
        os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_CONTROLS_STYLE="GremlinStyle"
    )
    result = subprocess.run(
        [sys.executable, "-c", _LOOK_SCRIPT, str(_ROOT / "qml" / "Style.qml"),
         str(_ROOT / "theme")],
        capture_output=True, text=True, timeout=60, env=env,
    )
    assert result.returncode == 0, result.stderr
    return [json.loads(line) for line in result.stdout.split()]


def _lightness(colour: str) -> float:
    c = QtGui.QColor(colour)
    return c.lightnessF()


def test_s74_s76_dark_mode_switches_at_once_and_light_mode_is_grey() -> None:
    dark, light, dark_again = _looks()
    # S74: every token and control background follows the switch, both ways,
    # without a restart.
    assert dark == dark_again
    assert [k for k in dark if dark[k] == light[k]] == []
    # S76: light mode is a grey mode: no surface or control is white.
    surfaces = {k: v for k, v in light.items() if k not in ("fg", "line")}
    white = {k: v for k, v in surfaces.items() if _lightness(v) > 0.85}
    assert white == {}


# --- S78: fonts come from the Style tokens only -----------------------------

_FAMILY = re.compile(r"""family\s*[:=]\s*["']([^"']+)["']""")
# Where the font names are defined: the Style tokens and the icon font loader.
_DEFINES_FONTS = {"qml/Style.qml", "qml/BootstrapIcons.qml"}


def test_s78_screens_name_no_font_family_themselves() -> None:
    found = {}
    for folder in ("qml", "theme", "action_plugins"):
        paths = [*(_ROOT / folder).rglob("*.qml"), *(_ROOT / folder).rglob("*.js")]
        for path in paths:
            name = path.relative_to(_ROOT).as_posix()
            if name in _DEFINES_FONTS:
                continue
            families = _FAMILY.findall(path.read_text(encoding="utf-8"))
            if families:
                found[name] = families
    assert found == {}
