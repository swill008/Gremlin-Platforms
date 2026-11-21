# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Driver setup work: install, update, remove HidHide, set up vJoy devices.

Spec: 12 S25 (changed), S25a, S25b. Used only by Gremlin Device Helper (the
only part of Gremlin with administrator rights). No Qt and no imports from
the rest of the program except gremlin.drivers.

Every command goes through a `runner(command, timeout) -> (exit code,
output)`; the real one is blocked under pytest.
"""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Callable, Iterable

from gremlin import drivers
from gremlin.drivers import (
    DRIVERS,
    VJOY_AXES,
    DriverInfo,
    Job,
    JobResult,
    RealRunnerBlocked,
    Registry,
    VJoyDevice,
)

__all__ = [
    "RealRunnerBlocked",
    "Runner",
    "current_vjoy_devices",
    "parse_report",
    "parse_status_list",
    "real_runner",
    "run_job",
    "vjoy_setup",
    "vjoyconfig_path",
]

Runner = Callable[[list[str], float], tuple[int, str]]

INSTALL_TIMEOUT_S = 600.0
UNINSTALL_TIMEOUT_S = 300.0
VJOYCONFIG_TIMEOUT_S = 60.0


def real_runner(command: list[str], timeout: float) -> tuple[int, str]:
    """Runs one command, bounded; (-1, why) when it could not run."""
    if drivers._under_test():
        raise RealRunnerBlocked("driver_jobs.real_runner called from a test")
    if os.name != "nt":
        return -1, "needs Windows"
    try:
        done = subprocess.run(
            command,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
            check=False,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired:
        return -1, f"no answer after {timeout:.0f} s"
    except OSError as error:
        return -1, str(error)
    return done.returncode, (done.stdout or "") + (done.stderr or "")


# -- install / update / remove ------------------------------------------------


def _from_exit_code(
    info: DriverInfo, code: int, output: str, what: str
) -> tuple[str, str, bool]:
    """(state, message, restart) for an installer's exit code."""
    if code == 0:
        return "done", f"{what}: done", False
    if code in info.restart_codes:
        return "done", f"{what}: done, restart needed", True
    tail = output.strip().splitlines()[-1] if output.strip() else ""
    detail = f" ({tail})" if tail else ""
    return "failed", f"{what}: failed, exit code {code}{detail}", False


def _install(
    job: Job,
    runner: Runner,
    check_bundled: Callable,
    check_download: Callable,
    log_dir: str | None,
    reg: Registry | None = None,
) -> JobResult:
    info = DRIVERS[job.driver]
    notes: list[str] = []
    for item in job.files:
        path, kind = item["path"], item["kind"]
        if kind == "download":
            why = check_download(path, info)
        else:
            why = check_bundled(path, info)
        if why:
            notes.append(f"{kind} copy skipped: {why}")
            continue
        command = [path, *info.install_args]
        if job.driver == "vjoy" and log_dir:
            command.append(f"/LOG={os.path.join(log_dir, 'vjoy_install.log')}")
        verb = "Updating" if job.op == "update" else "Installing"
        what = f"{verb} {info.name} ({kind} copy)"
        code, output = runner(command, INSTALL_TIMEOUT_S)
        state, message, restart = _from_exit_code(info, code, output, what)
        if (
            job.driver == "vigembus"
            and state == "failed"
            and (code == 1604 or not drivers.installed_version(job.driver, reg))
        ):
            # ViGEmBus's own release notes: updating needs the setup run twice.
            # The first run can remove the old driver and stop (1604); the same
            # (already checked) file is run once more, never a third time.
            code2, output2 = runner(command, INSTALL_TIMEOUT_S)
            state, message, restart = _from_exit_code(info, code2, output2, what)
            if state == "done":
                message += " (second run, as ViGEmBus needs when updating)"
            else:
                message += (
                    f" (first run exit code {code}, second run exit code {code2})"
                )
        return JobResult(state, "; ".join([*notes, message]), restart, kind)
    notes.append(f"{info.name} not installed: no copy passed its check")
    return JobResult("failed", "; ".join(notes), False, "")


_GUID = re.compile(r"\{[0-9A-Fa-f]{8}-(?:[0-9A-Fa-f]{4}-){3}[0-9A-Fa-f]{12}\}")


def hidhide_product_code(reg: Registry | None = None) -> str:
    """The MSI product code of the installed HidHide, "" when none."""
    entry = drivers.uninstall_entry("HidHide", reg)
    if entry is None:
        return ""
    subkey, fields = entry
    match = _GUID.search(fields.get("UninstallString", "")) or _GUID.fullmatch(subkey)
    return match.group(0) if match else ""


def _remove(job: Job, runner: Runner, reg: Registry | None) -> JobResult:
    info = DRIVERS[job.driver]
    code = hidhide_product_code(reg)
    if not code:
        return JobResult("failed", f"Removing {info.name}: not found in Windows' list")
    windir = os.environ.get("SystemRoot", r"C:\Windows")
    msiexec = os.path.join(windir, "System32", "msiexec.exe")
    exit_code, output = runner(
        [msiexec, "/x", code, "/qn", "/norestart"], UNINSTALL_TIMEOUT_S
    )
    state, message, restart = _from_exit_code(
        info, exit_code, output, f"Removing {info.name}"
    )
    if state == "done":  # spec 12 S25b: a removed HidHide always needs a restart
        message, restart = f"Removing {info.name}: done, restart needed", True
    return JobResult(state, message, restart, "")


def run_job(
    job: Job,
    runner: Runner,
    *,
    check_bundled: Callable = drivers.check_bundled,
    check_download: Callable = drivers.check_download,
    reg: Registry | None = None,
    log_dir: str | None = None,
) -> JobResult:
    """Runs one job; never raises except RealRunnerBlocked."""
    try:
        if job.op in ("install", "update"):
            return _install(job, runner, check_bundled, check_download, log_dir, reg)
        if job.op == "remove":
            return _remove(job, runner, reg)
        if job.op == "vjoy_setup":
            ok, message, restart = vjoy_setup(job.devices, runner)
            return JobResult("done" if ok else "failed", message, restart, "")
        return JobResult("failed", f"unknown job {job.op!r}")
    except RealRunnerBlocked:
        raise
    except Exception as error:  # noqa: BLE001 - reported, never a crash
        return JobResult("failed", f"{job.op} {job.driver}: {error}")


# -- vJoy devices -------------------------------------------------------------


def vjoyconfig_path() -> str:
    root = os.environ.get("ProgramFiles", r"C:\Program Files")
    return os.path.join(root, "vJoy", "x64", "vJoyConfig.exe")


def _count(n: int, singular: str, plural: str) -> str:
    return f"{n} {singular if n == 1 else plural}"


def describe_device(device: VJoyDevice) -> str:
    """"4 axes, 32 buttons, 1 hat": singular only for exactly one."""
    return ", ".join(
        (
            _count(device.axes, "axis", "axes"),
            _count(device.buttons, "button", "buttons"),
            _count(device.hats, "hat", "hats"),
        )
    )


def vjoy_setup(devices: Iterable[VJoyDevice], runner: Runner) -> tuple[bool, str, bool]:
    """Sets the devices up, deletes the others, reads back; (ok, message, restart).

    vJoyConfig's exit code is 0 even on bad arguments, so only the read-back
    (`vJoyConfig -t <id>`) decides. The driver refreshes once: every set-up
    passes `-l` (defer the refresh) and the deletion, which always refreshes
    (`-d` ignores `-l`), runs last; with nothing to delete the last set-up
    omits `-l` and carries the refresh.
    """
    exe = vjoyconfig_path()
    devices = list(devices)
    if not devices:
        return False, "vJoy: no devices to set up", False
    for device in devices:
        problem = device.problem()
        if problem:
            return False, f"vJoy: {problem}", False
    wanted = {d.id for d in devices}
    _, listing = runner([exe, "-t"], VJOYCONFIG_TIMEOUT_S)
    stale = sorted(i for i in parse_status_list(listing) if i not in wanted)
    last = len(devices) - 1
    for index, device in enumerate(devices):
        command = [exe, str(device.id), "-f"]
        if device.axes:  # UNVERIFIED: how vJoyConfig takes zero axes
            command += ["-a", *VJOY_AXES[: device.axes]]
        command += ["-b", str(device.buttons), "-p", str(device.hats)]
        if stale or index != last:
            command.append("-l")
        code, output = runner(command, VJOYCONFIG_TIMEOUT_S)
        if code != 0:
            return (
                False,
                f"vJoy device {device.id}: vJoyConfig failed, exit code {code}"
                + (f" ({output.strip()})" if output.strip() else ""),
                False,
            )
    if stale:
        code, output = runner(
            [exe, "-d", *(str(i) for i in stale)], VJOYCONFIG_TIMEOUT_S
        )
        if code != 0:
            return (
                False,
                f"vJoy: deleting {_ids(stale)}: vJoyConfig failed, exit code {code}"
                + (f" ({output.strip()})" if output.strip() else ""),
                False,
            )
    for device in devices:
        code, output = runner([exe, "-t", str(device.id)], VJOYCONFIG_TIMEOUT_S)
        found = {d.id: d for d in parse_report(output)}.get(device.id)
        if found is None:
            return False, f"vJoy device {device.id}: not found after setup", False
        if (found.axes, found.buttons, found.hats) != (
            device.axes,
            device.buttons,
            device.hats,
        ):
            return (
                False,
                f"vJoy device {device.id}: reads back as {describe_device(found)}, "
                f"asked for {describe_device(device)}",
                False,
            )
    for device_id in stale:
        _, output = runner([exe, "-t", str(device_id)], VJOYCONFIG_TIMEOUT_S)
        if any(d.id == device_id for d in parse_report(output)):
            return False, f"vJoy device {device_id}: still listed after delete", False
    count = len(devices)
    summary = "; ".join(f"device {d.id}: {describe_device(d)}" for d in devices)
    noun = "device" if count == 1 else "devices"
    message = f"vJoy set up, {count} {noun} ({summary})"
    if stale:
        message += f"; deleted {_ids(stale)}"
    return True, message, False


def _ids(ids: list[int]) -> str:
    return ("device " if len(ids) == 1 else "devices ") + ", ".join(map(str, ids))


# vJoyConfig -t report format, from BrunnerInnovation/vJoy
# apps/vJoyConf/vJoyConfig/vJoyConfig.cpp (read 2026-11-21, not yet run on
# 2.2.2.0): `-t N` prints one block per existing device,
#   "Device:\t\t\t%d", "State:\t\t\t%s", "Buttons:\t\t%d",
#   "Descrete POVs:\t\t%d", "Continous POVs:\t\t%d",
#   "Axes:\t\t\t" then "%s " per axis (X Y Z Rx Ry Rz Sl0 Sl1 Wheel ...;
#   a missing axis prints "-"), "FFB Effects: ...".
# Nothing is printed for a MISSING/UNKNOWN device. `-t` with no id prints
# "Device %d:\tStatus: %s" for 1-16 (OWNED, FREE, BUSY, MISSING, UNKNOWN).
_FIELD = re.compile(r"^\s*([A-Za-z ]+?)\s*:\s*(.*?)\s*$")


def parse_report(text: str) -> list[VJoyDevice]:
    """The devices in `vJoyConfig -t <id>` output."""
    found: list[VJoyDevice] = []
    current: VJoyDevice | None = None
    for line in (text or "").splitlines():
        match = _FIELD.match(line)
        if not match:
            continue
        name, value = match.group(1).lower(), match.group(2)
        if name == "device":
            if not value.isdigit():
                current = None
                continue
            current = VJoyDevice(int(value), axes=0, buttons=0, hats=0)
            found.append(current)
        elif current is None:
            continue
        elif name == "buttons" and value.isdigit():
            current.buttons = int(value)
        elif name in ("continous povs", "continuous povs") and value.isdigit():
            current.hats = int(value)
        elif name == "axes":
            names = [token.lower() for token in value.split()]
            count = 0
            for axis, token in zip(VJOY_AXES, names):
                if axis != token:
                    break
                count += 1
            current.axes = count
    return found


_STATUS = re.compile(r"^\s*Device\s+(\d+)\s*:\s*Status\s*:\s*(\w+)", re.IGNORECASE)


def parse_status_list(text: str) -> list[int]:
    """Device numbers `vJoyConfig -t` lists as existing (not MISSING/UNKNOWN)."""
    ids: list[int] = []
    for line in (text or "").splitlines():
        match = _STATUS.match(line)
        if match and match.group(2).upper() not in ("MISSING", "UNKNOWN"):
            ids.append(int(match.group(1)))
    return ids


def current_vjoy_devices(runner: Runner) -> list[VJoyDevice]:
    """What vJoy has now (read-only); [] when vJoy or vJoyConfig is missing."""
    exe = vjoyconfig_path()
    try:
        code, output = runner([exe, "-t"], VJOYCONFIG_TIMEOUT_S)
    except RealRunnerBlocked:
        raise
    except Exception:  # noqa: BLE001 - unknown is shown as empty
        return []
    devices: list[VJoyDevice] = []
    for device_id in parse_status_list(output):
        try:
            _, report = runner([exe, "-t", str(device_id)], VJOYCONFIG_TIMEOUT_S)
        except RealRunnerBlocked:
            raise
        except Exception:  # noqa: BLE001
            continue
        devices += [d for d in parse_report(report) if d.id == device_id]
    return devices
