# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The control API's window calls (claude/plans/control-api-contract.md).

Windows are named by their shown title, any case: "Options", "device
library", or the whole title bar text. Every call runs on the main thread
(control_api runs them there); a press only checks the button and queues
the click, so a button that opens a dialog never holds the API's reply.
Each open, close, press and type writes a system log line "... by API".
"""

from __future__ import annotations

import logging
from typing import Any

from PySide6 import QtCore, QtGui, QtQml, QtQuick

from gremlin import threads
from gremlin.control_api import CallError
from gremlin.ui import window_titles


class WindowError(CallError):
    """A window call that can't be done; its text is the API's error (an
    expected error: one plain line, no traceback)."""


def _log(text: str) -> None:
    logging.getLogger("system").info(f"{text} by API")


# --- windows ---------------------------------------------------------------


def _windows() -> list[QtQuick.QQuickWindow]:
    """The program's titled QML windows, shown or not."""
    return [
        w
        for w in QtGui.QGuiApplication.topLevelWindows()
        if isinstance(w, QtQuick.QQuickWindow) and w.title().strip()
    ]


def _names(window: QtGui.QWindow) -> set[str]:
    """Every way a window may be named: its title, without the unsaved
    mark, and the title bar text."""
    title = window.title().strip()
    names = {title, title.removeprefix("* ").strip(), window_titles.format_title(title)}
    return {n.casefold() for n in names if n}


def find_window(name: str) -> QtQuick.QQuickWindow:
    """The window called name (any case); a shown one before a hidden one,
    then a title starting with name when only one does."""
    want = (name or "").strip().casefold()
    if not want:
        raise WindowError("No window named")
    windows = _windows()
    exact = [w for w in windows if want in _names(w)]
    if not exact:
        exact = [w for w in windows if any(n.startswith(want) for n in _names(w))]
    shown = [w for w in exact if w.isVisible()]
    found = shown or exact
    if len(found) == 1:
        return found[0]
    if not found:
        raise WindowError(f"No window called {name!r}")
    titles = ", ".join(sorted({w.title() for w in found}))
    raise WindowError(f"{len(found)} windows match {name!r}: {titles}")


def _is_main(window: QtGui.QWindow) -> bool:
    engine = QtQml.qmlEngine(window)
    if not isinstance(engine, QtQml.QQmlApplicationEngine):
        return False
    roots = engine.rootObjects()
    return bool(roots) and roots[0] is window


# --- items -----------------------------------------------------------------


def _walk(item: QtQuick.QQuickItem) -> list[QtQuick.QQuickItem]:
    """Every shown item under item, item first (popups too: they sit in
    the window's overlay, under the content item's parent)."""
    out: list[QtQuick.QQuickItem] = []
    stack = [item]
    while stack:
        it = stack.pop()
        if not it.isVisible() or it.opacity() <= 0:
            continue
        out.append(it)
        stack.extend(reversed(it.childItems()))
    return out


def _root(window: QtQuick.QQuickWindow) -> QtQuick.QQuickItem:
    # The content item's parent is the root item: content plus overlay.
    content = window.contentItem()
    return content.parentItem() or content


def _plain(text: object) -> str:
    """A label as shown: mnemonic marks off, one line."""
    if not isinstance(text, str):
        return ""
    return " ".join(
        text.replace("&&", "\0").replace("&", "").replace("\0", "&").split()
    )


def _text_inside(item: QtQuick.QQuickItem) -> str:
    """The item's text, or the first shown text inside it."""
    own = _plain(item.property("text"))
    if own:
        return own
    for child in _walk(item)[1:]:
        if child.inherits("QQuickText"):
            text = _plain(child.property("text"))
            if text:
                return text
    return ""


def _kind(item: QtQuick.QQuickItem) -> str | None:
    if item.inherits("QQuickAbstractButton"):
        return "check" if item.property("checkable") else "button"
    if item.inherits("QQuickMouseArea") and item.objectName():
        # A home-made button: only a named one (most mouse areas are hover
        # or drag areas).
        return "button"
    if item.inherits("QQuickTextInput") or item.inherits("QQuickTextEdit"):
        if item.property("readOnly"):
            return "text"
        return "field"
    if item.inherits("QQuickText"):
        return "text"
    return None


def _row(item: QtQuick.QQuickItem, kind: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": kind,
        "name": item.objectName(),
        "text": _text_inside(item)
        if kind in ("button", "check")
        else _plain(item.property("text")),
        "enabled": bool(item.isEnabled()),
    }
    if kind == "check":
        row["checked"] = bool(item.property("checked"))
    if kind == "field":
        row["placeholder"] = _plain(item.property("placeholderText"))
    return row


def read_items(window: QtQuick.QQuickWindow) -> list[dict[str, Any]]:
    """The window's shown text, buttons, checks and fields, in item order.
    Text inside a button or field belongs to it, not listed again."""
    rows: list[dict[str, Any]] = []
    stack = [_root(window)]
    while stack:
        it = stack.pop()
        if not it.isVisible() or it.opacity() <= 0:
            continue
        kind = _kind(it)
        if kind is not None:
            row = _row(it, kind)
            if kind != "text" or row["text"]:
                rows.append(row)
            if kind in ("button", "check", "field"):
                continue
        stack.extend(reversed(it.childItems()))
    return rows


def _pick(
    window: QtQuick.QQuickWindow, name: str, kinds: tuple[str, ...], what: str
) -> QtQuick.QQuickItem:
    """The one shown item of kinds named name: its objectName first, then
    its text (fields: their placeholder text), any case."""
    want = (name or "").strip()
    if not want:
        raise WindowError(f"No {what} named")
    items = [it for it in _walk(_root(window)) if _kind(it) in kinds]
    by_id = [it for it in items if it.objectName() == want]
    if not by_id:
        low = want.casefold()

        def label(it: QtQuick.QQuickItem) -> str:
            if _kind(it) == "field":
                return _plain(it.property("placeholderText"))
            return _text_inside(it)

        by_id = [it for it in items if label(it).casefold() == low]
    if len(by_id) == 1:
        return by_id[0]
    if not by_id:
        raise WindowError(f"No {what} {name!r} in {window.title()}")
    raise WindowError(
        f"{len(by_id)} {what}s called {name!r} in {window.title()};"
        " name one by its objectName"
    )


# --- actions ---------------------------------------------------------------


def _click(item: QtQuick.QQuickItem) -> None:
    """A click as the user's: click() on a Controls button, else a mouse
    press and release at the item's centre."""
    try:
        if item.metaObject().indexOfMethod("click()") >= 0:
            QtCore.QMetaObject.invokeMethod(item, "click")
            return
        window = item.window()
        if window is None:
            return
        centre = item.mapToScene(QtCore.QPointF(item.width() / 2, item.height() / 2))
        glob = QtCore.QPointF(window.mapToGlobal(centre.toPoint()))
        left = QtCore.Qt.MouseButton.LeftButton
        none = QtCore.Qt.KeyboardModifier.NoModifier
        for kind, buttons in (
            (QtCore.QEvent.Type.MouseButtonPress, left),
            (QtCore.QEvent.Type.MouseButtonRelease, QtCore.Qt.MouseButton.NoButton),
        ):
            event = QtGui.QMouseEvent(kind, centre, centre, glob, left, buttons, none)
            QtGui.QGuiApplication.sendEvent(window, event)
    except RuntimeError as e:  # the item went away before the click
        logging.getLogger("system").warning(f"API press: {e}")


def _type_into(field: QtQuick.QQuickItem, text: str) -> None:
    """Replaces the field's text as typing would (its edit handlers run),
    then finishes the edit as leaving the field does."""
    QtCore.QMetaObject.invokeMethod(field, "selectAll")
    none = QtCore.Qt.KeyboardModifier.NoModifier
    if not text:
        for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
            QtCore.QCoreApplication.sendEvent(
                field, QtGui.QKeyEvent(kind, QtCore.Qt.Key.Key_Delete, none)
            )
    for ch in text:
        for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
            QtCore.QCoreApplication.sendEvent(field, QtGui.QKeyEvent(kind, 0, none, ch))
    if _plain(field.property("text")) != _plain(text):
        # A validator or input mask turned keys away: set it as written.
        field.setProperty("text", text)
    if field.metaObject().indexOfMethod("editingFinished()") >= 0:
        QtCore.QMetaObject.invokeMethod(field, "editingFinished")


def _backend(given: object) -> Any:  # noqa: ANN401
    """The program's Backend: given, else the QML engines' "backend"."""
    if given is not None:
        return given
    for window in _windows():
        engine = QtQml.qmlEngine(window)
        if engine is None:
            continue
        value = engine.rootContext().contextProperty("backend")
        if value is not None:
            return value
    return None


# --- calls -----------------------------------------------------------------


def _arg(args: dict | None, key: str) -> str:
    value = (args or {}).get(key)
    if value is None or str(value).strip() == "":
        raise WindowError(f"Missing {key!r}")
    return str(value)


def call_list(_args: dict | None = None) -> list[dict[str, Any]]:
    return [{"title": w.title(), "visible": bool(w.isVisible())} for w in _windows()]


def call_open(args: dict | None, backend: object = None) -> dict[str, Any]:
    command = _arg(args, "command")
    be = _backend(backend)
    run = getattr(be, "run_command_id", None)
    if run is None:
        raise WindowError("Menu commands aren't ready yet")
    ran = bool(run(command))
    if not ran:
        raise WindowError(
            f"Command {command!r} isn't a menu command or can't be used now"
        )
    _log(f"Ran menu command {command}")
    return {"ran": True}


def call_close(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window"))
    if _is_main(window):
        raise WindowError("The main window isn't closed by the API")
    title = window.title()
    window.close()
    _log(f"Closed window {title}")
    return {"closed": title}


def call_read(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window"))
    return {"title": window.title(), "items": read_items(window)}


def call_screenshot(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window"))
    path = _arg(args, "path")
    if not path.lower().endswith(".png"):
        raise WindowError("The picture path must end in .png")
    folder = QtCore.QFileInfo(path).absoluteDir()
    if not folder.exists():
        raise WindowError(f"No folder {folder.absolutePath()}")
    image = window.grabWindow()
    if image.isNull():
        raise WindowError(f"Couldn't take a picture of {window.title()}")
    if not image.save(path):
        raise WindowError(f"Couldn't write {path}")
    return {"path": path, "width": image.width(), "height": image.height()}


def call_press(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window"))
    item = _pick(window, _arg(args, "button"), ("button", "check"), "button")
    text = _text_inside(item) or item.objectName()
    if not item.isEnabled():
        raise WindowError(f"{text!r} is turned off in {window.title()}")
    # Queued: a button that opens a dialog or runs long doesn't hold the reply.
    threads.main_call(_click, item)
    _log(f"Pressed {text!r} in {window.title()}")
    return {"pressed": text}


def call_type(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window"))
    field = _pick(window, _arg(args, "field"), ("field",), "field")
    text = str((args or {}).get("text", ""))
    if not field.isEnabled():
        raise WindowError(f"That field is turned off in {window.title()}")
    _type_into(field, text)
    name = field.objectName() or _plain(field.property("placeholderText"))
    _log(f"Typed into {name!r} in {window.title()}")
    return {"text": _plain(field.property("text"))}


def _guard(fn: Any) -> Any:  # noqa: ANN401
    """Checks the call runs on the main thread (WindowError is already
    control_api's CallError)."""

    def run(args: dict | None) -> Any:  # noqa: ANN401
        threads.assert_main(f"control_windows.{fn.__name__}")
        return fn(args)

    run.__name__ = fn.__name__
    return run


def register_api_calls(control_api: object, backend: object = None) -> None:
    """Registers the window calls with gremlin/control_api.py (attach_ui).
    backend: the program's Backend (found through the QML engine when not
    given)."""
    register = getattr(control_api, "register")
    calls = (
        (
            "window.list",
            call_list,
            10.0,
            "Every window: title and whether it is shown.",
        ),
        (
            "window.open",
            lambda args: call_open(args, backend),
            10.0,
            "Opens a window by its menu command id {command}.",
        ),
        (
            "window.close",
            call_close,
            10.0,
            "Closes a window {window} (not the main window).",
        ),
        (
            "window.read",
            call_read,
            10.0,
            "A window's shown text, buttons, checks and fields {window}.",
        ),
        (
            "window.screenshot",
            call_screenshot,
            30.0,
            "A PNG of one window {window, path}.",
        ),
        (
            "window.press",
            call_press,
            10.0,
            "Presses a button {window, button} (text or objectName).",
        ),
        ("window.type", call_type, 10.0, "Types into a field {window, field, text}."),
    )
    for name, fn, timeout_s, summary in calls:
        register(
            name, _guard(fn), main_thread=True, timeout_s=timeout_s, summary=summary
        )
