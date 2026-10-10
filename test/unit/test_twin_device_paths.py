# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Twins (two identical pads: same Windows name, VID and PID) are told
apart by their own HID instance path, never by name (02 S16 twin names are
for display only; HidHide hidden list per device and the Input Tester's
expected rows, 02 S99-S114). Seen on the user's PC 2026-10-10: one pad on
HidHide's list, the other not; both were "expected hidden", the visible
pad was reported under the first pad's name, and the HidHide watch named
the visible path under both names. Fake devices and a fake HidHide only:
DirectInput, dill and the HidHide driver are never opened."""

from __future__ import annotations

import os
import pathlib
import uuid
from types import SimpleNamespace

import pytest

from gremlin import device_paths, hidhide_watch, trace
from gremlin import hidhide_driver as drv
from gremlin import input_tester_link as link
from gremlin.input_tester import compare as cmp
from gremlin.input_tester.devices import SeenDevice
from test.unit.test_input_tester_link import setup  # noqa: F401 - the fixture
from test.unit.test_input_tester_logs import make, write_expected
from test.unit.test_trace_hidhide import hidhide  # noqa: F401 - the fixture

NAME = "Controller (Xbox One For Windows)"
TWIN = NAME + " (2)"
GA = uuid.UUID("2E8681B0-A954-11F1-8001-444553540000")
GB = uuid.UUID("3EF38010-C471-11F1-8001-444553540000")
PA = r"HID\VID_045E&PID_02FF&IG_00\8&325ECAAB&0&0000"
PB = r"HID\VID_045E&PID_02FF&IG_00\B&27477816&0&0000"


class _Guid:
    def __init__(self, value: uuid.UUID) -> None:
        self.uuid = value

    def __str__(self) -> str:
        return "{" + str(self.uuid).upper() + "}"


def _pad(guid: uuid.UUID, name: str) -> SimpleNamespace:
    return SimpleNamespace(
        device_guid=_Guid(guid), name=name, vendor_id=0x045E, product_id=0x02FF,
        is_virtual=False,
    )


@pytest.fixture
def twins(monkeypatch: pytest.MonkeyPatch) -> list[SimpleNamespace]:
    """Pad A (hidden path PA) and pad B (PB, not on the list); DirectInput
    answers each GUID with its own path; no HidHide window links."""
    from gremlin import device_initialization, input_monitor
    from gremlin.ui import hidhide as hh

    pads = [_pad(GA, NAME), _pad(GB, TWIN)]
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: pads)
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [])
    monkeypatch.setattr(
        drv, "list_hid_devices",
        lambda gaming_only: [
            {"instanceId": PA, "instanceIds": [PA], "name": NAME},
            {"instanceId": PB, "instanceIds": [PB], "name": NAME},
        ],
    )
    paths = {GA: PA, GB: PB}
    monkeypatch.setattr(device_paths, "hid_instance", lambda guid: paths.get(guid, ""))
    monkeypatch.setattr(hh, "_load_links", lambda: {})
    names = {GA: NAME, GB: TWIN}
    monkeypatch.setattr(input_monitor, "device_name", lambda uid: names[uid])
    return pads


def test_interface_path_becomes_instance_path() -> None:
    assert device_paths.instance_id(
        r"\\?\hid#vid_045e&pid_02ff&ig_00#b&27477816&0&0000"
        r"#{4d1e55b2-f16f-11cf-88cb-001111000030}"
    ) == PB
    assert device_paths.instance_id("not a path") == ""


def test_hidhide_watch_names_each_path_once_under_its_own_name(
    hidhide: object,  # noqa: F811
    twins: list[SimpleNamespace],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """02 S96: a ticked stick not on the hidden list under its own path is
    one warning, for that stick only."""
    monkeypatch.setattr(trace, "ticked_devices", lambda: [GA, GB])
    monkeypatch.setattr(hidhide_watch, "_rows", None)
    out = hidhide_watch._not_hidden([PA])
    assert list(out.values()) == [
        f"{TWIN} is NOT hidden: it is {PB}, which isn't on the list"
    ]


def test_expected_json_gives_each_twin_its_own_path_and_expect(
    setup: SimpleNamespace,  # noqa: F811
    twins: list[SimpleNamespace],
) -> None:
    setup.hh.devices = [PA]
    sticks = {s["guid"]: s for s in link.build_expected()["sticks"]}
    a, b = sticks[str(_Guid(GA))], sticks[str(_Guid(GB))]
    assert (a["name"], a["instance_ids"], a["expect"]) == (NAME, [PA], "hidden")
    assert (b["name"], b["instance_ids"], b["expect"]) == (TWIN, [PB], "visible")


def test_tester_reports_the_visible_twin_under_its_own_name() -> None:
    """The tester sees only pad B, and DirectInput gave it pad A's GUID in
    the tester's process: matched by path, pad A is hidden as expected and
    pad B is the one seen."""
    expected = {
        "sticks": [
            {"name": NAME, "windows_name": NAME, "vid": 0x045E, "pid": 0x02FF,
             "guid": str(_Guid(GA)), "instance_ids": [PA], "expect": "hidden"},
            {"name": TWIN, "windows_name": TWIN, "vid": 0x045E, "pid": 0x02FF,
             "guid": str(_Guid(GB)), "instance_ids": [PB], "expect": "visible"},
        ],
    }
    seen = [
        SeenDevice(
            key=f"di:{_Guid(GA)}", kind="directinput", name=NAME, vid=0x045E,
            pid=0x02FF, guid=str(_Guid(GA)), instance_id=PB,
        )
    ]
    rows = {r.name: r for r in cmp.compare(expected, seen, False).rows}
    assert (rows[NAME].seen, rows[NAME].verdict) == (False, "ok")
    assert (rows[TWIN].seen, rows[TWIN].verdict) == (True, "ok")
    assert all(r.kind != "other" for r in rows.values())


def _changed_lines(gremlin_dir: pathlib.Path) -> int:
    text = (gremlin_dir / "tester" / "tester.log").read_text(encoding="utf-8")
    return text.count("Gremlin's expected devices changed")


def test_tester_says_expected_changed_only_when_it_did(
    qapp: object, tmp_path: pathlib.Path,
) -> None:
    """Refresh and a rewrite with the same content (only "written" moves)
    log no change; a real change logs one."""
    path = write_expected(tmp_path)
    model = make(str(tmp_path))
    model.refresh()
    model.refresh()
    write_expected(tmp_path, written="2026-10-10T04:09:00")
    os.utime(path, (1, 1))
    model.check_changes()
    assert _changed_lines(tmp_path) == 0
    write_expected(tmp_path, hidhide_change="settings")
    os.utime(path, (2, 2))
    model.check_changes()
    assert _changed_lines(tmp_path) == 1
