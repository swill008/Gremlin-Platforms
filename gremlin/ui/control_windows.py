# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The control API's window calls (claude/plans/control-api-contract.md).

Windows are named by their shown title, any case: "Options", "device
library", or the whole title bar text. Every call runs on the main thread
(control_api runs them there); a press only checks the button and queues
the click, so a button that opens a dialog never holds the API's reply.
Each open, close, press and type writes a system log line "... by API"
at Warning level (13 S18). Errors are one sentence with names in 'quotes'
and a code (13 S25, S27); close, type and open say whether they worked
(13 S29).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from PySide6 import QtCore, QtGui, QtQml, QtQuick

from gremlin import threads
from gremlin.control_api import Arg, CallError
from gremlin.ui import window_titles


class WindowError(CallError):
    """A window call that can't be done; its text is the API's error (an
    expected error: one plain line, no traceback) and code one of
    control_api.CODES."""


def _log(text: str) -> None:
    logging.getLogger("system").warning(f"{text} by API")


def _q(name: object) -> str:
    """A name as messages quote it (13 S27)."""
    return f"'{name}'"


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
    windows = _windows()
    exact = [w for w in windows if want in _names(w)]
    if not exact:
        exact = [w for w in windows if any(n.startswith(want) for n in _names(w))]
    shown = [w for w in exact if w.isVisible()]
    found = shown or exact
    if len(found) == 1:
        return found[0]
    if not found:
        raise WindowError(f"No window called {_q(name)}.", "not_found")
    titles = ", ".join(_q(t) for t in sorted({w.title() for w in found}))
    raise WindowError(f"{len(found)} windows match {_q(name)}: {titles}.", "not_found")


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


def _spin_box(field: QtQuick.QQuickItem) -> QtQuick.QQuickItem | None:
    """The spin box whose number field this is, if any."""
    parent = field.parentItem()
    if parent is not None and parent.inherits("QQuickSpinBox"):
        return parent
    return None


def _name(item: QtQuick.QQuickItem) -> str:
    """The item's objectName; a spin box's number field goes by its spin
    box's name, or the name of the item that loads the spin box (as
    FloatSpinBox does)."""
    own = item.objectName()
    box = _spin_box(item) if not own else None
    if box is None:
        return own
    if box.objectName():
        return box.objectName()
    holder = box.parentItem()
    if holder is not None and holder.inherits("QQuickLoader"):
        holder = holder.parentItem()
        if holder is not None:
            return holder.objectName()
    return ""


def _row(item: QtQuick.QQuickItem, kind: str) -> dict[str, Any]:
    row: dict[str, Any] = {
        "kind": kind,
        "name": _name(item),
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
    items = [it for it in _walk(_root(window)) if _kind(it) in kinds]
    by_id = [it for it in items if _name(it) == want]
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
        raise WindowError(f"No {what} {_q(name)} in {_q(window.title())}.", "not_found")
    raise WindowError(
        f"{len(by_id)} {what}s called {_q(name)} in {_q(window.title())};"
        " name one by its objectName.",
        "not_found",
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


def _kept(field: QtQuick.QQuickItem, text: str) -> bool:
    """Whether the field shows text (a spin box: the same number, however
    it formats it)."""
    shown = _plain(field.property("text"))
    if shown == _plain(text):
        return True
    if _spin_box(field) is None:
        return False
    try:
        return float(shown.replace(",", "")) == float(text.replace(",", ""))
    except ValueError:
        return False


def _type_into(field: QtQuick.QQuickItem, text: str) -> bool:
    """Replaces the field's text as typing would (its edit handlers run),
    then finishes the edit as leaving the field does. False, with the old
    text put back, when the field turned the text away (a validator or
    input mask, or a spin box that kept its number) (13 S29)."""
    old = field.property("text")
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
    if not _kept(field, text):
        # A validator or input mask turned keys away.
        field.setProperty("text", old)
        return False
    if field.metaObject().indexOfMethod("editingFinished()") >= 0:
        QtCore.QMetaObject.invokeMethod(field, "editingFinished")
    box = _spin_box(field)
    if box is not None:
        # A spin box takes the typed number on Enter, as the user's would.
        for kind in (QtCore.QEvent.Type.KeyPress, QtCore.QEvent.Type.KeyRelease):
            QtCore.QCoreApplication.sendEvent(
                box, QtGui.QKeyEvent(kind, QtCore.Qt.Key.Key_Return, none)
            )
    # A spin box puts its old number back when the typed one is out of range.
    return _kept(field, text)


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


def _arg(args: dict | None, key: str, call: str) -> str:
    """A required argument (control_api checks the declared ones first;
    this covers a direct call)."""
    value = (args or {}).get(key)
    if value is None or str(value).strip() == "":
        raise WindowError(f"{call} needs {key}.", "bad_args")
    return str(value)


def call_list(_args: dict | None = None) -> list[dict[str, Any]]:
    return [{"title": w.title(), "visible": bool(w.isVisible())} for w in _windows()]


def call_open(args: dict | None, backend: object = None) -> dict[str, Any]:
    """Runs a main window command that opens a window (13 S29): its row in
    Backend.command_list says so with "window": true."""
    command = _arg(args, "id", "window.open")
    be = _backend(backend)
    listing = getattr(be, "command_list", None)
    run = getattr(be, "run_command_id", None)
    rows = listing() if listing is not None else []
    if run is None or not rows:
        raise WindowError("The menu commands aren't ready yet.", "not_ready")
    row = next((r for r in rows if r.get("id") == command), None)
    if row is None:
        raise WindowError(f"No command called {_q(command)}.", "not_found")
    if not row.get("window"):
        raise WindowError(
            f"{_q(command)} opens no window; run it with command.run"
            " (gremlin-ctl run-command).",
            "refused",
        )
    if not run(command):
        raise WindowError(f"{_q(command)} can't be used now.", "not_ready")
    _log(f"Ran menu command {_q(command)}")
    return {"ran": True}


def call_close(args: dict | None) -> dict[str, Any]:
    """Answers once the window has closed; one that stays open (it asks
    about unsaved changes) is refused (13 S13, S29)."""
    window = find_window(_arg(args, "window", "window.close"))
    if _is_main(window):
        raise WindowError("The API doesn't close the main window.", "refused")
    title = window.title()
    window.close()
    if window.isVisible():
        raise WindowError(
            f"{_q(title)} stayed open; it may be asking about unsaved changes"
            " in the program.",
            "refused",
        )
    _log(f"Closed window {_q(title)}")
    return {"closed": title}


def call_read(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window", "window.read"))
    return {"title": window.title(), "items": read_items(window)}


def call_screenshot(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window", "window.screenshot"))
    path = _arg(args, "path", "window.screenshot")
    if not Path(path).is_absolute():
        raise WindowError("Give the full path.", "bad_args")
    if not path.lower().endswith(".png"):
        raise WindowError("The picture path must end in .png.", "bad_args")
    folder = QtCore.QFileInfo(path).absoluteDir()
    if not folder.exists():
        raise WindowError(f"No folder {_q(folder.absolutePath())}.", "not_found")
    if not window.isVisible():
        raise WindowError(f"{_q(window.title())} isn't shown.", "not_ready")
    image = window.grabWindow()
    if image.isNull():
        raise WindowError(f"Couldn't take a picture of {_q(window.title())}.")
    if not image.save(path):
        raise WindowError(f"Couldn't write {_q(path)}.")
    return {"path": path, "width": image.width(), "height": image.height()}


def call_press(args: dict | None) -> dict[str, Any]:
    window = find_window(_arg(args, "window", "window.press"))
    item = _pick(
        window, _arg(args, "button", "window.press"), ("button", "check"), "button"
    )
    text = _text_inside(item) or item.objectName()
    if not item.isEnabled():
        raise WindowError(
            f"{_q(text)} is turned off in {_q(window.title())}.", "refused"
        )
    # Queued: a button that opens a dialog or runs long doesn't hold the reply.
    threads.main_call(_click, item)
    _log(f"Pressed {_q(text)} in {_q(window.title())}")
    return {"pressed": text}


def call_type(args: dict | None) -> dict[str, Any]:
    """Types text (required; "" clears the field) and checks the field
    kept it (13 S29)."""
    window = find_window(_arg(args, "window", "window.type"))
    field = _pick(window, _arg(args, "field", "window.type"), ("field",), "field")
    if (args or {}).get("text") is None:
        raise WindowError("window.type needs text.", "bad_args")
    text = str((args or {})["text"])
    name = _name(field) or _plain(field.property("placeholderText"))
    if not field.isEnabled():
        raise WindowError(
            f"{_q(name)} is turned off in {_q(window.title())}.", "refused"
        )
    if not _type_into(field, text):
        raise WindowError(
            f"{_q(name)} in {_q(window.title())} doesn't take {_q(text)}.", "refused"
        )
    _log(f"Typed into {_q(name)} in {_q(window.title())}")
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
    window = Arg("str", required=True, help="the window's shown title, any case")
    calls = (
        (
            "window.list",
            call_list,
            10.0,
            "Every window: title and whether it is shown.",
            {},
        ),
        (
            "window.open",
            lambda args: call_open(args, backend),
            10.0,
            "Opens a window by its menu command id {id} (commands lists them).",
            {"id": Arg("str", required=True, help="a menu command id from commands")},
        ),
        (
            "window.close",
            call_close,
            10.0,
            "Closes a window {window} (not the main window).",
            {"window": window},
        ),
        (
            "window.read",
            call_read,
            10.0,
            "A window's shown text, buttons, checks and fields {window}.",
            {"window": window},
        ),
        (
            "window.screenshot",
            call_screenshot,
            30.0,
            "A PNG of one window {window, path}.",
            {
                "window": window,
                "path": Arg("str", required=True, help="the full path of a .png file"),
            },
        ),
        (
            "window.press",
            call_press,
            10.0,
            "Presses a button {window, button} (text or objectName).",
            {
                "window": window,
                "button": Arg("str", required=True, help="its text or objectName"),
            },
        ),
        (
            "window.type",
            call_type,
            10.0,
            "Types into a field {window, field, text}.",
            {
                "window": window,
                "field": Arg(
                    "str", required=True, help="its objectName or placeholder text"
                ),
                "text": Arg(
                    "str",
                    required=True,
                    allow_empty=True,
                    help='the text; "" clears the field',
                ),
            },
        ),
    )
    for name, fn, timeout_s, summary, args in calls:
        register(
            name,
            _guard(fn),
            main_thread=True,
            timeout_s=timeout_s,
            summary=summary,
            args=args,
        )
