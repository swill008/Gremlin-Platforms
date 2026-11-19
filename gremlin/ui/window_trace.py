# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Window tracing (01 S175-S178, D-01-WINDOW-TRACE).

What the main window, the tray and the pages do: shown, hidden, moved,
screens, active, page loads. Every line goes to the recent events
(trace.recent, always, memory only) and, while Tracing is on and the Window
row is ticked, to the Trace tab as a WINDOW line. Save Window State writes
the window's state to system.log at Warning.

The Qt taps run on the main thread (signals of the main window and the
app); note() and last_known() may be called from any thread. Nothing here
starts a thread, waits or raises.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable

from PySide6 import QtCore, QtGui, QtQml

from gremlin import clock, trace

MAIN = "Main window"
SETTLE_MS = 500
ACTIVE_GAP_S = 1.0
# A page line is a tray event (kept in the recent events) this long after
# the page's trayed flag changed.
_TRAY_PAGE_S = 3.0

_lock = threading.Lock()
_last: dict[str, object] = {}
_tray_reader: Callable[[], bool] | None = None
_bridge: WindowTrace | None = None
_pages: dict[str, str] = {}

_VISIBILITY = {
    QtGui.QWindow.Visibility.Hidden: "hidden",
    QtGui.QWindow.Visibility.Windowed: "shown (Windowed)",
    QtGui.QWindow.Visibility.Minimized: "minimized",
    QtGui.QWindow.Visibility.Maximized: "maximized",
    QtGui.QWindow.Visibility.FullScreen: "full screen",
    QtGui.QWindow.Visibility.AutomaticVisibility: "shown (automatic)",
}


def _log() -> logging.Logger:
    return logging.getLogger("system")


def _remember(**values: object) -> None:
    with _lock:
        _last.update(values)


def note(control: str, text: str, ring: bool = True) -> None:
    """One window event: to the recent events when ring, and a WINDOW line
    while the Window row is on. Any thread; never raises."""
    try:
        text = str(text)
        if ring:
            trace.recent(str(control), text)
        trace.window(str(control), text)
        if text.startswith("displays "):
            _remember(displays=text[len("displays "):], displays_at=_clock_text())
        elif text in ("sleeping", "resumed"):
            _remember(power=text, power_at=_clock_text())
    except Exception:
        pass


def warn(text: str) -> None:
    """system.log Warning "Window: <text>" followed by the recent events
    (S175); the line also goes to the recent events. Never raises."""
    try:
        lines = trace.recent_lines()
        body = "\n".join(f"  {line}" for line in lines) or "  (none)"
        _log().warning(
            "Window: %s\nRecent window events (last %d):\n%s",
            text, trace.RECENT_MAX, body,
        )
    except Exception:
        pass
    note(MAIN, f"warning: {text}")


def set_tray_state_reader(fn: Callable[[], bool] | None) -> None:
    """The tray's own "hidden to the tray" flag, for the differ mark."""
    global _tray_reader
    _tray_reader = fn


def _tray_says() -> bool | None:
    reader = _tray_reader
    if reader is None:
        return None
    try:
        return bool(reader())
    except Exception:
        return None


def _clock_text() -> str:
    try:
        return QtCore.QTime.currentTime().toString("HH:mm:ss")
    except Exception:
        return "?"


def _screen_text(screen: QtGui.QScreen | None) -> str:
    try:
        if screen is None:
            return "none"
        return f"{screen.name()} ({round(screen.devicePixelRatio() * 100)}%)"
    except Exception:
        return "?"


def _screen_place(screen: QtGui.QScreen) -> str:
    try:
        g = screen.geometry()
        return f"{screen.name()} {g.width()}x{g.height()} at {g.x()},{g.y()}"
    except Exception:
        return "?"


def _state_name(state: object) -> str:
    try:
        s = QtCore.Qt.WindowState
        value = QtCore.Qt.WindowState(state)  # type: ignore[call-overload]
        if value & s.WindowFullScreen:
            return "full screen"
        if value & s.WindowMinimized:
            return "minimized"
        if value & s.WindowMaximized:
            return "maximized"
        return "normal"
    except Exception:
        return "?"


class WindowTrace(QtCore.QObject):
    """The Qt side: the main window's taps, and the QML context property
    windowTrace (page(), saveWindowState())."""

    def __init__(self, parent: QtCore.QObject | None = None) -> None:
        super().__init__(parent)
        self._window: QtGui.QWindow | None = None
        self._engine: QtQml.QQmlEngine | None = None
        self._state = "normal"
        self._screen: QtGui.QScreen | None = None
        self._trayed_at = -1e9
        self._active_line_at = -1e9
        self._active_between = 0
        self._settle = QtCore.QTimer(self)
        self._settle.setSingleShot(True)
        self._settle.setInterval(SETTLE_MS)
        self._settle.timeout.connect(self._moved)
        self._active_timer = QtCore.QTimer(self)
        self._active_timer.setSingleShot(True)
        self._active_timer.timeout.connect(self._active_line)

    # QML -----------------------------------------------------------------

    @QtCore.Slot(str, str)
    def page(self, name: str, what: str) -> None:
        """A page Loader's report (PageLoader.qml): loaded, unloaded,
        failed to load. Kept in the recent events when tray related."""
        try:
            with _lock:
                _pages[str(name)] = str(what)
                _last["pages"] = dict(_pages)
            win = self._window
            # The page's trayed flag changes before its own notify reaches
            # _trayed_changed, so a flag not yet noted counts too.
            with _lock:
                noted = _last.get("page_trayed")
            tray_related = (
                what == "failed to load"
                or clock.monotonic() - self._trayed_at < _TRAY_PAGE_S
                or (win is not None and not win.isVisible())
                or (win is not None and _page_trayed(win) != noted)
            )
            note(str(name), f"{name} {what}", ring=tray_related)
        except Exception:
            pass

    @QtCore.Slot()
    def saveWindowState(self) -> None:  # noqa: N802 (QML name)
        save_state()

    # Taps ----------------------------------------------------------------

    def attach(self, window: QtGui.QWindow, engine: QtQml.QQmlEngine | None) -> None:
        self._window = window
        self._engine = engine
        self._screen = window.screen()
        self._state = _state_name(window.windowState())
        window.visibilityChanged.connect(self._visibility)
        window.windowStateChanged.connect(self._window_state)
        for sig in (window.xChanged, window.yChanged,
                    window.widthChanged, window.heightChanged):
            sig.connect(self._place_changed)
        window.screenChanged.connect(self._screen_changed)
        window.activeChanged.connect(self._active_changed)
        app = QtGui.QGuiApplication.instance()
        if isinstance(app, QtGui.QGuiApplication):
            app.screenAdded.connect(self._screen_added)
            app.screenRemoved.connect(self._screen_removed)
            app.primaryScreenChanged.connect(self._primary_changed)
        try:
            prop = QtQml.QQmlProperty(window, "trayed")
            if prop.isValid() and prop.hasNotifySignal():
                slot = QtCore.SLOT("_trayed_changed()")
                prop.connectNotifySignal(self, slot)  # pyright: ignore[reportArgumentType, reportCallIssue]
        except Exception:
            pass
        self._remember_all()

    def _remember_all(self) -> None:
        win = self._window
        if win is None:
            return
        try:
            _remember(
                visible=win.isVisible(),
                visibility=_VISIBILITY.get(win.visibility(), "?"),
                state=_state_name(win.windowState()),
                place=f"{win.x()},{win.y()} {win.width()}x{win.height()}",
                screen=_screen_text(win.screen()),
                active=win.isActive(),
                page_trayed=_page_trayed(win),
                at=_clock_text(),
            )
        except Exception:
            pass

    def _visibility(self, visibility: object) -> None:
        try:
            note(MAIN, _VISIBILITY.get(visibility, f"visibility {visibility}"))  # type: ignore[call-overload]
            self._remember_all()
        except Exception:
            pass

    def _window_state(self, state: object) -> None:
        try:
            name = _state_name(state)
            before, self._state = self._state, name
            if name == "normal" and before != "normal":
                note(MAIN, "restored")
            self._remember_all()
        except Exception:
            pass

    def _place_changed(self, *_args: object) -> None:
        self._settle.start()

    def _moved(self) -> None:
        win = self._window
        if win is None:
            return
        try:
            note(
                MAIN,
                f"moved to {win.x()},{win.y()} {win.width()}x{win.height()} "
                f"on {_screen_text(win.screen())}",
            )
            self._remember_all()
        except Exception:
            pass

    def _screen_changed(self, screen: QtGui.QScreen | None) -> None:
        try:
            before = self._screen.name() if self._screen is not None else "none"
            self._screen = screen
            after = screen.name() if screen is not None else "none"
            note(MAIN, f"screen changed: {before} → {after}")
            self._remember_all()
        except Exception:
            pass

    def _screen_added(self, screen: QtGui.QScreen) -> None:
        note(MAIN, f"screen added {_screen_place(screen)}")

    def _screen_removed(self, screen: QtGui.QScreen) -> None:
        try:
            name = screen.name()
        except Exception:
            name = "?"
        note(MAIN, f"screen removed {name}")

    def _primary_changed(self, screen: QtGui.QScreen | None) -> None:
        try:
            name = screen.name() if screen is not None else "none"
        except Exception:
            name = "?"
        note(MAIN, f"primary screen now {name}")

    def _active_changed(self) -> None:
        """At most one line a second; the last state is written when the
        gap is up, with how many changes came between."""
        try:
            win = self._window
            if win is not None:
                _remember(active=win.isActive())
            wait = self._active_line_at + ACTIVE_GAP_S - clock.monotonic()
            if wait <= 0 and not self._active_timer.isActive():
                self._active_line()
                return
            self._active_between += 1
            if not self._active_timer.isActive():
                self._active_timer.start(max(0, round(wait * 1000)))
        except Exception:
            pass

    def _active_line(self) -> None:
        try:
            win = self._window
            if win is None:
                return
            between = self._active_between
            self._active_between = 0
            self._active_line_at = clock.monotonic()
            text = "active" if win.isActive() else "inactive"
            if between > 1:
                text += f" ({between - 1} changes between)"
            note(MAIN, text, ring=False)
        except Exception:
            pass

    @QtCore.Slot()
    def _trayed_changed(self) -> None:
        try:
            self._trayed_at = clock.monotonic()
            win = self._window
            value = _page_trayed(win) if win is not None else None
            _remember(page_trayed=value)
            note(MAIN, f"page trayed: {'yes' if value else 'no'}")
        except Exception:
            pass


def _page_trayed(window: QtCore.QObject | None) -> bool | None:
    try:
        if window is None:
            return None
        value = QtQml.QQmlProperty.read(window, "trayed")
        return None if value is None else bool(value)
    except Exception:
        return None


def bridge() -> WindowTrace:
    """The one WindowTrace (made on first use, on the main thread)."""
    global _bridge
    if _bridge is None:
        _bridge = WindowTrace()
    return _bridge


def expose(engine: QtQml.QQmlEngine) -> None:
    """Sets the QML context property windowTrace; before Main.qml loads so
    its first page loads are seen. Main thread."""
    try:
        ctx = engine.rootContext()
        if ctx.contextProperty("windowTrace") is not bridge():
            ctx.setContextProperty("windowTrace", bridge())
    except Exception:
        _log().exception("Window trace: context property")


def install(window: QtCore.QObject, engine: QtQml.QQmlEngine | None) -> None:
    """Connects the main window's taps (main thread, start-up)."""
    try:
        if not isinstance(window, QtGui.QWindow):
            _log().warning("Window trace: the main window is not a window")
            return
        if engine is not None:
            expose(engine)
        bridge().attach(window, engine)
    except Exception:
        _log().exception("Window trace: install")


def _yes(value: object) -> str:
    if value is None:
        return "unknown"
    return "yes" if value else "no"


def state_text() -> str:
    """The Save Window State block (S178). Main thread; no waits."""
    b = _bridge
    win = b._window if b is not None else None
    lines = ["Window state (asked for):"]
    try:
        if win is None:
            lines.append("  window: not known (window trace not installed)")
            page_trayed = None
        else:
            b._remember_all()  # type: ignore[union-attr]
            g = f"{win.x()},{win.y()} {win.width()}x{win.height()}"
            lines.append(
                f"  window: visible {_yes(win.isVisible())}, visibility "
                f"{_VISIBILITY.get(win.visibility(), '?')}, state "
                f"{_state_name(win.windowState())}, {g}, screen "
                f"{_screen_text(win.screen())}, active {_yes(win.isActive())}"
            )
            page_trayed = _page_trayed(win)
        tray = _tray_says()
        differ = tray is not None and page_trayed is not None and tray != page_trayed
        lines.append(
            f"  tray: tray says hidden-to-tray {_yes(tray)}, page says trayed "
            f"{_yes(page_trayed).upper() if differ else _yes(page_trayed)}"
            + ("  <-- differ" if differ else "")
        )
        with _lock:
            pages = dict(_pages)
            last = dict(_last)
        room = tab = "?"
        try:
            if b is not None and b._engine is not None:
                ui = b._engine.rootContext().contextProperty("uiState")
                if ui is not None:
                    room = str(ui.property("currentRoom"))
                    tab = str(ui.property("currentTab"))
        except Exception:
            pass
        loaded = ", ".join(n for n, w in pages.items() if w == "loaded") or "none"
        unloaded = ", ".join(n for n, w in pages.items() if w != "loaded") or "none"
        lines.append(
            f"  pages: room {room}, tab {tab}; loaded: {loaded}; "
            f"unloaded or failed: {unloaded}"
        )
        displays = last.get("displays")
        power = last.get("power")
        lines.append(
            "  displays: "
            + (f"{displays} (last report {last.get('displays_at')})" if displays
               else "no report this session")
            + ", last sleep/resume: "
            + (f"{power} at {last.get('power_at')}" if power else "none this session")
        )
        lines.append(f"  Screen Saver Mode: {_screen_saver_text()}")
    except Exception as exc:
        lines.append(f"  (could not read all of it: {type(exc).__name__}: {exc})")
    recent = trace.recent_lines()
    lines.append(f"  Recent window events (last {trace.RECENT_MAX}):")
    lines.extend(f"    {line}" for line in recent or ["(none)"])
    return "\n".join(lines)


def _screen_saver_text() -> str:
    try:
        from gremlin import screen_saver_mode

        mgr = screen_saver_mode._manager
        if mgr is None:
            return "off"
        on = bool(getattr(mgr, "_running", False))
        keeping = bool(getattr(mgr, "_keeping_off", False))
        return f"{'on' if on else 'off'}, keeping displays off {_yes(keeping)}"
    except Exception:
        return "unknown"


def save_state() -> None:
    """Debug > Save Window State (S178): the state to system.log at Warning
    and, while the Window row is on, a WINDOW line. Changes nothing."""
    try:
        text = state_text()
    except Exception as exc:
        text = f"Window state could not be read: {type(exc).__name__}: {exc}"
    try:
        _log().warning(text)
    except Exception:
        pass
    try:
        trace.window(MAIN, text)
    except Exception:
        pass


def last_known() -> dict:
    """Plain values kept by the taps (any thread; no Qt calls): for the
    Not responding dump."""
    with _lock:
        out = dict(_last)
    out["tray_says_trayed"] = _tray_says()
    return out


def _reset_for_tests() -> None:
    global _bridge, _tray_reader
    with _lock:
        _last.clear()
        _pages.clear()
    _tray_reader = None
    _bridge = None
