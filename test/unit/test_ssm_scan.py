# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Screen Saver Mode checks: Refresh Devices (S12) and Refresh Programs /
Ignore this program (S13, S14). Windows is faked: nothing here opens a
device, elevates or runs powercfg."""

from __future__ import annotations

import pytest

from gremlin import clock, hid_report_scan, power_requests
from gremlin.hid_report_scan import DONE, ERROR, PENDING
from gremlin.power_requests import ProgramRequest

REQUESTS_SAMPLE = """\
DISPLAY:
[PROCESS] \\Device\\HarddiskVolume3\\Program Files\\RustDesk\\RustDesk.exe
Video Wake Lock

SYSTEM:
[DRIVER] Realtek High Definition Audio(SST) (HDAUDIO\\FUNC_01&VEN_10EC\\5&2f2&0)
An audio stream is currently in use.
[PROCESS] \\Device\\HarddiskVolume3\\Program Files\\RustDesk\\RustDesk.exe
Video Wake Lock

AWAYMODE:
None.

EXECUTION:
[PROCESS] \\Device\\HarddiskVolume5\\Games\\Steam\\steam.exe
Steam is downloading

PERFBOOST:
[PROCESS] \\Device\\HarddiskVolume3\\Windows\\perfonly.exe
Boost

ACTIVELOCKSCREEN:
None.
"""

NONE_SAMPLE = """\
DISPLAY:
None.

SYSTEM:
None.

AWAYMODE:
None.

EXECUTION:
None.

PERFBOOST:
None.

ACTIVELOCKSCREEN:
None.
"""

OVERRIDES_SAMPLE = """\
[SERVICE]

[PROCESS]
RustDesk.exe DISPLAY SYSTEM AWAYMODE
My Player.exe DISPLAY

[DRIVER]
Realtek High Definition Audio(SST) SYSTEM
"""


# Parsing ------------------------------------------------------------------


def test_parse_requests_lists_programs_with_kinds() -> None:
    programs = {p.name: p for p in power_requests.parse_requests(REQUESTS_SAMPLE)}
    rust = programs["RustDesk.exe"]
    assert (
        rust.path == "\\Device\\HarddiskVolume3\\Program Files\\RustDesk\\RustDesk.exe"
    )
    assert rust.kinds == ["Display", "System"]
    assert programs["steam.exe"].kinds == ["Execution"]
    driver = [p for p in programs.values() if p.name.startswith("Realtek")]
    assert len(driver) == 1 and driver[0].path == "" and driver[0].kinds == ["System"]
    # PERFBOOST doesn't keep the display or PC awake; reason lines are no entries.
    assert "perfonly.exe" not in programs
    assert not any("Wake Lock" in name for name in programs)
    assert len(programs) == 3


def test_parse_requests_none_is_empty() -> None:
    assert power_requests.parse_requests(NONE_SAMPLE) == []
    assert power_requests.parse_requests("") == []


def test_parse_overrides_reads_process_section_only() -> None:
    assert power_requests.parse_overrides(OVERRIDES_SAMPLE) == [
        "RustDesk.exe",
        "My Player.exe",
    ]
    assert power_requests.parse_overrides("[SERVICE]\n\n[PROCESS]\n\n[DRIVER]\n") == []


def test_merge_marks_ignored_and_adds_ignored_not_asking() -> None:
    merged = power_requests.merge(
        power_requests.parse_requests(REQUESTS_SAMPLE),
        power_requests.parse_overrides(OVERRIDES_SAMPLE),
    )
    by_name = {p.name: p for p in merged}
    assert by_name["RustDesk.exe"].ignored is True
    assert by_name["steam.exe"].ignored is False
    assert by_name["My Player.exe"] == ProgramRequest("My Player.exe", "", [], True)


# list_requests / set_ignored with a fake runner -----------------------------


class FakeRunner:
    def __init__(
        self, outputs: list[str] | None = None, error: Exception | None = None
    ) -> None:
        self.outputs = outputs
        self.error = error
        self.calls: list[list[str]] = []

    def __call__(self, commands: list[str]) -> list[str]:
        self.calls.append(list(commands))
        if self.error is not None:
            raise self.error
        return list(self.outputs or [])


def test_list_requests_ok_one_run_with_both_commands() -> None:
    runner = FakeRunner([REQUESTS_SAMPLE, OVERRIDES_SAMPLE])
    result = power_requests.list_requests(runner)
    assert result.ok and result.error == ""
    assert runner.calls == [["powercfg /requests", "powercfg /requestsoverride"]]
    names = [p.name for p in result.programs]
    assert "RustDesk.exe" in names and "My Player.exe" in names


def test_list_requests_refused() -> None:
    result = power_requests.list_requests(FakeRunner(error=power_requests.Refused()))
    assert result.ok is False
    assert result.error == "Administrator rights were refused."
    assert result.programs == []


def test_list_requests_timeout() -> None:
    result = power_requests.list_requests(FakeRunner(error=TimeoutError()))
    assert result.ok is False and result.error == power_requests.TIMEOUT_TEXT


def test_set_ignored_on_builds_override_with_types() -> None:
    runner = FakeRunner(["", OVERRIDES_SAMPLE])
    assert power_requests.set_ignored("RustDesk.exe", True, runner) == (True, "")
    assert runner.calls == [
        [
            'powercfg /requestsoverride PROCESS "RustDesk.exe" DISPLAY SYSTEM AWAYMODE',
            "powercfg /requestsoverride",
        ]
    ]


def test_set_ignored_off_removes_and_checks_windows() -> None:
    runner = FakeRunner(["", "[SERVICE]\n\n[PROCESS]\n\n[DRIVER]\n"])
    assert power_requests.set_ignored("RustDesk.exe", False, runner) == (True, "")
    assert runner.calls[0][0] == 'powercfg /requestsoverride PROCESS "RustDesk.exe"'


def test_set_ignored_reports_when_windows_did_not_change() -> None:
    # Asked to ignore, but Windows' list doesn't have it afterwards.
    runner = FakeRunner(["error text", "[PROCESS]\n"])
    ok, error = power_requests.set_ignored("Other.exe", True, runner)
    assert ok is False and error == power_requests.NOT_CHANGED_TEXT


def test_set_ignored_refused_and_timeout() -> None:
    assert power_requests.set_ignored(
        "RustDesk.exe", True, FakeRunner(error=power_requests.Refused())
    ) == (False, "Administrator rights were refused.")
    assert power_requests.set_ignored(
        "RustDesk.exe", True, FakeRunner(error=TimeoutError())
    ) == (False, power_requests.TIMEOUT_TEXT)


@pytest.mark.parametrize(
    "name",
    [
        "",
        "RustDesk",
        'Rust"Desk.exe',
        "C:\\Tools\\RustDesk.exe",
        "dir/RustDesk.exe",
        "a.exe & del x.exe",
        "%TEMP%.exe",
        " RustDesk.exe",
        "Realtek High Definition Audio(SST)",
        "x" * 300 + ".exe",
    ],
)
def test_bad_names_never_reach_the_runner(name: str) -> None:
    runner = FakeRunner(["", ""])
    ok, error = power_requests.set_ignored(name, True, runner)
    assert ok is False and error
    assert runner.calls == []


@pytest.mark.parametrize(
    "name", ["RustDesk.exe", "My Player.exe", "steam.EXE", "app-2_x.exe"]
)
def test_good_names_are_valid(name: str) -> None:
    assert power_requests.valid_name(name)


def test_command_line_appends_each_output() -> None:
    line = power_requests.command_line(
        ["powercfg /requests", "powercfg /requestsoverride"],
        ["C:\\t\\a.txt", "C:\\t\\b.txt"],
    )
    assert line == (
        '/d /c "powercfg /requests >> "C:\\t\\a.txt" 2>&1 & '
        'powercfg /requestsoverride >> "C:\\t\\b.txt" 2>&1"'
    )


def test_real_runner_refuses_under_test() -> None:
    with pytest.raises(power_requests.RealRunnerBlocked):
        power_requests._real_runner(["powercfg /requests"])


# scan() with Windows faked --------------------------------------------------


class FakeTime:
    def __init__(self) -> None:
        self.t = 100.0

    def monotonic(self) -> float:
        return self.t


class FakeDev:
    def __init__(
        self,
        path: str,
        rate: float,
        info: tuple[int, int, int] | None = (0x01, 0x04, 9),
        product: str = "",
        openable: bool = True,
        fail_after: int | None = None,
    ) -> None:
        self.path = path
        self.rate = rate  # reports per second
        self.info = info
        self.product = product
        self.openable = openable
        self.fail_after = fail_after
        self.delivered = 0


class FakeOp:
    def __init__(self, dev: FakeDev) -> None:
        self.dev = dev


class FakeHid:
    """Each device has rate * elapsed reports ready; a read finishes at once
    while reports are waiting. wait() moves the fake clock on."""

    def __init__(
        self, devices: list[FakeDev], time_: FakeTime, raise_in: str | None = None
    ) -> None:
        self.devices = {d.path: d for d in devices}
        self.time = time_
        self.start = time_.t
        self.raise_in = raise_in
        self.opened: list[str] = []
        self.closed: list[str] = []
        self.cancelled: list[str] = []
        self.freed: list[str] = []

    def interfaces(self) -> list[tuple[str, str, str]]:
        return [(p, f"HID\\{p}", f"desc {p}") for p in self.devices]

    def open(self, path: str) -> str | None:
        if not self.devices[path].openable:
            return None
        self.opened.append(path)
        return path

    def info(self, handle: str) -> tuple[int, int, int] | None:
        return self.devices[handle].info

    def product(self, handle: str) -> str:
        return self.devices[handle].product

    def new_read(self, handle: str, length: int) -> FakeOp:
        return FakeOp(self.devices[handle])

    def _state(self, op: FakeOp) -> str:
        dev = op.dev
        if self.raise_in == "read":
            raise OSError("boom")
        if dev.fail_after is not None and dev.delivered >= dev.fail_after:
            return ERROR
        ready = int(dev.rate * (self.time.t - self.start))
        if dev.delivered < ready:
            dev.delivered += 1
            return DONE
        return PENDING

    def submit(self, op: FakeOp) -> str:
        return self._state(op)

    def check(self, op: FakeOp) -> str:
        return self._state(op)

    def wait(self, ops: list[FakeOp], timeout_ms: int) -> None:
        assert 0 < timeout_ms <= 50  # bounded
        self.time.t += timeout_ms / 1000.0

    def cancel(self, op: FakeOp) -> None:
        self.cancelled.append(op.dev.path)

    def free(self, op: FakeOp) -> None:
        self.freed.append(op.dev.path)

    def close(self, handle: str) -> None:
        self.closed.append(handle)


@pytest.fixture
def fake_time(monkeypatch: pytest.MonkeyPatch) -> FakeTime:
    time_ = FakeTime()
    monkeypatch.setattr(clock, "monotonic", time_.monotonic)

    def sleep(s: float) -> None:
        time_.t += s

    monkeypatch.setattr(clock, "sleep", sleep)
    return time_


def test_scan_rates_threshold_and_order(fake_time: FakeTime) -> None:
    api = FakeHid(
        [
            FakeDev("mic", 18, info=(0x0C, 0x01, 4), product="Maono PD200X"),
            FakeDev("quiet", 0),
            FakeDev("slow", 1),
            FakeDev("throttle", 12.5, product="VKBsim NXT"),
            FakeDev("nameless", 5, product=""),
        ],
        fake_time,
    )
    rates = hid_report_scan.scan(4.0, api=api)
    assert [r.name for r in rates] == ["Maono PD200X", "VKBsim NXT", "desc nameless"]
    mic, throttle, nameless = rates
    assert mic.reports_per_s == pytest.approx(18, abs=0.6)
    assert throttle.reports_per_s == pytest.approx(12.5, abs=0.6)
    assert nameless.reports_per_s == pytest.approx(5, abs=0.6)
    assert (mic.usage_page, mic.usage, mic.instance_id) == (0x0C, 0x01, "HID\\mic")
    # Ran for the asked time, not longer.
    assert fake_time.t - 100.0 == pytest.approx(4.0, abs=0.06)
    assert sorted(api.closed) == sorted(api.opened)


def test_scan_skips_devices_that_cannot_be_opened_or_read(fake_time: FakeTime) -> None:
    api = FakeHid(
        [
            FakeDev("keyboard", 50, openable=False),
            FakeDev("nocaps", 50, info=None),
            FakeDev("noinput", 50, info=(0x01, 0x02, 0)),
            FakeDev("pad", 10),
        ],
        fake_time,
    )
    rates = hid_report_scan.scan(2.0, api=api)
    assert [r.instance_id for r in rates] == ["HID\\pad"]
    assert "keyboard" not in api.opened
    assert sorted(api.closed) == ["nocaps", "noinput", "pad"]


def test_scan_device_unplugged_mid_scan_keeps_others(fake_time: FakeTime) -> None:
    api = FakeHid([FakeDev("gone", 30, fail_after=3), FakeDev("pad", 10)], fake_time)
    rates = hid_report_scan.scan(4.0, api=api)
    assert [r.instance_id for r in rates] == ["HID\\pad"]
    assert sorted(api.closed) == ["gone", "pad"]


def test_scan_closes_every_handle_on_error(fake_time: FakeTime) -> None:
    api = FakeHid([FakeDev("a", 10), FakeDev("b", 10)], fake_time, raise_in="read")
    with pytest.raises(OSError):
        hid_report_scan.scan(4.0, api=api)
    assert sorted(api.closed) == ["a", "b"]
    assert sorted(api.freed) == ["a", "b"]


def test_scan_cancels_pending_reads_before_freeing(fake_time: FakeTime) -> None:
    api = FakeHid([FakeDev("pad", 10)], fake_time)
    hid_report_scan.scan(1.0, api=api)
    assert api.cancelled == ["pad"] and api.freed == ["pad"] and api.closed == ["pad"]


def test_scan_stops_when_asked(fake_time: FakeTime) -> None:
    api = FakeHid([FakeDev("pad", 10)], fake_time)
    rates = hid_report_scan.scan(4.0, should_stop=lambda: fake_time.t >= 101.0, api=api)
    assert rates == []
    assert fake_time.t < 101.2
    assert api.closed == ["pad"]
