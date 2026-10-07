# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen: the Button Map's Options pane in an 800 px wide Button Map
window at a UI scale (test_handson_G2_options_labels.py). For every group
but Library, each setting's label: its text, whether it is shortened (…)
and whether its text runs past its box. Prints RESULT {json}.

    python test/unit/handson_G2_options_labels_smoke.py SCALE [shot-folder]
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake = fake_hardware.install()

SCALE = int(sys.argv[1]) if len(sys.argv) > 1 else 100
SHOTS = Path(sys.argv[2]) if len(sys.argv) > 2 else None

from gremlin.ui import ui_scale_option  # noqa: E402

ui_scale_option.active_scale = lambda: SCALE  # type: ignore[assignment]

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtQuick, QtTest  # noqa: E402

import dill  # noqa: E402
import joystick_gremlin  # noqa: E402

GUID = str(dill.GUID(fake.devices[0].device_guid).uuid)


def call(obj: QtCore.QObject, name: str, *args: object) -> object:
    return QtCore.QMetaObject.invokeMethod(
        obj,
        name,
        QtCore.Q_RETURN_ARG("QVariant"),
        *[QtCore.Q_ARG("QVariant", a) for a in args],
    )


def wait_until(check, what: str, timeout: float = 10.0):  # noqa: ANN001, ANN201
    deadline = time.monotonic() + timeout
    while True:
        value = check()
        if value:
            return value
        if time.monotonic() > deadline:
            raise TimeoutError(what)
        QtTest.QTest.qWait(20)


def main() -> None:
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root = wait_until(lambda: app.engine.rootObjects(), "the main window")[0]
    card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": GUID}
    call(root, "openButtonMapForCard", card)
    win = wait_until(lambda: call(root, "buttonMapWindow"), "the Button Map")
    # The width the hands-on check used.
    win.setProperty("width", 800)
    win.setProperty("height", 600)
    QtTest.QTest.qWait(300)
    out: dict = {"scale": SCALE, "window": win.property("width")}

    def ev(code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, code)
        value = expr.evaluate()
        if expr.hasError():
            return "error: " + expr.error().toString()
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for c in item.childItems():
            found += items(c)
        return found

    def child(name: str) -> QtQuick.QQuickItem | None:
        found = (c for c in items(win.contentItem()) if c.objectName() == name)
        return next(found, None)

    ev("_tools.setOpen('options', true)")
    pane = wait_until(
        lambda: (p := child("optionsPane")) is not None and p.isVisible() and p,
        "the Options pane",
    )
    groups = ["labels", "editing", "autosave", "view", "colours"]
    labels: list = []
    for group in groups:
        ev(f"_opts.paneGroup = '{group}'")
        QtTest.QTest.qWait(300)
        rows = [
            c
            for c in items(pane)
            if c.objectName().startswith("option:") and c.isVisible()
        ]
        for row in rows:
            # The row's first text: the setting's label.
            label = next(c for c in row.childItems() if c.inherits("QQuickText"))
            # A number box's or list's own text: not squeezed either.
            boxes = [
                c.property("contentItem")
                for c in row.childItems()
                if c.isVisible()
                and (c.inherits("QQuickSpinBox") or c.inherits("QQuickComboBox"))
            ]
            box = [
                [b.property("contentWidth"), b.width()]
                for b in boxes
                if b is not None and b.property("contentWidth") is not None
            ]
            labels.append(
                {
                    "group": group,
                    "key": row.objectName()[len("option:") :],
                    "text": label.property("text"),
                    "truncated": bool(label.property("truncated")),
                    "content": label.property("contentWidth"),
                    "width": label.width(),
                    "lines": label.property("lineCount"),
                    "box": box,
                    # The row is inside the pane.
                    "row-end": row.mapToScene(QtCore.QPointF(row.width(), 0)).x(),
                    "pane-end": pane.mapToScene(QtCore.QPointF(pane.width(), 0)).x(),
                }
            )
        if SHOTS is not None:
            SHOTS.mkdir(parents=True, exist_ok=True)
            win.grabWindow().save(str(SHOTS / f"options-{SCALE}-{group}.png"))
    out["pane-width"] = pane.width()
    out["labels"] = labels
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
