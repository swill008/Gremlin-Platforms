# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Qt properties QML sets need a getter: QML silently drops a value set on a
property it can't read (upstream 855eb31c). So a Logical Device picker that
asked for buttons was shown every axis, button and hat.

Spec: 06 section 10 (Logical Device picker filter), 05 (Health and Search
target pickers ask for one input type).
"""

from __future__ import annotations

import ast
import pathlib
import sys
from collections.abc import Iterator

sys.path.append(".")

import pytest
from PySide6 import QtCore, QtQml

from gremlin.logical_device import LogicalDevice
from gremlin.types import InputType

ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture
def logical() -> Iterator[LogicalDevice]:
    """The Logical Device holding one axis and one button."""
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    assert app is not None
    device = LogicalDevice()
    device.reset()
    device.create(InputType.JoystickAxis)
    device.create(InputType.JoystickButton)
    yield device
    device.reset()


def test_selector_with_valid_types_button_lists_only_buttons(
    logical: LogicalDevice,
) -> None:
    import gremlin.ui.device  # noqa: F401  (registers Gremlin.Device)
    import gremlin.ui.model_factory  # noqa: F401  (registers Gremlin.UI)

    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    # Made through the factory as every page now does (memory fix); QML
    # still sets validTypes itself, which is what the getter must allow.
    component.setData(
        b"import QtQuick\nimport Gremlin.Device\nimport Gremlin.UI\n"
        b"QtObject {\n  id: root\n"
        b"  readonly property QtObject m:\n"
        b'    ModelFactory.create("LogicalDeviceSelectorModel", root)\n'
        b'  Component.onCompleted: m.validTypes = ["button"]\n}',
        QtCore.QUrl(),
    )
    holder = component.create()
    assert holder is not None, component.errorString()
    model = QtQml.QQmlProperty.read(holder, "m")
    assert model is not None
    try:
        assert model.rowCount() == 1  # 2 (axis and button) when QML drops it
        assert model.property("validTypes") == ["button"]
        type_role = QtCore.Qt.ItemDataRole.UserRole + 3
        assert model.data(model.index(0, 0), type_role) == "button"
    finally:
        holder.deleteLater()
        engine.deleteLater()


def _write_only_properties(path: pathlib.Path) -> list[str]:
    """`QtCore.Property(..., fset=...)` calls with no getter: neither a
    second positional argument nor fget=. The decorator form
    (`@QtCore.Property(type, fset=...)`) decorates the getter, so it has one."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    decorators = {
        id(d)
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        for d in node.decorator_list
    }
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or id(node) in decorators:
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
        if name != "Property":
            continue
        keywords = {k.arg for k in node.keywords}
        has_getter = len(node.args) >= 2 or "fget" in keywords
        if "fset" in keywords and not has_getter:
            found.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    return found


def test_no_qt_property_has_a_setter_without_a_getter() -> None:
    files = [
        p
        for folder in ("gremlin", "action_plugins")
        for p in (ROOT / folder).rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    assert files
    found = [hit for p in files for hit in _write_only_properties(p)]
    assert found == [], f"setter without a getter (QML drops the value): {found}"
