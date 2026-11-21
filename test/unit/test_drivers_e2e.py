# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Driver setup, end to end on the real path (06 S185-S188, 12 S25/S25a/S25b).

DriversModel -> job file -> Gremlin Device Helper's main(--jobs/--results)
-> driver_jobs.run_job -> results file -> the model's poll. Only the edges
are fake: the registry (a drivers.MemoryRegistry the fake installers change),
the command runner (no installer, msiexec or vJoyConfig ever runs) and the
launcher (runs the helper's main() on a thread instead of ShellExecute). The
job, results and pending files, the SHA-256 check and the HidHide two-half
update are the real code.
"""

from __future__ import annotations

import dataclasses
import hashlib
import logging
import threading
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

import gremlin_device_helper
from gremlin import clock, driver_jobs, drivers
from gremlin.ui.drivers_model import DriversModel

HIDHIDE_CODE = "{11111111-2222-3333-4444-555555555555}"
HIDHIDE_ENTRY = drivers.UNINSTALL + "\\" + HIDHIDE_CODE


class World:
    """A fake Windows: a registry the fake installers edit, vJoy devices, and
    the commands that were run."""

    def __init__(self) -> None:
        self.reg = drivers.MemoryRegistry()
        self.calls: list[list[str]] = []
        self.exit_codes: dict[str, int] = {}  # driver key -> installer exit code
        self.devices: dict[int, drivers.VJoyDevice] = {}
        self.vjoy_lies = False  # -t reports one axis fewer than was set

    # -- the registry --------------------------------------------------------

    def _set(self, path: str, name: str, value: str) -> None:
        if path.lower() not in self.reg.values:
            self.reg.paths.append(path)
        self.reg.values.setdefault(path.lower(), {})[name] = value

    def install_vjoy(self, version: str) -> None:
        self._set(drivers.VJOY_UNINSTALL, "DisplayVersion", version)

    def install_vigembus(self, version: str) -> None:
        self.reg.files[drivers.vigembus_sys_path().lower()] = version

    def install_hidhide(self, version: str) -> None:
        self._set(drivers.HIDHIDE_KEY, "Version", version)
        self._set(HIDHIDE_ENTRY, "DisplayName", "HidHide")
        self._set(HIDHIDE_ENTRY, "DisplayVersion", version)
        self._set(HIDHIDE_ENTRY, "UninstallString", f"MsiExec.exe /X{HIDHIDE_CODE}")

    def remove_hidhide(self) -> None:
        for path in (drivers.HIDHIDE_KEY, HIDHIDE_ENTRY):
            self.reg.values.pop(path.lower(), None)
            if path in self.reg.paths:
                self.reg.paths.remove(path)

    def statuses(self) -> list[drivers.DriverStatus]:
        return drivers.all_status(self.reg)

    # -- the fake commands -----------------------------------------------------

    def run(self, command: list[str], timeout: float) -> tuple[int, str]:
        """The command runner the helper's jobs use."""
        self.calls.append(list(command))
        exe = Path(command[0]).name.lower()
        if exe == drivers.DRIVERS["vjoy"].bundled_file.lower():
            code = self.exit_codes.get("vjoy", 0)
            if code in (0, 8):
                self.install_vjoy("2.2.2.0")
            return code, ""
        if exe == drivers.DRIVERS["vigembus"].bundled_file.lower():
            code = self.exit_codes.get("vigembus", 0)
            if code in (0, 3010, 1641):
                self.install_vigembus("1.22.0")
            return code, ""
        if exe == drivers.DRIVERS["hidhide"].bundled_file.lower():
            code = self.exit_codes.get("hidhide", 0)
            if code in (0, 3010, 1641):
                self.install_hidhide("1.5.230")
            return code, ""
        if exe == "msiexec.exe":
            assert command[1:] == ["/x", HIDHIDE_CODE, "/qn", "/norestart"]
            self.remove_hidhide()
            return 0, ""
        if exe == "vjoyconfig.exe":
            return self._vjoyconfig(command[1:])
        raise AssertionError(f"unexpected command {command}")

    def _vjoyconfig(self, args: list[str]) -> tuple[int, str]:
        if args[0] == "-d":
            for device_id in args[1:]:
                self.devices.pop(int(device_id), None)
            return 0, ""
        if args[0] == "-t" and len(args) == 1:
            return 0, "".join(
                f"Device {i}:\tStatus: {'FREE' if i in self.devices else 'MISSING'}\n"
                for i in range(1, 17)
            )
        if args[0] == "-t":
            device = self.devices.get(int(args[1]))
            if device is None:
                return 0, ""
            axes = device.axes - (1 if self.vjoy_lies and device.axes else 0)
            names = " ".join(drivers.VJOY_AXES[:axes])
            return 0, (
                f"Device:\t\t\t{device.id}\nState:\t\t\tFREE\n"
                f"Buttons:\t\t{device.buttons}\n"
                f"Descrete POVs:\t\t0\nContinous POVs:\t\t{device.hats}\n"
                f"Axes:\t\t\t{names} \n"
            )
        device_id = int(args[0])
        assert args[1] == "-f"
        axes = 0
        if "-a" in args:
            start = args.index("-a") + 1
            while start + axes < len(args) and not args[start + axes].startswith("-"):
                axes += 1
        buttons = int(args[args.index("-b") + 1])
        hats = int(args[args.index("-p") + 1])
        self.devices[device_id] = drivers.VJoyDevice(device_id, axes, buttons, hats)
        return 0, ""

    def vjoy_devices(self) -> list[drivers.VJoyDevice]:
        return [dataclasses.replace(d) for d in self.devices.values()]

    def ran_installer(self, key: str) -> bool:
        wanted = drivers.DRIVERS[key].bundled_file.lower()
        return any(Path(c[0]).name.lower() == wanted for c in self.calls)


class HelperLauncher:
    """Stands in for ShellExecute "runas": runs the real helper main() in
    jobs mode on a thread, with the world's fake runner."""

    def __init__(self, world: World) -> None:
        self.world = world
        self.params: list[str] = []
        self.thread: threading.Thread | None = None
        self.exit_code: int | None = None

    def __call__(self, file: str, parameters: str) -> HelperLauncher:
        assert file.endswith("Gremlin Device Helper.exe")
        parts = parameters.split('"')
        argv = ["--jobs", parts[1], "--results", parts[3]]
        self.params.append(parameters)

        def run_job(job: drivers.Job, runner: Callable) -> drivers.JobResult:
            return driver_jobs.run_job(job, runner, reg=self.world.reg)

        def work() -> None:
            self.exit_code = gremlin_device_helper.main(
                argv, run_job=run_job, job_runner=self.world.run
            )

        self.thread = threading.Thread(target=work, name="e2e-helper")
        self.thread.start()
        return self

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def close(self) -> None:
        if self.thread is not None:
            self.thread.join(5)


def _sync(
    name: str, work: Callable[[], object], done: Callable[[object], None]
) -> None:
    done(work())


class Restarter:
    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1


@pytest.fixture
def helper_log(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """The helper's log goes to tmp_path, and is let go afterwards."""
    monkeypatch.setattr(
        gremlin_device_helper, "jobs_log_path", lambda: tmp_path / "device_helper.log"
    )
    yield
    for handler in list(gremlin_device_helper.log.handlers):
        gremlin_device_helper.log.removeHandler(handler)
        handler.close()
    logging.getLogger("gremlin.device_helper").handlers.clear()


@pytest.fixture
def world() -> World:
    return World()


@pytest.fixture
def app(tmp_path: Path) -> Path:
    folder = tmp_path / "app"
    (folder / "drivers").mkdir(parents=True)
    return folder


def _bundle(
    app: Path, monkeypatch: pytest.MonkeyPatch, key: str, content: bytes | None
) -> Path:
    """Writes the bundled file; with content, its real SHA-256 is patched into
    DRIVERS for the test (None: junk that does not match the real hash)."""
    info = drivers.DRIVERS[key]
    path = app / "drivers" / info.bundled_file
    if content is None:
        path.write_bytes(b"not the real installer")
        return path
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    monkeypatch.setitem(drivers.DRIVERS, key, dataclasses.replace(info, sha256=digest))
    return path


def _model(
    app: Path, tmp_path: Path, world: World, launcher: HelperLauncher, **kw: object
) -> DriversModel:
    return DriversModel(
        status_source=world.statuses,
        app=lambda: app,
        launcher=launcher,
        vjoy_reader=world.vjoy_devices,
        background=_sync,
        restarter=Restarter(),
        temp_dir=tmp_path,
        poll_ms=5,
        **kw,
    )


def _pump(until: Callable[[], bool], limit: float = 10.0) -> None:
    end = clock.monotonic() + limit
    while not until() and clock.monotonic() < end:
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 20)
    assert until(), "condition not reached in time"


def _run(model: DriversModel) -> None:
    assert model.apply()
    assert model.busy
    _pump(lambda: not model.busy)


def _results(model: DriversModel) -> dict[str, dict]:
    return {r["driver"]: r for r in model.results}


def test_missing_vjoy_and_vigembus_install_from_bundled_files(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
) -> None:
    vjoy_file = _bundle(app, monkeypatch, "vjoy", b"vjoy installer bytes")
    vigem_file = _bundle(app, monkeypatch, "vigembus", b"vigembus installer bytes")
    world.install_hidhide("1.5.230")
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher)

    rows = {r["key"]: r for r in model.rows}
    assert rows["vjoy"]["ticked"] and rows["vigembus"]["ticked"]
    text = model.describe()
    assert "Install vJoy" in text and "Install ViGEmBus" in text
    assert "Set up 1 vJoy device" in text

    finished: list[bool] = []
    model.finished.connect(lambda: finished.append(True))
    _run(model)

    assert finished == [True] and launcher.exit_code == 0
    # The real SHA-256 check let both through, and they were run with their args.
    assert [str(vjoy_file), "/VERYSILENT"] == world.calls[0][:2]
    assert world.ran_installer("vigembus")
    assert [c[0] for c in world.calls if c[0] == str(vigem_file)] == [str(vigem_file)]
    results = _results(model)
    assert results["vJoy"]["state"] == "done"
    assert results["ViGEmBus"]["state"] == "done"
    assert results["vJoy devices"]["state"] == "done"
    assert not model.restartNeeded
    # The model reloaded from the (fake) registry: nothing is left to install.
    assert {r["key"]: r["state"] for r in model.rows} == {
        "vjoy": "same",
        "vigembus": "same",
        "hidhide": "same",
    }
    assert [d["axes"] for d in model.vjoyCurrent] == [8]


def test_bundled_file_with_a_wrong_hash_is_never_run(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
) -> None:
    world.install_vjoy("2.2.2.0")
    world.devices[1] = drivers.VJoyDevice(1)
    world.install_hidhide("1.5.230")
    _bundle(app, monkeypatch, "vigembus", None)  # real hash does not match the file
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher)

    _run(model)

    assert not world.ran_installer("vigembus")
    assert world.calls == []
    row = _results(model)["ViGEmBus"]
    assert row["state"] == "failed"
    assert "fingerprint (SHA-256) does not match" in row["message"]
    assert not model.restartNeeded
    assert {r["key"]: r["state"] for r in model.rows}["vigembus"] == "missing"


def test_vjoy_installer_exit_8_needs_a_restart(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
) -> None:
    _bundle(app, monkeypatch, "vjoy", b"vjoy installer bytes")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.exit_codes["vjoy"] = 8
    model = _model(app, tmp_path, world, HelperLauncher(world))

    _run(model)

    results = _results(model)
    assert results["vJoy"]["state"] == "done"
    assert "restart needed" in results["vJoy"]["message"]
    assert model.restartNeeded
    model.restartNow()
    assert model._restarter.count == 1  # type: ignore[attr-defined]


def test_hidhide_update_in_two_halves(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
) -> None:
    hidhide_file = _bundle(app, monkeypatch, "hidhide", b"hidhide installer bytes")
    world.install_vjoy("2.2.2.0")
    world.devices[1] = drivers.VJoyDevice(1)
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.2.122.0")
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher)

    row = {r["key"]: r for r in model.rows}["hidhide"]
    assert row["state"] == "older" and not row["ticked"]
    model.setTicked("hidhide", True)
    assert "step 1 of 2" in model.describe()
    assert not model.pendingHidHide

    # Step 1: the old HidHide is removed, pending.json is left, restart needed.
    _run(model)
    assert world.calls == [
        [
            str(
                Path(drivers.os.environ.get("SystemRoot", r"C:\Windows"))
                / "System32"
                / "msiexec.exe"
            ),
            "/x",
            HIDHIDE_CODE,
            "/qn",
            "/norestart",
        ]
    ]
    assert _results(model)["HidHide"]["state"] == "done"
    assert model.restartNeeded
    pending = drivers.read_pending(app)
    assert pending is not None
    assert pending["hidhide"]["version"] == "1.5.230"
    assert pending["hidhide"]["file"] == str(hidhide_file)
    assert drivers.pending_path(app).is_file()

    # After the restart a new model sees the unfinished update.
    fresh = _model(app, tmp_path, world, launcher)
    assert fresh.pendingHidHide and fresh.pendingVersion == "1.5.230"
    assert {r["key"]: r["state"] for r in fresh.rows}["hidhide"] == "missing"

    # Step 2: install the new one, clear pending.json, restart needed.
    assert fresh.finishHidHide()
    assert fresh.busy
    _pump(lambda: not fresh.busy)
    assert world.ran_installer("hidhide")
    assert _results(fresh)["HidHide"]["state"] == "done"
    assert fresh.restartNeeded
    assert not drivers.pending_path(app).exists()
    assert not fresh.pendingHidHide
    assert {r["key"]: r["state"] for r in fresh.rows}["hidhide"] == "same"
    assert launcher.exit_code == 0


def test_vjoy_custom_layout_that_reads_back_wrong_fails_with_a_message(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    world.install_vjoy("2.2.2.0")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[1] = drivers.VJoyDevice(1)
    world.vjoy_lies = True
    model = _model(app, tmp_path, world, HelperLauncher(world))
    assert [d["axes"] for d in model.vjoyCurrent] == [8]

    model.setPreset("Custom")
    model.setDeviceCount(2)
    model.setDevice(0, 6, 32, 1)
    assert model.vjoyEdited and model.vjoyWarning
    assert "Set up 2 vJoy devices" in model.describe()

    _run(model)

    row = _results(model)["vJoy devices"]
    assert row["state"] == "failed"
    assert "reads back as 5 axes" in row["message"]
    assert "asked for 6 axes" in row["message"]
    # vJoyConfig was asked for the layout, then read back.
    sets = [c for c in world.calls if "-b" in c]
    first = sets[0]
    assert ["-b", "32", "-p", "1"] == first[first.index("-b") : first.index("-b") + 4]
    # Nothing is deleted: -l on every device but the last (12 S25b).
    assert [c[-1] == "-l" for c in sets] == [True, False]
    assert any(c[1] == "-t" for c in world.calls)
    assert not model.restartNeeded


def test_vjoy_custom_layout_that_reads_back_right_is_done(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    world.install_vjoy("2.2.2.0")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[1] = drivers.VJoyDevice(1)
    model = _model(app, tmp_path, world, HelperLauncher(world))

    model.setPreset("Custom")
    model.setDeviceCount(2)
    model.setDevice(0, 6, 32, 1)
    _run(model)

    assert _results(model)["vJoy devices"]["state"] == "done"
    assert [
        (d["id"], d["axes"], d["buttons"], d["hats"]) for d in model.vjoyCurrent
    ] == [
        (1, 6, 32, 1),
        (2, 8, 128, 4),
    ]


def test_vjoy_two_devices_down_to_one_deletes_device_2(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    world.install_vjoy("2.2.2.0")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[1] = drivers.VJoyDevice(1)
    world.devices[2] = drivers.VJoyDevice(2)
    model = _model(app, tmp_path, world, HelperLauncher(world))
    assert [d["id"] for d in model.vjoyCurrent] == [1, 2]

    model.setDeviceCount(1)
    assert model.vjoyEdited and model.vjoyWarning
    text = model.describe()
    assert "vJoy device 2 will be deleted." in text
    assert "vJoy device 1 will be deleted." not in text

    _run(model)

    assert _results(model)["vJoy devices"]["state"] == "done"
    assert any(c[1:3] == ["-d", "2"] for c in world.calls)
    assert [d["id"] for d in model.vjoyCurrent] == [1]
    listing = driver_jobs.current_vjoy_devices(world.run)
    assert [d.id for d in listing] == [1]
