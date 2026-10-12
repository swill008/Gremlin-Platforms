# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final fix round X3: a binding's Note on the input rows (05 S43,
D-05-S43-BOTHROWS) and mode lists in alphabetical order whatever the
capitals (04 S41, D-04-ALPHA-CASEFOLD).

Off-screen, fakes only.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import uuid
from collections.abc import Iterator
from typing import Any

import pytest
from PySide6 import QtCore

import dill
from gremlin import plugin_manager, shared_state
from gremlin.event_handler import Event
from gremlin.profile import Profile
from gremlin.types import InputType

_STICK = uuid.UUID("0f0f0f0f-0303-0303-0303-0f0f0f0f0f0f")
_APPS: list[QtCore.QCoreApplication] = []
_KEEP: list[QtCore.QObject] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app
    while _KEEP:
        _KEEP.pop().deleteLater()


@pytest.fixture
def profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    shared_state.current_profile = Profile()
    yield shared_state.current_profile
    shared_state.current_profile = old


def _vjoy(out: int) -> Any:  # noqa: ANN401
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _bind(item: Any, out: int, note: str | None = None) -> None:  # noqa: ANN401
    binding = item.add_item_binding()
    binding.root_action.insert_action(_vjoy(out), "children")
    if note is not None:
        binding.root_action.action_label = note


def _role(model: Any, name: bytes) -> int:  # noqa: ANN401
    return next(r for r, n in model.roleNames().items() if bytes(n) == name)


# --- 05 S43: the Note on the input's row --------------------------------------


def test_a_new_binding_has_no_note(profile: Profile) -> None:
    from gremlin.ui.binding_catalog import item_note

    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    _bind(item, 1)  # its root keeps the plugin name "Root"
    assert item_note(item) == ""
    _bind(item, 2, "  ")
    _bind(item, 3, "Gear lever")
    _bind(item, 4, "Flaps")
    _bind(item, 5, "Gear lever")
    assert item_note(item) == "Gear lever, Flaps"
    assert item_note(item, [3]) == "Flaps"


@pytest.fixture
def catalog(profile: Profile) -> Iterator[Any]:
    # The Device Bindings page's model (HardwareLayoutModel), buttons 1-2 claimed.
    from test.unit.hardware_page_helper import close, page_on

    model: Any = page_on(_STICK, [("button", 1), ("button", 2)])
    yield model
    close(model)


def test_the_device_bindings_input_row_carries_the_note(
    profile: Profile, catalog: Any  # noqa: ANN401
) -> None:
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    _bind(item, 1, "Gear lever")
    other = profile.get_input_item(
        _STICK, InputType.JoystickButton, 2, "Default", create_if_missing=True
    )
    _bind(other, 2)
    catalog._rebuild()
    note = _role(catalog, b"note")
    by_kind = {
        (catalog.data(catalog.index(i, 0), _role(catalog, b"rowKind")),
         catalog.data(catalog.index(i, 0), _role(catalog, b"systemName"))): i
        for i in range(catalog.rowCount())
    }
    subtitle = _role(catalog, b"subtitle")
    group = catalog.index(by_kind[("parent", "Button 1")], 0)
    assert catalog.data(group, note) == "Gear lever"
    assert catalog.data(group, subtitle) == "Gear lever"  # the line under the name
    # No Note: no line, and the role is "" (QML wants a string); the row
    # still names its destination.
    plain = catalog.index(by_kind[("parent", "Button 2")], 0)
    assert catalog.data(plain, note) == ""
    assert catalog.data(plain, subtitle) == ""
    # Named in its action summary (05 S142), with or without the red ⚠
    # (no vJoy module here, D-05-CANT-SEND).
    dest = str(catalog.data(plain, _role(catalog, b"actionSummary")))
    assert dest.startswith("1 action · ")
    assert "vJoy 1" in dest and "Button 2" in dest
    leaf = catalog.index(by_kind[("child", "Button 1")], 0)
    assert catalog.data(leaf, note) == ""


def test_the_keyboard_key_row_carries_the_note(profile: Profile) -> None:
    # The Keyboard page's model (KeyboardLayoutModel, 05 S128): the key's
    # parent row shows the Note under its name, as the Device Bindings page.
    from gremlin.modules import store
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel

    model = KeyboardLayoutModel()
    _KEEP.append(model)
    key = (0x21, False)
    event = Event(InputType.Keyboard, key, dill.UUID_Keyboard, "Default")
    # addKey holds the new key in the Keyboard layout until Save (AD4):
    # dropped after, or a later test's "*" sees it.
    row_key = model.addKey([event], "Default")
    try:
        item = profile.get_input_item(
            dill.UUID_Keyboard, InputType.Keyboard, key, "Default"
        )

        def subtitle() -> str:
            model._rebuild()
            rows = [r for r in model._rows if r["key"] == row_key]
            assert rows, row_key
            return rows[0]["subtitle"]

        assert subtitle() == ""
        _bind(item, 1, "Gear lever")
        assert subtitle() == "Gear lever"
    finally:
        store.discard_pending(str(dill.UUID_Keyboard))


# --- 04 S41: alphabetical whatever the capitals ---------------------------------


def test_the_mode_list_sorts_ignoring_capitals(
    profile: Profile,
) -> None:
    from gremlin.ui.profile import ModeListModel

    for name in ("echo", "Bravo", "alpha"):
        profile.modes.add_mode(name)
    model = ModeListModel()
    _KEEP.append(model)
    role = QtCore.Qt.ItemDataRole.UserRole + 1
    listed = [model.data(model.index(i, 0), role) for i in range(model.rowCount())]
    assert listed == ["alpha", "Bravo", "Default", "echo"]
