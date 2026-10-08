# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library model, the gaps filled by LF, over LU's stand-in
Library (device_library_LU_fake_smoke.py): a device's inputs and when it was
last seen (S8), a saved setup's photo (S11), Copy from a device's current
settings (S22) and the open profile that was never saved (S33) passed on to
Copy, Swap, Change vJoy Output and Save."""

from __future__ import annotations

import importlib.util
import pathlib
from collections.abc import Callable

import pytest
from pytestqt.qtbot import QtBot

from gremlin.ui.device_library_model import DeviceLibraryModel

_HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke", _HERE / "device_library_LU_fake_smoke.py"
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)
Fake = fake_mod.FakeLibrary


@pytest.fixture
def lib() -> Fake:
    return fake_mod.FakeLibrary()


@pytest.fixture
def model(qtbot: QtBot, lib: Fake) -> DeviceLibraryModel:
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    qtbot.waitUntil(lambda: "Library: 48 MB" in m.statusText, timeout=5000)
    return m


def _run(qtbot: QtBot, model: DeviceLibraryModel, start: Callable[[], int]) -> dict:
    with qtbot.waitSignal(model.result, timeout=5000) as blocker:
        ticket = start()
    assert ticket
    return blocker.args[0]


def _calls(lib: Fake, name: str) -> list[tuple]:
    return [c for c in lib.calls if c[0] == name]


def test_s8_a_devices_inputs_and_last_seen(model: DeviceLibraryModel) -> None:
    model.select("dev-00000003")
    d = model.details
    assert d["inputs"] == "no buttons, 3 axes, no hats"
    assert d["lastSeen"] == "2026-10-05 18:30"
    model.select("dev-00000001")
    d = model.details
    assert d["inputs"] == "32 buttons, 6 axes, 1 hat"
    assert d["lastSeen"] == "now"


def test_s8_plugged_in_sticks_are_noted_as_seen(
    model: DeviceLibraryModel, lib: Fake
) -> None:
    noted = _calls(lib, "note_seen")
    assert noted and noted[0][1] == ["{AAAA-0001}", "{BBBB-0002}"]
    # Unplugged: noted once more (its last time seen), then not again.
    lib.devs[1]["state"] = "not_connected"
    model.refresh()
    assert _calls(lib, "note_seen")[-1][1] == ["{AAAA-0001}", "{BBBB-0002}"]
    count = len(_calls(lib, "note_seen"))
    model.refresh()
    assert len(_calls(lib, "note_seen")) == count


def test_s11_a_saved_setups_photo(
    model: DeviceLibraryModel, lib: Fake, tmp_path: pathlib.Path
) -> None:
    lib.photo_file = str(tmp_path / "photo.png")
    model.select("set-00000001")
    assert model.details["photo"] == lib.photo_file
    model.select("set-00000004")
    assert model.details["photo"] == ""


def test_s22_a_device_copies_its_current_settings(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    model.select("dev-00000003")  # set up here, not plugged in, no saved setups
    assert model.details["hasCurrent"] is True
    res = _run(
        qtbot,
        model,
        lambda: model.copy("dev-00000003", "dev-00000002", ["setup"], [""], []),
    )
    assert res["ok"], res
    assert _calls(lib, "copy")[-1][1:3] == ("dev-00000003", "Right stick")
    # A device only from someone else's pack has no current settings.
    model.select("dev-00000005")
    assert model.details["hasCurrent"] is False


def test_s33_the_never_saved_open_profile_is_passed_on(
    qtbot: QtBot, model: DeviceLibraryModel, lib: Fake
) -> None:
    unsaved = str(pathlib.Path(""))
    profiles = ["", "C:/p/DCS.xml"]
    _run(
        qtbot,
        model,
        lambda: model.copy("set-00000001", "dev-00000002", ["bindings"], profiles, []),
    )
    assert _calls(lib, "copy")[-1][4] == [unsaved, str(pathlib.Path("C:/p/DCS.xml"))]
    _run(
        qtbot,
        model,
        lambda: model.swap("dev-00000001", "dev-00000002", ["bindings"], profiles),
    )
    assert _calls(lib, "swap")[-1][4][0] == unsaved
    _run(
        qtbot,
        model,
        lambda: model.changeOutput("dev-00000001", {"1": 2}, False, profiles),
    )
    assert _calls(lib, "change_output")[-1][4][0] == unsaved
    _run(qtbot, model, lambda: model.saveToLibrary("dev-00000001", [""]))
    assert _calls(lib, "save_setup")[-1][3] == [unsaved]
