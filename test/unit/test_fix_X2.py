# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Fix round X2: a device with no module file that isn't plugged in at a
scan is forgotten (twin name, alias, HidHide photo and link; decision
D-02-GL243-FORGET, 02 S13, S15), and Device Information's own pad note
(D-02-Q6-WORDING).

Fake driver only; the HidHide driver is never called (its writers raise),
and every setting a test changes is put back."""

from __future__ import annotations

import sys

sys.path.append(".")

import collections
import json
import pathlib
from collections.abc import Iterator

import pytest
import shiboken6
from PySide6 import QtCore

import dill
from gremlin import device_initialization as di
from gremlin.config import Configuration
from test import fake_hardware

_APP = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
_STICK = str(dill.GUID(fake_hardware.raw_guid(is_virtual=False)).uuid).upper()
_GONE = "11111111-2222-3333-4444-555555555555"
_KEPT = "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE"
_BOUND = "99999999-8888-7777-6666-555555555555"


@pytest.fixture
def scan(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Iterator[pathlib.Path]:
    """A first scan from an empty list with modules in tmp_path; the twin,
    alias and HidHide settings put back after."""
    from gremlin import device_aliases, hidhide_driver
    from gremlin.modules import store
    from gremlin.ui import device_names, hidhide

    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    monkeypatch.setattr(di, "_joystick_devices", collections.OrderedDict())
    monkeypatch.setattr(di, "_left_out", set())
    monkeypatch.setattr(di, "_vjoy_problems", [])
    monkeypatch.setattr(di, "_told", ())
    monkeypatch.setattr(di, "_own_pads", [])
    monkeypatch.setattr("gremlin.modules.output.reset_vjoy", lambda: None)
    monkeypatch.setattr("gremlin.signal.display_error", lambda *a: None)

    def never(*_a: object) -> bool:
        raise AssertionError("the HidHide driver was called")

    for name in ("set_active", "set_blacklist", "set_whitelist", "set_inverse"):
        monkeypatch.setattr(hidhide_driver, name, never)
        monkeypatch.setattr(hidhide, name, never)

    cfg = Configuration()
    device_names._ensure()
    hidhide._ensure_options()
    keys = [
        di.TWIN_SETTING,
        (device_names.SECTION, device_names.GROUP, device_names.NAME),
        ("display", "hidhide", "photos"),
        ("display", "hidhide", "module-links"),
    ]
    before = [cfg.value(*key) for key in keys]
    device_aliases._CACHE = None
    yield tmp_path
    for key, value in zip(keys, before):
        cfg.set(*key, value)
    device_aliases._CACHE = None
    # The real device list back for the next tests.
    monkeypatch.undo()
    di._joystick_devices.clear()
    di.joystick_devices_initialization()


def _module(folder: pathlib.Path, slug: str, doc: dict) -> None:
    (folder / f"{slug}.json").write_text(json.dumps(doc), encoding="utf-8")


def test_twin_names_of_unplugged_devices_without_a_file_are_forgotten(
    scan: pathlib.Path,
) -> None:
    _module(scan, "pjoy_pro_3", {"device": "pJoy Pro (3)", "boundGuidLocal": _KEPT})
    Configuration().set(*di.TWIN_SETTING, {
        _STICK: "pJoy Pro (2)",  # plugged in alone: still "(2)" (S15)
        _GONE: "pJoy Pro (4)",  # not plugged in, no module file
        _KEPT: "pJoy Pro (3)",  # not plugged in, has a module file (S13)
    })
    di.joystick_devices_initialization()

    assert Configuration().value(*di.TWIN_SETTING) == {
        _STICK: "pJoy Pro (2)", _KEPT: "pJoy Pro (3)",
    }
    names = {str(uid).upper(): dev.name for uid, dev in di._joystick_devices.items()}
    assert names[_STICK] == "pJoy Pro (2)"


def test_aliases_of_forgotten_devices_go_others_stay(scan: pathlib.Path) -> None:
    from gremlin import device_aliases
    from gremlin.ui import device_names

    _module(scan, "pjoy_pro_3", {"device": "pJoy Pro (3)", "boundGuidLocal": _KEPT})
    _module(scan, "old_stick", {"device": "Old Stick", "boundGuidLocal": _BOUND})
    Configuration().set(*di.TWIN_SETTING, {_KEPT: "pJoy Pro (3)"})
    device_names.set_alias(_STICK, "Main stick")  # plugged in
    device_names.set_alias("{" + _GONE.lower() + "}", "Gone stick")
    device_names.set_alias(_KEPT, "Spare twin")  # file found by its twin name
    device_names.set_alias(_BOUND, "Old one")  # file bound to its id
    device_names.set_alias("keyboard", "Keys")  # not a device id
    di.joystick_devices_initialization()

    device_aliases._CACHE = None
    assert device_names._load() == {
        _STICK: "Main stick", _KEPT: "Spare twin", _BOUND: "Old one",
        "keyboard": "Keys",
    }


def test_hidhide_photo_and_link_of_a_forgotten_device_go(scan: pathlib.Path) -> None:
    from gremlin.ui import hidhide

    _module(scan, "kept_stick", {"device": "Kept Stick"})
    photos = {"HID\\" + c: f"{c}.png" for c in "ABCD"}
    hidhide._save_links({
        r"HID\A": "Gone Stick", r"HID\B": "pJoy Pro", r"HID\C": "Kept Stick",
    })
    hidhide._save_photos(photos)
    di.joystick_devices_initialization()

    assert hidhide._load_links() == {r"HID\B": "pJoy Pro", r"HID\C": "Kept Stick"}
    # D has no link: the device scan can't tell; the HidHide list does.
    assert set(hidhide._load_photos()) == {r"HID\B", r"HID\C", r"HID\D"}
    hidhide._forget_unlisted_photos(
        [{"instanceId": r"HID\B", "instanceIds": [r"HID\B"]}]
    )
    assert set(hidhide._load_photos()) == {r"HID\B", r"HID\C"}


def test_gaming_only_list_forgets_no_photos(
    scan: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import hidhide

    hidhide._save_links({})
    hidhide._save_photos({r"HID\D": "d.png"})
    monkeypatch.setattr(hidhide, "_saved_gaming_only", lambda: True)
    monkeypatch.setattr(hidhide, "driver_present", lambda: False)
    monkeypatch.setattr(
        hidhide, "list_hid_devices", lambda _g: [{"instanceId": r"HID\B", "name": "x"}]
    )
    monkeypatch.setattr(hidhide, "_enrich_devices", lambda rows: rows)
    model = hidhide.HidHideModel()
    try:
        assert set(hidhide._load_photos()) == {r"HID\D"}
    finally:
        shiboken6.delete(model)  # off the device change signal


def test_device_information_names_this_programs_xbox_pad() -> None:
    assert di.NOTE_OWN_PAD == "this program's Xbox pad"
