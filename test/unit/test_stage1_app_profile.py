# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Stage 1 safety net: app shell, input, profile and action paths.

Covers these gap-list items (claude/gap-list.md, section 1):

- GL-003 (05 S1, S9, S104, Q2): every built-in action is registered at
  start, also on a PC without vJoy; can_create() only decides what Add
  Action offers. Map to vJoy with no vJoy device: registered, kept in the
  Options action list, not offered by Add Action, and harmless at Run.
- GL-007 (01 S83-S89): the tray logic, driven without a real icon.
- GL-008 (01 S81, S116, S124, S126, S127): restart after quit, data and
  logs folders and their fallback, the legacy device-file copy, Skip This
  Version and the release page.
- GL-009 (02 S45-S52, S61-S65, G10): the keyboard and mouse hook
  callbacks, key tables, Listen, macro recording, a missing device_db.json.
- GL-015 (04 S52, S63, S77): the real Backend on Load / New / Save,
  selectMode, an unknown Startup Mode, Swap onto a device with bindings.
- GL-017 (05 S8, S34, S63, S74, S99, S104): Run with an unfinished action,
  Merge Axis reuse then Cancel, save with the pane open, a new key's first
  action, Map to Mouse from a hat, the Load Profile action end to end.

Known gaps are written for the spec behaviour and marked xfail(strict) with
their GL id: GL-003 (load without vJoy), GL-033, GL-036, GL-039,
GL-055, GL-097, GL-164.

Nothing here touches the PC: no tray icon, hook, key or mouse output, no
vJoy; Windows calls are replaced by recorders.
"""

from __future__ import annotations

import ctypes
import re
import sys
import time
import types
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any, cast

sys.path.append(".")

import pytest
from PySide6 import QtCore, QtGui

import dill
from gremlin import (
    clock,
    code_runner,
    config,
    device_initialization,
    event_handler,
    keyboard,
    mode_manager,
    plugin_manager,
    sendinput,
    shared_state,
    swap_devices,
    util,
    windows_event_hook,
)
from gremlin.base_classes import Value
from gremlin.common import SingletonMetaclass
from gremlin.logical_device import LogicalDevice
from gremlin.profile import Profile
from gremlin.types import HatDirection, InputType, MouseButton

_ROOT = Path(__file__).resolve().parents[2]
_STICK = uuid.UUID("55555555-6666-7777-8888-999999999999")
_OTHER_STICK = uuid.UUID("11111111-2222-3333-4444-555555555555")
_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
# Qt objects a test made and other objects still point at (signal links);
# _release_kept unhooks them from the program-wide signals after the test.
_KEEP: list[object] = []


def _global_signals() -> list[QtCore.SignalInstance]:
    """Every signal of the program-wide objects models hook into."""
    from gremlin.signal import signal

    owners = (
        signal,
        event_handler.EventListener(),
        event_handler.EventHandler(),
        mode_manager.ModeManager(),
    )
    return [
        getattr(owner, name)
        for owner in owners
        for name in dir(type(owner))
        if isinstance(getattr(type(owner), name, None), QtCore.Signal)
    ]


def _own_slots(obj: QtCore.QObject) -> list[object]:
    """The methods and signals obj's program classes define."""
    found: dict[str, object] = {}
    for cls in type(obj).__mro__:
        if not cls.__module__.startswith(("gremlin", "action_plugins")):
            continue
        for name, value in vars(cls).items():
            if name.startswith("__") or name in found:
                continue
            if isinstance(value, (types.FunctionType, QtCore.Signal)):
                found[name] = getattr(obj, name)
    return list(found.values())


def _release(obj: object, signals: list[QtCore.SignalInstance]) -> None:
    """Disconnects obj (and its QObject children) from the program-wide
    signals, so a later test's profile change doesn't reach it."""
    import warnings

    if not isinstance(obj, QtCore.QObject):
        return
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # "Failed to disconnect"
        for target in (obj, *obj.findChildren(QtCore.QObject)):
            for slot in _own_slots(target):
                for sig in signals:
                    try:
                        sig.disconnect(slot)
                    except (RuntimeError, TypeError):
                        pass


@pytest.fixture(autouse=True)
def _release_kept() -> Iterator[None]:
    start = len(_KEEP)
    yield
    made = _KEEP[start:]
    del _KEEP[start:]
    if made:
        signals = _global_signals()
        for obj in made:
            _release(obj, signals)


def _wait_for(condition: Callable[[], bool], limit: float = 10.0) -> bool:
    """Polls (running Qt events) until condition holds or limit seconds pass."""
    deadline = clock.monotonic() + limit
    while clock.monotonic() < deadline:
        QtCore.QCoreApplication.processEvents()
        if condition():
            return True
        clock.sleep(0.01)
    QtCore.QCoreApplication.processEvents()
    return condition()


def _create(name: str, kind: InputType = InputType.JoystickButton) -> Any:  # noqa: ANN401
    return plugin_manager.PluginManager().create_instance(name, kind)


def _kids(item: Any, index: int = 0) -> list:  # noqa: ANN401
    return item.action_sequences[index].root_action.get_actions()[0]


def _item(profile: Profile, hw: int, kind: InputType = InputType.JoystickButton,
          device: uuid.UUID = _STICK, mode: str = "Default") -> Any:  # noqa: ANN401
    return profile.get_input_item(device, kind, hw, mode, create_if_missing=True)


@pytest.fixture
def profile() -> Iterator[Profile]:
    before = shared_state.current_profile
    LogicalDevice().reset()
    p = Profile()
    shared_state.current_profile = p
    yield p
    shared_state.current_profile = before
    LogicalDevice().reset()


@pytest.fixture
def settings_kept() -> Iterator[Callable[..., None]]:
    """Puts back the program settings a test changes through the real
    Configuration (call keep(*key) before changing one)."""
    cfg = config.Configuration()
    kept: list[tuple[tuple[str, ...], Any]] = []

    def keep(*key: str) -> None:
        kept.append((key, cfg.value(*key)))

    yield keep
    for key, value in reversed(kept):
        cfg.set(*key, value)


# --- GL-003: built-in actions on a PC without vJoy -------------------------


def _editor_root(profile: Profile, hw: int) -> Any:  # noqa: ANN401
    """The root action's model of a new binding on stick button hw, as the
    action editor gets it."""
    from gremlin.ui.profile import InputItemBindingModel, InputItemModel

    item = _item(profile, hw)
    binding = item.add_item_binding()
    owner = InputItemModel(item, 0, None)
    model = InputItemBindingModel(binding, owner)
    _KEEP.extend([owner, model])
    return next(
        m for m in model._action_models.values() if m.action_data.tag == "root"
    )


@pytest.fixture
def no_vjoy(monkeypatch: pytest.MonkeyPatch) -> None:
    """A PC with no vJoy device (the fake driver's vJoy 1 left out)."""
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])


@pytest.fixture
def started_without_vjoy(
    monkeypatch: pytest.MonkeyPatch, no_vjoy: None
) -> plugin_manager.PluginManager:
    """The action plugins as a start on a PC without vJoy finds them: a
    fresh manager through the real discovery, used as the program's one
    while the test runs (put back after)."""
    monkeypatch.setattr(plugin_manager.QtQml, "qmlRegisterType", lambda *a: 1)
    manager = object.__new__(plugin_manager.PluginManager)
    plugin_manager.PluginManager.__init__(manager)
    monkeypatch.setitem(
        SingletonMetaclass._instances, plugin_manager.PluginManager, manager
    )
    return manager


def test_every_built_in_action_is_registered_without_vjoy(
    started_without_vjoy: plugin_manager.PluginManager,
) -> None:
    manager = started_without_vjoy
    assert "map-to-vjoy" in manager.tag_map  # was left out: no vJoy device
    assert manager.get_class("Map to vJoy").tag == "map-to-vjoy"
    # Every built-in plugin folder is registered.
    folders = {
        p.parent.name
        for p in (_ROOT / "action_plugins").glob("*/__init__.py")
    }
    modules = {cls.__module__.split(".")[-1] for cls in manager.repository.values()}
    assert folders <= modules


def test_add_action_does_not_offer_map_to_vjoy_without_vjoy(
    started_without_vjoy: plugin_manager.PluginManager,
    profile: Profile,
    action_order: None,
) -> None:
    for kind, actions in started_without_vjoy.type_action_map.items():
        names = [a.name for a in actions]
        assert "Map to vJoy" not in names, kind
        assert "Map to Mouse" in names, kind

    # The list the Add Action menus and the action selector read.
    root = _editor_root(profile, 1)
    offered = root.compatibleActions
    assert "Map to vJoy" not in offered and "Macro" in offered
    # Asked for anyway (an old menu): nothing is added, nothing breaks.
    root.appendAction("Map to vJoy", "children")
    assert _kids(_item(profile, 1)) == []


def test_add_action_offers_map_to_vjoy_with_vjoy(
    profile: Profile, action_order: None
) -> None:
    root = _editor_root(profile, 1)
    assert "Map to vJoy" in root.compatibleActions
    root.appendAction("Map to vJoy", "children")
    assert [a.tag for a in _kids(_item(profile, 1))] == ["map-to-vjoy"]


@pytest.fixture
def action_order(settings_kept: Callable[..., None]) -> None:
    """The Options action list as a start leaves it (every action listed)."""
    import joystick_gremlin

    settings_kept("action", "general", "action-priorities")
    joystick_gremlin.update_action_priorities()


def test_options_action_list_keeps_map_to_vjoy_without_vjoy(
    started_without_vjoy: plugin_manager.PluginManager,
    settings_kept: Callable[..., None],
) -> None:
    import joystick_gremlin

    key = ("action", "general", "action-priorities")
    settings_kept(*key)
    cfg = config.Configuration()
    chosen = [["Macro", True], ["Map to vJoy", False]]
    cfg.set(*key, chosen + [[n, True] for n, _s in cfg.value(*key)
                            if n not in ("Macro", "Map to vJoy")])
    joystick_gremlin.update_action_priorities()  # what a start runs
    after = cfg.value(*key)
    # Kept, with the user's order and choice (was dropped from the list).
    assert [list(v) for v in after[:2]] == chosen


def test_a_profile_with_map_to_vjoy_opens_without_vjoy(
    profile: Profile, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vjoy = _create("Map to vJoy")
    vjoy.vjoy_input_id = 7
    _item(profile, 1).add_item_binding().root_action.insert_action(vjoy, "children")
    path = tmp_path / "with_vjoy.xml"
    profile.to_xml(path)

    # The next start has no vJoy.
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(plugin_manager.QtQml, "qmlRegisterType", lambda *a: 1)
    manager = object.__new__(plugin_manager.PluginManager)
    plugin_manager.PluginManager.__init__(manager)
    monkeypatch.setitem(
        SingletonMetaclass._instances, plugin_manager.PluginManager, manager
    )
    opened = Profile()
    opened.from_xml(path)
    kept = _kids(opened.get_input_item(_STICK, InputType.JoystickButton, 1, "Default"))
    assert [(a.tag, a.vjoy_input_id) for a in kept] == [("map-to-vjoy", 7)]
    # And a save keeps it: the same action, id and values unchanged.
    opened.to_xml(tmp_path / "saved.xml")
    assert _vjoy_actions(tmp_path / "saved.xml") == _vjoy_actions(path)
    assert len(_vjoy_actions(path)) == 1


def _vjoy_actions(path: Path) -> list[bytes]:
    """The profile file's Map to vJoy actions, as XML (id, properties)."""
    from xml.etree import ElementTree

    tree = ElementTree.parse(path)
    return [
        ElementTree.canonicalize(ElementTree.tostring(node), strip_text=True).encode()
        for node in tree.iter("action")
        if node.get("type") == "map-to-vjoy"
    ]


def test_map_to_vjoy_at_run_with_no_vjoy_device_does_nothing(
    profile: Profile, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import output

    asked: list[tuple[tuple, bool]] = []
    opened: list[object] = []
    real_write, real_open = output.write_vjoy, output._open_vjoy

    def write(*args: Any) -> bool:  # noqa: ANN401
        ok = real_write(*args)
        asked.append((args, ok))
        return ok

    def open_vjoy(vjoy_id: int) -> Any:  # noqa: ANN401
        dev = real_open(vjoy_id)
        opened.append(dev)
        return dev

    monkeypatch.setattr(output, "write_vjoy", write)
    monkeypatch.setattr(output, "_open_vjoy", open_vjoy)
    vjoy = _create("Map to vJoy")
    vjoy.vjoy_device_id = 9  # no such device on this PC
    functor = vjoy.functor(vjoy)
    event = event_handler.Event(
        InputType.JoystickButton, 1, _STICK, "Default", is_pressed=True,
        raw_value=True,
    )
    functor(event, Value(True))  # no exception, nothing sent
    event.is_pressed = False
    functor(event, Value(False))
    # Press and release reached the output module, which sent neither.
    assert [args[:2] for args, _ok in asked] == [(9, "button"), (9, "button")]
    assert [ok for _args, ok in asked] == [False, False]
    assert all(dev is None for dev in opened)


# --- GL-007: the tray, without a real icon ---------------------------------


class _Window(QtCore.QObject):
    """Stands in for the main window."""

    visibilityChanged = QtCore.Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self.shown = True
        self.calls: list[object] = []

    def visibility(self) -> QtGui.QWindow.Visibility:
        return QtGui.QWindow.Visibility.Windowed

    def isVisible(self) -> bool:
        return self.shown

    def hide(self) -> None:
        self.shown = False
        self.calls.append("hide")

    def setVisibility(self, mode: object) -> None:
        self.shown = True
        self.calls.append("show")

    def raise_(self) -> None:
        self.calls.append("raise")

    def requestActivate(self) -> None:
        self.calls.append("activate")


class _TrayBackend(QtCore.QObject):
    activityChanged = QtCore.Signal()
    quitRequested = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self.gremlinActive = False
        self.engine = None
        self.toggled = 0

    def toggleActiveState(self) -> None:
        self.toggled += 1


class _Settings:
    def __init__(self) -> None:
        self.values: dict[tuple[str, ...], object] = {
            ("global", "general", "minimize-to-tray"): False,
            ("global", "internal", "tray-notice-shown"): False,
        }

    def exists(self, *key: str) -> bool:
        return tuple(key) in self.values

    def value(self, *key: str) -> object:
        return self.values[tuple(key)]

    def set(self, *key_and_value: object) -> None:
        *key, value = key_and_value
        self.values[tuple(str(k) for k in key)] = value


_IDLE_ICON, _ACTIVE_ICON = 101, 202


@pytest.fixture
def tray(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.SimpleNamespace]:
    """A SystemTrayIcon with every Windows call recorded instead of made."""
    from gremlin.ui import system_tray

    calls: list[tuple] = []
    gui = system_tray.win32gui

    def notify(message: int, data: tuple) -> None:
        calls.append(("notify", message, data))

    def load_image(_h: int, path: str, *_a: object) -> int:
        return _ACTIVE_ICON if path.endswith("icon_active.ico") else _IDLE_ICON

    menu: list[str] = []
    for name, fake in {
        "Shell_NotifyIcon": notify,
        "LoadImage": load_image,
        "RegisterWindowMessage": lambda _n: 49999,
        "RegisterClass": lambda _wc: 7,
        "CreateWindowEx": lambda *a: 55,
        "CreatePopupMenu": lambda: 66,
        "AppendMenu": lambda _m, _f, _i, text: menu.append(text),
        "TrackPopupMenu": lambda *a: calls.append(("track",)),
        "PostMessage": lambda *a: None,
        "DestroyMenu": lambda *a: None,
        "SetForegroundWindow": lambda *a: None,
        "DestroyWindow": lambda *a: None,
        "UnregisterClass": lambda *a: None,
        "DestroyIcon": lambda *a: None,
    }.items():
        monkeypatch.setattr(gui, name, fake)
    monkeypatch.setattr(system_tray.win32api, "GetModuleHandle", lambda _n: 3)
    monkeypatch.setattr(system_tray.win32api, "GetSystemMetrics", lambda _n: 16)
    trayed: list[str] = []
    memory = system_tray.tray_memory
    monkeypatch.setattr(memory, "let_hidden_window_release_graphics", lambda w: None)
    monkeypatch.setattr(memory, "enter_tray", lambda w, e: trayed.append("enter"))
    monkeypatch.setattr(memory, "leave_tray", lambda w: trayed.append("leave"))
    backend = _TrayBackend()
    monkeypatch.setattr(system_tray, "Backend", lambda: backend)
    settings = _Settings()
    monkeypatch.setattr(system_tray, "Configuration", lambda: settings)
    window = _Window()
    icon = system_tray.SystemTrayIcon(window)  # type: ignore[arg-type]
    yield types.SimpleNamespace(
        icon=icon, window=window, backend=backend, settings=settings,
        calls=calls, menu=menu, trayed=trayed, module=system_tray, gui=gui,
    )
    icon.release_resources()
    window.removeEventFilter(icon)


def _notified(tray: types.SimpleNamespace, message: int) -> list[tuple]:
    return [c[2] for c in tray.calls if c[0] == "notify" and c[1] == message]


def test_tray_icon_follows_run_and_stop(tray: types.SimpleNamespace) -> None:
    added = _notified(tray, tray.gui.NIM_ADD)
    assert added and added[0][4] == _IDLE_ICON
    assert added[0][5] == "Gremlin-Platforms"
    tray.backend.gremlinActive = True
    tray.backend.activityChanged.emit()
    assert _notified(tray, tray.gui.NIM_MODIFY)[-1][4] == _ACTIVE_ICON
    tray.backend.gremlinActive = False
    tray.backend.activityChanged.emit()
    assert _notified(tray, tray.gui.NIM_MODIFY)[-1][4] == _IDLE_ICON


def test_tray_clicks_and_menu(tray: types.SimpleNamespace) -> None:
    import win32con

    wm_tray = tray.module._WM_TRAY
    tray.window.shown = False
    tray.icon._system_tray_event_cb(55, wm_tray, 0, win32con.WM_LBUTTONUP)
    assert tray.window.shown and tray.window.calls[-3:] == ["show", "raise", "activate"]

    tray.icon._system_tray_event_cb(55, wm_tray, 0, win32con.WM_RBUTTONUP)
    assert [t for t in tray.menu if t] == [
        "Hide Gremlin-Platforms", "Run Profile", "Exit Gremlin-Platforms"
    ]
    tray.menu.clear()
    tray.window.shown = False
    tray.backend.gremlinActive = True
    tray.icon._system_tray_event_cb(55, wm_tray, 0, win32con.WM_RBUTTONUP)
    assert [t for t in tray.menu if t] == [
        "Show Gremlin-Platforms", "Stop Profile", "Exit Gremlin-Platforms"
    ]
    toggle = tray.module._ID_TOGGLE
    tray.icon._handle_context_menu_cb(55, win32con.WM_COMMAND, toggle, 0)
    assert tray.backend.toggled == 1
    tray.icon._handle_context_menu_cb(55, win32con.WM_COMMAND, tray.module._ID_SHOW, 0)
    assert tray.window.shown


class _XClose(QtGui.QCloseEvent):
    """The main window's X: a close from Windows (spontaneous), GL-111."""

    def spontaneous(self) -> bool:
        return True


def test_minimize_to_tray_hides_on_minimize_and_close(
    tray: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    saved: list[object] = []
    monkeypatch.setattr(tray.module.window_placement, "save_window", saved.append)
    minimized = QtGui.QWindow.Visibility.Minimized
    close = _XClose()

    # Off (the default): minimize stays minimized, X closes.
    tray.window.visibilityChanged.emit(minimized)
    assert tray.window.shown
    assert tray.icon.eventFilter(tray.window, close) is False

    tray.settings.values[("global", "general", "minimize-to-tray")] = True
    tray.window.visibilityChanged.emit(minimized)
    assert not tray.window.shown
    tray.window.shown = True
    close = _XClose()
    assert tray.icon.eventFilter(tray.window, close) is True
    assert not close.isAccepted() and not tray.window.shown
    assert saved == [tray.window]  # GL-112: its place is kept
    # Hidden: pages unloaded; shown again: loaded again.
    tray.window.visibilityChanged.emit(QtGui.QWindow.Visibility.Hidden)
    tray.window.visibilityChanged.emit(QtGui.QWindow.Visibility.Windowed)
    assert tray.trayed == ["enter", "leave"]


def test_x_says_still_running_once(
    tray: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(tray.module.window_placement, "save_window", lambda w: None)
    tray.settings.values[("global", "general", "minimize-to-tray")] = True
    for _ in range(3):
        tray.window.shown = True
        tray.icon.eventFilter(tray.window, _XClose())
    balloons = [
        d for d in _notified(tray, tray.gui.NIM_MODIFY) if d[2] == tray.gui.NIF_INFO
    ]
    assert len(balloons) == 1
    assert "still running" in balloons[0][8]
    assert tray.settings.values[("global", "internal", "tray-notice-shown")] is True


def test_tray_icon_comes_back_after_explorer_restarts(
    tray: types.SimpleNamespace,
) -> None:
    tray.calls.clear()
    tray.icon._taskbar_created_cb(55, 49999, 0, 0)
    order = [c[1] for c in tray.calls if c[0] == "notify"]
    assert order[:2] == [tray.gui.NIM_DELETE, tray.gui.NIM_ADD]
    assert tray.icon._icon_present


def test_tray_exit_brings_the_window_back_first(tray: types.SimpleNamespace) -> None:
    import win32con

    seen: list[bool] = []
    tray.backend.quitRequested.connect(lambda: seen.append(tray.window.shown))
    tray.window.shown = False
    tray.icon._handle_context_menu_cb(55, win32con.WM_COMMAND, tray.module._ID_QUIT, 0)
    assert seen == [True]  # visible when the unsaved-changes questions come


def test_no_tray_icon_never_hides_the_window(
    tray: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The icon could not be added (Explorer not running): the window must
    # stay reachable, so minimize and X behave as without the option.
    tray.icon._icon_present = False
    tray.settings.values[("global", "general", "minimize-to-tray")] = True
    tray.window.visibilityChanged.emit(QtGui.QWindow.Visibility.Minimized)
    assert tray.window.shown
    close = _XClose()
    assert tray.icon.eventFilter(tray.window, close) is False


# --- GL-008: restart, folders, legacy copy, update skip --------------------


def test_restart_quits_the_usual_way_and_a_cancel_clears_it(tmp_path: Path) -> None:
    """A restart with unsaved changes, in the running program off-screen (its
    own process): the usual question; Cancel calls the restart off; Discard
    quits through Qt.quit() with the restart still set."""
    from test.unit.test_stage1_button_map import (  # pyright: ignore[reportMissingImports]
        _run,
    )

    out = _run("quit", tmp_path / "home")
    assert out["restart-asks"] == {"title": "Unsaved Changes", "restart-set": True}
    assert out["restart-cancel"] == {"restart-set": False, "quit": 0}
    assert out["restart-discard"] == {"quit": [True], "restart-set": True}
    # Cancel in the display panels' own question (needs unsaved panel
    # options) is still read from the source.
    qml = (_ROOT / "qml" / "Main.qml").read_text(encoding="utf-8")
    leave = re.search(r"function cancelDisplayLeave\(\)\s*\{(.*?)\n    \}", qml, re.S)
    assert leave and "backend.setRestartOnExit(false)" in leave.group(1)
    # main() after the event loop can't be driven here (it ends the
    # process): it starts the program again only when restart_on_exit is
    # still set.
    main = (_ROOT / "joystick_gremlin.py").read_text(encoding="utf-8")
    tail = main[main.index("app.exec()"):]
    assert "backend.restart_on_exit" in tail and "startDetached" in tail


def test_backend_restart_request(real_backend: Any) -> None:  # noqa: ANN401
    asked: list[bool] = []
    real_backend.restartRequested.connect(lambda: asked.append(True))
    real_backend.requestRestart()
    assert asked == [True]
    assert real_backend.restart_on_exit is False  # only the quit path sets it
    real_backend.setRestartOnExit(True)
    assert real_backend.restart_on_exit is True
    real_backend.setRestartOnExit(False)


@pytest.fixture
def folder_settings(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Options > Folders values, read through the real Configuration."""
    chosen: dict[str, str] = {}
    settings = type(config.Configuration())
    real_value, real_exists = settings.value, settings.exists

    def value(self: object, *key: str) -> object:
        if key[:2] == ("global", "files") and key[2] in chosen:
            return chosen[key[2]]
        return real_value(self, *key)

    def exists(self: object, *key: str) -> bool:
        if key[:2] == ("global", "files") and key[2] in chosen:
            return True
        return real_exists(self, *key)

    monkeypatch.setattr(settings, "value", value)
    monkeypatch.setattr(settings, "exists", exists)
    return chosen


def test_data_and_logs_folders_follow_options_and_fall_back(
    folder_settings: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    default = tmp_path / "Gremlin Platforms"
    folder_settings["data-folder"] = ""  # the defaults
    folder_settings["logs-folder"] = ""
    monkeypatch.setattr(util, "userprofile_path", lambda: str(default))
    assert Path(util.data_folder()) == default
    assert util.logs_dir() == default / "logs"

    chosen = tmp_path / "elsewhere"
    folder_settings["data-folder"] = str(chosen)
    assert Path(util.data_folder()) == chosen.resolve()
    assert util.logs_dir() == chosen.resolve() / "logs"
    assert util.logs_dir().is_dir()

    own_logs = tmp_path / "my logs"
    folder_settings["logs-folder"] = str(own_logs)
    assert util.logs_dir() == own_logs.resolve()

    # A chosen folder that can't be made falls back to the default.
    blocker = tmp_path / "a file"
    blocker.write_text("x", encoding="utf-8")
    folder_settings["data-folder"] = str(blocker / "data")
    assert Path(util.data_folder()) == default
    folder_settings["logs-folder"] = str(blocker / "logs")
    assert util.logs_dir() == default / "logs"


def test_a_data_folder_that_cannot_be_made_does_not_stop_folder_lookups(
    folder_settings: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocker = tmp_path / "a file"
    blocker.write_text("x", encoding="utf-8")
    home = blocker / "Gremlin Platforms"
    monkeypatch.setattr(util, "userprofile_path", lambda: str(home))
    folder_settings["data-folder"] = ""  # the defaults
    folder_settings["logs-folder"] = ""
    util.logs_dir()  # must not raise


def _release_doc(version: str) -> dict:
    return {
        "tag_name": f"Gremlin-Platforms-R1-{version}",
        "html_url": f"https://github.com/x/y/releases/tag/{version}",
        "assets": [{
            "name": f"Gremlin-Platforms-R1-{version}-Setup.exe",
            "browser_download_url": "https://github.com/x/y/releases/download/t/s.exe",
            "size": 1000,
            "digest": "sha256:" + "a" * 64,
        }],
    }


class _Reply:
    """A finished update-check reply carrying doc."""

    def __init__(self, doc: dict) -> None:
        import json

        self._data = QtCore.QByteArray(json.dumps(doc).encode("utf-8"))

    def error(self) -> object:
        from PySide6 import QtNetwork

        return QtNetwork.QNetworkReply.NetworkError.NoError

    def readAll(self) -> QtCore.QByteArray:
        return self._data

    def deleteLater(self) -> None:
        pass


def test_skip_this_version_and_the_release_page(
    settings_kept: Callable[..., None], monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import update_model

    settings_kept("global", "internal", "skipped-update-version")
    opened: list[str] = []
    monkeypatch.setattr(
        QtGui.QDesktopServices, "openUrl", lambda url: opened.append(url.toString())
    )
    newer = "999.0.0"
    model = update_model.UpdateModel()
    _KEEP.append(model)
    offers: list[bool] = []
    model.offerUpdate.connect(lambda: offers.append(True))

    model._manual = False  # the start-up check
    model._on_checked(_Reply(_release_doc(newer)))  # type: ignore[arg-type]
    assert model.state == "available" and offers == [True]
    model.openReleasePage()
    assert opened == [f"https://github.com/x/y/releases/tag/{newer}"]
    model.skipVersion()

    model._manual = False
    model._on_checked(_Reply(_release_doc(newer)))  # type: ignore[arg-type]
    assert model.state == "upToDate" and offers == [True]
    model._manual = True  # a check the user asked for still shows it
    model._on_checked(_Reply(_release_doc(newer)))  # type: ignore[arg-type]
    assert model.state == "available" and offers == [True, True]


# --- GL-009: hooks, key tables, Listen, macro recording ---------------------


@pytest.fixture
def hook_calls(monkeypatch: pytest.MonkeyPatch) -> types.SimpleNamespace:
    """The hook callbacks with Windows' next-hook call recorded, and the
    program's key and mouse callbacks replaced by recorders."""
    passed: list[tuple] = []
    keys: list[windows_event_hook.KeyEvent] = []
    mice: list[windows_event_hook.MouseEvent] = []

    def next_hook(hook: object, n_code: int, w_param: int, l_param: int) -> int:
        passed.append((n_code, w_param))
        return 0

    monkeypatch.setattr(
        windows_event_hook, "user32", types.SimpleNamespace(CallNextHookEx=next_hook)
    )
    monkeypatch.setattr(windows_event_hook, "g_keyboard_callbacks", [keys.append])
    monkeypatch.setattr(windows_event_hook, "g_mouse_callbacks", [mice.append])
    return types.SimpleNamespace(passed=passed, keys=keys, mice=mice)


def _key(n_code: int, w_param: int, scan: int, flags: int = 0) -> None:
    msg = windows_event_hook.KBDLLHOOKSTRUCT(0, scan, flags, 0, 0)
    windows_event_hook.process_keyboard_event(n_code, w_param, ctypes.addressof(msg))


def _mouse(w_param: int, data: int = 0) -> None:
    msg = windows_event_hook.MSLLHOOKSTRUCT(mouseData=data)
    windows_event_hook.process_mouse_event(0, w_param, ctypes.addressof(msg))


def test_keyboard_hook_reports_keys_and_passes_every_event_on(
    hook_calls: types.SimpleNamespace,
) -> None:
    _key(0, 0x0100, 0x1E)  # A down
    _key(0, 0x0101, 0x1E)  # A up
    _key(0, 0x0104, 0x38)  # Alt down (system key)
    _key(0, 0x0100, 0x1D, flags=0x01)  # Right Ctrl: extended
    _key(0, 0x0100, 0x1E, flags=0x10)  # injected
    _key(0, 0x0100, 541)  # AltGr's extra Ctrl: dropped
    _key(-1, 0x0100, 0x1E)  # not for us
    _key(0, 0x0100, 0)  # no scan code
    got = [(k.scan_code, k.is_extended, k.is_pressed, k.is_injected)
           for k in hook_calls.keys]
    assert got == [
        (0x1E, False, True, False),
        (0x1E, False, False, False),
        (0x38, False, True, False),
        (0x1D, True, True, False),
        (0x1E, False, True, True),
    ]
    # Windows and games get every event (S45).
    assert len(hook_calls.passed) == 8


def test_mouse_hook_reports_buttons_and_the_wheel(
    hook_calls: types.SimpleNamespace,
) -> None:
    hook = windows_event_hook
    _mouse(hook.WM_MOUSEMOVE)  # ignored
    for down, up in ((hook.WM_LBUTTONDOWN, hook.WM_LBUTTONUP),
                     (hook.WM_RBUTTONDOWN, hook.WM_RBUTTONUP),
                     (hook.WM_MBUTTONDOWN, hook.WM_MBUTTONUP)):
        _mouse(down)
        _mouse(up)
    _mouse(hook.WM_XBUTTONDOWN, 1 << 16)
    _mouse(hook.WM_XBUTTONUP, 1 << 16)
    _mouse(hook.WM_XBUTTONDOWN, 2 << 16)
    _mouse(hook.WM_MOUSEWHEEL, 120 << 16)
    _mouse(hook.WM_MOUSEWHEEL, 65416 << 16)
    got = [(m.button_id, m.is_pressed) for m in hook_calls.mice]
    assert got == [
        (MouseButton.Left, True), (MouseButton.Left, False),
        (MouseButton.Right, True), (MouseButton.Right, False),
        (MouseButton.Middle, True), (MouseButton.Middle, False),
        (MouseButton.Back, True), (MouseButton.Back, False),
        (MouseButton.Forward, True),
        (MouseButton.WheelUp, True), (MouseButton.WheelDown, True),
    ]
    assert len(hook_calls.passed) == 12


def test_key_tables() -> None:
    enter = keyboard.key_from_name("enter")
    numpad_enter = keyboard.key_from_name("npenter")
    assert (enter.scan_code, enter.is_extended) == (numpad_enter.scan_code, False)
    assert numpad_enter.is_extended and enter != numpad_enter
    assert keyboard.key_from_code(0x1C, True) == numpad_enter
    left = keyboard.key_from_name("Left Control")
    assert left != keyboard.key_from_name("rightcontrol")
    modifiers = keyboard.modifier_keys()
    assert keyboard.key_from_name("rightshift") in modifiers
    assert keyboard.key_from_name("rightalt") in modifiers
    # Every named key is found again from its code.
    for name, key in keyboard.g_name_to_key.items():
        assert keyboard.key_from_code(key.scan_code, key.is_extended) == key, name
    with pytest.raises(keyboard.KeyboardError):
        keyboard.key_from_name("no such key name")


def test_a_held_key_is_one_press_and_one_release(
    hook_calls: types.SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    listener = event_handler.EventListener()
    monkeypatch.setattr(
        windows_event_hook, "g_keyboard_callbacks", [listener._keyboard_handler]
    )
    seen: list[tuple] = []

    def record(event: event_handler.Event) -> None:
        seen.append((event.identifier, event.is_pressed))

    listener.keyboard_event.connect(record)
    try:
        for _ in range(4):  # Windows repeats a held key
            _key(0, 0x0100, 0x1E)
        _key(0, 0x0101, 0x1E)
    finally:
        listener.keyboard_event.disconnect(record)
    assert seen == [((0x1E, False), True), ((0x1E, False), False)]


@pytest.fixture
def highlighting_kept() -> Iterator[None]:
    before = shared_state.suspend_input_highlighting()
    yield
    shared_state.set_suspend_input_highlighting(before)


def _listener(kinds: list[InputType], several: bool = False) -> tuple[Any, list]:  # noqa: ANN401
    from gremlin.ui.util import InputListenerModel

    model = InputListenerModel()
    _KEEP.append(model)
    done: list[list] = []
    model.listeningTerminated.connect(lambda inputs: done.append(list(inputs)))
    # As the QML sets them.
    model.setProperty("eventTypes", [InputType.to_string(k) for k in kinds])
    model.setProperty("multipleInputs", several)
    model.setProperty("enabled", True)
    return model, done


def _button(
    number: int, pressed: bool, device: uuid.UUID = _STICK
) -> event_handler.Event:
    return event_handler.Event(
        InputType.JoystickButton, number, device, "Default", is_pressed=pressed,
        raw_value=pressed,
    )


def test_listen_single_input_ends_at_the_first_press(highlighting_kept: None) -> None:
    model, done = _listener([InputType.JoystickButton])
    assert shared_state.suspend_input_highlighting()  # paused while listening
    model._joy_event_cb(_button(3, True))
    assert [[e.identifier for e in d] for d in done] == [[3]]


def test_listen_several_inputs_ends_at_the_first_release(
    highlighting_kept: None,
) -> None:
    model, done = _listener([InputType.JoystickButton], several=True)
    model._joy_event_cb(_button(3, True))
    model._joy_event_cb(_button(5, True))
    assert done == []
    model._joy_event_cb(_button(3, False))
    assert sorted(e.identifier for e in done[0]) == [3, 5]


def test_listen_ignores_logical_and_virtual_inputs_and_a_centred_hat(
    highlighting_kept: None,
) -> None:
    model, done = _listener([InputType.JoystickButton, InputType.JoystickHat])
    model._joy_event_cb(_button(1, True, dill.UUID_LogicalDevice))
    model._joy_event_cb(_button(1, True, dill.UUID_Virtual))
    centre = event_handler.Event(
        InputType.JoystickHat, 1, _STICK, "Default", value=HatDirection.Center
    )
    model._joy_event_cb(centre)
    assert done == []
    north = event_handler.Event(
        InputType.JoystickHat, 1, _STICK, "Default", value=HatDirection.North
    )
    model._joy_event_cb(north)
    assert [e.value for e in done[0]] == [HatDirection.North]


def test_listen_takes_the_mouse_wheel_at_once(highlighting_kept: None) -> None:
    model, done = _listener([InputType.Mouse], several=True)
    wheel = event_handler.Event(
        InputType.Mouse, cast(Any, MouseButton.WheelUp), dill.UUID_Keyboard, "Default",
        is_pressed=True,
    )
    model._mouse_event_cb(wheel)
    assert [e.identifier for e in done[0]] == [MouseButton.WheelUp]


def test_holding_esc_cancels_listen(highlighting_kept: None) -> None:
    model, done = _listener([InputType.JoystickButton])
    esc = keyboard.key_from_name("esc")
    model._kb_event_cb(event_handler.Event(
        InputType.Keyboard, (esc.scan_code, esc.is_extended), dill.UUID_Keyboard,
        "Default", is_pressed=True,
    ))
    assert done == []
    assert _wait_for(lambda: bool(done), limit=10.0)
    assert done == [[]]


# stop() disconnects every signal, also those it never connected (a warning).
@pytest.mark.filterwarnings("ignore:libpyside. Failed to disconnect:RuntimeWarning")
def test_macro_recording_records_a_key_from_the_hook(
    highlighting_kept: None, hook_calls: types.SimpleNamespace,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui.util import MacroRecorder

    listener = event_handler.EventListener()
    monkeypatch.setattr(
        windows_event_hook, "g_keyboard_callbacks", [listener._keyboard_handler]
    )
    recorded: list[Any] = []
    recorder = MacroRecorder(recorded.append)
    recorder.start([InputType.Keyboard], False)
    try:
        _key(0, 0x0100, 0x1E)
        _key(0, 0x0101, 0x1E)
        assert _wait_for(lambda: len(recorded) >= 2)
    finally:
        recorder.stop()
    assert [(a.key.scan_code, a.is_pressed) for a in recorded] == [
        (0x1E, True), (0x1E, False)
    ]


def test_a_missing_device_database_gives_plain_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gremlin import input_cache

    monkeypatch.setattr(
        input_cache.util, "resource_path", lambda rel: str(tmp_path / rel)
    )
    db = object.__new__(input_cache.DeviceDatabase)
    input_cache.DeviceDatabase.__init__(db)
    device = device_initialization.physical_devices()[0]
    assert db.get_mapping(device) is None


def test_a_damaged_device_database_gives_plain_names(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from gremlin import input_cache

    (tmp_path / "device_db.json").write_text("{not json", encoding="utf-8")
    monkeypatch.setattr(
        input_cache.util, "resource_path", lambda rel: str(tmp_path / rel)
    )
    db = object.__new__(input_cache.DeviceDatabase)
    input_cache.DeviceDatabase.__init__(db)
    device = device_initialization.physical_devices()[0]
    assert db.get_mapping(device) is None


# --- GL-015: the real Backend -----------------------------------------------


@pytest.fixture
def real_backend(
    monkeypatch: pytest.MonkeyPatch, settings_kept: Callable[..., None]
) -> Iterator[Any]:
    """The program's Backend class (not the shared instance), without its
    process-monitor thread. Puts back the open profile, the mode stack, the
    recent-profile settings and sys.path."""
    from gremlin import process_monitor
    from gremlin.ui import backend

    monkeypatch.setattr(process_monitor.ProcessMonitor, "start", lambda self: None)
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.setattr(backend, "display_error", lambda *a, **k: None)
    settings_kept("global", "internal", "last-profile")
    settings_kept("global", "internal", "recent-profiles")
    before = shared_state.current_profile
    mm = mode_manager.ModeManager()
    stack = list(mm._mode_stack)
    be = backend.Backend.klass(cast(Any, None))
    _KEEP.append(be)
    yield be
    shared_state.current_profile = before
    mm._mode_stack = stack
    LogicalDevice().reset()


def _profile_with_modes(path: Path, start: str) -> Path:
    p = Profile()
    p.modes.add_mode("Alpha")
    p.modes.add_mode("Bravo")
    p.settings.startup_mode = start
    p.to_xml(path)
    return path


def test_load_signal_order_and_the_open_profile(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    from gremlin.signal import signal

    path = _profile_with_modes(tmp_path / "flight.xml", "Use Heuristic")
    order: list[str] = []
    seen_profile: list[object] = []
    links = [
        (real_backend.recentProfilesChanged, lambda: order.append("recent")),
        (real_backend.profileChanged, lambda: order.append("profile")),
        (real_backend.windowTitleChanged, lambda: order.append("title")),
        (
            signal.profileChanged,
            lambda: seen_profile.append(shared_state.current_profile),
        ),
    ]
    for sig, slot in links:
        sig.connect(slot)
    try:
        real_backend.loadProfile(str(path))
    finally:
        for sig, slot in links:
            sig.disconnect(slot)
    # Recorded first, then the profile change (whose handlers set the title).
    assert order[0] == "recent" and sorted(order) == ["profile", "recent", "title"]
    assert real_backend.profile.fpath == path
    assert seen_profile == [real_backend.profile]  # the new one, not the old
    assert real_backend.windowTitle == "flight.xml"
    cfg = config.Configuration()
    assert cfg.value("global", "internal", "last-profile") == str(path)
    assert str(path) in cfg.value("global", "internal", "recent-profiles")


def test_load_puts_the_toolbar_in_the_new_profiles_startup_mode(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    path = _profile_with_modes(tmp_path / "flight.xml", "Bravo")
    real_backend.loadProfile(str(path))
    assert mode_manager.ModeManager().current.name == "Bravo"
    assert real_backend.ui_state.currentMode == "Bravo"


def test_new_puts_the_toolbar_in_default(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    path = _profile_with_modes(tmp_path / "flight.xml", "Bravo")
    real_backend.profile = Profile()
    real_backend.profile.from_xml(path)
    shared_state.current_profile = real_backend.profile
    real_backend.newProfile()
    assert mode_manager.ModeManager().current.name == "Default"
    assert real_backend.ui_state.currentMode == "Default"


def test_select_mode(real_backend: Any, tmp_path: Path) -> None:  # noqa: ANN401
    path = _profile_with_modes(tmp_path / "flight.xml", "Use Heuristic")
    real_backend.loadProfile(str(path))
    real_backend.selectMode("Bravo")
    assert mode_manager.ModeManager().current.name == "Bravo"
    assert real_backend.ui_state.currentMode == "Bravo"
    real_backend.selectMode("No such mode")
    assert real_backend.ui_state.currentMode == "Bravo"


def test_new_profile_replaces_the_open_one(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    path = _profile_with_modes(tmp_path / "flight.xml", "Use Heuristic")
    real_backend.loadProfile(str(path))
    old = real_backend.profile
    order: list[str] = []
    real_backend.profileChanged.connect(lambda: order.append("profile"))
    real_backend.newProfile()
    assert real_backend.profile is not old
    assert real_backend.profile.fpath is None
    assert not real_backend.profileContainsUnsavedChanges
    assert shared_state.current_profile is real_backend.profile
    assert real_backend.windowTitle == "Untitled"
    assert order == ["profile"]


def test_save_writes_the_file_and_records_it(
    real_backend: Any, tmp_path: Path  # noqa: ANN401
) -> None:
    desc = _create("Description")
    desc.description = "saved text"
    _item(real_backend.profile, 2).add_item_binding().root_action.insert_action(
        desc, "children"
    )
    path = tmp_path / "saved.xml"
    assert real_backend.saveProfile(path.as_uri()) is True
    assert real_backend.profile.fpath == path
    assert real_backend.windowTitle == "saved.xml"
    last = config.Configuration().value("global", "internal", "last-profile")
    assert last == str(path)
    back = Profile()
    back.from_xml(path)
    kept = _kids(back.get_input_item(_STICK, InputType.JoystickButton, 2, "Default"))
    assert [a.description for a in kept] == ["saved text"]
    assert real_backend.saveProfile("") is False


def test_unknown_startup_mode_resolves_like_use_heuristic(tmp_path: Path) -> None:
    path = _profile_with_modes(tmp_path / "odd.xml", "Bravo")
    text = path.read_text(encoding="utf-8").replace(
        "<startup-mode>Bravo</startup-mode>", "<startup-mode>Gone</startup-mode>"
    )
    path.write_text(text, encoding="utf-8")
    p = Profile()
    p.from_xml(path)
    assert mode_manager.resolve_start_mode(p) == "Alpha"


def test_unknown_startup_mode_shows_as_use_heuristic(
    profile: Profile, tmp_path: Path
) -> None:
    from gremlin.ui.profile import StartupModeModel

    path = _profile_with_modes(tmp_path / "odd.xml", "Bravo")
    text = path.read_text(encoding="utf-8").replace(
        "<startup-mode>Bravo</startup-mode>", "<startup-mode>Gone</startup-mode>"
    )
    path.write_text(text, encoding="utf-8")
    profile.from_xml(path)
    model = StartupModeModel()
    _KEEP.append(model)
    assert model.currentSelectionIndex == 0


def test_swap_onto_a_device_with_bindings_swaps_both_ways(
    profile: Profile, tmp_path: Path
) -> None:
    for device, note in ((_STICK, "from profile"), (_OTHER_STICK, "connected")):
        desc = _create("Description")
        desc.description = note
        _item(profile, 4, device=device).add_item_binding().root_action.insert_action(
            desc, "children"
        )
    result = swap_devices.swap_devices(profile, _STICK, _OTHER_STICK)
    assert result.input_swaps == 2
    path = tmp_path / "swapped.xml"
    profile.to_xml(path)
    back = Profile()
    back.from_xml(path)

    def text(device: uuid.UUID) -> list[str]:
        item = back.get_input_item(device, InputType.JoystickButton, 4, "Default")
        return [a.description for a in _kids(item)]

    assert text(_OTHER_STICK) == ["from profile"]
    assert text(_STICK) == ["connected"]


# --- GL-017: risky action paths ---------------------------------------------


def test_run_skips_unfinished_actions(
    profile: Profile, caplog: pytest.LogCaptureFixture
) -> None:
    item = _item(profile, 1)
    root = item.add_item_binding().root_action
    desc = _create("Description")
    desc.description = "finished"
    root.insert_action(_create("Reference"), "children")
    root.insert_action(desc, "children")
    callback = code_runner.CallbackObject(item.action_sequences[0])
    root_functor: Any = callback._functor
    kinds = [type(f).__name__ for f in root_functor.functors["children"]]
    assert kinds == ["DescriptionFunctor"]
    assert any("not finished" in r.getMessage() for r in caplog.records)


def _catalog(profile: Profile, kind: InputType, hw: int) -> Any:  # noqa: ANN401
    """The Configuration page model with its pane on stick input hw."""
    from gremlin.ui.binding_catalog import BindingCatalogModel

    model = BindingCatalogModel()
    _KEEP.append(model)

    def spec(device_index: int) -> tuple:
        real = profile.get_input_item(_STICK, kind, hw, "Default")
        return profile, _STICK, kind, hw, "Default", real

    model._control_spec = spec
    return model


def _pane_root(model: Any) -> Any:  # noqa: ANN401
    from gremlin.ui.profile import InputItemBindingModel

    binding = InputItemBindingModel(
        model._pane_shadow.action_sequences[0], model._pane_model
    )
    _KEEP.append(binding)
    return next(
        m for m in binding._action_models.values() if m.action_data.tag == "root"
    )


def test_merge_axis_reused_in_the_pane_then_cancel_changes_nothing(
    profile: Profile,
) -> None:
    merge = _create("Merge Axis", InputType.JoystickAxis)
    for axis, number in ((merge.axis_in1, 1), (merge.axis_in2, 2)):
        axis.device_guid = _STICK
        axis.input_id = number
        axis.input_type = InputType.JoystickAxis
    merge.label = "live"
    first = _item(profile, 1, InputType.JoystickAxis)
    first.add_item_binding().root_action.insert_action(merge, "children")
    _item(profile, 4, InputType.JoystickAxis).add_item_binding()
    model = _catalog(profile, InputType.JoystickAxis, 4)
    model.beginPane(0, 0)
    _pane_root(model).appendAction("Merge Axis", "children")
    reused = _kids(model._pane_shadow)[0]
    reused.label = "edited in the pane"
    model.discardPane()
    model.endPane()
    assert merge.label == "live"


def test_save_with_the_pane_open_leaves_the_draft_alone(
    profile: Profile, tmp_path: Path
) -> None:
    item = _item(profile, 1)
    desc = _create("Description")
    desc.description = "on the input"
    item.add_item_binding().root_action.insert_action(desc, "children")
    model = _catalog(profile, InputType.JoystickButton, 1)
    model.beginPane(0, 0)
    draft = _kids(model._pane_shadow)[0]
    draft.description = "in the pane"

    profile.to_xml(tmp_path / "while_open.xml")  # File > Save
    saved = (tmp_path / "while_open.xml").read_text(encoding="utf-8")
    assert "on the input" in saved and "in the pane" not in saved
    assert draft.description == "in the pane"
    assert profile.library.has_action(draft.id)
    assert model.paneDirty()

    model.commitPane()  # OK after the save
    model.endPane()
    profile.to_xml(tmp_path / "after_ok.xml")
    assert "in the pane" in (tmp_path / "after_ok.xml").read_text(encoding="utf-8")


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-164: a key added with Add Key has no binding to add an action to",
)
def test_a_new_key_can_get_its_first_action(profile: Profile) -> None:
    from gremlin.ui.device import KeyboardManagerModel
    from gremlin.ui.profile import InputItemModel

    keys = KeyboardManagerModel()
    _KEEP.append(keys)
    key = keyboard.key_from_name("a")
    event = event_handler.Event(
        InputType.Keyboard, (key.scan_code, key.is_extended), dill.UUID_Keyboard,
        "Default", is_pressed=True,
    )
    assert keys.addKey([event], "Default") >= 0
    item = profile.get_input_item(
        dill.UUID_Keyboard, InputType.Keyboard, (key.scan_code, key.is_extended),
        "Default",
    )
    assert item is not None
    editor = InputItemModel(item, 0, None)
    _KEEP.append(editor)
    assert editor.rowCount() >= 1  # a binding whose Add Action can be used


@pytest.fixture
def mouse_controller() -> Iterator[Any]:
    controller = sendinput.MouseController()
    controller.stop()  # no motion left from before (no thread runs)
    yield controller
    controller.stop()


def test_map_to_mouse_from_a_hat_moves_and_stops(
    profile: Profile, mouse_controller: Any  # noqa: ANN401
) -> None:
    from action_plugins.map_to_mouse import MapToMouseMode

    action = _create("Map to Mouse", InputType.JoystickHat)
    assert action.mode == MapToMouseMode.Motion
    functor = action.functor(action)

    def hat(direction: HatDirection) -> None:
        event = event_handler.Event(
            InputType.JoystickHat, 1, _STICK, "Default", value=direction,
            raw_value=direction,
        )
        functor(event, Value(direction))

    hat(HatDirection.North)
    moving = mouse_controller._delta_generator
    assert abs(moving.direction.x) < 1e-6 and moving.direction.y == pytest.approx(-1)
    assert any(moving() != (0, 0) for _ in range(200))
    hat(HatDirection.Center)
    stopped = mouse_controller._delta_generator
    assert all(stopped() == (0, 0) for _ in range(50))


def test_load_profile_action_end_to_end(
    real_backend: Any, tmp_path: Path, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    from gremlin.signal import signal
    from gremlin.ui import backend

    target = _profile_with_modes(tmp_path / "next.xml", "Use Heuristic")
    monkeypatch.setattr(backend.Backend, "instance", real_backend)
    switches: list[bool] = []
    monkeypatch.setattr(real_backend, "activate_gremlin", switches.append)
    notes: list[tuple[str, str]] = []

    def note(title: str, text: str) -> None:
        notes.append((title, text))

    signal.showNotification.connect(note)
    try:
        action = _create("Load Profile")
        functor = action.functor(action)
        press = event_handler.Event(
            InputType.JoystickButton, 1, _STICK, "Default", is_pressed=True,
            raw_value=True,
        )

        action.profile_filename = str(tmp_path / "missing.xml")
        functor(press, Value(True), [])
        assert real_backend.profile.fpath is None and "missing" in notes[-1][1]

        action.profile_filename = str(target)
        real_backend.profile.modes.add_mode("Unsaved edit")
        assert real_backend.profile.has_unsaved_changes()
        functor(press, Value(True), [])
        assert real_backend.profile.fpath is None
        assert notes[-1][0] == "Load Profile Waited"
        real_backend.profile.mark_clean()

        functor(press, Value(True), [])
        # GL-057: not from inside the event; it loads once Qt events run.
        assert real_backend.profile.fpath is None
        end = time.monotonic() + 2.0
        while real_backend.profile.fpath != target and time.monotonic() < end:
            QtCore.QCoreApplication.processEvents()
            time.sleep(0.01)
        assert real_backend.profile.fpath == target
        assert switches[-2:] == [False, True]  # stopped, then run again
    finally:
        signal.showNotification.disconnect(note)
