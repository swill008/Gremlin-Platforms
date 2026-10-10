# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""gremlin.device_reset with a fake runner, fake device list and fake clock.
The real runner (pnputil through an elevated cmd.exe) is never reached."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from gremlin import clock, device_reset

STICK_HID = "HID\\VID_231D&PID_3201\\A&1&0000"
STICK_USB = "USB\\VID_231D&PID_3201\\9&1D65FFE4&0&3"
PEDAL_HID = "HID\\VID_06A3&PID_0763\\B&2&0000"
PEDAL_USB = "USB\\VID_06A3&PID_0763\\5&ABC&0&1"


def _row(
    hid: str,
    usb: str,
    name: str,
    vid: int,
    pid: int,
    bus: str = "USB\\ROOT_HUB30\\4&1",
    bus_desc: str = "Root Hub",
) -> dict:
    return {
        "hid_id": hid,
        "usb_id": usb,
        "bus_id": bus,
        "bus_desc": bus_desc,
        "name": name,
        "windows_name": "USB Input Device",
        "vid": vid,
        "pid": pid,
    }


ROWS = [
    _row(STICK_HID, STICK_USB, "VPC Stick", 0x231D, 0x3201),
    # second collection of the same stick
    _row(STICK_HID + "X", STICK_USB, "VPC Stick", 0x231D, 0x3201),
    _row(PEDAL_HID, PEDAL_USB, "Pro Flight Rudder", 0x06A3, 0x0763),
    # vJoy: root enumerated and VID 1234 PID BEAD
    _row("HID\\HIDCLASS&COL01\\1&2", "ROOT\\HIDCLASS\\0000", "vJoy", 0x1234, 0xBEAD),
    _row("HID\\X&COL01\\1&3", "USB\\VID_1234&PID_BEAD\\1", "vJoy", 0x1234, 0xBEAD),
    # ViGEm Xbox 360 pad on the ViGEm bus
    _row(
        "HID\\VID_045E&PID_028E&IG_00\\1",
        "USB\\VID_045E&PID_028E\\1&2&3",
        "Controller (XBOX 360 For Windows)",
        0x045E,
        0x028E,
        bus="ROOT\\SYSTEM\\0002",
        bus_desc="Nefarius Virtual Gamepad Emulation Bus",
    ),
]


class FakeClock:
    def __init__(self) -> None:
        self.t = 100.0

    def monotonic(self) -> float:
        return self.t

    def sleep(self, s: float) -> None:
        self.t += s


@pytest.fixture(autouse=True)
def fakes(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[tuple[FakeClock, list[list[str]]]]:
    fc = FakeClock()
    monkeypatch.setattr(clock, "monotonic", fc.monotonic)
    monkeypatch.setattr(clock, "sleep", fc.sleep)
    device_reset.set_enumerator(lambda: [dict(r) for r in ROWS])
    device_reset.set_presence(lambda _i: True)
    calls: list[list[str]] = []

    def runner(ids: list[str]) -> dict[str, int]:
        calls.append(list(ids))
        return {i: 0 for i in ids}

    device_reset.set_runner(runner)
    yield fc, calls
    device_reset.set_runner(None)
    device_reset.set_enumerator(None)
    device_reset.set_presence(None)


def test_list_excludes_vjoy_and_vigem_and_groups_by_usb() -> None:
    devs = device_reset.list_devices([])
    assert [d.usb_id for d in devs] == [PEDAL_USB, STICK_USB]
    stick = devs[1]
    assert stick.hid_ids == [STICK_HID, STICK_HID + "X"]
    assert stick.vid_pid_text == "VID 231D · PID 3201"
    assert stick.plugged


def test_hidden_preselection_and_in_profile() -> None:
    devs = device_reset.list_devices(
        [STICK_HID.lower()],
        profile_device_names=["pro flight rudder"],
        gremlin_names={STICK_USB: "Right Stick"},
    )
    by = {d.usb_id: d for d in devs}
    assert by[STICK_USB].hidden and not by[PEDAL_USB].hidden
    assert by[STICK_USB].name == "Right Stick"
    assert by[PEDAL_USB].in_profile and not by[STICK_USB].in_profile
    ticked = [d.usb_id for d in devs if d.plugged and d.hidden]
    assert ticked == [STICK_USB]


def test_known_but_unplugged_rows() -> None:
    devs = device_reset.list_devices(
        [],
        known=[
            {"usb_id": "USB\\VID_1111&PID_2222\\1", "name": "Old Throttle"},
            {"usb_id": STICK_USB, "name": "dup"},
        ],
    )
    assert [d.plugged for d in devs] == [True, True, False]
    assert devs[-1].name == "Old Throttle"


@pytest.mark.parametrize(
    ("code", "outcome", "text"),
    [
        (0, "ok", "reset ✓ · back after 0.0 s"),
        (3010, "restart", "needs a Windows restart"),
        (0xE000020B, "failed", "failed: 3758096907 (0xE000020B)"),
        (5, "failed", "failed: 5 (0x00000005)"),
        (-536870389, "failed", "failed: -536870389 (0xE000020B)"),
    ],
)
def test_outcome_mapping(code: int, outcome: str, text: str) -> None:
    [res] = device_reset.reset([STICK_USB], runner=lambda ids: {ids[0]: code})
    assert (res.outcome, res.code, res.text) == (outcome, code, text)


def test_missing_result_is_failed() -> None:
    [res] = device_reset.reset([STICK_USB], runner=lambda ids: {})
    assert res.outcome == "failed" and res.text == "failed: no result"


def test_one_runner_call_for_all(fakes: tuple[FakeClock, list[list[str]]]) -> None:
    _fc, calls = fakes
    out = device_reset.reset([STICK_USB, PEDAL_USB])
    assert calls == [[STICK_USB, PEDAL_USB]]
    assert [r.outcome for r in out] == ["ok", "ok"]


def test_cancel_marks_all_declined() -> None:
    def runner(_ids: list[str]) -> dict[str, int]:
        raise device_reset.Cancelled()

    out = device_reset.reset([STICK_USB, PEDAL_USB], runner=runner)
    assert [r.text for r in out] == ["permission declined"] * 2


def test_back_after_timing_waits_for_usb_and_hid(
    fakes: tuple[FakeClock, list[list[str]]],
) -> None:
    fc, _calls = fakes
    ran: dict[str, float] = {}

    def runner(ids: list[str]) -> dict[str, int]:
        ran["at"] = fc.t
        return {i: 0 for i in ids}

    def present(i: str) -> bool:
        if "at" not in ran:
            return True
        return fc.t - ran["at"] >= (2.4 if "HID" in i else 1.0)

    dev = device_reset.list_devices([])[1]
    device_reset.set_presence(present)
    [res] = device_reset.reset([dev], runner=runner)
    assert res.back_after == pytest.approx(2.4, abs=0.11)
    assert res.text.startswith("reset ✓ · back after 2.")


def test_not_back_is_bounded(fakes: tuple[FakeClock, list[list[str]]]) -> None:
    fc, _calls = fakes
    start = fc.t
    gone = {"now": False}

    def runner(ids: list[str]) -> dict[str, int]:
        gone["now"] = True
        return {i: 0 for i in ids}

    device_reset.set_presence(lambda _i: not gone["now"])
    [res] = device_reset.reset([STICK_USB], runner=runner)
    assert res.back_after is None
    assert fc.t - start <= device_reset.BACK_TIMEOUT + 0.2
    assert res.text == "reset ✓ · not back after 10 s"


def test_batch_and_result_parsing() -> None:
    ids = [STICK_USB, "USB\\VID_1&PID_2\\50%"]
    text = device_reset._batch_text(ids, "C:\\t\\result.txt")
    assert f'pnputil /restart-device "{STICK_USB}"' in text
    assert "50%%" in text
    assert '>>"C:\\t\\result.txt" echo 1^|%errorlevel%' in text
    parsed = device_reset._parse_results("0|0\r\n1|3010\r\njunk\r\n", ids)
    assert parsed == {STICK_USB: 0, ids[1]: 3010}


def test_real_runner_is_blocked_under_tests() -> None:
    device_reset.set_runner(None)
    with pytest.raises(device_reset.RealRunnerBlocked):
        device_reset.reset([STICK_USB])


def test_running_listed_games(monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin import process_paths

    monkeypatch.setattr(
        process_paths,
        "running_programs",
        lambda names=None: [
            ("C:\\Games\\DCS\\bin\\DCS.exe", None),
            ("D:\\Other\\DCS.exe", None),
        ],
    )
    games = [{"path": "c:\\games\\dcs\\bin\\dcs.exe"}, "C:\\x\\notrunning.exe"]
    assert device_reset.running_listed_games(games) == ["DCS.exe"]
    assert device_reset.running_listed_games([]) == []


def test_absent_before_reset_is_not_found_and_not_sent(
    fakes: tuple[FakeClock, list[list[str]]],
) -> None:
    _fc, calls = fakes
    device_reset.set_presence(lambda i: i != PEDAL_USB)
    out = device_reset.reset([STICK_USB, PEDAL_USB])
    assert calls == [[STICK_USB]]
    assert [r.text for r in out] == ["reset ✓ · back after 0.0 s", "not found"]


def test_all_absent_never_calls_runner(
    fakes: tuple[FakeClock, list[list[str]]],
) -> None:
    _fc, calls = fakes
    device_reset.set_presence(lambda _i: False)
    out = device_reset.reset([STICK_USB])
    assert calls == []
    assert out[0].outcome == "not_found"
