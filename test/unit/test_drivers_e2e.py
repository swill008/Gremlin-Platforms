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
import json
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


def report_axes(axes: tuple[str, ...]) -> str:
    """vJoyConfig -t's Axes line: 16 tokens, "-" where an axis is missing."""
    tokens = [a.title() if a in axes else "-" for a in drivers.VJOY_AXES]
    return " ".join(tokens + ["-"] * 8)


class World:
    """A fake Windows: a registry the fake installers edit, vJoy devices, and
    the commands that were run."""

    def __init__(self) -> None:
        self.reg = drivers.MemoryRegistry()
        self.calls: list[list[str]] = []
        self.exit_codes: dict[str, int] = {}  # driver key -> installer exit code
        self.devices: dict[int, drivers.VJoyDevice] = {}
        self.vjoy_lies = False  # -t reports one axis fewer than was set
        self.axis_args: list[list[str]] = []  # the names after -a, per set call
        self.report_override: str | None = None  # verbatim "Axes:" line of -t
        self.busy: set[int] = set()  # devices another program holds (-t: BUSY)
        # What installing vJoy 2.2.2.0 does to the devices (a real update
        # loses devices set up by old vJoy tools and adds a default vJoy 1).
        self.after_vjoy_install: Callable[[], None] | None = None
        self.drop_set_devices: set[int] = set()  # -f for these ids never sticks

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
                if self.after_vjoy_install is not None:
                    self.after_vjoy_install()
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

    def _status(self, device_id: int) -> str:
        if device_id not in self.devices:
            return "MISSING"
        return "BUSY" if device_id in self.busy else "FREE"

    def _vjoyconfig(self, args: list[str]) -> tuple[int, str]:
        if args[0] == "-d":
            for device_id in args[1:]:
                self.devices.pop(int(device_id), None)
            return 0, ""
        if args[0] == "-t" and len(args) == 1:
            return 0, "".join(
                f"Device {i}:\tStatus: {self._status(i)}\n" for i in range(1, 17)
            )
        if args[0] == "-t":
            device = self.devices.get(int(args[1]))
            if device is None:
                return 0, ""
            axes = device.axes[:-1] if self.vjoy_lies else device.axes
            names = self.report_override or report_axes(axes)
            return 0, (
                f"Device:\t\t\t{device.id}\nState:\t\t\tFREE\n"
                f"Buttons:\t\t{device.buttons}\n"
                f"Descrete POVs:\t\t0\nContinous POVs:\t\t{device.hats}\n"
                f"Axes:\t\t\t{names} \n"
            )
        device_id = int(args[0])
        assert args[1] == "-f"
        axes: list[str] = []
        if "-a" in args:
            for token in args[args.index("-a") + 1 :]:
                if token.startswith("-"):
                    break
                axes.append(token)
        self.axis_args.append(list(axes))
        if device_id in self.drop_set_devices:
            return 0, ""
        buttons = int(args[args.index("-b") + 1])
        hats = int(args[args.index("-p") + 1])
        self.devices[device_id] = drivers.VJoyDevice(
            device_id, tuple(axes), buttons, hats
        )
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
        self.jobs_seen: list[drivers.Job] = []
        self.results_seen: list[list[drivers.JobResult]] = []

    def __call__(self, file: str, parameters: str) -> HelperLauncher:
        assert file.endswith("Gremlin Device Helper.exe")
        parts = parameters.split('"')
        argv = ["--jobs", parts[1], "--results", parts[3]]
        self.params.append(parameters)
        self.jobs_seen.extend(drivers.read_jobs(parts[1]))

        def run_job(
            job: drivers.Job, runner: Callable, **kw: object
        ) -> drivers.JobResult:
            return driver_jobs.run_job(job, runner, reg=self.world.reg, **kw)  # pyright: ignore[reportArgumentType]

        def work() -> None:
            self.exit_code = gremlin_device_helper.main(
                argv, run_job=run_job, job_runner=self.world.run
            )
            self.results_seen.append(drivers.read_results(parts[3])[0])

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
    assert {
        r["key"]: r["state"] for r in model.rows if r["key"] in drivers.DRIVERS
    } == {
        "vjoy": "same",
        "vigembus": "same",
        "hidhide": "same",
    }
    assert [d["axes"] for d in model.vjoyCurrent] == [list(drivers.VJOY_AXES)]


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
    assert [d["axes"] for d in model.vjoyCurrent] == [list(drivers.VJOY_AXES)]

    model.setPreset("Custom")
    model.setDeviceCount(2)
    model.setDevice(0, ["x", "y", "z", "rx", "ry", "rz"], 32, 1)
    assert model.vjoyEdited and model.vjoyWarning
    assert "Set up 2 vJoy devices" in model.describe()

    _run(model)

    row = _results(model)["vJoy devices"]
    assert row["state"] == "failed"
    assert "reads back as 5 axes (X, Y, Z, Rx, Ry)" in row["message"]
    assert "asked for 6 axes (X, Y, Z, Rx, Ry, Rz)" in row["message"]
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
    model.setDevice(0, ["x", "y", "z", "rx", "ry", "rz"], 32, 1)
    _run(model)

    assert _results(model)["vJoy devices"]["state"] == "done"
    assert [
        (d["id"], d["axes"], d["buttons"], d["hats"]) for d in model.vjoyCurrent
    ] == [
        (1, ["x", "y", "z", "rx", "ry", "rz"], 32, 1),
        (2, list(drivers.VJOY_AXES), 127, 4),
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


def _vjoy_ready(world: World) -> None:
    world.install_vjoy("2.2.2.0")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[1] = drivers.VJoyDevice(1)


def _pick_x_y_sl0(model: DriversModel) -> None:
    model.setPreset("Custom")
    model.setDeviceCount(1)
    model.setDevice(0, ["x", "y"], 8, 0)
    model.setAxis(0, "sl0", True)
    assert model.vjoyCurrent  # the live layout is untouched until Apply


def test_vjoy_axes_picked_by_name_reach_vjoyconfig_and_read_back_done(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    _vjoy_ready(world)
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher)
    _pick_x_y_sl0(model)

    _run(model)

    # The job file carried the names; vJoyConfig got exactly "-a x y sl0".
    sets = [c for c in world.calls if len(c) > 2 and c[2] == "-f"]
    assert len(sets) == 1
    command = sets[0]
    start = command.index("-a")
    assert command[start : start + 4] == ["-a", "x", "y", "sl0"]
    assert command[start + 4] == "-b"
    assert world.axis_args == [["x", "y", "sl0"]]
    # The report reads "Axes: X Y - - - - Sl0 - ..." and matches.
    assert report_axes(("x", "y", "sl0")).startswith("X Y - - - - Sl0 - ")
    assert _results(model)["vJoy devices"]["state"] == "done"
    assert [d["axes"] for d in model.vjoyCurrent] == [["x", "y", "sl0"]]
    assert launcher.exit_code == 0


def test_vjoy_axes_that_read_back_as_a_different_set_fail_naming_both(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    _vjoy_ready(world)
    world.report_override = "X Y Z - - - - - - - - - - - - -"
    model = _model(app, tmp_path, world, HelperLauncher(world))
    _pick_x_y_sl0(model)

    _run(model)

    row = _results(model)["vJoy devices"]
    assert row["state"] == "failed"
    assert "reads back as 3 axes (X, Y, Z)" in row["message"]
    assert "asked for 3 axes (X, Y, S1)" in row["message"]
    assert world.axis_args == [["x", "y", "sl0"]]


# --- the button countdown: the preset and the program's own sameness rule ---


def test_two_devices_full_preset_reaches_vjoyconfig_as_128_and_127(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    world.install_vjoy("2.2.2.0")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[1] = drivers.VJoyDevice(1, ("x", "y"), 8, 0)
    model = _model(app, tmp_path, world, HelperLauncher(world))

    model.setPreset("2 devices, full")
    # The job file carries the preset's own numbers (write_jobs / read_jobs).
    path = tmp_path / "jobs.json"
    jobs = [drivers.Job("vjoy_setup", "vjoy", [], drivers.PRESETS["2 devices, full"])]
    drivers.write_jobs(path, jobs)
    [back] = drivers.read_jobs(path)
    assert [(d.id, d.buttons) for d in back.devices] == [(1, 128), (2, 127)]

    _run(model)

    assert _results(model)["vJoy devices"]["state"] == "done"
    sets = [c for c in world.calls if "-b" in c]
    assert [(c[1], c[c.index("-b") + 1]) for c in sets] == [("1", "128"), ("2", "127")]
    # Read back from vJoyConfig: two different layouts, so not alike.
    assert [(d.id, d.buttons) for d in world.vjoy_devices()] == [(1, 128), (2, 127)]
    assert drivers.alike_devices(world.vjoy_devices()) == []


def _fake_vjoy_raw(index: int, layout: tuple[int, int, int]) -> object:
    import dill

    raw = dill._DeviceSummary()
    raw.device_guid = dill._GUID(
        Data1=700000 + index, Data2=1, Data3=2, Data4=(1, 2, 3, 4, 5, 6, 7, index)
    )
    raw.vendor_id = 0x1234
    raw.product_id = 0xBEAD
    raw.joystick_id = index
    raw.name = b"vJoy Device"
    raw.axis_count, raw.button_count, raw.hat_count = layout
    return raw


def _start_up_matching(
    monkeypatch: pytest.MonkeyPatch, devices: list[drivers.VJoyDevice]
) -> tuple[list[int], list[str]]:
    """Runs the program's real vJoy matching on fake vJoy devices; returns the
    ids it linked and the "can't be told apart" problems it reported."""
    import dill
    from gremlin import device_initialization as di
    from gremlin.modules import output
    from test import fake_hardware

    layouts = {d.id: (len(d.axes), d.buttons, d.hats) for d in devices}
    before = dill.DILL._dll
    dill.DILL._dll = fake_hardware.FakeDill(
        [_fake_vjoy_raw(d.id, layouts[d.id]) for d in devices]
    )  # type: ignore[assignment]
    monkeypatch.setattr(output, "vjoy_ids", lambda: sorted(layouts))
    monkeypatch.setattr(output, "vjoy_layout", lambda i: layouts[int(i)])
    monkeypatch.setattr(output, "vjoy_hats_continuous", lambda i: True)
    monkeypatch.setattr(output, "reset_vjoy", lambda: None)
    for name in ("_joystick_devices", "_own_pads", "_layout_changed"):
        monkeypatch.setattr(di, name, type(getattr(di, name))())
    monkeypatch.setattr(di, "_window_up", False)
    monkeypatch.setattr(di, "_forget_unplugged", lambda seen: None)
    monkeypatch.setattr(di, "_sync_folder_names", lambda: None, raising=False)
    try:
        di._initialize_devices()
        linked = sorted(
            dev.vjoy_id for dev in di._joystick_devices.values() if dev.vjoy_id > 0
        )
        texts = [text for _vid, text in di._vjoy_problems]
    finally:
        dill.DILL._dll = before  # type: ignore[assignment]
    return linked, texts


@pytest.mark.parametrize(
    "devices",
    [
        # the old preset: two full devices
        [drivers.VJoyDevice(1), drivers.VJoyDevice(2)],
        # alike by count, not by which axes
        [
            drivers.VJoyDevice(1, ("x", "y"), 8, 0),
            drivers.VJoyDevice(2, ("z", "rx"), 8, 0),
            drivers.VJoyDevice(3, ("x", "y", "z"), 8, 0),
        ],
        # unlike
        [drivers.PRESETS["2 devices, full"][0], drivers.PRESETS["2 devices, full"][1]],
        [
            drivers.VJoyDevice(1, ("x",), 8, 0),
            drivers.VJoyDevice(2, ("x",), 9, 0),
            drivers.VJoyDevice(3, ("x",), 8, 1),
        ],
    ],
    ids=["old-preset", "alike-count", "preset-countdown", "unlike"],
)
def test_layout_key_alike_is_exactly_what_start_up_leaves_out(
    monkeypatch: pytest.MonkeyPatch, devices: list[drivers.VJoyDevice]
) -> None:
    alike_ids = {i for group in drivers.alike_devices(devices) for i in group}
    linked, texts = _start_up_matching(monkeypatch, devices)

    assert {d.id for d in devices} - set(linked) == alike_ids
    assert set(linked) == {d.id for d in devices} - alike_ids
    assert (len(texts) > 0) == bool(alike_ids)
    if alike_ids:
        assert all("can't be told apart" in t for t in texts)
    # The warning names the same devices the start-up message does.
    for group in drivers.alike_devices(devices):
        assert f"vJoy {group[0]}" in " ".join(texts)


def test_preset_devices_are_linked_by_start_up_matching(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    devices = drivers.PRESETS["2 devices, full"]
    assert [d.buttons for d in devices] == [128, 127]
    linked, texts = _start_up_matching(monkeypatch, devices)
    assert linked == [1, 2]
    assert texts == []


# -- Tools > Drivers has no runtime code (06 S185, D-01-RUNTIME-ROW) -----------


def test_model_rows_are_exactly_vjoy_vigembus_hidhide(
    qapp: object, app: Path, tmp_path: Path, world: World
) -> None:
    model = _model(app, tmp_path, world, HelperLauncher(world))
    keys = [r["key"] for r in model.rows]
    assert keys == ["vjoy", "vigembus", "hidhide"]
    assert not any("vcredist" in key for key in keys)


def test_job_file_with_the_runtime_driver_is_refused_and_runs_nothing(
    tmp_path: Path, world: World, helper_log: None
) -> None:
    jobs = tmp_path / "jobs.json"
    results = tmp_path / "results.json"
    jobs.write_text(
        json.dumps(
            {
                "version": drivers.FILE_VERSION,
                "jobs": [
                    {
                        "op": "update",
                        "driver": "vcredist",
                        "files": [
                            {"path": str(tmp_path / "x.exe"), "kind": "download"}
                        ],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unknown driver"):
        drivers.read_jobs(jobs)

    code = gremlin_device_helper.main(
        ["--jobs", str(jobs), "--results", str(results)], job_runner=world.run
    )

    assert code == 2
    assert world.calls == []
    assert not results.exists()


# --- batch 2: devices in use, the last axis, S1/S2 labels (06 S185) ---------


def _two_devices(world: World, tmp_path: Path, app: Path) -> DriversModel:
    """vJoy 1 FREE, vJoy 2 BUSY; the model reads busy through the real
    driver_jobs.busy_vjoy_devices with the fake runner."""
    _vjoy_ready(world)
    world.devices[2] = drivers.VJoyDevice(2, ("x", "y"), 8, 0)
    world.busy = {2}
    return _model(
        app,
        tmp_path,
        world,
        HelperLauncher(world),
        busy_reader=lambda: driver_jobs.busy_vjoy_devices(world.run),
    )


def test_busy_status_line_reaches_busy_vjoy_devices(world: World) -> None:
    _vjoy_ready(world)
    world.devices[2] = drivers.VJoyDevice(2)
    world.busy = {2}
    assert driver_jobs.busy_vjoy_devices(world.run) == [2]
    text = world.run(["vJoyConfig.exe", "-t"], 5)[1]
    assert driver_jobs.parse_status(text)[1] == "FREE"


def test_busy_device_is_marked_and_warned_when_edited_or_removed(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    helper_log: None,
) -> None:
    model = _two_devices(world, tmp_path, app)
    _pump(lambda: model.vjoyInUse == [2])
    assert {d["id"]: d["inUse"] for d in model.vjoyDevices} == {
        1: False,
        2: True,
    }
    assert model.inUseWarning() == ""  # nothing edited yet

    # Editing vJoy 1 only: untouched vJoy 2 does not warn.
    model.setAxis(0, "z", False)
    assert model.inUseWarning() == ""
    # Editing vJoy 2 warns, naming it and only it.
    model.setAxis(1, "z", True)
    warning = model.inUseWarning()
    assert warning == drivers.in_use_warning([2])
    assert "vJoy 2 is in use by another program" in warning
    assert "vJoy 1" not in warning


def test_lowering_devices_to_remove_a_busy_device_warns(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    helper_log: None,
) -> None:
    model = _two_devices(world, tmp_path, app)
    _pump(lambda: model.vjoyInUse == [2])
    model.setDeviceCount(1)  # device 2 will be deleted
    assert model.inUseWarning() == drivers.in_use_warning([2])


def test_preset_that_rewrites_a_busy_device_warns(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    helper_log: None,
) -> None:
    model = _two_devices(world, tmp_path, app)
    _pump(lambda: model.vjoyInUse == [2])
    model.setPreset("2 devices, full")  # vJoy 2 goes from X Y/8 to full
    assert model.inUseWarning() == drivers.in_use_warning([2])


def test_last_ticked_axis_cannot_be_unticked_and_job_never_axis_less(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    _vjoy_ready(world)
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher)
    model.setPreset("Custom")
    model.setDevice(0, ["x", "y"], 8, 0)
    model.setAxis(0, "x", False)
    model.setAxis(0, "y", False)  # the last one: refused
    model.setAxis(0, "y", False)
    assert model.vjoyDevices[0]["axes"] == ["y"]

    # Even setDevice with no axes keeps the device usable (never axis-less).
    model.setDevice(0, [], 8, 0)
    assert model.vjoyDevices[0]["axes"] != []

    _run(model)
    assert world.axis_args and all(a for a in world.axis_args)
    assert all(d.axes for d in world.vjoy_devices())
    sent = [d for job in launcher.jobs_seen for d in job.devices]
    assert sent and all(d.axes for d in sent)


def test_labels_are_s1_s2_but_vjoyconfig_gets_sl0_sl1(
    qapp: object, app: Path, tmp_path: Path, world: World, helper_log: None
) -> None:
    assert drivers.VJOY_AXIS_LABELS[-2:] == ("S1", "S2")
    assert drivers.VJOY_AXES[-2:] == ("sl0", "sl1")
    _vjoy_ready(world)
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher)
    model.setPreset("Custom")
    model.setDevice(0, ["x", "sl0", "sl1"], 8, 0)
    assert [a["label"] for a in model.vjoyAxes[-2:]] == ["S1", "S2"]
    assert [a["name"] for a in model.vjoyAxes[-2:]] == ["sl0", "sl1"]

    _run(model)

    command = next(c for c in world.calls if len(c) > 2 and c[2] == "-f")
    start = command.index("-a")
    assert command[start : start + 4] == ["-a", "x", "sl0", "sl1"]
    # The job file keeps the vJoyConfig names too.
    assert [d.axes for j in launcher.jobs_seen for d in j.devices] == [
        ("x", "sl0", "sl1")
    ]


# -- a vJoy update keeps the devices (01 S187, 06 S185, 12 S25b) --------------


def _old_vjoy_update_loses_device_2(world: World) -> None:
    """The test-machine reproduction: vJoy 2.1.9 with vJoy 2 (X Y Z, 32
    buttons, 0 hats) is updated; 2.2.2.0 drops it and adds a default vJoy 1."""
    world.install_vjoy("2.1.9.1")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[2] = drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)

    def update() -> None:
        world.devices.clear()
        world.devices[1] = drivers.VJoyDevice(1)

    world.after_vjoy_install = update


@pytest.fixture
def profile() -> Path:
    """The temp data folder test/conftest.py points the program at, so
    vjoy_lost.json never lands in the real one."""
    from gremlin import util

    folder = Path(util.userprofile_path())
    (folder / drivers.LOST_FILE).unlink(missing_ok=True)
    return folder


def _lost_file() -> Path:
    return drivers.lost_path()


def _ids(devices: list[drivers.VJoyDevice]) -> list[int]:
    return [d.id for d in devices]


def _update_vjoy(
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[DriversModel, HelperLauncher]:
    _bundle(app, monkeypatch, "vjoy", b"vjoy installer bytes")
    launcher = HelperLauncher(world)
    model = _model(app, tmp_path, world, launcher, lost_reader=drivers.read_lost)
    assert {r["key"]: r["state"] for r in model.rows}["vjoy"] == "older"
    model.setTicked("vjoy", True)
    _run(model)
    return model, launcher


def test_vjoy_update_that_loses_device_2_reports_lost_and_added(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
    profile: Path,
) -> None:
    _old_vjoy_update_loses_device_2(world)
    model, launcher = _update_vjoy(app, tmp_path, world, monkeypatch)

    # The update job carried the devices read before the update.
    update = [j for j in launcher.jobs_seen if j.op == "update"]
    assert [_ids(list(j.devices)) for j in update] == [[2]]
    assert world.ran_installer("vjoy")

    row = _results(model)["vJoy"]
    assert row["state"] == "done"
    assert "vJoy 1 was added by the vJoy update" in row["message"]
    result = launcher.results_seen[0][0]
    assert result.lost == [drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)]
    assert result.added == [1]
    assert model.lostText() == drivers.lost_text(result.lost)
    assert _ids(world.vjoy_devices()) == [1]

    # The lost device is remembered in vjoy_lost.json (temp profile).
    lost_file = _lost_file()
    assert lost_file.is_file() and lost_file.parent == profile
    data = json.loads(lost_file.read_text(encoding="utf-8"))
    assert data["version"] == 1 and [d["id"] for d in data["devices"]] == [2]
    assert _ids(drivers.read_lost()) == [2]

    # The real Tools > Drivers model shows it as a lost row with Repair.
    assert [d["id"] for d in model.vjoyLost] == [2]
    assert "vJoy 2 (3 axes, 32 buttons, 0 hats) is missing" in drivers.lost_text(
        drivers.read_lost()
    )


def test_repair_puts_back_only_vjoy_2_and_deletes_nothing(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
    profile: Path,
) -> None:
    _old_vjoy_update_loses_device_2(world)
    model, launcher = _update_vjoy(app, tmp_path, world, monkeypatch)
    calls_before = len(world.calls)

    assert model.repairDevice(2)
    assert model.busy
    _pump(lambda: not model.busy)

    restore = [j for j in launcher.jobs_seen if j.op == "vjoy_restore"]
    assert [_ids(list(j.devices)) for j in restore] == [[2]]
    assert _results(model)["vJoy devices"]["state"] == "done"
    new_calls = world.calls[calls_before:]
    # Only vJoy 2 is set up (-f), nothing deleted (-d), vJoy 1 untouched.
    assert not any(c[1:2] == ["-d"] for c in new_calls)
    sets = [c for c in new_calls if "-f" in c]
    assert [c[1] for c in sets] == ["2"]
    assert not any(c[1] == "1" for c in new_calls)
    assert world.devices[2] == drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)
    assert _ids(world.vjoy_devices()) == [1, 2]

    # The store is cleared and the model shows no lost row.
    assert drivers.read_lost() == []
    assert [d["id"] for d in model.vjoyLost] == []
    if _lost_file().exists():
        assert json.loads(_lost_file().read_text(encoding="utf-8"))["devices"] == []


def test_vjoy_update_that_loses_nothing_leaves_no_lost_data_and_no_file(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
    profile: Path,
) -> None:
    world.install_vjoy("2.1.9.1")
    world.install_vigembus("1.22.0")
    world.install_hidhide("1.5.230")
    world.devices[1] = drivers.VJoyDevice(1)  # the update keeps it
    model, launcher = _update_vjoy(app, tmp_path, world, monkeypatch)

    row = _results(model)["vJoy"]
    assert row["state"] == "done"
    result = launcher.results_seen[0][0]
    assert result.lost == [] and result.added == []
    assert model.lostText() == ""
    assert not _lost_file().exists()
    assert drivers.read_lost() == []
    assert [d["id"] for d in model.vjoyLost] == []


# -- update + edited set-up in one run (06 S185, user 2026-11-22) -------------


def _update_then_edit(
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    devices: int,
    also_vjoy_1: bool = False,
) -> tuple[DriversModel, HelperLauncher]:
    """The test-machine run: vJoy 2 (X Y Z, 32, 0) exists, vJoy is updated
    (which loses it) and the set-up lists `devices` devices."""
    _old_vjoy_update_loses_device_2(world)
    if also_vjoy_1:
        world.devices[1] = drivers.VJoyDevice(1)
    _bundle(app, monkeypatch, "vjoy", b"vjoy installer bytes")
    launcher = HelperLauncher(world)
    model = _model(
        app,
        tmp_path,
        world,
        launcher,
        lost_reader=drivers.read_lost,
        lost_pruner=drivers.prune_lost,
    )
    model.setTicked("vjoy", True)
    model.setDeviceCount(devices)
    assert len(model.vjoyDevices) == devices
    _run(model)
    ops = [j.op for j in launcher.jobs_seen]
    assert ops == ["update", "vjoy_setup"], ops
    return model, launcher


def test_update_then_setup_listing_vjoy_2_loses_nothing(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
    profile: Path,
) -> None:
    model, launcher = _update_then_edit(app, tmp_path, world, monkeypatch, 2)

    results = launcher.results_seen[0]
    assert [r.lost for r in results] == [[], []]
    assert [r.added for r in results] == [[], []]
    assert 2 in _ids(world.vjoy_devices())
    assert world.devices[2] == drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)
    assert model.lostText() == ""
    assert not _lost_file().exists()
    assert drivers.read_lost() == []
    assert [d["id"] for d in model.vjoyLost] == []


def test_update_then_setup_not_listing_vjoy_2_is_not_lost(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
    profile: Path,
) -> None:
    model, launcher = _update_then_edit(
        app, tmp_path, world, monkeypatch, 1, also_vjoy_1=True
    )

    results = launcher.results_seen[0]
    assert [r.lost for r in results] == [[], []]
    assert _ids(world.vjoy_devices()) == [1]
    assert model.lostText() == ""
    assert not _lost_file().exists()
    assert [d["id"] for d in model.vjoyLost] == []


def test_update_then_setup_that_leaves_vjoy_2_missing_is_lost_on_last_result(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    monkeypatch: pytest.MonkeyPatch,
    helper_log: None,
    profile: Path,
) -> None:
    world.drop_set_devices = {2}
    model, launcher = _update_then_edit(app, tmp_path, world, monkeypatch, 2)

    update, setup = launcher.results_seen[0]
    assert update.lost == []  # only the last vJoy result carries it
    assert [d.id for d in setup.lost] == [2]
    assert 2 not in _ids(world.vjoy_devices())
    assert [d["id"] for d in model.vjoyLost] == [2]
    assert _ids(drivers.read_lost()) == [2]
    assert model.lostText() == drivers.lost_text(setup.lost)


def test_remembered_lost_device_present_again_is_pruned_when_model_reads(
    qapp: object,
    app: Path,
    tmp_path: Path,
    world: World,
    helper_log: None,
    profile: Path,
) -> None:
    _vjoy_ready(world)
    world.devices[2] = drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)
    drivers.write_lost(
        [
            drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0),
            drivers.VJoyDevice(3, ("x",), 8, 0),  # still missing: stays
        ]
    )
    assert _ids(drivers.read_lost()) == [2, 3]

    model = _model(
        app,
        tmp_path,
        world,
        HelperLauncher(world),
        lost_reader=drivers.read_lost,
        lost_pruner=drivers.prune_lost,
    )

    assert _ids(drivers.read_lost()) == [3]
    assert [d["id"] for d in model.vjoyLost] == [3]
