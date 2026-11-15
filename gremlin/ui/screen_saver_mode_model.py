# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Screen Saver Mode window's model (12 S1-S15): its four settings
(stored in the program's settings, so History records them, S10), the
status line read from screen_saver_mode.manager() once a second while the
window is open, and the two checks (Refresh Devices, Refresh Programs) and
the Ignore this program switches, run on program threads."""

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
        return (
            "On hold: a full-screen program is in front. "
            "The countdown starts again when it ends."
        )
    if hold == "locked":
        return (
            "On hold: the PC is locked. Windows looks after the screens "
            "while it is locked."
        )
    return ""


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
    busyChanged = QtCore.Signal()

    # Worker results, queued to the main thread.
    _devicesDone = QtCore.Signal(object)
    _programsDone = QtCore.Signal(object)
    _ignoreDone = QtCore.Signal(str, bool, bool, str)

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        _ensure_options()
        self._status: Any = None
        self._devices: list[dict] = []
        self._devices_message = ""
        self._programs: list[dict] = []
        self._programs_message = ""
        self._scanning_devices = False
        self._scanning_programs = False
        self._pending_ignore = ""
        self._stop = False
        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.refreshStatus)
        Queued = QtCore.Qt.ConnectionType.QueuedConnection
        self._devicesDone.connect(self._take_devices, Queued)
        self._programsDone.connect(self._take_programs, Queued)
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
        return self._scanning_programs

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
            return
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
        else:
            rows = result if isinstance(result, list) else []
            self._devices = sorted(rows, key=lambda d: -d["rate"])
            self._devices_message = (
                f"Checked {_clock_text()} · Screen Saver Mode ignores these."
                if self._devices
                else f"Checked {_clock_text()} · No device is sending reports "
                "all the time."
            )
        self.busyChanged.emit()
        self.devicesChanged.emit()

    # Refresh Programs (S13) and Ignore this program (S14) --------------------

    @QtCore.Property(list, notify=programsChanged)
    def programs(self) -> list:
        return list(self._programs)

    @QtCore.Property(str, notify=programsChanged)
    def programsMessage(self) -> str:
        return self._programs_message

    @QtCore.Slot(str, result=bool)
    def isIgnored(self, name: str) -> bool:
        """Whether Windows has the program ignored, as last read or changed."""
        return any(r["name"] == str(name) and r["ignored"] for r in self._programs)

    @QtCore.Slot()
    def refreshPrograms(self) -> None:
        if self._scanning_programs:
            return
        self._scanning_programs = True
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import power_requests

                result: Any = power_requests.list_requests()
            except Exception as exc:
                _log.exception("Screen Saver Mode: Refresh Programs failed")
                result = f"The programs couldn't be listed: {exc}"
            self._emit(self._programsDone, result)

        if not self._start("Screen Saver Mode programs", work):
            self._take_programs("The programs check couldn't start.")

    @QtCore.Slot(object)
    def _take_programs(self, result: object) -> None:
        self._scanning_programs = False
        if isinstance(result, str):
            self._programs_message = result
        elif not getattr(result, "ok", False):
            # Refused: the window says so and nothing else happens (S13).
            self._programs_message = str(
                getattr(result, "error", "") or "The programs couldn't be listed."
            )
        else:
            self._programs = [
                {
                    "name": str(p.name),
                    "path": str(p.path),
                    "kinds": ", ".join(str(k) for k in p.kinds),
                    "ignored": bool(p.ignored),
                }
                for p in getattr(result, "programs", [])
            ]
            self._programs_message = (
                f"Checked {_clock_text()} · ignored programs no longer keep "
                "the display on."
                if self._programs
                else f"Checked {_clock_text()} · No program is asking Windows "
                "to keep the display on."
            )
        self.busyChanged.emit()
        self.programsChanged.emit()

    @QtCore.Slot(str, bool)
    def setIgnored(self, name: str, ignored: bool) -> None:
        name = str(name)
        if self._pending_ignore:
            # One change at a time: the switch goes back.
            self.programsChanged.emit()
            return
        self._pending_ignore = name
        self.busyChanged.emit()

        def work() -> None:
            try:
                from gremlin import power_requests

                ok, error = power_requests.set_ignored(name, bool(ignored))
            except Exception as exc:
                _log.exception("Screen Saver Mode: Ignore this program failed")
                ok, error = False, str(exc)
            self._emit(
                self._ignoreDone, name, bool(ignored), bool(ok), str(error or "")
            )

        if not self._start("Screen Saver Mode ignore", work):
            self._take_ignore(name, bool(ignored), False, "The change couldn't start.")

    @QtCore.Slot(str, bool, bool, str)
    def _take_ignore(self, name: str, ignored: bool, ok: bool, error: str) -> None:
        self._pending_ignore = ""
        if ok:
            for row in self._programs:
                if row["name"] == name:
                    row["ignored"] = ignored
            self._programs_message = (
                f"{name} is ignored: it no longer keeps the display on."
                if ignored
                else f"{name} is no longer ignored."
            )
        else:
            # The switch goes back to what Windows has (programsChanged) and
            # the window says why (S14).
            self._programs_message = error or "The change wasn't made."
        self.busyChanged.emit()
        self.programsChanged.emit()
