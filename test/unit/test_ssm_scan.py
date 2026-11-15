# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Screen Saver Mode checks: Refresh Devices (S12) and Refresh Programs /
Ignore this program (S13, S14). Windows is faked: nothing here opens a
device, elevates or runs powercfg."""

from __future__ import annotations

import logging

import pytest

from gremlin import clock, hid_report_scan, power_requests, trace
from gremlin.hid_report_scan import DONE, ERROR, PENDING
from gremlin.power_requests import ProgramRequest

# The real formats, from the user's PC (contract-2, 2026-11-15).
USB_AUDIO = r"USB Audio 2.0 (USB\VID_0DB0&PID_CD0E&MI_00\9&9c4d365&0&0000)"

# Raw: the backslashes are Windows' own.
REQUESTS_SAMPLE = r"""
DISPLAY:
[PROCESS] \Device\HarddiskVolume3\Program Files\RustDesk\RustDesk.exe
Video Wake Lock

SYSTEM:
[DRIVER] USB Audio 2.0 (USB\VID_0DB0&PID_CD0E&MI_00\9&9c4d365&0&0000)
An audio stream is currently in use.
[PROCESS] \Device\HarddiskVolume3\Program Files\RustDesk\RustDesk.exe
Video Wake Lock

AWAYMODE:
None.

EXECUTION:
[PROCESS] \Device\HarddiskVolume3\Users\me\AppData\Local\AnthropicClaude\claude.exe
Electron

PERFBOOST:
[PROCESS] \Device\HarddiskVolume3\Windows\perfonly.exe
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

[DRIVER]
FxSound Audio Enhancer SYSTEM

"""

EMPTY_OVERRIDES = "[SERVICE]\n\n[PROCESS]\n\n[DRIVER]\n"


# Parsing ------------------------------------------------------------------


def test_parse_requests_real_format_kinds_and_details() -> None:
    rows = power_requests.parse_requests(REQUESTS_SAMPLE)
    by_name = {p.name: p for p in rows}
    rust = by_name["RustDesk.exe"]
    assert rust.kind == "PROCESS"
    assert rust.path == r"\Device\HarddiskVolume3\Program Files\RustDesk\RustDesk.exe"
    assert rust.kinds == ["Display", "System"]
    assert rust.detail == "Video Wake Lock"
    usb = by_name[USB_AUDIO]
    assert usb.kind == "DRIVER" and usb.path == "" and usb.kinds == ["System"]
    assert usb.detail == "An audio stream is currently in use."
    claude = by_name["claude.exe"]
    assert claude.kind == "PROCESS" and claude.kinds == ["Execution"]
    assert claude.detail == "Electron"
    # PERFBOOST doesn't keep the display or PC awake; detail lines are no entries.
    assert "perfonly.exe" not in by_name
    assert len(rows) == 3


def test_parse_requests_none_is_empty() -> None:
    assert power_requests.parse_requests(NONE_SAMPLE) == []
    assert power_requests.parse_requests("") == []


def test_parse_overrides_reads_every_kind() -> None:
    assert power_requests.parse_overrides(OVERRIDES_SAMPLE) == [
        ("PROCESS", "RustDesk.exe"),
        ("DRIVER", "FxSound Audio Enhancer"),
    ]
    assert power_requests.parse_overrides(EMPTY_OVERRIDES) == []
    # A driver name with spaces, brackets, backslashes and &.
    text = f"[DRIVER]\n{USB_AUDIO} SYSTEM\n\n[SERVICE]\nSome Service DISPLAY SYSTEM\n"
    assert power_requests.parse_overrides(text) == [
        ("DRIVER", USB_AUDIO),
        ("SERVICE", "Some Service"),
    ]


def test_merge_matches_by_kind_and_name() -> None:
    merged = power_requests.merge(
        power_requests.parse_requests(REQUESTS_SAMPLE),
        power_requests.parse_overrides(OVERRIDES_SAMPLE),
    )
    by_name = {p.name: p for p in merged}
    assert by_name["RustDesk.exe"].ignored is True
    assert by_name["claude.exe"].ignored is False
    assert by_name[USB_AUDIO].ignored is False
    assert by_name["FxSound Audio Enhancer"] == ProgramRequest(
        "FxSound Audio Enhancer", "", [], True, "DRIVER"
    )
    # Same name, other kind: not the same caller.
    other = power_requests.merge(
        [ProgramRequest("x.exe", "", ["Display"])], [("DRIVER", "x.exe")]
    )
    assert [(p.kind, p.ignored) for p in other] == [
        ("PROCESS", False),
        ("DRIVER", True),
    ]


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
    assert "RustDesk.exe" in names and "FxSound Audio Enhancer" in names


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
    assert power_requests.set_ignored("RustDesk.exe", True, runner=runner) == (
        True,
        "",
    )
    assert runner.calls == [
        [
            'powercfg /requestsoverride PROCESS "RustDesk.exe" DISPLAY SYSTEM AWAYMODE',
            "powercfg /requestsoverride",
        ]
    ]


def test_set_ignored_off_removes_and_checks_windows() -> None:
    runner = FakeRunner(["", EMPTY_OVERRIDES])
    assert power_requests.set_ignored("RustDesk.exe", False, runner=runner) == (
        True,
        "",
    )
    assert runner.calls[0][0] == 'powercfg /requestsoverride PROCESS "RustDesk.exe"'


def test_set_ignored_reports_when_windows_did_not_change() -> None:
    # Asked to ignore, but Windows' list doesn't have it afterwards.
    runner = FakeRunner(["error text", "[PROCESS]\n"])
    ok, error = power_requests.set_ignored("Other.exe", True, runner=runner)
    assert ok is False and error == power_requests.NOT_CHANGED_TEXT


def test_set_ignored_refused_and_timeout() -> None:
    assert power_requests.set_ignored(
        "RustDesk.exe", True, runner=FakeRunner(error=power_requests.Refused())
    ) == (False, "Administrator rights were refused.")
    assert power_requests.set_ignored(
        "RustDesk.exe", True, runner=FakeRunner(error=TimeoutError())
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
    ok, error = power_requests.set_ignored(name, True, runner=runner)
    assert ok is False and error
    assert runner.calls == []


def test_set_ignored_driver_quotes_the_full_name() -> None:
    runner = FakeRunner(["", f"[PROCESS]\n\n[DRIVER]\n{USB_AUDIO} SYSTEM\n"])
    assert power_requests.set_ignored(USB_AUDIO, True, "DRIVER", runner) == (True, "")
    assert runner.calls == [
        [
            f'powercfg /requestsoverride DRIVER "{USB_AUDIO}" DISPLAY SYSTEM AWAYMODE',
            "powercfg /requestsoverride",
        ]
    ]
    assert runner.calls[0][0] == (
        "powercfg /requestsoverride DRIVER "
        '"USB Audio 2.0 (USB\\VID_0DB0&PID_CD0E&MI_00\\9&9c4d365&0&0000)"'
        " DISPLAY SYSTEM AWAYMODE"
    )


def test_set_ignored_driver_off_removes_with_no_types() -> None:
    runner = FakeRunner(["", OVERRIDES_SAMPLE])  # FxSound still listed
    ok, error = power_requests.set_ignored(
        "FxSound Audio Enhancer", False, "DRIVER", runner
    )
    assert (ok, error) == (False, power_requests.NOT_CHANGED_TEXT)
    assert runner.calls[0][0] == (
        'powercfg /requestsoverride DRIVER "FxSound Audio Enhancer"'
    )
    runner = FakeRunner(["", EMPTY_OVERRIDES])
    assert power_requests.set_ignored(
        "FxSound Audio Enhancer", False, "DRIVER", runner
    ) == (True, "")


def test_set_ignored_check_compares_kind_and_name() -> None:
    # Windows lists the name under [PROCESS], not [DRIVER]: not ignored.
    runner = FakeRunner(["", "[PROCESS]\nFxSound Audio Enhancer SYSTEM\n"])
    ok, _error = power_requests.set_ignored(
        "FxSound Audio Enhancer", True, "DRIVER", runner
    )
    assert ok is False


def test_set_ignored_service_form() -> None:
    # Not verified on a real PC (no service request there); built like DRIVER.
    runner = FakeRunner(["", "[SERVICE]\nMy Service SYSTEM DISPLAY AWAYMODE\n"])
    assert power_requests.set_ignored("My Service", True, "SERVICE", runner) == (
        True,
        "",
    )
    assert runner.calls[0][0] == (
        'powercfg /requestsoverride SERVICE "My Service" DISPLAY SYSTEM AWAYMODE'
    )


@pytest.mark.parametrize(
    "name",
    ["", 'USB "Audio"', "Line\nbreak", "Tab\there", "x" * 261, " lead", "50%PATH%"],
)
def test_bad_driver_names_never_reach_the_runner(name: str) -> None:
    runner = FakeRunner(["", ""])
    ok, error = power_requests.set_ignored(name, True, "DRIVER", runner)
    assert ok is False and error
    assert runner.calls == []


def test_good_driver_names_are_valid() -> None:
    assert power_requests.valid_caller_name(USB_AUDIO)
    assert power_requests.valid_caller_name("FxSound Audio Enhancer")
    assert power_requests.valid_caller_name("x" * 260)


def test_set_ignored_unknown_kind_refused() -> None:
    runner = FakeRunner(["", ""])
    ok, _error = power_requests.set_ignored("x.exe", True, "USER", runner)
    assert ok is False and runner.calls == []


# Tracing and the normal log ----------------------------------------------------


@pytest.fixture
def traced(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    lines: list[str] = []
    monkeypatch.setattr(trace, "screen_saver", lines.append, raising=False)
    return lines


def test_list_requests_traces_command_exit_code_output_and_rows(
    traced: list[str],
) -> None:
    def runner(commands: list[str]) -> list[str]:
        return power_requests.Outputs(
            [REQUESTS_SAMPLE, OVERRIDES_SAMPLE], '/d /c "..."', 0
        )

    assert power_requests.list_requests(runner).ok
    text = "\n".join(traced)
    assert "command: powercfg /requests" in text
    assert "command: powercfg /requestsoverride" in text
    assert "exit code 0" in text
    assert "An audio stream is currently in use." in text  # raw output
    assert "FxSound Audio Enhancer SYSTEM" in text
    assert f"[DRIVER] {USB_AUDIO}: System" in text  # parsed row
    assert "[DRIVER] FxSound Audio Enhancer: not asking, ignored" in text
    assert "Refresh Programs: 4 rows" in text


def test_trace_trims_raw_output(traced: list[str]) -> None:
    big = "x" * 10000
    power_requests.list_requests(FakeRunner([big, ""]))
    out = [line for line in traced if "output of powercfg /requests:" in line]
    assert len(out) == 1
    assert len(out[0]) < power_requests.TRACE_OUTPUT_LIMIT + 200
    assert "5904 more characters" in out[0]


def test_set_ignored_traces_command_and_check(traced: list[str]) -> None:
    runner = FakeRunner(["", f"[DRIVER]\n{USB_AUDIO} SYSTEM\n"])
    power_requests.set_ignored(USB_AUDIO, True, "DRIVER", runner)
    text = "\n".join(traced)
    assert f'command: powercfg /requestsoverride DRIVER "{USB_AUDIO}"' in text
    assert "exit code unknown" in text
    assert "check ok" in text


def test_errors_go_to_the_normal_log(
    traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="system")
    power_requests.list_requests(FakeRunner(error=power_requests.Refused()))
    power_requests.set_ignored("x.exe", True, runner=FakeRunner(error=TimeoutError()))
    power_requests.set_ignored("Other.exe", True, runner=FakeRunner(["", ""]))
    power_requests.set_ignored('bad"name', True, "DRIVER", FakeRunner(["", ""]))
    messages = [r.getMessage() for r in caplog.records if r.name == "system"]
    assert any(power_requests.REFUSED_TEXT in m for m in messages)
    assert any(power_requests.TIMEOUT_TEXT in m for m in messages)
    assert any(power_requests.NOT_CHANGED_TEXT in m for m in messages)
    assert any("is not a name Windows can ignore" in m for m in messages)
    assert any("refused" in line for line in traced)
    assert any("timeout" in line for line in traced)
    assert any("check failed" in line for line in traced)


def test_errors_logged_with_tracing_off(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(trace, "screen_saver", lambda text: None, raising=False)
    caplog.set_level(logging.WARNING, logger="system")
    power_requests.list_requests(FakeRunner(error=OSError("nope")))
    assert any("nope" in r.getMessage() for r in caplog.records)


def test_nonzero_exit_code_logged(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.WARNING, logger="system")
    power_requests.list_requests(
        lambda commands: power_requests.Outputs(["", ""], "", 1)
    )
    assert any("exit code 1" in r.getMessage() for r in caplog.records)


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


def test_scan_traces_interfaces_rates_and_unopened(
    fake_time: FakeTime, traced: list[str]
) -> None:
    api = FakeHid(
        [
            FakeDev("keyboard", 50, openable=False),
            FakeDev("mouse", 50, openable=False),
            FakeDev("quiet", 0, product="Quiet Pad"),
            FakeDev("throttle", 12.5, product="VKBsim NXT"),
        ],
        fake_time,
    )
    hid_report_scan.scan(4.0, api=api)
    text = "\n".join(traced)
    assert "4 HID interfaces" in text
    assert "2 could not be opened" in text
    assert r"VKBsim NXT (HID\throttle" in text and "listed" in text
    assert r"Quiet Pad (HID\quiet" in text and "0.0 reports/s, quiet" in text
    assert "1 devices never go quiet" in text
    # The names of devices that couldn't be opened are not traced.
    assert "keyboard" not in text


def test_scan_error_traced_and_logged(
    fake_time: FakeTime, traced: list[str], caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.WARNING, logger="system")
    api = FakeHid([FakeDev("a", 10)], fake_time, raise_in="read")
    with pytest.raises(OSError):
        hid_report_scan.scan(4.0, api=api)
    assert any("Refresh Devices: failed" in line for line in traced)
    assert any("Refresh Devices failed" in r.getMessage() for r in caplog.records)
