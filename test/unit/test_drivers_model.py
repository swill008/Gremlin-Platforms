# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Tools › Drivers' model (06 S185-S188, 12 S25/S25a): rows and labels, the
vJoy layout, the job file, progress and results from the helper's results
file, and the two-half HidHide update. Nothing real is launched: the
launcher, status, vJoy read and clock are fakes; the job, results and
pending files are the real ones from gremlin.drivers in tmp_path."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import clock, drivers
from gremlin.ui import drivers_model
from gremlin.ui.drivers_model import DriversModel


def _status(key: str, installed: str, state: str) -> drivers.DriverStatus:
    info = drivers.DRIVERS[key]
    return drivers.DriverStatus(key, info.name, installed, info.bundled_version, state)


class Launcher:
    def __init__(self, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.error = error
        self.alive = True

    def __call__(self, file: str, parameters: str) -> Launcher:
        self.calls.append((file, parameters))
        if self.error is not None:
            raise self.error
        return self

    def running(self) -> bool:
        return self.alive

    def close(self) -> None:
        pass


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def _sync(
    name: str, work: Callable[[], object], done: Callable[[object], None]
) -> None:
    done(work())


@pytest.fixture
def app(tmp_path: Path) -> Path:
    folder = tmp_path / "app"
    (folder / "drivers").mkdir(parents=True)
    return folder


def _model(
    app: Path,
    tmp_path: Path,
    statuses: list[drivers.DriverStatus],
    *,
    current: list[drivers.VJoyDevice] | None = None,
    **kw: object,
) -> DriversModel:
    kw.setdefault("launcher", Launcher())
    holder = {"statuses": statuses}
    model = DriversModel(
        status_source=lambda: holder["statuses"],
        app=lambda: app,
        vjoy_reader=lambda: list(current or []),
        background=_sync,
        temp_dir=tmp_path,
        poll_ms=5,
        **kw,
    )
    model._test_holder = holder  # type: ignore[attr-defined]
    return model


def _pump(qapp: object, until: Callable[[], bool], limit: float = 3.0) -> None:
    end = clock.monotonic() + limit
    while not until() and clock.monotonic() < end:
        QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 20)
    assert until(), "condition not reached in time"


def _job_path(launcher: Launcher) -> tuple[Path, Path]:
    params = launcher.calls[-1][1]
    parts = params.split('"')
    return Path(parts[1]), Path(parts[3])


ALL_MISSING = [
    _status("vjoy", "", "missing"),
    _status("vigembus", "", "missing"),
    _status("hidhide", "", "missing"),
]


def test_rows_show_each_driver_with_its_label_and_box(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(
        app,
        tmp_path,
        [
            _status("vjoy", "", "missing"),
            _status("vigembus", "1.21.442.0", "older"),
            _status("hidhide", "1.5.230", "same"),
        ],
    )
    rows = {r["key"]: r for r in model.rows}
    assert rows["vjoy"]["label"] == "not installed"
    assert rows["vjoy"]["ticked"] and rows["vjoy"]["tickable"]
    assert rows["vigembus"]["label"] == "update available: 1.21.442.0 → 1.22.0"
    assert not rows["vigembus"]["ticked"] and rows["vigembus"]["tickable"]
    assert rows["hidhide"]["label"] == "1.5.230"
    assert not rows["hidhide"]["tickable"] and not rows["hidhide"]["ticked"]
    model.setTicked("vigembus", True)
    model.setTicked("hidhide", True)  # no box: ignored
    rows = {r["key"]: r for r in model.rows}
    assert rows["vigembus"]["ticked"] and not rows["hidhide"]["ticked"]
    model.reload()
    assert {r["key"]: r for r in model.rows}["vigembus"]["ticked"]


def test_presets_and_custom_layout(qapp: object, app: Path, tmp_path: Path) -> None:
    model = _model(app, tmp_path, ALL_MISSING)
    assert model.presets == ["1 device, full", "2 devices, full", "Custom"]
    assert model.vjoyPreset == "1 device, full"
    assert model.vjoyDevices == [{"id": 1, "axes": 8, "buttons": 128, "hats": 4}]
    assert model.vjoyCurrent == []
    model.setPreset("2 devices, full")
    assert len(model.vjoyDevices) == 2 and model.vjoyEdited
    assert model.vjoyWarning == ""  # vJoy has no devices yet
    model.setDeviceCount(3)
    model.setDevice(2, 99, 500, -1)
    assert model.vjoyPreset == "Custom"
    assert model.vjoyDevices[2] == {"id": 3, "axes": 8, "buttons": 128, "hats": 0}
    model.setDeviceCount(40)
    assert len(model.vjoyDevices) == 16


def test_existing_devices_shown_as_they_are_and_warned_when_edited(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    current = [drivers.VJoyDevice(1, 4, 32, 1)]
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")], current=current)
    assert model.vjoyCurrent == [{"id": 1, "axes": 4, "buttons": 32, "hats": 1}]
    assert model.vjoyDevices == model.vjoyCurrent
    assert model.vjoyPreset == "Custom" and not model.vjoyEdited
    assert model.vjoyWarning == "" and model.describe() == ""
    assert not model.apply()
    model.setPreset("1 device, full")
    assert model.vjoyEdited
    assert (
        model.vjoyWarning
        == "Running games will lose the vJoy devices until they restart."
    )
    text = model.describe()
    assert "1. Set up 1 vJoy device." in text
    assert model.vjoyWarning in text
    model.setDevice(0, 4, 32, 1)  # back to what vJoy has
    assert not model.vjoyEdited and model.vjoyWarning == ""


def test_describe_says_what_in_what_order_and_the_one_prompt(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(
        app,
        tmp_path,
        [
            _status("vjoy", "", "missing"),
            _status("vigembus", "1.21.442.0", "older"),
            _status("hidhide", "1.4.0", "older"),
        ],
    )
    model.setTicked("vigembus", True)
    model.setTicked("hidhide", True)
    lines = model.describe().splitlines()
    assert lines[:5] == [
        "The program will do these steps, in this order:",
        "1. Install vJoy 2.2.2.0.",
        "2. Set up 1 vJoy device.",
        "3. Update ViGEmBus 1.21.442.0 to 1.22.0.",
        "4. Remove HidHide 1.4.0.",
    ]
    text = "\n".join(lines)
    assert "administrator permission once" in text
    assert "step 1 of 2" in text and "HidHide 1.5.230" in text and "restart" in text


def test_apply_writes_the_job_file_and_starts_the_helper(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _model(
        app,
        tmp_path,
        [
            _status("vjoy", "", "missing"),
            _status("vigembus", "1.21.442.0", "older"),
            _status("hidhide", "1.5.230", "same"),
        ],
        launcher=launcher,
        results_reader=lambda p: ([], False),
    )
    model.setTicked("vigembus", True)
    assert model.apply()
    assert model.busy
    file, params = launcher.calls[0]
    assert file == str(app / "Gremlin Device Helper.exe")
    assert params.startswith("--jobs ") and " --results " in params
    jobs_path, results_path = _job_path(launcher)
    assert jobs_path.parent == tmp_path and results_path.parent == tmp_path
    jobs = drivers.read_jobs(jobs_path)
    assert [(j.op, j.driver) for j in jobs] == [
        ("install", "vjoy"),
        ("vjoy_setup", "vjoy"),
        ("update", "vigembus"),
    ]
    assert jobs[0].files == [
        {
            "path": str(app / "drivers" / drivers.DRIVERS["vjoy"].bundled_file),
            "kind": "bundled",
        }
    ]
    assert jobs[1].devices == [drivers.VJoyDevice(1, 8, 128, 4)]
    assert not model.apply()  # busy: one run at a time
    model._timer.stop()


def test_progress_and_results_follow_the_results_file(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _model(
        app,
        tmp_path,
        [_status("vjoy", "", "missing"), _status("vigembus", "", "missing")],
        launcher=launcher,
    )
    model.setTicked("vjoy", False)
    model.setTicked("vjoy", True)
    seen: list[str] = []
    model.changed.connect(lambda: seen.append(model.progress))
    done: list[bool] = []
    model.finished.connect(lambda: done.append(True))
    assert model.apply()
    _, results = _job_path(launcher)
    assert model.progress == "Waiting for Gremlin Device Helper…"
    R = drivers.JobResult
    drivers.write_results(results, [R("running"), R("waiting"), R("waiting")], False)
    _pump(qapp, lambda: model.progress == "Installing vJoy 2.2.2.0…")
    drivers.write_results(
        results,
        [
            R("done", "vJoy 2.2.2.0 is installed.", False, "bundled"),
            R("done"),
            R("running"),
        ],
        False,
    )
    _pump(qapp, lambda: model.progress == "Installing ViGEmBus 1.22.0…")
    assert not done
    drivers.write_results(
        results,
        [
            R("done", "vJoy 2.2.2.0 is installed."),
            R("done", "1 device set up."),
            R("done", "", True),
        ],
        True,
    )
    _pump(qapp, lambda: bool(done))
    assert not model.busy and model.restartNeeded
    assert model.results == [
        {"driver": "vJoy", "state": "done", "message": "vJoy 2.2.2.0 is installed."},
        {"driver": "vJoy devices", "state": "done", "message": "1 device set up."},
        {"driver": "ViGEmBus", "state": "done", "message": "Done."},
    ]
    assert "Installing vJoy 2.2.2.0…" in seen


def test_hidhide_update_in_two_halves(qapp: object, app: Path, tmp_path: Path) -> None:
    launcher = Launcher()
    model = _model(
        app, tmp_path, [_status("hidhide", "1.4.0", "older")], launcher=launcher
    )
    model.setTicked("hidhide", True)
    assert model.apply()
    jobs_path, results = _job_path(launcher)
    assert [(j.op, j.driver, j.files) for j in drivers.read_jobs(jobs_path)] == [
        ("remove", "hidhide", [])
    ]
    R = drivers.JobResult
    drivers.write_results(results, [R("running")], False)
    _pump(qapp, lambda: model.progress == "Removing HidHide 1.4.0…")
    model._test_holder["statuses"] = [_status("hidhide", "", "missing")]
    drivers.write_results(results, [R("done", "HidHide 1.4.0 is removed.")], True)
    _pump(qapp, lambda: not model.busy)
    assert model.restartNeeded and model.pendingHidHide
    assert model.pendingVersion == "1.5.230"
    pending = drivers.read_pending(app)
    bundled = str(app / "drivers" / drivers.DRIVERS["hidhide"].bundled_file)
    assert pending == {
        "hidhide": {"version": "1.5.230", "file": bundled, "kind": "bundled"}
    }

    # Step 2, after the restart: a new model, as at Gremlin's next start.
    launcher2 = Launcher()
    model2 = _model(
        app, tmp_path, [_status("hidhide", "", "missing")], launcher=launcher2
    )
    assert model2.pendingHidHide
    model2.laterHidHide()
    assert model2.pendingHidHide and not launcher2.calls
    assert model2.finishHidHide()
    jobs_path, results = _job_path(launcher2)
    jobs = drivers.read_jobs(jobs_path)
    assert [(j.op, j.driver, j.files) for j in jobs] == [
        ("install", "hidhide", [{"path": bundled, "kind": "bundled"}])
    ]
    drivers.write_results(results, [R("running")], False)
    _pump(qapp, lambda: model2.progress == "Installing HidHide 1.5.230…")
    drivers.write_results(results, [R("done", "HidHide 1.5.230 is installed.")], True)
    _pump(qapp, lambda: not model2.busy)
    assert model2.restartNeeded
    assert not model2.pendingHidHide and drivers.read_pending(app) is None


def test_a_failed_step_2_keeps_the_pending_update(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    drivers.write_pending(
        app, {"hidhide": {"version": "1.5.230", "file": "x.exe", "kind": "bundled"}}
    )
    launcher = Launcher()
    model = _model(
        app, tmp_path, [_status("hidhide", "", "missing")], launcher=launcher
    )
    assert model.finishHidHide()
    _, results = _job_path(launcher)
    drivers.write_results(
        results, [drivers.JobResult("failed", "exit code 1603")], True
    )
    _pump(qapp, lambda: not model.busy)
    assert model.results == [
        {"driver": "HidHide", "state": "failed", "message": "exit code 1603"}
    ]
    assert model.pendingHidHide and not model.restartNeeded


def test_nothing_to_do_or_no_program_folder_starts_nothing(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    same = [_status("vjoy", "2.2.2.0", "same")]
    model = _model(app, tmp_path, same, launcher=launcher)
    assert not model.apply() and model.describe() == ""
    assert not model.finishHidHide()  # no pending.json
    model = DriversModel(
        status_source=lambda: ALL_MISSING,
        app=lambda: None,
        launcher=launcher,
        background=_sync,
        vjoy_reader=list,
    )
    assert not model.apply()
    assert model.progress == drivers_model.NO_APP_TEXT
    assert launcher.calls == []


def test_refused_permission_is_reported(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    from gremlin import device_disable

    launcher = Launcher(device_disable.Refused())
    model = _model(app, tmp_path, ALL_MISSING, launcher=launcher)
    assert not model.apply()
    assert model.progress == "Administrator permission was refused."
    assert not model.busy


def test_the_wait_gives_up_after_30_minutes(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    ticks = Clock()
    model = _model(
        app,
        tmp_path,
        ALL_MISSING,
        monotonic=ticks,
        results_reader=lambda p: ([], False),
    )
    done: list[bool] = []
    model.finished.connect(lambda: done.append(True))
    assert model.apply()
    ticks.t += 29 * 60
    QtCore.QCoreApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
    assert model.busy
    ticks.t += 2 * 60
    _pump(qapp, lambda: bool(done))
    assert model.progress == drivers_model.GAVE_UP_TEXT
    assert {r["state"] for r in model.results} == {"failed"}


def test_helper_that_ends_early_fails_the_run(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _model(
        app,
        tmp_path,
        ALL_MISSING,
        launcher=launcher,
        results_reader=lambda p: ([drivers.JobResult("running")], False),
    )
    assert model.apply()
    launcher.alive = False
    _pump(qapp, lambda: not model.busy)
    assert model.progress == drivers_model.ENDED_TEXT
    assert model.results[0]["message"] == drivers_model.ENDED_TEXT


def test_restart_uses_the_hook_and_the_real_calls_are_blocked(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    calls: list[bool] = []
    model = _model(app, tmp_path, ALL_MISSING, restarter=lambda: calls.append(True))
    model.restartNow()
    assert calls == [True]
    with pytest.raises(drivers_model.RealCallBlocked):
        drivers_model._real_launcher("helper.exe", "--jobs x")
    with pytest.raises(drivers_model.RealCallBlocked):
        drivers_model._real_restart()
    model = DriversModel(
        status_source=lambda: ALL_MISSING,
        app=lambda: app,
        background=_sync,
        vjoy_reader=list,
        temp_dir=tmp_path,
    )
    with pytest.raises(drivers_model.RealCallBlocked):
        model.apply()


def test_the_vjoy_layout_is_read_off_the_main_thread(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    import threading

    where: list[bool] = []

    def reader() -> list[drivers.VJoyDevice]:
        where.append(threading.current_thread() is threading.main_thread())
        return [drivers.VJoyDevice(1), drivers.VJoyDevice(2)]

    model = DriversModel(
        status_source=lambda: [_status("vjoy", "2.2.2.0", "same")],
        app=lambda: app,
        launcher=Launcher(),
        vjoy_reader=reader,
        temp_dir=tmp_path,
    )
    _pump(qapp, lambda: bool(model.vjoyCurrent))
    assert where == [False]
    assert model.vjoyPreset == "2 devices, full" and not model.vjoyEdited
