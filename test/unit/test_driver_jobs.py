# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin.driver_jobs: install/update/remove/vJoy setup through a fake runner."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from pathlib import Path

import pytest

from gremlin import driver_jobs, drivers
from gremlin.drivers import (
    DRIVERS,
    UNINSTALL,
    DriverInfo,
    Job,
    MemoryRegistry,
    RealRunnerBlocked,
    VJoyDevice,
)


class FakeRunner:
    def __init__(
        self, answers: list | None = None, default: tuple[int, str] | None = (0, "")
    ) -> None:
        self.answers = list(answers or [])
        self.default = default
        self.calls: list[list[str]] = []

    def __call__(self, command: list[str], timeout: float) -> tuple[int, str]:
        assert timeout > 0
        self.calls.append(list(command))
        if self.answers:
            answer = self.answers.pop(0)
            return answer(command) if callable(answer) else answer
        return self.default


def _ok(path: str, info: DriverInfo) -> str:
    return ""


def _files(tmp_path: Path, *kinds: str) -> list[dict]:
    items = []
    for kind in kinds:
        path = tmp_path / f"{kind}.exe"
        path.write_bytes(kind.encode())
        items.append({"path": str(path), "kind": kind})
    return items


def test_real_runner_blocked_under_test() -> None:
    with pytest.raises(RealRunnerBlocked):
        driver_jobs.real_runner(["cmd.exe", "/c", "echo"], 1.0)
    assert driver_jobs.RealRunnerBlocked is drivers.RealRunnerBlocked


def _vigembus_reg(installed: bool = True) -> MemoryRegistry:
    if not installed:
        return MemoryRegistry()
    return MemoryRegistry(
        {
            UNINSTALL + "\\ViGEmBus": {
                "DisplayName": drivers.VIGEMBUS_DISPLAY_NAMES[0],
                "DisplayVersion": "1.22.0",
            }
        }
    )


@pytest.mark.parametrize(
    "driver, code, state, restart",
    [
        ("vjoy", 0, "done", False),
        ("vjoy", 8, "done", True),
        ("vjoy", 3010, "failed", False),
        ("vjoy", 109, "failed", False),
        ("vigembus", 0, "done", False),
        ("vigembus", 3010, "done", True),
        ("vigembus", 1641, "done", True),
        ("vigembus", 8, "failed", False),
        ("hidhide", 0, "done", False),
        ("hidhide", 3010, "done", True),
        ("hidhide", 1641, "done", True),
        ("hidhide", 1603, "failed", False),
        ("hidhide", -1, "failed", False),
    ],
)
def test_install_exit_codes(
    tmp_path: Path, driver: str, code: int, state: str, restart: bool
) -> None:
    runner = FakeRunner([(code, "installer said this")])
    job = Job("install", driver, _files(tmp_path, "bundled"))
    result = driver_jobs.run_job(
        job, runner, check_bundled=_ok, check_download=_ok, reg=_vigembus_reg()
    )
    assert (result.state, result.restart, result.used) == (state, restart, "bundled")
    assert len(runner.calls) == 1
    assert runner.calls[0][1:] == list(DRIVERS[driver].install_args)
    if state == "failed":
        assert f"exit code {code}" in result.message


def _vigembus_run(
    tmp_path: Path, answers: list, installed: bool = True, driver: str = "vigembus"
) -> tuple[driver_jobs.JobResult, FakeRunner]:
    runner = FakeRunner(answers)
    job = Job("update", driver, _files(tmp_path, "bundled"))
    result = driver_jobs.run_job(
        job,
        runner,
        check_bundled=_ok,
        check_download=_ok,
        reg=_vigembus_reg(installed),
    )
    return result, runner


def test_vigembus_update_1604_runs_the_same_file_again(tmp_path: Path) -> None:
    result, runner = _vigembus_run(tmp_path, [(1604, ""), (0, "")], installed=False)
    assert result.state == "done"
    assert len(runner.calls) == 2 and runner.calls[0] == runner.calls[1]
    assert "second run" in result.message and "Updating ViGEmBus" in result.message


def test_vigembus_other_failure_with_nothing_installed_runs_again(
    tmp_path: Path,
) -> None:
    result, runner = _vigembus_run(tmp_path, [(5, ""), (0, "")], installed=False)
    assert result.state == "done" and len(runner.calls) == 2


def test_vigembus_second_run_failing_names_both_codes(tmp_path: Path) -> None:
    result, runner = _vigembus_run(tmp_path, [(1604, ""), (1603, "")], installed=False)
    assert result.state == "failed" and len(runner.calls) == 2
    assert "1604" in result.message and "1603" in result.message


def test_vigembus_never_more_than_two_runs(tmp_path: Path) -> None:
    result, runner = _vigembus_run(
        tmp_path, [(1604, ""), (1604, ""), (0, "")], installed=False
    )
    assert result.state == "failed" and len(runner.calls) == 2


def test_vigembus_1604_runs_again_even_if_a_version_is_listed(tmp_path: Path) -> None:
    result, runner = _vigembus_run(tmp_path, [(1604, ""), (0, "")], installed=True)
    assert result.state == "done" and len(runner.calls) == 2


def test_vigembus_failure_with_driver_still_installed_is_not_repeated(
    tmp_path: Path,
) -> None:
    result, runner = _vigembus_run(tmp_path, [(5, "")], installed=True)
    assert result.state == "failed" and len(runner.calls) == 1


def test_vigembus_success_runs_once(tmp_path: Path) -> None:
    result, runner = _vigembus_run(tmp_path, [(0, "")], installed=False)
    assert result.state == "done" and len(runner.calls) == 1
    assert "second run" not in result.message


@pytest.mark.parametrize("driver", ["vjoy", "hidhide"])
def test_other_drivers_never_get_a_second_run(tmp_path: Path, driver: str) -> None:
    result, runner = _vigembus_run(tmp_path, [(1604, "")], False, driver)
    assert result.state == "failed" and len(runner.calls) == 1


def test_download_used_first_when_its_check_passes(tmp_path: Path) -> None:
    runner = FakeRunner()
    job = Job("update", "hidhide", _files(tmp_path, "download", "bundled"))
    result = driver_jobs.run_job(job, runner, check_bundled=_ok, check_download=_ok)
    assert result.used == "download"
    assert runner.calls == [[job.files[0]["path"], *DRIVERS["hidhide"].install_args]]
    assert "Updating HidHide" in result.message


def test_download_with_bad_signature_falls_back_to_bundled(tmp_path: Path) -> None:
    runner = FakeRunner()
    files = _files(tmp_path, "download", "bundled")
    info = DRIVERS["vjoy"]
    bundled = drivers.DriverInfo(
        **{**info.__dict__, "sha256": hashlib.sha256(b"bundled").hexdigest()}
    )
    real_check = drivers.check_download

    def check_download(path: str, info_: DriverInfo) -> str:
        return real_check(path, info_, signer=lambda p: (True, "CN=Mallory Ltd"))

    def check_bundled(path: str, info_: DriverInfo) -> str:
        return drivers.check_bundled(path, bundled)

    result = driver_jobs.run_job(
        Job("install", "vjoy", files),
        runner,
        check_bundled=check_bundled,
        check_download=check_download,
    )
    assert result.state == "done"
    assert result.used == "bundled"
    assert "download copy skipped" in result.message and "Mallory" in result.message
    assert [c[0] for c in runner.calls] == [files[1]["path"]]


def test_bundled_with_wrong_sha256_is_never_run(tmp_path: Path) -> None:
    runner = FakeRunner()
    files = _files(tmp_path, "bundled")  # content "bundled" never matches the pin
    result = driver_jobs.run_job(Job("install", "hidhide", files), runner)
    assert result.state == "failed"
    assert result.used == ""
    assert "does not match" in result.message
    assert runner.calls == []


def test_both_copies_fail_checks(tmp_path: Path) -> None:
    runner = FakeRunner()
    files = _files(tmp_path, "download", "bundled")
    result = driver_jobs.run_job(
        Job("install", "vjoy", files),
        runner,
        check_bundled=lambda p, i: "bad hash",
        check_download=lambda p, i: "bad sig",
    )
    assert result.state == "failed" and runner.calls == []
    assert "bad sig" in result.message and "bad hash" in result.message


def test_vjoy_log_file_added(tmp_path: Path) -> None:
    runner = FakeRunner()
    driver_jobs.run_job(
        Job("install", "vjoy", _files(tmp_path, "bundled")),
        runner,
        check_bundled=_ok,
        log_dir=str(tmp_path),
    )
    assert runner.calls[0][-1].startswith("/LOG=")


CODE = "{0E2E3D4D-1111-2222-3333-444455556666}"


def _hidhide_reg(
    uninstall_string: str = f"MsiExec.exe /X{CODE}", subkey: str = CODE
) -> MemoryRegistry:
    return MemoryRegistry(
        {
            UNINSTALL + "\\" + subkey: {
                "DisplayName": "HidHide",
                "DisplayVersion": "1.5.230",
                "UninstallString": uninstall_string,
            }
        }
    )


@pytest.mark.parametrize(
    "code, state, restart",
    [
        (0, "done", True),
        (3010, "done", True),
        (1641, "done", True),
        (1603, "failed", False),
    ],
)
def test_remove_hidhide_exit_codes(code: int, state: str, restart: bool) -> None:
    runner = FakeRunner([(code, "")])
    result = driver_jobs.run_job(
        Job("remove", "hidhide", []), runner, reg=_hidhide_reg()
    )
    assert (result.state, result.restart) == (state, restart)
    command = runner.calls[0]
    assert command[0].lower().endswith("msiexec.exe")
    assert command[1:] == ["/x", CODE, "/qn", "/norestart"]


def test_remove_uses_subkey_code_when_string_has_none() -> None:
    runner = FakeRunner()
    reg = _hidhide_reg(uninstall_string="C:\\x\\uninstall.exe")
    driver_jobs.run_job(Job("remove", "hidhide", []), runner, reg=reg)
    assert runner.calls[0][2] == CODE


def test_remove_when_not_installed() -> None:
    runner = FakeRunner()
    result = driver_jobs.run_job(
        Job("remove", "hidhide", []), runner, reg=MemoryRegistry()
    )
    assert result.state == "failed" and runner.calls == []


def _report(
    device_id: int,
    axes: str = "X Y Z Rx Ry Rz Sl0 Sl1",
    buttons: int = 128,
    cont: int = 4,
    disc: int = 0,
) -> str:
    return (
        "\n\n\n"
        + "=" * 72
        + f"\nDevice:\t\t\t{device_id}"
        + "\nState:\t\t\tFREE"
        + f"\nButtons:\t\t{buttons}"
        + f"\nDescrete POVs:\t\t{disc}"
        + f"\nContinous POVs:\t\t{cont}"
        + f"\nAxes:\t\t\t{axes} - - - - - - - - "
        + "\nFFB Effects:\t\tNone\n\n"
        + "=" * 72
        + "\n"
    )


def test_parse_report() -> None:
    [device] = driver_jobs.parse_report(
        _report(2, axes="X Y Z - - - - -", buttons=32, cont=1)
    )
    assert (device.id, device.axes, device.buttons, device.hats) == (
        2,
        ("x", "y", "z"),
        32,
        1,
    )
    [full] = driver_jobs.parse_report(_report(1))
    assert (full.axes, full.buttons, full.hats) == (drivers.VJOY_AXES, 128, 4)
    # Axes are read by position: a gap does not end the list.
    [gap] = driver_jobs.parse_report(_report(1, axes="X - Z"))
    assert gap.axes == ("x", "z")


def test_parse_report_of_the_real_mixed_line() -> None:
    text = _report(1).replace(
        "X Y Z Rx Ry Rz Sl0 Sl1 - - - - - - - - ", "X Y - - - - Sl0 - - - - - - - - - "
    )
    [device] = driver_jobs.parse_report(text)
    assert device.axes == ("x", "y", "sl0")


def test_vjoy_setup_passes_exactly_the_ticked_axes() -> None:
    device = VJoyDevice(1, ("x", "y", "sl0"), 8, 0)
    runner = _vjoy_runner(
        lambda i: _report(i, axes="X Y - - - - Sl0", buttons=8, cont=0)
    )
    ok, message, _ = driver_jobs.vjoy_setup([device], runner)
    assert ok, message
    command = runner.calls[1]
    assert command[command.index("-a") : command.index("-b")] == [
        "-a",
        "x",
        "y",
        "sl0",
    ]
    assert "3 axes (X, Y, S1), 8 buttons, 0 hats" in message


def test_vjoy_setup_reports_a_different_axis_set_on_read_back() -> None:
    runner = _vjoy_runner(lambda i: _report(i, axes="X Y Z", buttons=8, cont=0))
    ok, message, _ = driver_jobs.vjoy_setup(
        [VJoyDevice(1, ("x", "y", "sl0"), 8, 0)], runner
    )
    assert not ok
    assert "reads back as 3 axes (X, Y, Z)" in message
    assert "asked for 3 axes (X, Y, S1)" in message
    assert driver_jobs.parse_report("vJoy driver is not installed or disabled") == []
    assert [d.id for d in driver_jobs.parse_report(_report(1) + _report(3))] == [1, 3]


def test_parse_status_list() -> None:
    text = (
        "\nDevice 1:\tStatus: FREE\nDevice 2:\tStatus: OWNED"
        "\nDevice 3:\tStatus: MISSING\nDevice 4:\tStatus: UNKNOWN"
        "\nDevice 5:\tStatus: BUSY\n"
    )
    assert driver_jobs.parse_status_list(text) == [1, 2, 5]


def _vjoy_runner(read_back: Callable[[int], str], listing: str = "") -> FakeRunner:
    def answer(command: list[str]) -> tuple[int, str]:
        if command[1:] == ["-t"]:
            return 0, listing
        if command[1] == "-t":
            return 0, read_back(int(command[2]))
        return 0, ""

    return FakeRunner(default=None, answers=[answer] * 20)


def test_vjoy_setup_commands_and_read_back() -> None:
    devices = [VJoyDevice(1), VJoyDevice(2, ("x", "y", "z"), 32, 1)]
    layouts = {1: _report(1), 2: _report(2, axes="X Y Z", buttons=32, cont=1)}
    runner = _vjoy_runner(lambda i: layouts[i])
    ok, message, restart = driver_jobs.vjoy_setup(devices, runner)
    assert ok and not restart, message
    exe = driver_jobs.vjoyconfig_path()
    assert runner.calls == [
        [exe, "-t"],
        [
            exe,
            "1",
            "-f",
            "-a",
            "x",
            "y",
            "z",
            "rx",
            "ry",
            "rz",
            "sl0",
            "sl1",
            "-b",
            "128",
            "-p",
            "4",
            "-l",
        ],
        [exe, "2", "-f", "-a", "x", "y", "z", "-b", "32", "-p", "1"],
        [exe, "-t", "1"],
        [exe, "-t", "2"],
    ]


def test_vjoy_setup_exit_code_zero_is_not_trusted() -> None:
    runner = _vjoy_runner(lambda i: _report(i, buttons=64))
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok
    assert "reads back as 8 axes (X-S2), 64 buttons" in message


def test_device_text_uses_the_singular_for_one() -> None:
    describe = driver_jobs.describe_device
    assert (
        describe(VJoyDevice(4, ("x", "y", "z", "rx"), 32, 1))
        == "4 axes (X, Y, Z, Rx), 32 buttons, 1 hat"
    )
    assert describe(VJoyDevice(1, ("x",), 1, 0)) == "1 axis (X), 1 button, 0 hats"
    assert describe(VJoyDevice(1, (), 2, 1)) == "0 axes, 2 buttons, 1 hat"
    assert describe(VJoyDevice(1, buttons=2, hats=1)) == (
        "8 axes (X-S2), 2 buttons, 1 hat"
    )


def test_vjoy_setup_summary_and_read_back_use_the_singular() -> None:
    runner = _vjoy_runner(lambda i: _report(i, axes="X", buttons=1, cont=1))
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1, ("x",), 1, 1)], runner)
    assert ok and "device 1: 1 axis (X), 1 button, 1 hat" in message, message
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1, ("x", "y"), 2, 1)], runner)
    assert not ok
    assert "reads back as 1 axis (X), 1 button, 1 hat, " in message
    assert "asked for 2 axes (X, Y), 2 buttons, 1 hat" in message


def test_vjoy_setup_device_missing_after_setup() -> None:
    runner = _vjoy_runner(lambda i: "")
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok and "not found" in message


def test_vjoy_setup_nonzero_exit_fails() -> None:
    runner = FakeRunner([(0, ""), (-1, "bitness")])
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok and "exit code -1" in message
    assert len(runner.calls) == 2  # the list read, then the failed set-up


def test_vjoy_setup_deletes_devices_above_the_new_count() -> None:
    listing = "\nDevice 1:\tStatus: FREE\nDevice 2:\tStatus: FREE\n"
    gone: set[int] = set()
    exe = driver_jobs.vjoyconfig_path()

    def read_back(i: int) -> str:
        return "" if i in gone else _report(i)

    runner = _vjoy_runner(read_back, listing)
    real = runner.__call__

    def watching(command: list[str], timeout: float) -> tuple[int, str]:
        if command[1] == "-d":
            gone.update(int(i) for i in command[2:])
        return real(command, timeout)

    ok, message, restart = driver_jobs.vjoy_setup([VJoyDevice(1)], watching)
    assert ok and not restart, message
    assert "deleted device 2" in message
    # Every set-up defers; the delete (always a refresh) is the single refresh.
    assert runner.calls[1][-1] == "-l"
    assert [exe, "-d", "2"] in runner.calls
    assert runner.calls.index([exe, "-d", "2"]) > 1


def test_vjoy_setup_delete_that_leaves_the_device_listed_fails() -> None:
    listing = "\nDevice 1:\tStatus: FREE\nDevice 2:\tStatus: FREE\n"
    runner = _vjoy_runner(lambda i: _report(i), listing)
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok and "device 2" in message and "still listed" in message


def test_vjoy_setup_defers_all_but_the_last_device() -> None:
    runner = _vjoy_runner(lambda i: _report(i))
    driver_jobs.vjoy_setup([VJoyDevice(1), VJoyDevice(2), VJoyDevice(3)], runner)
    sets = [c for c in runner.calls if c[1] not in ("-t", "-d")]
    assert [c[-1] == "-l" for c in sets] == [True, True, False]


def test_vjoy_setup_rejects_bad_layout() -> None:
    runner = FakeRunner()
    ok, _, _ = driver_jobs.vjoy_setup([VJoyDevice(1, buttons=200)], runner)
    assert not ok and runner.calls == []


def test_vjoy_setup_job() -> None:
    runner = _vjoy_runner(lambda i: _report(i))
    result = driver_jobs.run_job(Job("vjoy_setup", "vjoy", [], [VJoyDevice(1)]), runner)
    assert result.state == "done"


def test_current_vjoy_devices() -> None:
    def answer(command: list[str]) -> tuple[int, str]:
        if command[1:] == ["-t"]:
            return 0, "\nDevice 1:\tStatus: FREE\nDevice 2:\tStatus: MISSING\n"
        return 0, _report(int(command[2]), buttons=16)

    runner = FakeRunner(answers=[answer] * 5)
    [device] = driver_jobs.current_vjoy_devices(runner)
    assert (device.id, device.buttons) == (1, 16)

    def broken(command: list[str], timeout: float) -> tuple[int, str]:
        raise OSError("no vJoyConfig")

    assert driver_jobs.current_vjoy_devices(broken) == []


def test_run_job_never_raises_on_runner_error(tmp_path: Path) -> None:
    def broken(command: list[str], timeout: float) -> tuple[int, str]:
        raise OSError("gone")

    result = driver_jobs.run_job(
        Job("install", "vjoy", _files(tmp_path, "bundled")), broken, check_bundled=_ok
    )
    assert result.state == "failed" and "gone" in result.message


_STATUS_TEXT = (
    "\nDevice 1:\tStatus: FREE\nDevice 2:\tStatus: OWNED"
    "\nDevice 3:\tStatus: MISSING\nDevice 4:\tStatus: busy\n"
)


def test_parse_status_all_devices_upper_case() -> None:
    assert driver_jobs.parse_status(_STATUS_TEXT) == {
        1: "FREE",
        2: "OWNED",
        3: "MISSING",
        4: "BUSY",
    }
    assert driver_jobs.parse_status("") == {}
    assert driver_jobs.parse_status_list(_STATUS_TEXT) == [1, 2, 4]


def test_busy_vjoy_devices() -> None:
    runner = FakeRunner([(0, _STATUS_TEXT)])
    assert driver_jobs.busy_vjoy_devices(runner) == [2, 4]
    assert runner.calls[0][1:] == ["-t"]
    assert (
        driver_jobs.busy_vjoy_devices(FakeRunner([(0, "Device 1:\tStatus: FREE")]))
        == []
    )

    def boom(command: list[str], timeout: float) -> tuple[int, str]:
        raise OSError("no vJoyConfig")

    assert driver_jobs.busy_vjoy_devices(boom) == []
    blocked = FakeRunner([lambda c: (_ for _ in ()).throw(RealRunnerBlocked("x"))])
    with pytest.raises(RealRunnerBlocked):
        driver_jobs.busy_vjoy_devices(blocked)
