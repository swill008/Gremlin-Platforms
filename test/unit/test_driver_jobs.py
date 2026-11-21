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
    result = driver_jobs.run_job(job, runner, check_bundled=_ok, check_download=_ok)
    assert (result.state, result.restart, result.used) == (state, restart, "bundled")
    assert runner.calls[0][1:] == list(DRIVERS[driver].install_args)
    if state == "failed":
        assert f"exit code {code}" in result.message


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
        (0, "done", False),
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
    assert (device.id, device.axes, device.buttons, device.hats) == (2, 3, 32, 1)
    [full] = driver_jobs.parse_report(_report(1))
    assert (full.axes, full.buttons, full.hats) == (8, 128, 4)
    # A gap ends the "first N axes" count.
    [gap] = driver_jobs.parse_report(_report(1, axes="X - Z"))
    assert gap.axes == 1
    assert driver_jobs.parse_report("vJoy driver is not installed or disabled") == []
    assert [d.id for d in driver_jobs.parse_report(_report(1) + _report(3))] == [1, 3]


def test_parse_status_list() -> None:
    text = (
        "\nDevice 1:\tStatus: FREE\nDevice 2:\tStatus: OWNED"
        "\nDevice 3:\tStatus: MISSING\nDevice 4:\tStatus: UNKNOWN"
        "\nDevice 5:\tStatus: BUSY\n"
    )
    assert driver_jobs.parse_status_list(text) == [1, 2, 5]


def _vjoy_runner(read_back: Callable[[int], str]) -> FakeRunner:
    def answer(command: list[str]) -> tuple[int, str]:
        if command[1] == "-t":
            return 0, read_back(int(command[2]))
        return 0, ""

    return FakeRunner(default=None, answers=[answer] * 20)


def test_vjoy_setup_commands_and_read_back() -> None:
    devices = [VJoyDevice(1), VJoyDevice(2, 3, 32, 1)]
    layouts = {1: _report(1), 2: _report(2, axes="X Y Z", buttons=32, cont=1)}
    runner = _vjoy_runner(lambda i: layouts[i])
    ok, message, restart = driver_jobs.vjoy_setup(devices, runner)
    assert ok and not restart, message
    exe = driver_jobs.vjoyconfig_path()
    assert runner.calls == [
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
        ],
        [exe, "2", "-f", "-a", "x", "y", "z", "-b", "32", "-p", "1"],
        [exe, "-t", "1"],
        [exe, "-t", "2"],
    ]


def test_vjoy_setup_exit_code_zero_is_not_trusted() -> None:
    runner = _vjoy_runner(lambda i: _report(i, buttons=64))
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok
    assert "reads back as 8 axes, 64 buttons" in message


def test_vjoy_setup_device_missing_after_setup() -> None:
    runner = _vjoy_runner(lambda i: "")
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok and "not found" in message


def test_vjoy_setup_nonzero_exit_fails() -> None:
    runner = FakeRunner([(-1, "bitness")])
    ok, message, _ = driver_jobs.vjoy_setup([VJoyDevice(1)], runner)
    assert not ok and "exit code -1" in message
    assert len(runner.calls) == 1


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
