# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Tools › Drivers (06 S185-S188): the driver rows, the vJoy device layout,
and the jobs sent to Gremlin Device Helper (12 S25, S25a).

The helper is started once, elevated, with a job file and a results file in
%TEMP%; a main-thread timer reads the results file until the helper says it
has finished (at most 30 minutes). The HidHide update comes in two halves
(06 S186): Apply removes the old one and leaves pending.json for
finishHidHide(), which installs the new one after the restart.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock, drivers, threads
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

_log = logging.getLogger("system")

HELPER_EXE = "Gremlin Device Helper.exe"
CUSTOM = "Custom"
DEFAULT_PRESET = "1 device, full"
VJOY_WARNING = "Running games will lose the vJoy devices until they restart."
POLL_MS = 500
GIVE_UP_SECONDS = 30 * 60

NOT_INSTALLED = "not installed"
GAVE_UP_TEXT = "Gremlin Device Helper did not finish within 30 minutes."
ENDED_TEXT = "Gremlin Device Helper ended before it finished."
REFUSED_TEXT = "Administrator permission was refused."
NO_APP_TEXT = "Drivers can be installed only from the installed program."
WAITING_TEXT = "Waiting for Gremlin Device Helper…"

MAX_DEVICES = 16


class Process(Protocol):
    """The started helper (device_disable's elevated process handle)."""

    def running(self) -> bool: ...

    def close(self) -> None: ...


class RealCallBlocked(RuntimeError):
    """A real elevation or Windows restart from a test."""


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


def _real_launcher(file: str, parameters: str) -> Process:
    """Starts the helper elevated ("runas"); the process handle has
    running() and close(). Raises device_disable.Refused when declined."""
    if _under_test():
        raise RealCallBlocked("drivers_model elevation called from a test")
    from gremlin import device_disable

    return device_disable._real_launcher(file, parameters)


def _real_restart() -> None:
    if _under_test():
        raise RealCallBlocked("drivers_model Windows restart called from a test")
    subprocess.Popen(["shutdown.exe", "/r", "/t", "0"], close_fds=True)


def _real_vjoy_reader() -> list[drivers.VJoyDevice]:
    from gremlin import driver_jobs

    return driver_jobs.current_vjoy_devices(driver_jobs.real_runner)


def _real_background(
    name: str, work: Callable[[], Any], done: Callable[[Any], None]
) -> None:
    """work() on a named thread, done(result) back on the main thread."""

    def run() -> None:
        try:
            result = work()
        except Exception as exc:
            _log.warning(f"{name} failed: {exc}")
            result = None
        threads.main_call(done, result)

    threads.start(name, run)


def _device_map(device: drivers.VJoyDevice) -> dict:
    return {
        "id": device.id,
        "axes": device.axes,
        "buttons": device.buttons,
        "hats": device.hats,
    }


def _layout(devices: list[drivers.VJoyDevice]) -> list[tuple[int, int, int]]:
    return [(d.axes, d.buttons, d.hats) for d in devices]


def _clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, int(value)))


def label_for(status: drivers.DriverStatus) -> str:
    """The row's version text (01 S187)."""
    if status.state == "missing":
        return NOT_INSTALLED
    if status.state == "older":
        return f"update available: {status.installed} → {status.bundled}"
    return status.installed


@ta.QmlElement
class DriversModel(QtCore.QObject):
    """Tools › Drivers: what is installed, what Apply will do, and the
    helper's progress and results."""

    changed = QtCore.Signal()
    finished = QtCore.Signal()

    def __init__(
        self,
        parent: ta.OQO = None,
        *,
        status_source: Callable[[], list[drivers.DriverStatus]] | None = None,
        app: Callable[[], Path | None] | None = None,
        launcher: Callable[[str, str], Process] | None = None,
        results_reader: Callable[[Path], tuple[list, bool]] | None = None,
        vjoy_reader: Callable[[], list[drivers.VJoyDevice]] | None = None,
        background: Callable[..., None] | None = None,
        restarter: Callable[[], None] | None = None,
        monotonic: Callable[[], float] | None = None,
        temp_dir: Path | None = None,
        poll_ms: int = POLL_MS,
    ) -> None:
        super().__init__(parent)
        self._status_source = status_source or drivers.all_status
        self._app = app or drivers.app_dir
        self._launcher = launcher or _real_launcher
        self._results_reader = results_reader or drivers.read_results
        self._vjoy_reader = vjoy_reader or _real_vjoy_reader
        self._background = background or _real_background
        self._restarter = restarter or _real_restart
        self._monotonic = monotonic or clock.monotonic
        self._temp_dir = temp_dir
        self._statuses: list[drivers.DriverStatus] = []
        self._ticked: dict[str, bool] = {}
        self._preset = DEFAULT_PRESET
        self._devices = self._preset_devices(DEFAULT_PRESET)
        self._current: list[drivers.VJoyDevice] = []
        self._user_edited = False
        self._busy = False
        self._progress = ""
        self._results: list[dict] = []
        self._restart_needed = False
        self._pending: dict | None = None
        # The run in progress.
        self._jobs: list[drivers.Job] = []
        self._results_path: Path | None = None
        self._process: Process | None = None
        self._started_at = 0.0
        self._hidhide_step = ""  # "remove" (step 1) or "install" (step 2)
        self._hidhide_new: dict | None = None
        self._runs = 0
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(poll_ms)
        self._timer.timeout.connect(self._poll)
        self.reload()

    # -- reading what is there ---------------------------------------------

    @QtCore.Slot()
    def reload(self) -> None:
        try:
            self._statuses = list(self._status_source())
        except Exception as exc:
            _log.warning(f"Driver status could not be read: {exc}")
            self._statuses = []
        ticked = {}
        for status in self._statuses:
            if status.state in ("missing", "older"):
                # Missing ticked, older unticked (01 S187); a reload keeps
                # what the user chose.
                ticked[status.key] = self._ticked.get(
                    status.key, status.state == "missing"
                )
        self._ticked = ticked
        self._read_pending()
        vjoy = self._status("vjoy")
        if vjoy is not None and vjoy.state != "missing":
            self._background("vJoy layout read", self._vjoy_reader, self._got_current)
        else:
            self._got_current([])
        self.changed.emit()

    def _got_current(self, devices: list[drivers.VJoyDevice] | None) -> None:
        self._current = list(devices or [])
        # What exists is shown as it is and changed only when edited (S185).
        if self._current and not self._user_edited:
            self._devices = [
                drivers.VJoyDevice(**_device_map(d)) for d in self._current
            ]
            self._preset = self._matching_preset()
        self.changed.emit()

    def _read_pending(self) -> None:
        app = self._app()
        try:
            self._pending = drivers.read_pending(app) if app else None
        except Exception as exc:
            _log.warning(f"pending.json could not be read: {exc}")
            self._pending = None

    def _status(self, key: str) -> drivers.DriverStatus | None:
        return next((s for s in self._statuses if s.key == key), None)

    # -- the vJoy layout ---------------------------------------------------

    @staticmethod
    def _preset_devices(name: str) -> list[drivers.VJoyDevice]:
        return [drivers.VJoyDevice(**_device_map(d)) for d in drivers.PRESETS[name]]

    def _matching_preset(self) -> str:
        for name, devices in drivers.PRESETS.items():
            if _layout(devices) == _layout(self._devices):
                return name
        return CUSTOM

    def _edited(self) -> None:
        self._user_edited = True
        if self._preset != CUSTOM:
            self._preset = self._matching_preset()
        self.changed.emit()

    @QtCore.Slot(str)
    def setPreset(self, name: str) -> None:
        if name == CUSTOM:
            self._preset = CUSTOM
            self.changed.emit()
            return
        if name not in drivers.PRESETS:
            return
        self._devices = self._preset_devices(name)
        self._preset = name
        self._edited()

    @QtCore.Slot(int)
    def setDeviceCount(self, n: int) -> None:
        n = _clamp(n, 1, MAX_DEVICES)
        devices = self._devices[:n]
        while len(devices) < n:
            # The lowest free id: vJoy can have gaps (devices 1 and 3).
            used = {d.id for d in devices}
            free = next(i for i in range(1, MAX_DEVICES + 1) if i not in used)
            devices.append(drivers.VJoyDevice(id=free))
        self._devices = devices
        self._preset = CUSTOM
        self._edited()

    @QtCore.Slot(int, int, int, int)
    def setDevice(self, index: int, axes: int, buttons: int, hats: int) -> None:
        if not 0 <= index < len(self._devices):
            return
        self._devices[index] = drivers.VJoyDevice(
            id=self._devices[index].id,
            axes=_clamp(axes, 0, 8),
            buttons=_clamp(buttons, 0, 128),
            hats=_clamp(hats, 0, 4),
        )
        self._preset = CUSTOM
        self._edited()

    def _vjoy_edited(self) -> bool:
        if not self._user_edited:
            return False
        if self._current:
            return _layout(self._current) != _layout(self._devices)
        return True

    def _deleted_ids(self) -> list[int]:
        """vJoy devices that exist now and are not in the chosen layout; the
        helper deletes them (12 S25b). A deletion counts as an edit."""
        if not self._vjoy_edited():
            return []
        wanted = {d.id for d in self._devices}
        return [d.id for d in self._current if d.id not in wanted]

    @QtCore.Slot(str, bool)
    def setTicked(self, key: str, on: bool) -> None:
        if key in self._ticked:
            self._ticked[key] = bool(on)
            self.changed.emit()

    # -- the jobs ----------------------------------------------------------

    def _bundled(self, app: Path, key: str) -> list[dict]:
        info = drivers.DRIVERS[key]
        return [{"path": str(app / "drivers" / info.bundled_file), "kind": "bundled"}]

    def _plan(self, app: Path) -> list[drivers.Job]:
        """The jobs Apply sends, in order: each ticked driver, the vJoy
        device setup right after vJoy."""
        jobs: list[drivers.Job] = []
        vjoy = self._status("vjoy")
        vjoy_new = False
        for status in self._statuses:
            if not self._ticked.get(status.key):
                continue
            if status.state == "missing":
                jobs.append(
                    drivers.Job(
                        "install", status.key, self._bundled(app, status.key), []
                    )
                )
                vjoy_new = vjoy_new or status.key == "vjoy"
            elif status.key == "hidhide":
                jobs.append(drivers.Job("remove", "hidhide", [], []))
            else:
                jobs.append(
                    drivers.Job(
                        "update", status.key, self._bundled(app, status.key), []
                    )
                )
            if status.key == "vjoy":
                if self._vjoy_edited() or (vjoy_new and not self._current):
                    jobs.append(self._setup_job())
        vjoy_ticked = any(j.driver == "vjoy" for j in jobs)
        if (
            not vjoy_ticked
            and self._vjoy_edited()
            and vjoy is not None
            and vjoy.state != "missing"
        ):
            jobs.insert(0, self._setup_job())
        return jobs

    def _setup_job(self) -> drivers.Job:
        devices = [drivers.VJoyDevice(**_device_map(d)) for d in self._devices]
        return drivers.Job("vjoy_setup", "vjoy", [], devices)

    def _step_text(self, job: drivers.Job) -> str:
        status = self._status(job.driver)
        info = drivers.DRIVERS[job.driver]
        old = status.installed if status else ""
        if job.op == "install":
            if job.driver == "hidhide" and self._hidhide_new:
                return f"Install HidHide {self._hidhide_new['version']}"
            return f"Install {info.name} {info.bundled_version}"
        if job.op == "update":
            return f"Update {info.name} {old} to {info.bundled_version}"
        if job.op == "remove":
            return f"Remove HidHide {old}"
        count = len(job.devices)
        return f"Set up {count} vJoy device{'s' if count != 1 else ''}"

    def _progress_text(self, job: drivers.Job) -> str:
        status = self._status(job.driver)
        info = drivers.DRIVERS[job.driver]
        if job.op == "install":
            version = info.bundled_version
            if job.driver == "hidhide" and self._hidhide_new:
                version = self._hidhide_new["version"]
            return f"Installing {info.name} {version}…"
        if job.op == "update":
            return f"Updating {info.name} to {info.bundled_version}…"
        if job.op == "remove":
            return f"Removing HidHide {status.installed if status else ''}…"
        return "Setting up the vJoy devices…"

    def _result_name(self, job: drivers.Job) -> str:
        if job.op == "vjoy_setup":
            return "vJoy devices"
        return drivers.DRIVERS[job.driver].name

    @QtCore.Slot(result=str)
    def describe(self) -> str:
        """The prompt before Apply (06 S187): what will happen, in what
        order, the one administrator prompt and any restart."""
        app = self._app() or Path(".")
        jobs = self._plan(app)
        if not jobs:
            return ""
        lines = ["The program will do these steps, in this order:"]
        for number, job in enumerate(jobs, 1):
            lines.append(f"{number}. {self._step_text(job)}.")
        lines.append("")
        lines.append(
            "Windows asks for administrator permission once, before the first step."
        )
        if any(j.op == "vjoy_setup" for j in jobs):
            for device_id in self._deleted_ids():
                lines.append(f"vJoy device {device_id} will be deleted.")
        if any(j.op == "remove" for j in jobs):
            new = drivers.DRIVERS["hidhide"].bundled_version
            lines.append(
                "HidHide update, step 1 of 2: a restart follows. After it, the "
                f"program installs HidHide {new} and asks for one more restart. "
                "Devices aren't hidden until then."
            )
        else:
            lines.append(
                "If a driver needs a restart, you are told when the steps end."
            )
        if self._vjoy_edited() and self._current:
            lines.append(VJOY_WARNING)
        return "\n".join(lines)

    @QtCore.Slot(result=bool)
    def apply(self) -> bool:
        if self._busy:
            return False
        app = self._app()
        if app is None:
            self._set_progress(NO_APP_TEXT)
            return False
        jobs = self._plan(app)
        if not jobs:
            return False
        self._hidhide_step = "remove" if any(j.op == "remove" for j in jobs) else ""
        self._hidhide_new = None
        return self._start(app, jobs)

    @QtCore.Slot(result=bool)
    def finishHidHide(self) -> bool:
        """Step 2 of the HidHide update (06 S186): install from pending.json."""
        if self._busy:
            return False
        app = self._app()
        self._read_pending()
        entry = (self._pending or {}).get("hidhide")
        if app is None or not entry:
            self.changed.emit()
            return False
        self._hidhide_step = "install"
        self._hidhide_new = dict(entry)
        files = [{"path": entry["file"], "kind": entry.get("kind", "bundled")}]
        return self._start(app, [drivers.Job("install", "hidhide", files, [])])

    @QtCore.Slot()
    def laterHidHide(self) -> None:
        """Step 2 put off: pending.json stays, Home keeps its line."""
        _log.info("HidHide update step 2 put off")

    @QtCore.Slot()
    def restartNow(self) -> None:
        try:
            self._restarter()
        except RealCallBlocked:
            raise
        except Exception as exc:
            _log.warning(f"Windows restart failed: {exc}")

    def _start(self, app: Path, jobs: list[drivers.Job]) -> bool:
        self._runs += 1
        folder = self._temp_dir or Path(tempfile.gettempdir())
        stem = f"gremlin-driver-jobs-{os.getpid()}-{self._runs}"
        jobs_path = folder / f"{stem}.json"
        results_path = folder / f"{stem}-results.json"
        try:
            results_path.unlink(missing_ok=True)
            drivers.write_jobs(jobs_path, jobs)
        except OSError as exc:
            self._set_progress(f"The job file could not be written: {exc}")
            return False
        helper = str(app / HELPER_EXE)
        params = (
            f'--jobs "{jobs_path}" --results "{results_path}" --parent {os.getpid()}'
        )
        try:
            self._process = self._launcher(helper, params)
        except RealCallBlocked:
            raise
        except Exception as exc:
            from gremlin import device_disable

            refused = isinstance(exc, device_disable.Refused)
            self._set_progress(
                REFUSED_TEXT
                if refused
                else f"Gremlin Device Helper did not start: {exc}"
            )
            return False
        self._jobs = jobs
        self._results_path = results_path
        self._results = []
        self._restart_needed = False
        self._busy = True
        self._progress = WAITING_TEXT
        self._started_at = self._monotonic()
        self._timer.start()
        self.changed.emit()
        return True

    def _poll(self) -> None:
        if not self._busy or self._results_path is None:
            self._timer.stop()
            return
        results, done = self._read_results()
        if done:
            self._finish(results, "")
            return
        running = next((i for i, r in enumerate(results) if r.state == "running"), None)
        text = (
            self._progress_text(self._jobs[running])
            if running is not None and running < len(self._jobs)
            else WAITING_TEXT
        )
        if text != self._progress:
            self._progress = text
            self.changed.emit()
        process = self._process
        if (
            process is not None
            and hasattr(process, "running")
            and not process.running()
        ):
            # Ended: one last read, it may have finished just now.
            results, done = self._read_results()
            self._finish(results, "" if done else ENDED_TEXT)
            return
        if self._monotonic() - self._started_at > GIVE_UP_SECONDS:
            self._finish(results, GAVE_UP_TEXT)

    def _read_results(self) -> tuple[list, bool]:
        if self._results_path is None:
            return [], False
        try:
            return self._results_reader(self._results_path)
        except Exception as exc:
            _log.warning(f"Driver results could not be read: {exc}")
            return [], False

    def _finish(self, results: list, problem: str) -> None:
        self._timer.stop()
        if self._process is not None and hasattr(self._process, "close"):
            try:
                self._process.close()
            except Exception:
                pass
        self._process = None
        rows = []
        restart = False
        for index, job in enumerate(self._jobs):
            result = results[index] if index < len(results) else None
            state = result.state if result else "failed"
            if state not in ("done", "failed"):
                state = "failed"
            message = (result.message if result else "") or problem
            if not message:
                message = "Done." if state == "done" else "Failed."
            rows.append(
                {"driver": self._result_name(job), "state": state, "message": message}
            )
            restart = restart or bool(result and result.restart)
            if job.driver == "hidhide" and state == "done":
                restart = self._hidhide_done(job) or restart
        self._results = rows
        self._restart_needed = restart
        self._busy = False
        self._progress = problem
        self._jobs = []
        self._results_path = None
        self._hidhide_step = ""
        self.reload()
        self.finished.emit()

    def _hidhide_done(self, job: drivers.Job) -> bool:
        """The two halves of the HidHide update; True: a restart is needed."""
        app = self._app()
        if app is None:
            return False
        try:
            if job.op == "remove":
                info = drivers.DRIVERS["hidhide"]
                drivers.write_pending(
                    app,
                    {
                        "hidhide": {
                            "version": info.bundled_version,
                            "file": self._bundled(app, "hidhide")[0]["path"],
                            "kind": "bundled",
                        }
                    },
                )
                return True
            if job.op == "install" and self._hidhide_step == "install":
                drivers.clear_pending(app)
                return True
        except OSError as exc:
            _log.warning(f"pending.json could not be written: {exc}")
        return False

    def _set_progress(self, text: str) -> None:
        self._progress = text
        self.changed.emit()

    # -- properties ----------------------------------------------------------

    def _get_rows(self) -> list:
        return [
            {
                "key": s.key,
                "name": s.name,
                "installed": s.installed,
                "bundled": s.bundled,
                "state": s.state,
                "label": label_for(s),
                "ticked": bool(self._ticked.get(s.key, False)),
                "tickable": s.key in self._ticked,
            }
            for s in self._statuses
        ]

    def _get_presets(self) -> list:
        return [*drivers.PRESETS.keys(), CUSTOM]

    def _get_preset(self) -> str:
        return self._preset

    def _get_devices(self) -> list:
        return [_device_map(d) for d in self._devices]

    def _get_current(self) -> list:
        return [_device_map(d) for d in self._current]

    def _get_edited(self) -> bool:
        return self._vjoy_edited()

    def _get_warning(self) -> str:
        return VJOY_WARNING if self._vjoy_edited() and self._current else ""

    def _get_busy(self) -> bool:
        return self._busy

    def _get_progress(self) -> str:
        return self._progress

    def _get_results(self) -> list:
        return list(self._results)

    def _get_restart(self) -> bool:
        return self._restart_needed

    def _get_pending(self) -> bool:
        return bool((self._pending or {}).get("hidhide"))

    def _get_pending_version(self) -> str:
        return str(((self._pending or {}).get("hidhide") or {}).get("version", ""))

    rows = QtCore.Property(list, fget=_get_rows, notify=changed)
    presets = QtCore.Property(list, fget=_get_presets, notify=changed)
    vjoyPreset = QtCore.Property(str, fget=_get_preset, notify=changed)
    vjoyDevices = QtCore.Property(list, fget=_get_devices, notify=changed)
    vjoyCurrent = QtCore.Property(list, fget=_get_current, notify=changed)
    vjoyEdited = QtCore.Property(bool, fget=_get_edited, notify=changed)
    vjoyWarning = QtCore.Property(str, fget=_get_warning, notify=changed)
    busy = QtCore.Property(bool, fget=_get_busy, notify=changed)
    progress = QtCore.Property(str, fget=_get_progress, notify=changed)
    results = QtCore.Property(list, fget=_get_results, notify=changed)
    restartNeeded = QtCore.Property(bool, fget=_get_restart, notify=changed)
    pendingHidHide = QtCore.Property(bool, fget=_get_pending, notify=changed)
    pendingVersion = QtCore.Property(str, fget=_get_pending_version, notify=changed)
