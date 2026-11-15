# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Screen Saver Mode window's model (12 S1-S19): its four settings
(stored in the program's settings, so History records them, S10), the
status line read from screen_saver_mode.manager() once a second while the
window is open (with what last reset the idle time, S18, and the full-screen
program, S19), and the three checks (Refresh Devices, Refresh Programs,
Refresh System; S12, S13, S17) and the Ignore switches (programs, drivers
and services, S14), run on program threads. Programs and System each run
their own elevated check and keep their own half (power_requests.split).
Button presses and every message shown go to the Screen Saver Mode trace
(S16); failures also go to the normal log."""

from __future__ import annotations

import logging
import time
import types
from typing import Any, Callable

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import config
from gremlin.signal import signal
from gremlin.types import PropertyType
from gremlin.ui.device import QML_IMPORT_MAJOR_VERSION, QML_IMPORT_NAME

assert QML_IMPORT_NAME == "Gremlin.Device"
assert QML_IMPORT_MAJOR_VERSION == 1

SECTION = "global"
GROUP = "screen-saver-mode"
ENABLED = "enabled"
ACTION = "action"
WAIT = "wait-override-s"
HOLD_FULLSCREEN = "hold-fullscreen"

ACTION_SCREEN_SAVER = "screen_saver"
ACTION_POWER_OFF = "power_off"
_ACTIONS = (ACTION_SCREEN_SAVER, ACTION_POWER_OFF)

# The longest wait that can be typed (minutes) and stored (seconds).
MAX_WAIT_MIN = 999
_MAX_WAIT_S = 86400

SCAN_SECONDS = 4.0

_log = logging.getLogger("system")

# powercfg's kinds of request (ProgramRequest.kind) and the word shown after
# a driver's or service's name.
KIND_PROCESS = "PROCESS"
_KIND_WORDS = {"DRIVER": "driver", "SERVICE": "service"}


def _trace(text: str) -> None:
    """One Screen Saver Mode trace line (S16); a no-op while tracing is off
    or before gremlin.trace has the Screen Saver Mode tick."""
    try:
        from gremlin import trace

        write = getattr(trace, "screen_saver", None)
        if write is not None:
            write(text)
    except Exception:
        _log.exception("Screen Saver Mode: the trace line could not be written")


def register_options() -> None:
    """The four settings (01 S6: registered before the purge). Exposed for
    History; Options leaves them out (the window has the controls)."""
    cfg = config.Configuration()
    cfg.register(
        SECTION,
        GROUP,
        ENABLED,
        PropertyType.Bool,
        False,
        "Screen Saver Mode: keep the program's own idle time from the keyboard and "
        "mouse only, and start the screen saver or power off the displays when "
        "it runs out.",
        {},
        True,
    )
    cfg.register(
        SECTION,
        GROUP,
        ACTION,
        PropertyType.String,
        ACTION_POWER_OFF,
        "Screen Saver Mode's action: Screen saver or Power off displays.",
        {},
        True,
    )
    cfg.register(
        SECTION,
        GROUP,
        WAIT,
        PropertyType.Int,
        0,
        "Screen Saver Mode's wait time in seconds; 0 uses Windows' time.",
        {"min": 0, "max": _MAX_WAIT_S},
        True,
    )
    cfg.register(
        SECTION,
        GROUP,
        HOLD_FULLSCREEN,
        PropertyType.Bool,
        True,
        "Screen Saver Mode: hold off during full-screen programs.",
        {},
        True,
    )


def _ensure_options() -> None:
    cfg = config.Configuration()
    if not all(
        cfg.exists(SECTION, GROUP, n) for n in (ENABLED, ACTION, WAIT, HOLD_FULLSCREEN)
    ):
        register_options()


def _value(name: str) -> Any:  # noqa: ANN401 - a setting of any type
    _ensure_options()
    return config.Configuration().value(SECTION, GROUP, name)


def _set(name: str, value: object) -> None:
    _ensure_options()
    config.Configuration().set(SECTION, GROUP, name, value)


def saved_action() -> str:
    action = str(_value(ACTION) or "")
    return action if action in _ACTIONS else ACTION_POWER_OFF


def saved_wait_s() -> int:
    try:
        return min(_MAX_WAIT_S, max(0, int(_value(WAIT) or 0)))
    except (TypeError, ValueError):
        return 0


def _core() -> types.ModuleType:
    from gremlin import screen_saver_mode

    return screen_saver_mode


def saved_settings() -> object:
    """The saved settings as screen_saver_mode.Settings."""
    return _core().Settings(
        enabled=bool(_value(ENABLED)),
        action=saved_action(),
        wait_override_s=saved_wait_s(),
        hold_fullscreen=bool(_value(HOLD_FULLSCREEN)),
    )


def apply_saved() -> None:
    """Hands the saved settings to the one Screen Saver Mode (at start,
    after a change in the window, after History puts settings back)."""
    try:
        core = _core()
        wanted = saved_settings()
        manager = core.manager()
        if manager.settings() != wanted:
            manager.apply(wanted)
    except Exception:
        _log.exception("Screen Saver Mode: could not apply the settings")


_following = False


def start() -> None:
    """At program start: apply the saved settings and follow changes made
    outside the window (History's Restore sends configChanged)."""
    global _following
    apply_saved()
    if not _following:
        signal.configChanged.connect(apply_saved)
        _following = True


def shutdown() -> None:
    """At quit: only a Screen Saver Mode that was loaded."""
    import sys

    global _following
    if _following:
        try:
            signal.configChanged.disconnect(apply_saved)
        except (RuntimeError, TypeError):
            pass
        _following = False
    core = sys.modules.get("gremlin.screen_saver_mode")
    if core is not None:
        core.manager().shutdown()


def duration_text(seconds: float) -> str:
    """'45 s', '2 min 41 s', '5 min', '1 h 30 min'."""
    s = max(0, int(seconds))
    if s < 60:
        return f"{s} s"
    if s < 3600:
        m, rest = divmod(s, 60)
        return f"{m} min {rest} s" if rest else f"{m} min"
    h, rest = divmod(s, 3600)
    m = rest // 60
    return f"{h} h {m} min" if m else f"{h} h"


def _clock_text() -> str:
    return time.strftime("%H:%M")


def _hold_text(status: object) -> str:
    hold = str(getattr(status, "hold", "") or "")
    if hold == "display_request":
        who = str(getattr(status, "hold_program", "") or "")
        return (
            "On hold: a program is keeping the display on"
            + (f" ({who})" if who else "")
            + ". The countdown starts again when it stops."
        )
    if hold == "fullscreen":
        who = str(getattr(status, "hold_program", "") or "")
        return (
            "On hold: a full-screen program is in front"
            + (f" ({who})" if who else "")
            + ". The countdown starts again when it ends."
        )
    if hold == "locked":
        return (
            "On hold: the PC is locked. Windows looks after the screens "
            "while it is locked."
        )
    return ""


def _last_reset_text(status: object) -> str:
    """S18: what last reset Gremlin's idle time; "" before the first input."""
    kind = str(getattr(status, "last_reset_kind", "") or "")
    if kind == "program":
        rate = int(getattr(status, "program_input_per_min", 0) or 0)
        if rate > 0:
            times = "once a minute" if rate == 1 else f"{rate} times a minute"
            return f"last reset by: input sent by a program, {times}"
        return "last reset by: input sent by a program, " + _ago(status)
    if kind in ("keyboard", "mouse"):
        name = str(getattr(status, "last_reset_by", "") or "").strip()
        who = f"{name} ({kind})" if name else f"a {kind}"
        return f"last reset by: {who}, " + _ago(status)
    return ""


def _ago(status: object) -> str:
    age = float(getattr(status, "last_reset_age_s", 0.0) or 0.0)
    return "just now" if age < 2 else f"{duration_text(age)} ago"


def _program_row(p: object) -> dict:
    """A Refresh Programs / Refresh System row for the window: the name, its
    kind (a driver's or service's word shown after the name), the detail
    line and whether it also keeps the PC awake (Programs rows)."""
    kind = str(getattr(p, "kind", "") or KIND_PROCESS).upper()
    return {
        "name": str(getattr(p, "name", "")),
        "path": str(getattr(p, "path", "") or ""),
        "kinds": ", ".join(str(k) for k in (getattr(p, "kinds", None) or [])),
        "ignored": bool(getattr(p, "ignored", False)),
        "kind": kind,
        "kindWord": _KIND_WORDS.get(kind, ""),
        "detail": str(getattr(p, "detail", "") or "").strip(),
        "alsoAwake": bool(getattr(p, "also_awake", False)),
    }


# The two elevated lists (S13, S17): which half of power_requests.split()
# each keeps, and its words.
PROGRAMS = "programs"
SYSTEM = "system"
_LISTS = {
    PROGRAMS: {
        "half": 0,
        "button": "Refresh Programs",
        "what": "programs",
        "kept": "ignored programs no longer keep the display on.",
        "none": "No program is asking Windows to keep the display on.",
        "ignored": "it no longer keeps the display on.",
    },
    SYSTEM: {
        "half": 1,
        "button": "Refresh System",
        "what": "system",
        "kept": "ignored ones no longer keep the PC awake.",
        "none": "Nothing is asking Windows to keep the PC awake.",
        "ignored": "it no longer keeps the PC awake.",
    },
}


def _problem_text(problem: str, action: str) -> str:
    if problem == "no_screen_saver":
        return "No screen saver is chosen in Windows."
    if problem == "windows_never":
        if action == ACTION_SCREEN_SAVER:
            return (
                "Windows never starts the screen saver: type a time to use "
                "Screen Saver Mode."
            )
        return (
            "Windows never turns the display off: type a time to use Screen Saver Mode."
        )
    if problem == "not_listening":
        return (
            "The keyboard and mouse can't be listened to, so Screen Saver Mode "
            "does nothing."
        )
    return ""


@ta.QmlElement
class ScreenSaverModeModel(QtCore.QObject):
    """The Screen Saver Mode window: settings, status and the two checks."""

    settingsChanged = QtCore.Signal()
    statusChanged = QtCore.Signal()
    devicesChanged = QtCore.Signal()
    programsChanged = QtCore.Signal()
    systemChanged = QtCore.Signal()
    busyChanged = QtCore.Signal()

    # Worker results, queued to the main thread.
    _devicesDone = QtCore.Signal(object)
    _requestsDone = QtCore.Signal(str, object)
    _ignoreDone = QtCore.Signal(str, str, bool, bool, str)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        _ensure_options()
        self._status: Any = None
        self._devices: list[dict] = []
        self._devices_message = ""
        self._rows: dict[str, list[dict]] = {PROGRAMS: [], SYSTEM: []}
        self._messages: dict[str, str] = {PROGRAMS: "", SYSTEM: ""}
        self._scanning: dict[str, bool] = {PROGRAMS: False, SYSTEM: False}
        self._scanning_devices = False
        self._pending_ignore = ""
        self._shown_problem = ""
        self._stop = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refreshStatus)
        Queued = QtCore.Qt.ConnectionType.QueuedConnection
        self._devicesDone.connect(self._take_devices, Queued)
        self._requestsDone.connect(self._take_requests, Queued)
        self._ignoreDone.connect(self._take_ignore, Queued)
        signal.configChanged.connect(self._on_config)

    # Settings ---------------------------------------------------------------

    @QtCore.Slot()
    def _on_config(self) -> None:
        self.settingsChanged.emit()
        self.refreshStatus()

    def _changed(self) -> None:
        apply_saved()
        self.settingsChanged.emit()
        self.refreshStatus()

    @QtCore.Property(bool, notify=settingsChanged)
    def enabled(self) -> bool:
        return bool(_value(ENABLED))

    @QtCore.Slot(bool)
    def setEnabled(self, on: bool) -> None:
        if bool(on) != self.enabled:
            _set(ENABLED, bool(on))
            self._changed()

    @QtCore.Property(str, notify=settingsChanged)
    def action(self) -> str:
        return saved_action()

    @QtCore.Slot(str)
    def setAction(self, action: str) -> None:
        action = str(action)
        if action in _ACTIONS and action != self.action:
            _set(ACTION, action)
            self._changed()

    @QtCore.Property(bool, notify=settingsChanged)
    def holdFullscreen(self) -> bool:
        return bool(_value(HOLD_FULLSCREEN))

    @QtCore.Slot(bool)
    def setHoldFullscreen(self, on: bool) -> None:
        if bool(on) != self.holdFullscreen:
            _set(HOLD_FULLSCREEN, bool(on))
            self._changed()

    @QtCore.Property(int, notify=settingsChanged)
    def waitOverrideS(self) -> int:
        return saved_wait_s()

    @QtCore.Property(str, notify=settingsChanged)
    def waitText(self) -> str:
        """The typed time in minutes as the box shows it, "" when none
        (Windows' time is used and shown greyed)."""
        s = saved_wait_s()
        if not s:
            return ""
        return str(s // 60) if s % 60 == 0 else f"{s / 60:g}"

    @QtCore.Slot(str, result=bool)
    def setWaitText(self, text: str) -> bool:
        """A typed time in minutes ("10", "10 min", "2.5"); "" clears it.
        False for text that isn't a time (nothing is changed)."""
        raw = str(text or "").strip().lower()
        if raw.endswith("min"):
            raw = raw[:-3].strip()
        if not raw:
            seconds = 0
        else:
            try:
                minutes = float(raw.replace(",", "."))
            except ValueError:
                return False
            if not (0 < minutes <= MAX_WAIT_MIN):
                return False
            seconds = max(1, round(minutes * 60))
        if seconds != saved_wait_s():
            _set(WAIT, int(seconds))
            self._changed()
        return True

    @QtCore.Slot()
    def clearWait(self) -> None:
        self.setWaitText("")

    @QtCore.Property(str, notify=statusChanged)
    def windowsWaitText(self) -> str:
        """Windows' time for the chosen action, for the greyed box: "5 min",
        or "Never"."""
        s = int(getattr(self._status, "windows_wait_s", 0) or 0)
        return duration_text(s) if s > 0 else "Never"

    @QtCore.Property(str, notify=statusChanged)
    def windowsWaitLabel(self) -> str:
        """The line next to the box, naming Windows' time it shows."""
        s = int(getattr(self._status, "windows_wait_s", 0) or 0)
        shown = duration_text(s) if s > 0 else "never"
        if self.action == ACTION_SCREEN_SAVER:
            return f"Windows' screen saver time ({shown})"
        return f"Windows' display-off time ({shown})"

    # Status -----------------------------------------------------------------

    @QtCore.Slot(bool)
    def setOpen(self, is_open: bool) -> None:
        """Polls the status once a second while the window is open."""
        if is_open:
            self.refreshStatus()
            self._timer.start()
        else:
            self._timer.stop()
            # A devices check still reading stops early.
            self._stop = True

    @QtCore.Slot()
    def refreshStatus(self) -> None:
        try:
            self._status = _core().manager().status()
        except Exception:
            _log.exception("Screen Saver Mode: status could not be read")
            self._status = None
        problem = self.problemText
        if problem != self._shown_problem:
            self._shown_problem = problem
            if problem:
                _trace(f"Message shown: {problem}")
        self.statusChanged.emit()

    def _st(self, name: str, default: object) -> Any:  # noqa: ANN401
        return (
            getattr(self._status, name, default)
            if self._status is not None
            else default
        )

    @QtCore.Property(bool, notify=statusChanged)
    def listening(self) -> bool:
        return bool(self._st("listening", False))

    @QtCore.Property(str, notify=statusChanged)
    def listeningText(self) -> str:
        if not self.enabled:
            return "Screen Saver Mode is off."
        if self.listening:
            return "Listening to the keyboard and mouse"
        return "Not listening to the keyboard and mouse"

    @QtCore.Property(str, notify=statusChanged)
    def idleText(self) -> str:
        return "Your idle time: " + duration_text(float(self._st("idle_s", 0.0) or 0.0))

    @QtCore.Property(str, notify=statusChanged)
    def lastResetText(self) -> str:
        """S18: "last reset by: …" next to the idle time."""
        if self._status is None:
            return ""
        return _last_reset_text(self._status)

    @QtCore.Property(str, notify=statusChanged)
    def windowsIdleText(self) -> str:
        win = float(self._st("windows_idle_s", 0.0) or 0.0)
        own = float(self._st("idle_s", 0.0) or 0.0)
        text = "Windows' idle time: " + duration_text(win)
        if self.enabled and own >= 10 and win < 2:
            text += " · devices are keeping Windows awake"
        return text

    @QtCore.Property(str, notify=statusChanged)
    def holdText(self) -> str:
        """On hold (S7, S11, S15), or the countdown, or done (S6)."""
        if not self.enabled or self._status is None:
            return ""
        held = _hold_text(self._status)
        if held:
            return held
        if self.problemText:
            return ""
        what = (
            "Screen saver"
            if self.action == ACTION_SCREEN_SAVER
            else "Power off displays"
        )
        if bool(self._st("fired", False)):
            return f"{what} done. Nothing more until the keyboard or mouse is used."
        remaining = float(self._st("remaining_s", 0.0) or 0.0)
        if remaining > 0:
            return f"{what} in {duration_text(remaining)}"
        return ""

    @QtCore.Property(bool, notify=statusChanged)
    def onHold(self) -> bool:
        return bool(self.enabled and self._st("hold", ""))

    @QtCore.Property(str, notify=statusChanged)
    def problemText(self) -> str:
        if not self.enabled:
            return ""
        return _problem_text(str(self._st("problem", "") or ""), saved_action())

    # Refresh Devices (S12) ---------------------------------------------------

    @QtCore.Property(bool, notify=busyChanged)
    def scanningDevices(self) -> bool:
        return self._scanning_devices

    @QtCore.Property(bool, notify=busyChanged)
    def scanningPrograms(self) -> bool:
        return self._scanning[PROGRAMS]

    @QtCore.Property(bool, notify=busyChanged)
    def scanningSystem(self) -> bool:
        return self._scanning[SYSTEM]

    @QtCore.Property(str, notify=busyChanged)
    def pendingIgnore(self) -> str:
        return self._pending_ignore

    @QtCore.Property(list, notify=devicesChanged)
    def devices(self) -> list:
        return list(self._devices)

    @QtCore.Property(str, notify=devicesChanged)
    def devicesMessage(self) -> str:
        return self._devices_message

    def _start(self, name: str, work: Callable[[], None]) -> bool:
        from gremlin import threads

        try:
            threads.start(name, work, stop=self._stop_work)
        except Exception:
            _log.exception(f"Screen Saver Mode: {name} could not start")
            return False
        return True

    def _stop_work(self, *_args: object) -> None:
        self._stop = True

    def _emit(self, sig: QtCore.SignalInstance, *args: object) -> None:
        try:
            sig.emit(*args)
        except RuntimeError:
            pass  # the window was closed

    @QtCore.Slot()
    def refreshDevices(self) -> None:
        if self._scanning_devices:
            _trace("Refresh Devices pressed: a check is already running")
            return
        _trace("Refresh Devices pressed")
        self._stop = False
        self._scanning_devices = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import hid_report_scan

                found = hid_report_scan.scan(SCAN_SECONDS, lambda: self._stop)
                result: Any = [
                    {
                        "name": str(d.name),
                        "instanceId": str(d.instance_id),
                        "rate": float(d.reports_per_s),
                    }
                    for d in found
                ]
            except Exception as exc:
                _log.exception("Screen Saver Mode: Refresh Devices failed")
                result = f"The devices couldn't be checked: {exc}"
            self._emit(self._devicesDone, result)

        if not self._start("Screen Saver Mode devices", work):
            self._take_devices("The devices check couldn't start.")

    @QtCore.Slot(object)
    def _take_devices(self, result: object) -> None:
        self._scanning_devices = False
        if isinstance(result, str):
            self._devices = []
            self._devices_message = result
            _log.warning(f"Screen Saver Mode: {result}")
        else:
            rows = result if isinstance(result, list) else []
            self._devices = sorted(rows, key=lambda d: -d["rate"])
            self._devices_message = (
                f"Checked {_clock_text()} · Screen Saver Mode ignores these."
                if self._devices
                else f"Checked {_clock_text()} · No device is sending reports "
                "all the time."
            )
        _trace(f"Message shown: {self._devices_message}")
        self.busyChanged.emit()
        self.devicesChanged.emit()

    # Refresh Programs (S13), Refresh System (S17), Ignore (S14) ------------

    @QtCore.Property(list, notify=programsChanged)
    def programs(self) -> list:
        return list(self._rows[PROGRAMS])

    @QtCore.Property(str, notify=programsChanged)
    def programsMessage(self) -> str:
        return self._messages[PROGRAMS]

    @QtCore.Property(list, notify=systemChanged)
    def system(self) -> list:
        return list(self._rows[SYSTEM])

    @QtCore.Property(str, notify=systemChanged)
    def systemMessage(self) -> str:
        return self._messages[SYSTEM]

    def _changed_list(self, which: str) -> None:
        (self.programsChanged if which == PROGRAMS else self.systemChanged).emit()

    def _row(self, row: dict, name: str, kind: str) -> bool:
        return row["name"] == name and (not kind or row["kind"] == kind)

    def _list_of(self, name: str, kind: str) -> str:
        """Which list holds the row (Programs when neither does)."""
        for which in (PROGRAMS, SYSTEM):
            if any(self._row(r, name, kind) for r in self._rows[which]):
                return which
        return PROGRAMS

    @QtCore.Slot(str, result=bool)
    @QtCore.Slot(str, str, result=bool)
    def isIgnored(self, name: str, kind: str = "") -> bool:
        """Whether Windows has the row ignored, as last read or changed
        (kind "" matches any kind), in either list."""
        name, kind = str(name), str(kind or "")
        return any(
            self._row(r, name, kind) and r["ignored"]
            for rows in self._rows.values()
            for r in rows
        )

    @QtCore.Slot()
    def refreshPrograms(self) -> None:
        self._refresh(PROGRAMS)

    @QtCore.Slot()
    def refreshSystem(self) -> None:
        self._refresh(SYSTEM)

    def _refresh(self, which: str) -> None:
        """One button's own elevated check (its own administrator prompt):
        list_requests() once, its half of split() kept (S13, S17)."""
        words = _LISTS[which]
        if self._scanning[which]:
            _trace(f"{words['button']} pressed: a check is already running")
            return
        _trace(f"{words['button']} pressed")
        self._scanning[which] = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import power_requests

                result: Any = power_requests.list_requests()
                if getattr(result, "ok", False):
                    halves = power_requests.split(list(result.programs))
                    result = (result, list(halves[words["half"]]))
            except Exception as exc:
                _log.exception(f"Screen Saver Mode: {words['button']} failed")
                result = f"The {words['what']} couldn't be listed: {exc}"
            self._emit(self._requestsDone, which, result)

        if not self._start(f"Screen Saver Mode {words['what']}", work):
            self._take_requests(which, f"The {words['what']} check couldn't start.")

    @QtCore.Slot(str, object)
    def _take_requests(self, which: str, result: object) -> None:
        words = _LISTS[which]
        self._scanning[which] = False
        if isinstance(result, str):
            self._messages[which] = result
            _log.warning(f"Screen Saver Mode: {result}")
        elif isinstance(result, tuple):
            self._rows[which] = [_program_row(p) for p in result[1]]
            self._messages[which] = (
                f"Checked {_clock_text()} · {words['kept']}"
                if self._rows[which]
                else f"Checked {_clock_text()} · {words['none']}"
            )
        else:
            # Refused: the window says so and nothing else happens (S13).
            self._messages[which] = str(
                getattr(result, "error", "")
                or f"The {words['what']} couldn't be listed."
            )
            _log.warning(
                f"Screen Saver Mode: {words['button']}: {self._messages[which]}"
            )
        _trace(f"Message shown: {self._messages[which]}")
        self.busyChanged.emit()
        self._changed_list(which)

    @QtCore.Slot(str, bool)
    @QtCore.Slot(str, bool, str)
    def setIgnored(self, name: str, ignored: bool, kind: str = KIND_PROCESS) -> None:
        """Ignore on/off for a row of any kind: a program (PROCESS), a
        driver or a service (S14); Windows checks the name."""
        name, kind = str(name), str(kind or KIND_PROCESS)
        _trace(f"Ignore {'on' if ignored else 'off'} pressed: {name} ({kind})")
        if self._pending_ignore:
            # One change at a time: the switch goes back.
            _trace(f"Ignore for {name} ({kind}) not sent: another change is running")
            self._changed_list(self._list_of(name, kind))
            return
        self._pending_ignore = name
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import power_requests

                ok, error = power_requests.set_ignored(name, bool(ignored), kind=kind)
            except Exception as exc:
                _log.exception("Screen Saver Mode: Ignore failed")
                ok, error = False, str(exc)
            self._emit(
                self._ignoreDone, name, kind, bool(ignored), bool(ok), str(error or "")
            )

        if not self._start("Screen Saver Mode ignore", work):
            self._take_ignore(
                name, kind, bool(ignored), False, "The change couldn't start."
            )

    @QtCore.Slot(str, str, bool, bool, str)
    def _take_ignore(
        self, name: str, kind: str, ignored: bool, ok: bool, error: str
    ) -> None:
        self._pending_ignore = ""
        which = self._list_of(name, kind)
        if ok:
            for row in self._rows[which]:
                if self._row(row, name, kind):
                    row["ignored"] = ignored
            self._messages[which] = (
                f"{name} is ignored: {_LISTS[which]['ignored']}"
                if ignored
                else f"{name} is no longer ignored."
            )
        else:
            # The switch goes back to what Windows has and the window says
            # why (S14).
            self._messages[which] = error or "The change wasn't made."
            _log.warning(
                f"Screen Saver Mode: Ignore {'on' if ignored else 'off'} for "
                f"{name} ({kind}) failed: {self._messages[which]}"
            )
        _trace(f"Message shown: {self._messages[which]}")
        self.busyChanged.emit()
        self._changed_list(which)
