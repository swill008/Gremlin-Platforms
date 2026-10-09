# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""01 S134/S135 (D-01-LEAVE-TEXT, D-01-ONE-RENAME) for the Button Map's
rename boxes, off-screen in the real program (started as joystick_gremlin.py
starts it, so the program-wide leave-text owner is in place): the saved style
and template renames in Options > Library and the template rename in File >
Templates > Manage Templates. Real clicks and keys: Rename (the box opens
focused with the whole name selected, no click into it), typing, then a
click away, Esc or Enter. Prints "RESULT name json" per check and
"done". test_leave_text_button_map.py runs it.

    python test/unit/leave_text_button_map_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert _spec and _spec.loader
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

import shiboken6  # noqa: E402
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402
from gremlin.ui import button_map_options  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)
Key = QtCore.Qt.Key
NoMod = QtCore.Qt.KeyboardModifier.NoModifier
Ctrl = QtCore.Qt.KeyboardModifier.ControlModifier
Left = QtCore.Qt.MouseButton.LeftButton

# Every style rename that reaches the store (one per leave, never two).
style_calls: list = []
_real_rename_style = button_map_options.rename_style


def _counted_rename_style(name: str, kind: str, new_name: str) -> bool:
    style_calls.append([name, new_name])
    return _real_rename_style(name, kind, new_name)


button_map_options.rename_style = _counted_rename_style


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj, name, QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def wait_until(check, timeout: float = 5.0):  # noqa: ANN001, ANN201
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            return None
        QtTest.QTest.qWait(20)


def items(item: QtQuick.QQuickItem) -> list:
    found = [item]
    for c in item.childItems():
        found += items(c)
    return found


def centre(item: QtQuick.QQuickItem) -> QtCore.QPoint:
    return item.mapToScene(
        QtCore.QPointF(item.width() / 2, item.height() / 2)
    ).toPoint()


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    QtTest.QTest.qWait(800)
    root = app.engine.rootObjects()[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    QtTest.QTest.qWait(1000)
    win = call(root, "buttonMapWindow")
    win.setProperty("width", 1200)
    win.setProperty("height", 800)
    QtTest.QTest.qWait(300)
    win.requestActivate()
    wait_until(lambda: QtGui.QGuiApplication.focusWindow() is win, 3)

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def click(point: QtCore.QPoint) -> None:
        QtTest.QTest.mouseClick(win, Left, NoMod, point)
        QtTest.QTest.qWait(200)

    def type_text(text: str) -> None:
        for ch in text:
            QtTest.QTest.keyClick(win, ch)
        QtTest.QTest.qWait(50)

    def key(code: QtCore.Qt.Key) -> None:
        QtTest.QTest.keyClick(win, code, NoMod)
        QtTest.QTest.qWait(250)

    def row_of(scope: QtQuick.QQuickItem, starts: str) -> QtQuick.QQuickItem | None:
        """The row whose label shows a name (a template's label adds its
        item count after the name)."""
        for it in items(scope):
            text = it.property("text") if it.inherits("QQuickText") else None
            if it.isVisible() and isinstance(text, str) and (
                text == starts or text.startswith(starts + "  ·  ")
            ):
                return it.parentItem()
        return None

    def start_rename(scope: QtQuick.QQuickItem, name: str, new: str) -> dict:
        """Rename on the row, then the new name typed straight away: the box
        opens focused with the whole old name selected (S135), so typing
        replaces it with no click into the box."""
        row = row_of(scope, name)
        if row is None:
            return {"row": False}
        button = next(
            c for c in items(row)
            if c.inherits("QQuickAbstractButton") and c.property("text") == "Rename"
        )
        click(centre(button))

        def open_box():  # noqa: ANN202
            return next(
                (c for c in items(row)
                 if c.inherits("QQuickTextInput") and c.isVisible()),
                None,
            )

        box = wait_until(open_box, 3)
        if box is None:
            return {"row": True, "shown": False, "focused": False}
        QtTest.QTest.qWait(100)
        focused = bool(box.hasActiveFocus())
        selected = box.property("selectedText") == name
        type_text(new)
        return {"row": True, "shown": True, "focused": focused,
                "selected": selected, "typed": box.property("text"), "box": box}

    def outcome(started: dict, renaming: object) -> dict:
        box = started.pop("box", None)
        started["renaming"] = renaming
        started["window"] = win.isVisible()
        # A saved rename rebuilds the row (the box goes with it).
        started["focus"] = bool(
            box is not None and shiboken6.isValid(box) and box.hasActiveFocus()
        )
        return started

    # --- Seed one saved style and two templates ---------------------------
    # Through the window's options (it tells every open Library).
    ev("_opts.saveStyle('Style A', 'chip', JSON.stringify({fill: '#ff0000'}))")
    nodes = json.dumps([{"id": "n1", "kind": "chip", "x": 0.1, "y": 0.1}])
    for name in ("Tmpl A", "Esc A", "Enter A", "Away A"):
        ev(f"_hw.saveTemplate({json.dumps(name)}, {json.dumps(nodes)}, 'pJoy Pro')")

    def style_names() -> list:
        return sorted(s["name"] for s in button_map_options.styles())

    def template_names() -> list:
        value = ev("JSON.stringify(_hw.templates().map(function(t){ return t.name }))")
        return sorted(json.loads(value)) if isinstance(value, str) else [value]

    # --- Options > Library ------------------------------------------------
    ev("_tools.setOpen('options', true)")
    ev("_opts.paneGroup = 'library'")
    QtTest.QTest.qWait(400)
    library = next(
        (c for c in items(win.contentItem())
         if c.metaObject().className().startswith("OptionButtonMapLibrary")),
        None,
    )
    if library is None:
        result("library", False)
        print("done", flush=True)
        os._exit(0)
    QtCore.QMetaObject.invokeMethod(library, "refreshTemplates")
    QtTest.QTest.qWait(200)
    heading = next(
        c for c in items(library)
        if c.inherits("QQuickText") and c.property("text") == "Styles"
    )
    blank = centre(heading)

    def lib_failed() -> bool:
        notice = next(
            (c for c in library.children() if c.objectName() == ""
             and c.metaObject().className().startswith("DismissibleDialog")
             and c.property("titleText") == "Rename Failed"),
            None,
        )
        return bool(notice is not None and notice.property("visible"))

    # Style: click away saves.
    s = start_rename(library, "Style A", "Style B")
    click(blank)
    QtTest.QTest.qWait(200)
    result("style-click-away", outcome(s, library.property("renaming"))
           | {"names": style_names(), "calls": list(style_calls)})
    # Style: Esc cancels (S135): the old name stays, nothing is saved.
    style_calls.clear()
    s = start_rename(library, "Style B", "Style C")
    key(Key.Key_Escape)
    result("style-esc", outcome(s, library.property("renaming"))
           | {"names": style_names(), "calls": list(style_calls),
              "window": win.isVisible()})
    # Style: Enter saves once.
    style_calls.clear()
    s = start_rename(library, "Style B", "Style D")
    key(Key.Key_Return)
    result("style-enter", outcome(s, library.property("renaming"))
           | {"names": style_names(), "calls": list(style_calls)})

    # Template in the Library: click away, Esc, Enter.
    for tag, new, how in (("click-away", "Tmpl B", None),
                          ("esc", "Tmpl C", Key.Key_Escape),
                          ("enter", "Tmpl D", Key.Key_Return)):
        # Esc cancels, so Enter starts from the name Esc left.
        old = {"Tmpl B": "Tmpl A", "Tmpl C": "Tmpl B", "Tmpl D": "Tmpl B"}[new]
        s = start_rename(library, old, new)
        if how is None:
            click(blank)
        else:
            key(how)
        QtTest.QTest.qWait(200)
        result(f"lib-template-{tag}", outcome(s, library.property("renaming"))
               | {"names": template_names(), "failed": lib_failed()})

    # --- File > Templates > Manage Templates --------------------------------
    ev("_tools.setOpen('options', false)")
    ev("_templatesDlg.open()")
    QtTest.QTest.qWait(500)
    dialog_items = [c for c in items(win.contentItem())]
    note = next(
        (c for c in dialog_items
         if c.inherits("QQuickText") and c.isVisible()
         and str(c.property("text") or "").startswith("Templates are kept")),
        None,
    )
    if note is None:
        result("dialog", False)
        print("done", flush=True)
        os._exit(0)
    dlg_blank = centre(note)
    scope = win.contentItem()

    def dlg_failed() -> bool:
        shown = "_failNotice.visible && _failNotice.titleText === 'Rename Failed'"
        return ev(shown) is True

    # One template each, so one way of leaving can't upset the next.
    for tag, old, new, how in (("esc", "Esc A", "Esc B", Key.Key_Escape),
                               ("enter", "Enter A", "Enter B", Key.Key_Return),
                               ("click-away", "Away A", "Away B", None)):
        s = start_rename(scope, old, new)
        if how is None:
            click(dlg_blank)
        else:
            key(how)
        QtTest.QTest.qWait(200)
        result(f"dlg-template-{tag}", outcome(s, ev("_templatesDlg.renaming"))
               | {"names": template_names(), "failed": dlg_failed(),
                  "open": ev("_templatesDlg.visible")})
        ev("_templatesDlg.renaming = ''")
        QtTest.QTest.qWait(100)

    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # noqa: BLE001
        print(f"ERROR {error!r}", flush=True)
    os._exit(1)
