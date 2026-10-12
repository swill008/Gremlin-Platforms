# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

# ONE-TIME (tracker OT-5): temporary click trace for the dead right-click
# report; remove after the fix (the whole file).

"""Temporary click trace for the Device Mapping Editor (tracker OT-5).

While Debug › Tracing is on and the Trace tab's Mouse row is ticked (off by
default, the tick saved), every mouse press, release and double click on
the Device Mapping Editor window (or a window that belongs to it) writes one
MOUSE line "CLICK ..." to the Trace tab and trace.log: the event, button,
window, position and the topmost item under the point; a 0 ms timer after
delivery adds the window's mouse grabber (an item took the press) and the focus window.
QML adds lines through the "clickTrace" context property (RigPointerArea's
right press, the right-click menu opening and closing).

Tracing off or Mouse unticked, the event filter is not installed: no cost
(trace's on_change hook runs on both). Nothing here raises into
Qt's event delivery and nothing waits."""

from __future__ import annotations

import shiboken6
from PySide6 import QtCore, QtGui, QtQuick

from gremlin import clock, trace

EDITOR_TITLE = "Device Mapping Editor"
PREFIX = "CLICK "
# How recent a press or Esc must be to name why the menu closed (seconds).
_REASON_WINDOW = 0.3
_MAX_DEPTH = 60
_MAX_VISITS = 4000
_MAX_HITS = 40

_E = QtCore.QEvent.Type
_MOUSE = {
    _E.MouseButtonPress: "press",
    _E.MouseButtonRelease: "release",
    _E.MouseButtonDblClick: "dblclick",
}

_current: ClickTrace | None = None


def _name(obj: object) -> str:
    """objectName, else the class (QML types show as e.g. RigPointerArea_QMLTYPE_12)."""
    try:
        if obj is None or not shiboken6.isValid(obj):
            return "none"
        name = obj.objectName()  # type: ignore[attr-defined]
        cls = obj.metaObject().className()  # type: ignore[attr-defined]
        return f"{cls}#{name}" if name else cls
    except Exception:
        return "?"


def _window_name(win: QtGui.QWindow | None) -> str:
    try:
        if win is None or not shiboken6.isValid(win):
            return "none"
        return f"'{win.title()}'({win.metaObject().className()})"
    except Exception:
        return "?"


def editor_window(win: object) -> bool:
    """The Device Mapping Editor window, or a window it owns (a popup window)."""
    try:
        w = win
        for _ in range(8):
            if not isinstance(w, QtGui.QWindow) or not shiboken6.isValid(w):
                return False
            if w.title().startswith(EDITOR_TITLE):
                return True
            w = w.transientParent()
    except Exception:
        pass
    return False


def _chain(path: list[object]) -> str:
    return " > ".join(_name(i) for i in path[-6:]) or "none"


def item_chain(win: QtQuick.QQuickWindow, scene: QtCore.QPointF) -> str:
    """What is under the point, from the window's root item (which also
    holds the overlay with any open popup): "top" is the topmost visible
    item, "mouse" the topmost one that takes mouse buttons (it gets the press
    first, pointer handlers aside). Last few names, outermost first; at most
    _MAX_VISITS items are looked at."""
    top: list[object] = []
    mouse: list[object] = []
    visits = 0
    try:
        content = win.contentItem()
        root = content.parentItem() if content is not None else None
        root = root or content
        no_button = QtCore.Qt.MouseButton.NoButton

        def walk(item: QtQuick.QQuickItem, path: list[object]) -> bool:
            """Children topmost first, then the item itself (Qt's delivery
            order); True once the mouse taker is found."""
            nonlocal visits, top, mouse
            visits += 1
            if visits > _MAX_VISITS or len(path) > _MAX_DEPTH:
                return True
            path = path + [item]
            inside = item.contains(item.mapFromScene(scene))
            if item.clip() and not inside:
                return False
            kids = sorted(
                enumerate(item.childItems()),
                key=lambda t: (t[1].z(), t[0]),
                reverse=True,
            )
            for _, kid in kids:
                if kid.isVisible() and walk(kid, path):
                    return True
            if inside and not top:
                top = path
            if inside and item.acceptedMouseButtons() != no_button:
                mouse = path
                return True
            return False

        if root is not None:
            walk(root, [])
    except Exception:
        return "?"
    return f"top=[{_chain(top)}] mouse=[{_chain(mouse)}]"


def _rect(item: object) -> str:
    """The item's box in window pixels."""
    try:
        r = item.mapRectToScene(  # type: ignore[attr-defined]
            QtCore.QRectF(0, 0, item.width(), item.height())  # type: ignore[attr-defined]
        )
        return f"({r.x():.0f},{r.y():.0f} {r.width():.0f}x{r.height():.0f})"
    except Exception:
        return "(?)"


def _int(v: object) -> int | str:
    try:
        return int(v)  # type: ignore[call-overload]
    except Exception:
        try:
            return int(v.value)  # type: ignore[attr-defined]
        except Exception:
            return "?"


def _input_of(item: QtQuick.QQuickItem) -> str:
    """How the item takes input: buttons, hover, pointer handlers, MouseArea."""
    parts = [f"buttons={_int(item.acceptedMouseButtons())}"]
    parts.append(f"hover={item.acceptHoverEvents()}")
    cls = item.metaObject().className()
    if "MouseArea" in cls:
        parts.append(f"MouseArea.accepted={_int(item.property('acceptedButtons'))}")
    handlers = []
    for child in item.children():
        try:
            hcls = child.metaObject().className()
            if "Handler" in hcls:
                on = child.property("enabled")
                handlers.append(f"{hcls}(enabled={on})")
        except Exception:
            continue
    if handlers:
        parts.append("handlers=" + "+".join(handlers))
    return " ".join(parts)


def hits(win: QtQuick.QQuickWindow, scene: QtCore.QPointF) -> list[str]:
    """Every visible item whose box holds the point, in Qt's delivery order
    (top to bottom), with its place and input; at most _MAX_HITS."""
    out: list[str] = []
    visits = 0
    try:
        content = win.contentItem()
        root = content.parentItem() if content is not None else None
        root = root or content

        def walk(item: QtQuick.QQuickItem) -> None:
            nonlocal visits
            visits += 1
            if visits > _MAX_VISITS or len(out) >= _MAX_HITS:
                return
            inside = item.contains(item.mapFromScene(scene))
            if item.clip() and not inside:
                return
            kids = sorted(
                enumerate(item.childItems()),
                key=lambda t: (t[1].z(), t[0]),
                reverse=True,
            )
            for _, kid in kids:
                if kid.isVisible():
                    walk(kid)
            if inside and len(out) < _MAX_HITS:
                parent = item.parentItem()
                out.append(
                    f"{_name(item)} parent={_name(parent)} z={item.z():g} "
                    f"rect={_rect(item)} enabled={item.isEnabled()} {_input_of(item)}"
                )

        if root is not None:
            walk(root)
    except Exception:
        out.append("?")
    return out


def _find(item: QtQuick.QQuickItem, prefix: str, budget: list[int]) -> object:
    """The first item under item whose class starts with prefix."""
    budget[0] -= 1
    if budget[0] < 0:
        return None
    for kid in item.childItems():
        if kid.metaObject().className().startswith(prefix):
            return kid
        found = _find(kid, prefix, budget)
        if found is not None:
            return found
    return None


def editor_rects(win: QtQuick.QQuickWindow) -> str:
    """Window-pixel boxes of the editor's view parts (VkbRigFace's _viewport
    and _world, VkbRigEditor, RigPointerArea, RigGrid) and the view's zoom
    and pan."""
    try:
        root = win.contentItem()
        budget = [_MAX_VISITS]
        face = _find(root, "VkbRigFace", budget)
        if face is None:
            return "no VkbRigFace"
        viewport = next(
            (k for k in face.childItems() if k.clip()), None  # type: ignore[attr-defined]
        )
        world = viewport.childItems()[0] if viewport and viewport.childItems() else None
        ed = _find(face, "VkbRigEditor", budget)  # type: ignore[arg-type]
        pointer = _find(ed, "RigPointerArea", budget) if ed else None  # type: ignore[arg-type]
        grid = _find(ed, "RigGrid", budget) if ed else None  # type: ignore[arg-type]
        view = (
            f"zoom={face.property('zoom')} pan=({face.property('panX')},"  # type: ignore[attr-defined]
            f"{face.property('panY')})"  # type: ignore[attr-defined]
        )
        return (
            f"face={_rect(face)} viewport={_rect(viewport)} world={_rect(world)} "
            f"editor={_rect(ed)} pointerArea={_rect(pointer)} grid={_rect(grid)} {view}"
        )
    except Exception:
        return "?"


def _buttons(ev: QtGui.QMouseEvent) -> str:
    try:
        b = ev.button()
        held = ev.buttons()
        names = {
            QtCore.Qt.MouseButton.LeftButton: "L",
            QtCore.Qt.MouseButton.RightButton: "R",
            QtCore.Qt.MouseButton.MiddleButton: "M",
        }
        held_text = "".join(v for k, v in names.items() if held & k) or "-"
        return f"button={names.get(b, str(int(b.value)))} held={held_text}"
    except Exception:
        return "button=?"


class ClickTrace(QtCore.QObject):
    """The event filter and the QML entry points. The filter sits only on
    the Device Mapping Editor's windows, and only while tracing is on and
Mouse is ticked: an
    application-wide Python filter would wrap every event of every object,
    including objects half-way through being destroyed."""

    changed = QtCore.Signal()

    def __init__(self, app: QtCore.QCoreApplication) -> None:
        super().__init__(app)
        self._app = app
        self._windows: list[QtGui.QWindow] = []
        self._last_press = 0.0
        self._last_esc = 0.0
        self._closing_reason = ""
        self._disposed = False
        if isinstance(app, QtGui.QGuiApplication):
            app.focusWindowChanged.connect(self.watch)
        app.aboutToQuit.connect(self.dispose)

    # --- switch --------------------------------------------------------------

    def sync(self) -> None:
        """While tracing is on and Mouse ticked, filter the editor windows
        already open; otherwise take the filter off every window."""
        try:
            if self._disposed:
                return
            if trace.mouse_on():
                if not isinstance(self._app, QtGui.QGuiApplication):
                    return
                for win in QtGui.QGuiApplication.topLevelWindows():
                    self.watch(win)
            else:
                self._unwatch_all()
            self.changed.emit()
        except Exception:
            pass

    @QtCore.Slot(QtGui.QWindow)
    def watch(self, win: QtGui.QWindow | None) -> None:
        """Filter this window if it is the editor's, tracing is on and Mouse
        is ticked."""
        try:
            if self._disposed or win is None or not trace.mouse_on():
                return
            if not shiboken6.isValid(win) or not editor_window(win):
                return
            self._windows = [w for w in self._windows if shiboken6.isValid(w)]
            if any(w is win for w in self._windows):
                return
            win.installEventFilter(self)
            self._windows.append(win)
        except Exception:
            pass

    def _unwatch_all(self) -> None:
        for win in self._windows:
            try:
                if shiboken6.isValid(win):
                    win.removeEventFilter(self)
            except Exception:
                pass
        self._windows = []

    def watched(self) -> int:
        """How many windows have the filter (tests)."""
        return len([w for w in self._windows if shiboken6.isValid(w)])

    @QtCore.Slot()
    def dispose(self) -> None:
        """Filters off, signals off, and no longer the current click trace."""
        global _current
        if self._disposed:
            return
        self._disposed = True
        self._unwatch_all()
        try:
            if shiboken6.isValid(self._app):
                if isinstance(self._app, QtGui.QGuiApplication):
                    self._app.focusWindowChanged.disconnect(self.watch)
                self._app.aboutToQuit.disconnect(self.dispose)
        except Exception:
            pass
        if _current is self:
            _current = None
            _drop_hook()

    on = QtCore.Property(bool, lambda self: trace.mouse_on(), notify=changed)

    # --- filter --------------------------------------------------------------

    def eventFilter(self, obj: QtCore.QObject, ev: QtCore.QEvent) -> bool:  # noqa: N802
        try:
            if self._disposed or not trace.mouse_on():
                return False
            t = ev.type()
            if t in _MOUSE:
                if isinstance(obj, QtQuick.QQuickWindow):
                    self._mouse(obj, ev, _MOUSE[t])  # type: ignore[arg-type]
            elif t == _E.KeyPress:
                if ev.key() == QtCore.Qt.Key.Key_Escape:  # type: ignore[attr-defined]
                    self._last_esc = clock.now()
                    trace.click(f"{PREFIX}key Esc window={_window_name(obj)}")  # type: ignore[arg-type]
        except Exception:
            pass
        return False

    def _mouse(
        self, win: QtQuick.QQuickWindow, ev: QtGui.QMouseEvent, kind: str
    ) -> None:
        pos = ev.position()
        scene = ev.scenePosition()
        if kind == "press":
            self._last_press = clock.now()
        trace.click(
            f"{PREFIX}{kind} t={ev.timestamp()}ms {_buttons(ev)} "
            f"window={_window_name(win)} pos=({pos.x():.0f},{pos.y():.0f}) "
            f"under: {item_chain(win, scene)}"
        )
        if kind == "press":
            found = hits(win, scene)
            for i, text in enumerate(found, 1):
                trace.click(f"{PREFIX}{kind} hit {i}/{len(found)}: {text}")
            trace.click(f"{PREFIX}{kind} boxes: {editor_rects(win)}")
        ref = win

        def after() -> None:
            try:
                if not shiboken6.isValid(ref) or not trace.mouse_on():
                    return
                grab = ref.mouseGrabberItem()
                took = "an item took it" if grab is not None else "no item grabbed"
                focus = QtGui.QGuiApplication.focusWindow()
                modal = QtGui.QGuiApplication.modalWindow()
                trace.click(
                    f"{PREFIX}{kind} after: grabber={_name(grab)} ({took}) "
                    f"focusWindow={_window_name(focus)} "
                    f"modalWindow={_window_name(modal)} "
                    f"activeFocusItem={_name(ref.activeFocusItem())}"
                )
            except Exception:
                pass

        # Owned by this object: dropped if it is deleted first.
        QtCore.QTimer.singleShot(0, self, after)

    # --- QML -----------------------------------------------------------------

    @QtCore.Slot(str)
    def line(self, text: str) -> None:
        """One CLICK line from QML (only while tracing is on and Mouse is
        ticked)."""
        if not trace.mouse_on():
            return
        trace.click(PREFIX + str(text))

    @QtCore.Slot(str)
    def closingFor(self, reason: str) -> None:  # noqa: N802
        """The menu is about to close for this reason (an item was chosen)."""
        self._closing_reason = str(reason)

    @QtCore.Slot(str, str)
    def menu(self, what: str, title: str) -> None:
        """The right-click menu opened or closed; title: its window's title,
        so only the Device Mapping Editor's menu is logged. Strings only:
        passing the item from QML here dropped Python's hold on the window."""
        try:
            if not trace.mouse_on():
                return
            reason = self._closing_reason
            if what in ("opened", "closed"):
                self._closing_reason = ""
            if not str(title).startswith(EDITOR_TITLE):
                return
            text = f"menu {what} window='{title}'"
            if what == "closed":
                now = clock.now()
                if not reason:
                    if now - self._last_esc <= _REASON_WINDOW:
                        reason = "Esc"
                    elif now - self._last_press <= _REASON_WINDOW:
                        reason = "outside press"
                    else:
                        reason = "other (closed by code)"
                text += f" reason={reason}"
            trace.click(PREFIX + text)
        except Exception:
            pass


def _hook() -> None:
    cur = _current
    if cur is not None and shiboken6.isValid(cur):
        cur.sync()


def _drop_hook() -> None:
    """Take _hook off trace's on_change list (trace has no off_change)."""
    with trace._LOCK:  # noqa: SLF001
        while _hook in trace._hooks:  # noqa: SLF001
            trace._hooks.remove(_hook)  # noqa: SLF001


def current() -> ClickTrace | None:
    cur = _current
    return cur if cur is not None and shiboken6.isValid(cur) else None


def dispose() -> None:
    """Remove the click trace (app quitting; tests)."""
    cur = current()
    if cur is not None:
        cur.dispose()
    _drop_hook()


def install(app: QtCore.QCoreApplication, engine: object = None) -> ClickTrace:
    """The app's one click trace (an older one is removed first), exposed to
    QML as "clickTrace"."""
    global _current
    cur = current()
    if cur is None or cur._app is not app:  # noqa: SLF001
        dispose()
        cur = ClickTrace(app)
        _current = cur
        trace.on_change(_hook)
        cur.sync()
    try:
        if engine is not None and shiboken6.isValid(engine):
            engine.rootContext().setContextProperty("clickTrace", cur)  # type: ignore[attr-defined]
    except Exception:
        pass
    return cur
