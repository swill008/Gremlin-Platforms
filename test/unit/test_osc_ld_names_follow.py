# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page follows the Logical Device (D-01-OWNER-NOTICES 4a, 5a).

The Feedback editor's Logical Device choices and the Feedback row titles
read the names from memory, so an unsaved control shows, a rename shows
at once and a reload of the Logical Device file is followed.

Spec: 09 (D-01-OWNER-NOTICES 4a, 5a).
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from gremlin import osc_device_file, shared_state
from gremlin.logical_device import LogicalDevice
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import osc_feedback_model
from gremlin.ui.osc_layout import OscLayoutModel


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def ld() -> Iterator[LogicalDevice]:
    device = LogicalDevice()
    saved = device.to_dict()
    device.reset()
    yield device
    device.reset()
    for control in saved["controls"]:
        device.create(
            InputType.to_enum(control["type"]),
            control["id"],
            label=control["label"],
            user_label=control["user-label"],
            group=control["group"],
            uid=control["uid"],
        )


@pytest.fixture
def page(qapp: object, modules: Path, ld: LogicalDevice) -> Iterator[OscLayoutModel]:
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    shared_state.current_profile = Profile()
    model = OscLayoutModel()
    yield model
    model.endPane()
    model.endFeedback()
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    shared_state.current_profile = saved


def _logical_row(uid: str) -> dict:
    row = dict(osc_feedback_model.new_row())
    row["id"] = osc_device_file.new_id()
    row["source"] = {"kind": "logical", "device": None, "input": uid}
    row["address"] = "/ld"
    osc_device_file.write_feedback([row])
    return osc_device_file.read_feedback()[0]


def _title(model: OscLayoutModel, fb_id: str) -> str:
    names = {int(k): bytes(v.data()).decode() for k, v in model.roleNames().items()}
    roles = {name: role for role, name in names.items()}
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        if model.data(index, roles["key"]) == f"feedback:{fb_id}":
            return str(model.data(index, roles["title"]))
    raise AssertionError("feedback row not shown")


def test_an_unsaved_control_is_a_logical_choice(
    qapp: object, modules: Path, ld: LogicalDevice
) -> None:
    control = ld.create(InputType.JoystickButton, user_label="Gear lever")
    choices = cast("list", osc_feedback_model.OscFeedbackModel().logicalChoices)
    assert {"value": control.uid, "text": "Gear lever"} in choices


def test_choices_announce_a_logical_device_change(
    qapp: object, modules: Path, ld: LogicalDevice
) -> None:
    model = osc_feedback_model.OscFeedbackModel()
    seen: list[int] = []
    model.changed.connect(lambda: seen.append(1))
    signal.logicalDeviceModified.emit()
    assert seen


def test_a_rename_updates_the_feedback_row_title(
    page: OscLayoutModel, ld: LogicalDevice
) -> None:
    control = ld.create(InputType.JoystickButton, user_label="Gear lever")
    row = _logical_row(control.uid)
    page._rebuild()
    assert "Gear lever" in _title(page, row["id"])
    ld.set_user_label(control.identifier, "Flaps lever")
    signal.logicalDeviceModified.emit()
    title = _title(page, row["id"])
    assert "Flaps lever" in title and "Gear lever" not in title


def test_a_reload_rebuilds_titles_and_the_open_editor(
    page: OscLayoutModel, ld: LogicalDevice
) -> None:
    control = ld.create(InputType.JoystickButton, user_label="Gear lever")
    uid = control.uid
    row = _logical_row(uid)
    page._rebuild()
    page.beginFeedback(f"feedback:{row['id']}")
    # A reload of the Logical Device file: new rows in memory, same uid.
    ld.reset()
    ld.create(InputType.JoystickButton, user_label="Brake", uid=uid)
    signal.logicalDeviceReloaded.emit()
    signal.logicalDeviceModified.emit()
    assert "Brake" in _title(page, row["id"])
    editor = cast("dict", page.feedbackEditor)
    assert {"value": uid, "text": "Brake"} in editor["choices"]["logical"]
