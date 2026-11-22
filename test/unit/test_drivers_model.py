# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Tools › Drivers' model (06 S185-S188, 12 S25/S25a): rows and labels, the
vJoy layout, the job file, progress and results from the helper's results
file, and the two-half HidHide update. Nothing real is launched: the
launcher, status, vJoy read and clock are fakes; the job, results and
pending files are the real ones from gremlin.drivers in tmp_path."""

from __future__ import annotations

import json
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


def _plain(devices: list) -> list:
    """vjoyDevices without the rows' view keys (inUse, locked)."""
    return [
        {k: v for k, v in d.items() if k not in ("inUse", "locked")} for d in devices
    ]


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


ALL = list(drivers.VJOY_AXES)


def test_presets_and_custom_layout(qapp: object, app: Path, tmp_path: Path) -> None:
    model = _model(app, tmp_path, ALL_MISSING)
    assert model.presets == ["1 device, full", "2 devices, full", "Custom"]
    assert model.vjoyPreset == "1 device, full"
    assert _plain(model.vjoyDevices) == [
        {"id": 1, "axes": ALL, "buttons": 128, "hats": 4}
    ]
    assert model.vjoyCurrent == []
    model.setPreset("2 devices, full")
    assert len(model.vjoyDevices) == 2 and model.vjoyEdited
    assert model.vjoyWarning == ""  # vJoy has no devices yet
    model.setDeviceCount(3)
    model.setDevice(2, ["x", "bogus", "SL1"], 500, -1)
    assert model.vjoyPreset == "Custom"
    assert _plain(model.vjoyDevices)[2] == {
        "id": 3,
        "axes": ["x", "sl1"],
        "buttons": 128,
        "hats": 0,
    }
    model.setDeviceCount(40)
    assert len(model.vjoyDevices) == 16


def test_set_axis_unticks_one_axis_and_the_job_lists_the_rest(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = DriversModel(
        status_source=lambda: [_status("vjoy", "2.2.2.0", "same")],
        app=lambda: app,
        launcher=launcher,
        results_reader=lambda p: ([], False),
        vjoy_reader=lambda: [],
        background=lambda n, w, d: d(w()),
        temp_dir=tmp_path,
    )
    # The short names from the one table; the job keeps vJoyConfig's names.
    assert [a["label"] for a in model.vjoyAxes] == [
        "X",
        "Y",
        "Z",
        "Rx",
        "Ry",
        "Rz",
        "S1",
        "S2",
    ]
    assert [a["label"] for a in model.vjoyAxes] == list(drivers.VJOY_AXIS_LABELS)
    assert [a["name"] for a in model.vjoyAxes] == list(drivers.VJOY_AXES)
    model.setAxis(0, "rz", False)
    assert model.vjoyDevices[0]["axes"] == ["x", "y", "z", "rx", "ry", "sl0", "sl1"]
    assert model.vjoyPreset == "Custom"
    model.setAxis(0, "nope", False)  # unknown: ignored
    model.setAxis(5, "x", False)  # no such device: ignored
    model.setAxis(0, "x", False)
    model.setAxis(0, "x", True)  # back on, order kept
    assert model.vjoyDevices[0]["axes"] == ["x", "y", "z", "rx", "ry", "sl0", "sl1"]
    assert model.apply()
    jobs_path, _ = _job_path(launcher)
    raw = json.loads(jobs_path.read_text(encoding="utf-8"))
    device = raw["jobs"][0]["devices"][0] if "jobs" in raw else raw[0]["devices"][0]
    assert device["axes"] == ["x", "y", "z", "rx", "ry", "sl0", "sl1"]
    model._timer.stop()


def test_device_summary_uses_the_helper_wording(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(app, tmp_path, ALL_MISSING)
    assert (
        model.deviceSummary(["x", "y", "sl0"], 8, 0)
        == "3 axes (X, Y, S1), 8 buttons, 0 hats"
    )
    assert model.deviceSummary(["x"], 1, 1) == "1 axis (X), 1 button, 1 hat"


def test_a_new_device_takes_the_lowest_free_id(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """vJoy can have gaps (devices 1 and 3): raising the count must not give
    two devices the same id (found by ISS2 reading the code)."""
    current = [drivers.VJoyDevice(1), drivers.VJoyDevice(3)]
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")], current=current)
    assert [d["id"] for d in model.vjoyDevices] == [1, 3]
    model.setDeviceCount(3)
    ids = [d["id"] for d in model.vjoyDevices]
    assert sorted(ids) == [1, 2, 3]


def test_added_devices_count_down_and_existing_ones_keep_their_numbers(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """D-01-VJOY-COUNTDOWN: an added device gets new_device(id), 129 - id
    buttons; devices already in the list are not renumbered."""
    current = [drivers.VJoyDevice(1, ("x", "y"), 32, 1), drivers.VJoyDevice(3)]
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")], current=current)
    model.setDeviceCount(4)
    by_id = {d["id"]: d for d in _plain(model.vjoyDevices)}
    assert by_id[1] == {"id": 1, "axes": ["x", "y"], "buttons": 32, "hats": 1}
    assert by_id[3]["buttons"] == 128  # kept, not 126
    assert by_id[2]["buttons"] == 127 and by_id[2]["hats"] == 4
    assert by_id[4]["buttons"] == 125
    assert by_id[2]["axes"] == list(drivers.VJOY_AXES)


def test_alike_devices_ask_before_apply_and_unlike_ones_do_not(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")])
    assert model.alikeWarning() == ""  # nothing to set up yet
    model.setPreset("2 devices, full")  # 128 and 127: told apart
    assert model.alikeWarning() == ""
    model.setDeviceCount(3)
    model.setDevice(2, list(drivers.VJOY_AXES), 128, 4)  # like vJoy 1
    assert model.alikeWarning() == (
        drivers.alike_warning([[1, 3]]) + " Continue anyway?"
    )
    assert model.alikeWarning().startswith("vJoy 1 and vJoy 3 have the same")
    # Asking runs nothing; apply() is the caller's Yes.
    assert model._launcher.calls == []  # type: ignore[attr-defined]


def test_alike_warning_only_for_devices_apply_will_set(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """Alike devices that exist and aren't edited are not asked about."""
    current = [drivers.VJoyDevice(1), drivers.VJoyDevice(2)]
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")], current=current)
    assert model.alikeWarning() == ""


def test_existing_devices_shown_as_they_are_and_warned_when_edited(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    current = [drivers.VJoyDevice(1, ("x", "y", "z", "rx"), 32, 1)]
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")], current=current)
    assert model.vjoyCurrent == [
        {"id": 1, "axes": ["x", "y", "z", "rx"], "buttons": 32, "hats": 1}
    ]
    assert _plain(model.vjoyDevices) == model.vjoyCurrent
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
    model.setDevice(0, ["x", "y", "z", "rx"], 32, 1)  # back to what vJoy has
    assert not model.vjoyEdited and model.vjoyWarning == ""


def test_a_smaller_layout_names_the_devices_that_will_be_deleted(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    current = [
        drivers.VJoyDevice(1, drivers.VJOY_AXES, 128, 4),
        drivers.VJoyDevice(2, drivers.VJOY_AXES, 128, 4),
        drivers.VJoyDevice(3, drivers.VJOY_AXES, 128, 4),
    ]
    model = _model(app, tmp_path, [_status("vjoy", "2.2.2.0", "same")], current=current)
    assert "deleted" not in model.describe() and model.vjoyWarning == ""
    model.setDeviceCount(1)
    text = model.describe()
    assert "vJoy device 2 will be deleted." in text
    assert "vJoy device 3 will be deleted." in text
    assert "vJoy device 1 will be deleted." not in text
    assert model.vjoyWarning in text and model.vjoyWarning
    # Growing is an edit too, but deletes nothing.
    model.setDeviceCount(4)
    assert "deleted" not in model.describe() and model.vjoyWarning


def test_a_hidhide_remove_says_a_restart_follows(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(app, tmp_path, [_status("hidhide", "1.4.0", "older")])
    model.setTicked("hidhide", True)
    assert "a restart follows" in model.describe()


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
    assert jobs[1].devices == [drivers.VJoyDevice(1, drivers.VJOY_AXES, 128, 4)]
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
        # The "2 devices, full" preset counts down: 128 and 127.
        return [drivers.new_device(1), drivers.new_device(2)]

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


# -- the rows (06 S185: setup's rows except the Visual C++ Runtime, 1b) ------

SAME = [
    _status("vjoy", "2.2.2.0", "same"),
    _status("vigembus", "1.22.0", "same"),
    _status("hidhide", "1.5.230", "same"),
]


def test_rows_are_exactly_vjoy_vigembus_hidhide(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(app, tmp_path, SAME)
    assert [r["key"] for r in model.rows] == ["vjoy", "vigembus", "hidhide"]
    assert model.describe() == ""  # nothing ticked: nothing to apply


# -- Tools › Drivers layout, one axis, devices in use (06 S185, 2026-11-22) ---

VJOY_SAME = [_status("vjoy", "2.2.2.0", "same")]


def test_remove_device_and_lowering_the_count_drops_the_highest(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """D-06-DRIVERS-LAYOUT: the row's ✕ removes that device; lowering
    Devices removes the highest-numbered; the last device stays."""
    model = _model(app, tmp_path, VJOY_SAME)
    model.setDeviceCount(4)
    model.removeDevice(1)
    assert [d["id"] for d in model.vjoyDevices] == [1, 3, 4]
    assert model.vjoyPreset == "Custom"
    model.setDeviceCount(4)  # the gap is filled, the list stays in id order
    assert [d["id"] for d in model.vjoyDevices] == [1, 2, 3, 4]
    model.setDeviceCount(2)
    assert [d["id"] for d in model.vjoyDevices] == [1, 2]
    model.removeDevice(9)  # no such row: ignored
    model.removeDevice(0)
    model.removeDevice(0)  # the last device stays
    assert [d["id"] for d in model.vjoyDevices] == [2]


def test_the_last_ticked_axis_cannot_be_unticked(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """D-01-VJOY-ONE-AXIS, through drivers.can_untick_axis."""
    model = _model(app, tmp_path, VJOY_SAME)
    model.setDevice(0, ["y"], 100, 0)
    assert model.vjoyDevices[0]["locked"] == ["y"]
    model.setAxis(0, "y", False)
    assert model.vjoyDevices[0]["axes"] == ["y"]
    model.setDevice(0, [], 100, 0)  # no axis: the device keeps its axes
    assert model.vjoyDevices[0]["axes"] == ["y"]
    model.setAxis(0, "x", True)
    assert model.vjoyDevices[0]["locked"] == []
    model.setAxis(0, "y", False)
    assert model.vjoyDevices[0]["axes"] == ["x"]


def _busy_model(
    app: Path, tmp_path: Path, busy: list[int], **kw: object
) -> DriversModel:
    current = [drivers.new_device(1), drivers.new_device(2)]
    return _model(
        app,
        tmp_path,
        VJOY_SAME,
        current=current,
        busy_reader=lambda: list(busy),
        **kw,
    )


def test_busy_devices_are_marked_and_warned_only_when_changed_or_removed(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """D-01-VJOY-IN-USE: the warning is drivers.in_use_warning of the busy
    devices the setup changes or removes, a preset included."""
    model = _busy_model(app, tmp_path, [2])
    assert model.vjoyInUse == [2]
    assert [r["inUse"] for r in model.vjoyDevices] == [False, True]
    assert model.inUseWarning() == ""  # nothing edited
    model.setDevice(0, list(drivers.VJOY_AXES), 100, 4)  # vJoy 1 only
    assert model.inUseWarning() == ""
    model.setDevice(1, list(drivers.VJOY_AXES), 99, 4)  # vJoy 2 changed
    assert model.inUseWarning() == drivers.in_use_warning([2])
    model.setPreset("1 device, full")  # vJoy 2 removed by a preset
    assert model.inUseWarning() == drivers.in_use_warning([2])
    model.setPreset("2 devices, full")  # back to what vJoy has
    assert model.inUseWarning() == ""


def test_several_busy_devices_named_together(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _busy_model(app, tmp_path, [1, 2])
    model.setDeviceCount(1)
    model.setDevice(0, ["x"], 128, 4)
    assert model.inUseWarning() == drivers.in_use_warning([1, 2])


def test_busy_ids_are_read_with_the_layout_off_the_main_thread(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    import threading

    where: list[bool] = []

    def busy() -> list[int]:
        where.append(threading.current_thread() is threading.main_thread())
        return [1]

    model = DriversModel(
        status_source=lambda: VJOY_SAME,
        app=lambda: app,
        launcher=Launcher(),
        vjoy_reader=lambda: [drivers.new_device(1)],
        busy_reader=busy,
        temp_dir=tmp_path,
    )
    _pump(qapp, lambda: bool(model.vjoyInUse))
    assert where == [False]
    assert model.vjoyInUse == [1]


def test_a_failing_busy_read_counts_as_none_busy(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    def broken() -> list[int]:
        raise OSError("no vJoyConfig")

    current = [drivers.new_device(1), drivers.new_device(2)]
    model = _model(app, tmp_path, VJOY_SAME, current=current, busy_reader=broken)
    assert model.vjoyInUse == []
    assert len(model.vjoyCurrent) == 2  # the layout still read


def test_own_run_hides_busy_ids_until_they_are_read_again_after_stop(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """User 2026-11-22 ("a"): while our own Run is on, busy ids are ours too,
    so none are shown or warned about; after Stop they are read again."""
    busy = [2]
    model = _busy_model(app, tmp_path, busy)
    read: list[str] = []
    model.inUseRead.connect(lambda: read.append("read"))
    model.runActive = True
    assert model.vjoyInUse == []
    assert not any(r["inUse"] for r in model.vjoyDevices)
    model.setDevice(1, list(drivers.VJOY_AXES), 99, 4)
    assert model.inUseWarning() == ""
    assert model.changesVjoy() is True
    busy[:] = []  # our Run let vJoy 2 go
    model.runActive = False
    assert read == ["read"]
    assert model.vjoyInUse == []
    assert model.inUseWarning() == ""
    busy[:] = [2]  # someone else holds it
    model.refreshInUse()
    assert model.inUseWarning() == drivers.in_use_warning([2])


def test_changes_vjoy_only_when_the_plan_touches_vjoy(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(app, tmp_path, [*VJOY_SAME, _status("vigembus", "1.21.0", "older")])
    assert model.changesVjoy() is False
    model.setTicked("vigembus", True)
    assert model.changesVjoy() is False
    model.setDeviceCount(2)
    assert model.changesVjoy() is True


def test_showing_line(qapp: object, app: Path, tmp_path: Path) -> None:
    model = _model(app, tmp_path, VJOY_SAME)
    assert model.showingText(0, 1) == "Showing 1 device"
    model.setDeviceCount(6)
    assert model.showingText(0, 6) == "Showing all 6 devices"
    assert model.showingText(0, 4) == "Showing 1-4 of 6 devices"
    assert model.showingText(2, 4) == "Showing 3-6 of 6 devices"


def test_add_device_takes_lowest_free_id_and_preview(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    """S185: the "+ Add device" row's preview and click."""
    model = _model(qapp, tmp_path, ALL_MISSING)
    assert model.addPreview == "vJoy 2 · 127 buttons"
    model.setDeviceCount(3)
    model.removeDevice(1)  # ids 1 and 3: the gap is the lowest free id
    assert model.addPreview == "vJoy 2 · 127 buttons"
    model.addDevice()
    devices = _plain(model.vjoyDevices)
    assert [d["id"] for d in devices] == [1, 2, 3]
    assert devices[1]["buttons"] == 127
    assert model.addPreview == "vJoy 4 · 125 buttons"
    model.setDeviceCount(16)
    assert model.addPreview == ""
    model.addDevice()
    assert len(model.vjoyDevices) == 16


# -- a vJoy update keeps the devices (06 S185, D-01-VJOY-UPDATE-KEEPS) --------

VJOY_OLDER = [_status("vjoy", "2.1.9.1", "older")]
V2 = drivers.VJoyDevice(2, ("x", "y", "z"), 32, 0)
V4 = drivers.VJoyDevice(4, drivers.VJOY_AXES, 32, 0)


def _update_model(
    app: Path, tmp_path: Path, launcher: Launcher, **kw: object
) -> DriversModel:
    kw.setdefault("current", [V2, V4])
    model = _model(app, tmp_path, VJOY_OLDER, launcher=launcher, **kw)  # type: ignore[arg-type]
    model.setTicked("vjoy", True)
    return model


def _run_update(
    qapp: object, model: DriversModel, launcher: Launcher, result: drivers.JobResult
) -> None:
    done: list[bool] = []
    model.finished.connect(lambda: done.append(True))
    assert model.apply()
    _, results = _job_path(launcher)
    drivers.write_results(results, [result], True)
    _pump(qapp, lambda: bool(done))


def test_the_vjoy_update_job_carries_the_devices_and_the_info_box_names_them(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _update_model(app, tmp_path, launcher, results_reader=lambda p: ([], False))
    assert model.updateInfo() == drivers.update_info_text([V2, V4])
    assert "your 2 vJoy devices (vJoy 2, vJoy 4)" in model.updateInfo()
    assert model.apply()
    jobs = drivers.read_jobs(_job_path(launcher)[0])
    assert [(j.op, j.driver) for j in jobs] == [("update", "vjoy")]
    assert jobs[0].devices == [V2, V4]
    model._timer.stop()


def test_devices_not_read_give_the_other_info_text(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _update_model(app, tmp_path, Launcher(), current=[])
    assert model.updateInfo() == drivers.update_info_text([])
    assert model.updateInfo().startswith("vJoy's devices couldn't be read")


def test_no_info_box_without_a_vjoy_update(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    model = _model(app, tmp_path, ALL_MISSING)  # a fresh install
    assert model.updateInfo() == ""
    model = _update_model(app, tmp_path, Launcher())
    model.setTicked("vjoy", False)
    assert model.updateInfo() == ""


def test_lost_devices_ask_repair_now_which_puts_back_exactly_those(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _update_model(app, tmp_path, launcher)
    _run_update(
        qapp,
        model,
        launcher,
        drivers.JobResult("done", "vJoy is updated.", lost=[V4], added=[1]),
    )
    assert model.lostText() == drivers.lost_text([V4])
    assert model.results[0]["message"] == (
        "vJoy is updated. vJoy 1 was added by the vJoy update."
    )
    assert model.repairNow()
    assert len(launcher.calls) == 2
    jobs = drivers.read_jobs(_job_path(launcher)[0])
    assert [(j.op, j.driver, j.devices) for j in jobs] == [
        ("vjoy_restore", "vjoy", [V4])
    ]
    assert model.lostText() == ""
    model._timer.stop()


def test_repair_later_writes_nothing(qapp: object, app: Path, tmp_path: Path) -> None:
    launcher = Launcher()
    model = _update_model(app, tmp_path, launcher)
    _run_update(
        qapp, model, launcher, drivers.JobResult("done", lost=[V2, V4], added=[])
    )
    assert model.lostText() == drivers.lost_text([V2, V4])
    before = sorted(tmp_path.glob("gremlin-driver-jobs-*"))
    model.repairLater()
    assert model.lostText() == ""
    assert len(launcher.calls) == 1
    assert sorted(tmp_path.glob("gremlin-driver-jobs-*")) == before
    assert not model.repairNow()  # nothing left to put back


def test_nothing_lost_shows_nothing(qapp: object, app: Path, tmp_path: Path) -> None:
    launcher = Launcher()
    model = _update_model(app, tmp_path, launcher)
    _run_update(qapp, model, launcher, drivers.JobResult("done", "vJoy is updated."))
    assert model.lostText() == ""
    assert model.vjoyLost == []
    assert model.results[0]["message"] == "vJoy is updated."


def test_lost_box_reads_the_vjoy_setup_result_of_an_update_and_set_up_run(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _update_model(app, tmp_path, launcher)
    model.addDevice()
    done: list[bool] = []
    model.finished.connect(lambda: done.append(True))
    assert model.apply()
    jobs = drivers.read_jobs(_job_path(launcher)[0])
    assert [j.op for j in jobs] == ["update", "vjoy_setup"]
    _, results = _job_path(launcher)
    drivers.write_results(
        results,
        [
            drivers.JobResult("done", "vJoy is updated."),
            drivers.JobResult("done", "Set up.", lost=[V4], added=[]),
        ],
        True,
    )
    _pump(qapp, lambda: bool(done))
    assert model.lostText() == drivers.lost_text([V4])
    model._timer.stop()


def test_update_and_set_up_run_reporting_none_shows_no_lost_box(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _update_model(app, tmp_path, launcher)
    model.addDevice()
    done: list[bool] = []
    model.finished.connect(lambda: done.append(True))
    assert model.apply()
    _, results = _job_path(launcher)
    drivers.write_results(
        results,
        [
            drivers.JobResult("done", "vJoy is updated."),
            drivers.JobResult("done", "Set up.", lost=[], added=[]),
        ],
        True,
    )
    _pump(qapp, lambda: bool(done))
    assert model.lostText() == ""
    model._timer.stop()


def test_reading_the_current_devices_prunes_the_remembered_lost_ones(
    app: Path, tmp_path: Path
) -> None:
    calls: list[list[drivers.VJoyDevice]] = []
    remembered = [V2]
    model = _model(
        app,
        tmp_path,
        [_status("vjoy", "2.2.2.0", "same")],
        current=[V2],
        lost_reader=lambda: list(remembered),
        lost_pruner=lambda cur: (calls.append(cur), remembered.clear()),
    )
    assert calls == [[V2]]
    assert model.vjoyLost == []
    model._timer.stop()


def test_remembered_lost_devices_show_as_rows_with_repair(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    v1 = drivers.new_device(1)
    model = _model(
        app,
        tmp_path,
        [_status("vjoy", "2.2.2.0", "same")],
        current=[v1],
        launcher=launcher,
        # vJoy 1 is back as it was: not a lost row; vJoy 2 is.
        lost_reader=lambda: [v1, V2],
    )
    assert model.vjoyLost == [
        {
            "id": 2,
            "axes": ["x", "y", "z"],
            "buttons": 32,
            "hats": 0,
            "summary": model.deviceSummary(["x", "y", "z"], 32, 0),
        }
    ]
    # The editable list is what vJoy has now; the lost row isn't in it.
    assert [d["id"] for d in model.vjoyDevices] == [1]
    assert not model.repairDevice(9)
    assert model.repairDevice(2)
    jobs = drivers.read_jobs(_job_path(launcher)[0])
    assert [(j.op, j.devices) for j in jobs] == [("vjoy_restore", [V2])]
    assert not model.repairDevice(2)  # busy: one run at a time
    model._timer.stop()


def test_a_restore_reads_as_putting_back(
    qapp: object, app: Path, tmp_path: Path
) -> None:
    launcher = Launcher()
    model = _model(
        app,
        tmp_path,
        [_status("vjoy", "2.2.2.0", "same")],
        launcher=launcher,
        lost_reader=lambda: [V2],
    )
    done: list[bool] = []
    model.finished.connect(lambda: done.append(True))
    assert model.repairDevice(2)
    _, results = _job_path(launcher)
    drivers.write_results(results, [drivers.JobResult("running")], False)
    _pump(qapp, lambda: model.progress == "Putting back the vJoy devices…")
    drivers.write_results(
        results, [drivers.JobResult("done", "1 device put back.")], True
    )
    _pump(qapp, lambda: bool(done))
    assert model.results == [
        {"driver": "vJoy devices", "state": "done", "message": "1 device put back."}
    ]
