# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Output modules: the only path to the vJoy and Xbox (ViGEm) drivers.

An output module is the firewall in front of a driver. A value reaches the
driver only when the output module claims that output and the driver has it;
anything else is dropped and logged once. Reads give back claimed outputs
only, so viewers and conditions see exactly what the firewall lets through.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any

from PySide6 import QtCore

from gremlin import clock, run_scope, trace
from gremlin.modules import registry
from gremlin.modules.claim import claim_allows, claim_friendly, claim_ids, kind_of
from gremlin.types import InputType

# Action plugins reach the Xbox output through this module, not the driver
# package (05 Q16).
from vigem.xbox import XboxError, XboxTarget  # noqa: F401

syslog = logging.getLogger("system")

# Claims are re-read from the module files at most this often (seconds).
_CLAIM_TTL = 1.0

# Guards the claim cache and the blocked-log, busy-vJoy and keep-alive state
# below: writes come from the event, macro and timer threads (GL-245).
_lock = threading.Lock()
_claims_at = 0.0
_vjoy_claims: dict[int, dict] = {}
_vjoy_names: dict[int, str] = {}
_xbox_modules: dict[int, registry.Module] = {}
_vjoy_modules: dict[int, registry.Module] = {}
_blocked: set[tuple] = set()
# A failed read of the output modules was logged (until one works again).
_told_read_failed = False

# A vJoy that failed to open is tried again at most this often (seconds).
_VJOY_RETRY = 3.0
_vjoy_failed_at: dict[int, float] = {}
_told_busy: set[int] = set()
# vJoy devices the driver didn't list at the last open (turned off).
_vjoy_off: set[int] = set()

# A held vJoy with no write for this long is reset so it doesn't time out
# (06 S54); checked this often, one timer per held device.
_KEEP_ALIVE_S = 60.0
_keep_alive: dict[int, tuple[object, run_scope.Timer]] = {}


# --- claims -----------------------------------------------------------------


def _refresh_claims(force: bool = False) -> None:
    global _claims_at, _vjoy_claims, _vjoy_names, _vjoy_modules, _xbox_modules
    global _told_read_failed
    now = clock.monotonic()
    if not force and now - _claims_at < _CLAIM_TTL:
        return
    with _lock:
        if not force and now - _claims_at < _CLAIM_TTL:
            return
        found: dict[int, registry.Module] = {}
        xbox: dict[int, registry.Module] = {}
        try:
            outputs = registry.outputs()
        except Exception:
            # Keep the last good claims (an empty list blocked every vJoy
            # output, 06 RB16); said once, tried again after _CLAIM_TTL.
            if not _told_read_failed:
                _told_read_failed = True
                syslog.exception(
                    "Output modules could not be read; the last ones read are used"
                )
            _claims_at = clock.monotonic()
            return
        _told_read_failed = False
        for module in outputs:
            if is_xbox_module(module.name):
                xbox.setdefault(xbox_pad_of(module.name), module)
                continue
            vjoy_id = registry.resolve_vjoy_id(module.name, module.bound_guid)
            if vjoy_id and vjoy_id not in found:
                found[vjoy_id] = module
        _vjoy_modules = found
        _vjoy_claims = {vid: module.claim for vid, module in found.items()}
        _vjoy_names = {vid: module.name for vid, module in found.items()}
        _xbox_modules = xbox
        _claims_at = clock.monotonic()


def refresh() -> None:
    """Re-read every output module now (on activation and after a save).
    A module file saved or deleted (store._saved) may change what can't be
    sent, so the notice goes out too."""
    _refresh_claims(force=True)
    notify_cant_send()


# --- the can't-be-sent notice (D-05-CANT-SEND-LIVE) --------------------------


class _CantSendNotice(QtCore.QObject):
    """Sends signal.cantSendChanged once per burst, on the main thread.

    It also listens to the program's own signals for what decides "can't be
    sent" (claims saved, the vJoy device list, OSC's settings, the Logical
    Device, the profile), so no ⚠ keeps its own list of them."""

    asked = QtCore.Signal()

    def __init__(self) -> None:
        super().__init__()
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(0)
        self._timer.timeout.connect(self._send)
        # A worker thread's ask is queued to the main thread.
        self.asked.connect(self._ask)

    def listen(self) -> None:
        from gremlin.signal import signal

        for sig in (
            signal.configChanged,
            signal.profileChanged,
            signal.oscServerSettingsChanged,
            signal.oscDeviceReloaded,
            signal.logicalDeviceModified,
            signal.logicalDeviceReloaded,
        ):
            sig.connect(self._ask)
        try:
            from gremlin import event_handler

            event_handler.EventListener().device_change_event.connect(self._ask)
        except Exception:  # noqa: BLE001 - no device listener (some tests)
            syslog.debug("Can't-be-sent notice: no device listener", exc_info=True)

    @QtCore.Slot()
    def _ask(self) -> None:
        self._timer.start()

    @QtCore.Slot()
    def _send(self) -> None:
        _send_cant_send()


_notice: _CantSendNotice | None = None
_notice_lock = threading.Lock()


def _send_cant_send() -> None:
    global _claims_at
    # Readers see the new claims, not the one-second cache.
    with _lock:
        _claims_at = 0.0
    from gremlin.signal import signal

    signal.cantSendChanged.emit()


def watch_cant_send() -> _CantSendNotice | None:
    """Starts the notice (once, on the main thread): None without a Qt
    application, or on another thread before it started. Every
    can't-be-sent reader calls it, so the notice is listening before any ⚠
    is shown."""
    global _notice
    if _notice is not None:
        return _notice
    app = QtCore.QCoreApplication.instance()
    if app is None or threading.current_thread() is not threading.main_thread():
        return None
    with _notice_lock:
        if _notice is None:
            notice = _CantSendNotice()
            notice.listen()
            _notice = notice
        return _notice


def notify_cant_send() -> None:
    """What can't be sent may have changed: signal.cantSendChanged goes out
    once for a burst of calls, on the main thread, with the claim cache
    dropped. Any thread may call it. Without a Qt application it is sent at
    once."""
    notice = watch_cant_send()
    if notice is not None:
        notice.asked.emit()
        return
    app = QtCore.QCoreApplication.instance()
    if app is None:
        _send_cant_send()
    else:
        # Another thread before the notice started: started on the main one.
        QtCore.QTimer.singleShot(0, app, notify_cant_send)


def vjoy_claim(vjoy_id: int) -> dict:
    """The claim of the output module that drives this vJoy device."""
    _refresh_claims()
    return _vjoy_claims.get(int(vjoy_id), {})


def vjoy_modules() -> list[tuple[int, registry.Module]]:
    """vJoy output modules, one per vJoy device, by vJoy number (read fresh)."""
    watch_cant_send()
    _refresh_claims(force=True)
    return sorted(_vjoy_modules.items())


def vjoy_module_name(vjoy_id: int) -> str:
    """Name of the output module that drives this vJoy ("" when none)."""
    _refresh_claims()
    return _vjoy_names.get(int(vjoy_id), "")


def vjoy_allows(vjoy_id: int, kind: str, input_id: int) -> bool:
    return claim_allows(vjoy_claim(vjoy_id), kind, input_id)


def is_xbox_module(name: str) -> bool:
    """Gremlin's own Xbox output module (not a real Xbox pad's module)."""
    from gremlin.modules.registry import is_gremlin_xbox_name

    return is_gremlin_xbox_name(name)


def xbox_pad_of(name: str) -> int:
    """Pad number of an Xbox output module: "Xbox 360 Controller" is pad 1,
    "Xbox 360 2" is pad 2 (the "360" is part of the name, not a number)."""
    text = re.sub(r"360", " ", str(name or ""))
    match = re.search(r"(\d+)", text)
    pad = int(match.group(1)) if match else 1
    return pad if 1 <= pad <= 4 else 1


# --- logging ----------------------------------------------------------------


def _first_time(key: tuple) -> bool:
    """True the first time this key is seen since the blocked log was cleared."""
    with _lock:
        if key in _blocked:
            return False
        _blocked.add(key)
        return True


def _log_once(key: tuple, message: str) -> None:
    if _first_time(key):
        syslog.warning(message)


def clear_blocked_log() -> None:
    """Allow each blocked output to be logged again (new run)."""
    with _lock:
        _blocked.clear()
        _vjoy_failed_at.clear()
        _told_busy.clear()
        was_off = bool(_vjoy_off)
        _vjoy_off.clear()
    if was_off:
        notify_cant_send()


# --- vJoy -------------------------------------------------------------------


def _vjoy_proxy() -> Any:  # noqa: ANN401
    from vjoy.vjoy import VJoyProxy

    return VJoyProxy


def _open_vjoy(vjoy_id: int) -> Any | None:  # noqa: ANN401
    """The vJoy device, opened for Gremlin if it is not yet. None if it fails.

    After a failure the open is tried again every few seconds, not on every
    write, so Gremlin carries on by itself once the device is free.
    """
    vid = int(vjoy_id)
    if _opened_vjoy(vid) is None and vjoy_driver_found() and not vjoy_exists(vid):
        # Turned off in the vJoy configuration tool: never asked to open
        # (the driver logs each try); said once per Run (06 S47).
        with _lock:
            newly_off = vid not in _vjoy_off
            _vjoy_off.add(vid)
        if newly_off:
            notify_cant_send()
        _log_once(
            ("vjoy-off", vid),
            f"Output blocked: vJoy {vid} is not available (the vJoy driver "
            "doesn't list it).",
        )
        return None
    with _lock:
        back_on = vid in _vjoy_off
        _vjoy_off.discard(vid)
        failed_at = _vjoy_failed_at.get(vid)
    if back_on:
        notify_cant_send()
    if failed_at is not None and clock.monotonic() - failed_at < _VJOY_RETRY:
        return None
    try:
        dev = _vjoy_proxy()()[vid]
    except Exception as exc:
        from gremlin.error import VJoyBusyError

        with _lock:
            _vjoy_failed_at[vid] = clock.monotonic()
        if isinstance(exc, VJoyBusyError):
            _log_once(
                ("vjoy-open", vid),
                f"vJoy {vid} is in use by another program. Its outputs won't "
                "move until that program lets it go.",
            )
            with _lock:
                tell = vid not in _told_busy
                _told_busy.add(vid)
            if tell:
                from gremlin.signal import display_error

                display_error(
                    f"vJoy {vid} is in use by another program.",
                    "Its outputs won't move until that program lets it go.",
                )
        else:
            _log_once(("vjoy-open", vid), f"vJoy {vid} unavailable: {exc}")
        return None
    with _lock:
        was_failing = _vjoy_failed_at.pop(vid, None) is not None
    if was_failing:
        syslog.info(f"vJoy {vid} opened")
    # The keep-alive needs to know when the device was last written.
    if hasattr(dev, "last_active"):
        _arm_keep_alive(vid)
    return dev


def _arm_keep_alive(
    vjoy_id: int, after: object = None, seconds: float | None = None
) -> None:
    """Checks the held vJoy _KEEP_ALIVE_S after its last write (06 S54), or
    after seconds. One timer per device: armed when it is opened (after=None,
    none armed yet) or by its own check (after=that check's token, still the
    current one).

    It is a Run timer (run_scope.timer, main thread): Stop cancels it with
    the rest of the Run, so it never outlives the Run that holds the device
    and is never a thread of its own. A device opened on another thread (a
    macro, the event thread) has its keep-alive armed on the main thread.
    """
    vid = int(vjoy_id)
    if after is None and threading.current_thread() is not threading.main_thread():
        door = _keep_alive_door()
        if door is not None:
            door.arm.emit(vid)
            return
    # Released while the request was on its way: nothing to keep alive.
    if after is None and _opened_vjoy(vid) is None:
        return
    with _lock:
        current = _keep_alive.get(vid)
        # One made outside a Run ends when a Run begins: arm a new one then.
        if after is None and current is not None and current[1].is_alive():
            return
        if after is not None and (current is None or current[0] is not after):
            return
        token = object()
        timer = run_scope.timer(
            f"vJoy {vid} keep-alive",
            _KEEP_ALIVE_S if seconds is None else seconds,
            _keep_alive_check,
            vid,
            token,
        )
        _keep_alive[vid] = (token, timer)


class _KeepAliveDoor(QtCore.QObject):
    """Passes a keep-alive asked for on another thread to the main thread."""

    arm = QtCore.Signal(int)

    def __init__(self) -> None:
        super().__init__()
        self.arm.connect(self._arm)

    @QtCore.Slot(int)
    def _arm(self, vjoy_id: int) -> None:
        _arm_keep_alive(vjoy_id)


_door: _KeepAliveDoor | None = None
_door_lock = threading.Lock()


def _keep_alive_door() -> _KeepAliveDoor | None:
    """None without a Qt application (no main-thread loop to pass it to)."""
    global _door
    app = QtCore.QCoreApplication.instance()
    if app is None:
        return None
    with _door_lock:
        if _door is None:
            door = _KeepAliveDoor()
            door.moveToThread(app.thread())
            _door = door
        return _door


def _keep_alive_check(vjoy_id: int, token: object) -> None:
    """Resets a held vJoy that had no write for _KEEP_ALIVE_S, then checks
    again _KEEP_ALIVE_S after its last write (a fixed period from the open
    re-sent it only after up to twice that). A released device arms no new
    check."""
    vid = int(vjoy_id)
    dev = _opened_vjoy(vid)
    if dev is None:
        with _lock:
            current = _keep_alive.get(vid)
            if current is not None and current[0] is token:
                del _keep_alive[vid]
        return
    wait = _KEEP_ALIVE_S
    try:
        idle = clock.monotonic() - float(dev.last_active)
        if idle >= _KEEP_ALIVE_S:
            dev.reset()
        else:
            # Never less than a little: a clock going back can't spin it.
            wait = max(_KEEP_ALIVE_S - idle, min(_KEEP_ALIVE_S, 1.0))
    except Exception:
        syslog.exception(f"vJoy {vid} keep-alive failed")
    # Released (reset_vjoy) while this check ran: no new timer.
    _arm_keep_alive(vid, after=token, seconds=wait)


def _stop_keep_alive() -> None:
    with _lock:
        timers = [timer for _token, timer in _keep_alive.values()]
        _keep_alive.clear()
    for timer in timers:
        timer.cancel()


def vjoy_ids() -> list[int]:
    """The vJoy devices set up in the driver (1-16)."""
    from vjoy import vjoy

    return [i for i in range(1, 17) if vjoy.device_exists(i)]


def vjoy_axes() -> dict[int, list[int]]:
    """Each vJoy set up in the driver -> its axis ids, by vJoy number (for
    Profile Settings). Empty when the driver can't be read."""
    try:
        from vjoy import vjoy

        return {vid: sorted(vjoy.axis_ids(vid)) for vid in vjoy_ids()}
    except Exception:
        return {}


def vjoy_axis_ids(vjoy_id: int) -> set[int]:
    """The axis ids (1 = X ... 8 = SL1) the vJoy driver gives this device;
    they can be sparse (1, 2, 6). Empty when the driver can't be read."""
    try:
        from vjoy import vjoy

        return set(vjoy.axis_ids(int(vjoy_id)))
    except Exception:
        return set()


def vjoy_layout(vjoy_id: int) -> tuple[int, int, int]:
    """(axes, buttons, hats) of a vJoy device, as the driver sets it up."""
    from vjoy import vjoy

    return (
        vjoy.axis_count(vjoy_id), vjoy.button_count(vjoy_id), vjoy.hat_count(vjoy_id)
    )


def vjoy_hats_continuous(vjoy_id: int) -> bool:
    """Whether the vJoy device's hats are continuous (Gremlin needs that)."""
    from vjoy import vjoy

    return bool(vjoy.hat_configuration_valid(vjoy_id))


def vjoy_in_use_elsewhere(vjoy_id: int) -> bool:
    """Whether another program holds the vJoy device, so Gremlin can't use it."""
    try:
        from vjoy.vjoy import held_by_another_program

        return bool(held_by_another_program(int(vjoy_id)))
    except Exception:
        return False


def _opened_vjoy(vjoy_id: int) -> Any | None:  # noqa: ANN401
    """The vJoy device only if Gremlin already holds it. Never opens one."""
    try:
        devices = _vjoy_proxy().vjoy_devices or {}
    except Exception:
        return None
    for key, dev in devices.items():
        try:
            if int(key) == int(vjoy_id):
                return dev
        except (TypeError, ValueError):
            continue
    return None


def _has(dev: Any, kind: str, input_id: int) -> bool:  # noqa: ANN401
    if kind == "axis":
        return bool(dev.is_axis_valid(axis_id=input_id))
    if kind == "button":
        return bool(dev.is_button_valid(input_id))
    if kind == "hat":
        return bool(dev.is_hat_valid(input_id))
    return False


def _sending() -> bool:
    """True during a Run and while Stop runs its steps (releases, neutral
    values); nothing is sent while stopped (06 S4, Q19)."""
    if run_scope.running() or run_scope.stopping():
        return True
    syslog.debug("Output not sent: no profile is running.")
    return False


def _passes(vjoy_id: int, kind: str, input_id: int) -> bool:
    if vjoy_allows(vjoy_id, kind, input_id):
        return True
    _log_once(
        ("vjoy", int(vjoy_id), kind, int(input_id)),
        f"Output blocked: vJoy {vjoy_id} {kind} {input_id} is not claimed by "
        f"its output module. Claim it on the vJoy {vjoy_id} output module to use it.",
    )
    return False


def write_vjoy(vjoy_id: int, kind: str, input_id: int, value: Any) -> bool:  # noqa: ANN401
    """Send a value to a claimed vJoy output. False when it was blocked.

    kind is "axis" (value -1..1), "button" (pressed) or "hat" (HatDirection).
    """
    input_id = int(input_id)
    result = _write_vjoy(vjoy_id, kind, input_id, value)
    if trace.enabled():
        # OUTPUT tap (D-01-TRACE): trace keeps it only for a ticked input.
        trace.output(vjoy_id, kind, input_id, value, result)
    return result == "written"


def _write_vjoy(vjoy_id: int, kind: str, input_id: int, value: Any) -> str:  # noqa: ANN401
    """write_vjoy's work; the result as the trace says it."""
    if not _sending():
        return "blocked (not running)"
    if not _passes(vjoy_id, kind, input_id):
        return f"blocked (not claimed by the vJoy {vjoy_id} module)"
    dev = _open_vjoy(vjoy_id)
    if dev is None:
        with _lock:
            off = int(vjoy_id) in _vjoy_off
        if off:
            return f"missing (vJoy {vjoy_id} is not available)"
        return f"failed: vJoy {vjoy_id} not open"
    if not _has(dev, kind, input_id):
        _log_once(
            ("vjoy-missing", int(vjoy_id), kind, input_id),
            f"Output blocked: vJoy {vjoy_id} has no {kind} {input_id}.",
        )
        return f"missing (vJoy {vjoy_id} has no {kind} {input_id})"
    try:
        if kind == "axis":
            dev.axis(input_id).value = float(value)
        elif kind == "button":
            dev.button(input_id).is_pressed = bool(value)
        else:
            dev.hat(input_id).direction = value
    except Exception as exc:
        key = ("vjoy-error", int(vjoy_id), kind, input_id)
        _log_once(key, f"vJoy write failed: {exc}")
        return f"failed: {exc}"
    return "written"


def write_vjoy_axis_linear(vjoy_id: int, linear_index: int, value: float) -> bool:
    """Write an axis given by its position in the axis list (1 = first axis).

    A device is opened only for a claimed axis (S49, S51)."""
    axis_id = _linear_axis_id(vjoy_id, int(linear_index))
    if axis_id is None:
        return False
    return write_vjoy(vjoy_id, "axis", axis_id, value)


def _linear_axis_id(vjoy_id: int, linear_index: int) -> int | None:
    """The axis id at this place in the axis list; None when there is none
    or no axis of the device is claimed (the device then stays closed)."""
    if not claim_ids(vjoy_claim(vjoy_id), "axis"):
        return None
    dev = _open_vjoy(vjoy_id)
    if dev is None or not dev.is_axis_valid(linear_index=linear_index):
        return None
    return int(dev.axis_id(linear_index))


def release_vjoy_button(vjoy_id: int, button_id: int) -> bool:
    return write_vjoy(vjoy_id, "button", button_id, False)


def _neutral(kind: str) -> Any:  # noqa: ANN401
    if kind == "axis":
        return 0.0
    if kind == "button":
        return False
    from gremlin.types import HatDirection

    return HatDirection.Center


def vjoy_value(vjoy_id: int, kind: str, input_id: int) -> Any:  # noqa: ANN401
    """Current value of a claimed vJoy output; neutral when unclaimed or
    missing, or when Gremlin does not hold the device: a read never opens
    one, only writes do (06 Q16)."""
    input_id = int(input_id)
    if not vjoy_allows(vjoy_id, kind, input_id):
        return _neutral(kind)
    dev = _opened_vjoy(vjoy_id)
    if dev is None or not _has(dev, kind, input_id):
        return _neutral(kind)
    if kind == "axis":
        return float(dev.axis(input_id).value)
    if kind == "button":
        return bool(dev.button(input_id).is_pressed)
    return dev.hat(input_id).direction


def vjoy_held(vjoy_id: int) -> bool:
    """True when Gremlin has opened this vJoy device (a profile is driving it)."""
    return _opened_vjoy(vjoy_id) is not None


def vjoy_lost(vjoy_id: int) -> bool:
    """True when Gremlin opened this vJoy device and no longer owns it
    (another program took it). A device not opened yet is not lost: the
    next write opens it (05 S83)."""
    dev = _opened_vjoy(vjoy_id)
    if dev is None:
        return False
    try:
        return not bool(dev.is_owned())
    except Exception:
        return True


def vjoy_state(
    vjoy_id: int, claim: dict | None = None, hats: bool = False
) -> dict[tuple[str, int], Any]:
    """Values of every claimed output of a vJoy device Gremlin holds.

    Axes are -1..1 and buttons 1.0 / 0.0; hats (when asked for) are
    HatDirection. Empty when Gremlin has not opened that device, so a viewer
    never opens one itself.
    """
    dev = _opened_vjoy(vjoy_id)
    if dev is None:
        return {}
    if claim is None:
        claim = vjoy_claim(vjoy_id)
    state: dict[tuple[str, int], Any] = {}
    for axis_id in claim_ids(claim, "axis"):
        if dev.is_axis_valid(axis_id=axis_id):
            axis = dev.axis(axis_id=axis_id)
            state[("axis", axis_id)] = float(getattr(axis, "_value", 0.0))
    for button_id in claim_ids(claim, "button"):
        if dev.is_button_valid(button_id):
            pressed = bool(getattr(dev.button(button_id), "_is_pressed", False))
            state[("button", button_id)] = 1.0 if pressed else 0.0
    if hats:
        for hat_id in claim_ids(claim, "hat"):
            if dev.is_hat_valid(hat_id):
                hat = dev.hat(hat_id)
                direction = getattr(hat, "_direction", None)
                if direction is None:
                    direction = hat.direction
                state[("hat", hat_id)] = direction
    return state


def vjoy_driver_found() -> bool:
    """True when the vJoy driver is installed and running."""
    try:
        from vjoy.vjoy_interface import VJoyInterface

        # The interface's functions are made when its DLL loads.
        enabled = getattr(VJoyInterface, "vJoyEnabled", None)
        return bool(enabled and enabled())
    except Exception:
        return False


def vjoy_exists(vjoy_id: int) -> bool:
    """True when the vJoy driver has this device enabled."""
    try:
        from vjoy import vjoy

        return bool(vjoy.device_exists(int(vjoy_id)))
    except Exception:
        return False


def vjoy_driver_ids(vjoy_id: int) -> dict[str, set[int]]:
    """The axis, button and hat ids the vJoy driver gives this device
    ({"axes", "buttons", "hats"}); all empty when the program doesn't list
    it. The one check for "the driver has it" (Auto Mapping Tool, the output
    picker and new actions, 05 S118). Axes by id: the driver can leave gaps."""
    from gremlin import device_initialization

    empty: dict[str, set[int]] = {"axes": set(), "buttons": set(), "hats": set()}
    for device in device_initialization.vjoy_devices() or []:
        if int(device.vjoy_id) != int(vjoy_id):
            continue
        # Its sizes through the driver (08 R7, GL-275).
        try:
            axis_count, button_count, hat_count = vjoy_layout(int(vjoy_id))
        except Exception:  # noqa: BLE001 - the driver can't be read
            axis_count = button_count = hat_count = 0
        axes = vjoy_axis_ids(int(vjoy_id))
        if not (axes or axis_count or button_count or hat_count):
            # The driver can't be read: the device list's sizes.
            axes = {int(axis.axis_index) for axis in device.axis_map}
            button_count = int(device.button_count)
            hat_count = int(device.hat_count)
        return {
            "axes": set(axes),
            "buttons": set(range(1, int(button_count) + 1)),
            "hats": set(range(1, int(hat_count) + 1)),
        }
    return empty


_DRIVER_BUCKET = {"axis": "axes", "button": "buttons", "hat": "hats"}


def driver_claim(vjoy_id: int, claim: dict | None) -> dict:
    """The claim cut to the ids the vJoy driver has (05 S118)."""
    have = vjoy_driver_ids(vjoy_id)
    out = dict(claim or {})
    for kind, bucket in _DRIVER_BUCKET.items():
        out[bucket] = [i for i in claim_ids(claim, kind) if i in have[bucket]]
    return out


def first_claimed_output(
    kinds: list[InputType],
    exclude: set[tuple[int, InputType, int]] | None = None,
) -> tuple[int, InputType, int] | None:
    """(vjoy_id, kind, input_id) of the first output a vJoy output module
    claims: modules by vJoy number, kinds in the order given, ids ascending.
    Only vJoy devices used as outputs and only ids the driver has; any in
    `exclude` are passed over. None when there is none (05 S113, S115)."""
    from gremlin import device_initialization

    skip = {(int(v), t, int(i)) for v, t, i in (exclude or set())}
    try:
        outputs = {
            int(device.vjoy_id)
            for device in device_initialization.output_vjoy_devices()
        }
    except Exception:  # noqa: BLE001 - no device list: nothing to offer
        return None
    for vjoy_id, module in vjoy_modules():
        if int(vjoy_id) not in outputs:
            continue
        have = vjoy_driver_ids(vjoy_id)
        for input_type in kinds:
            kind = kind_of(input_type)
            bucket = _DRIVER_BUCKET.get(kind)
            if bucket is None:
                continue
            for input_id in claim_ids(module.claim, kind):
                if input_id not in have[bucket]:
                    continue
                if (int(vjoy_id), input_type, input_id) in skip:
                    continue
                return (int(vjoy_id), input_type, input_id)
    return None


class _ScriptAxis:
    def __init__(self, vjoy_id: int, axis_id: int) -> None:
        self._vjoy_id, self._axis_id = vjoy_id, axis_id

    @property
    def value(self) -> float:
        return float(vjoy_value(self._vjoy_id, "axis", self._axis_id))

    @value.setter
    def value(self, value: float) -> None:
        write_vjoy(self._vjoy_id, "axis", self._axis_id, value)


class _ScriptButton:
    def __init__(self, vjoy_id: int, button_id: int) -> None:
        self._vjoy_id, self._button_id = vjoy_id, button_id

    @property
    def is_pressed(self) -> bool:
        return bool(vjoy_value(self._vjoy_id, "button", self._button_id))

    @is_pressed.setter
    def is_pressed(self, value: bool) -> None:
        write_vjoy(self._vjoy_id, "button", self._button_id, value)


class _ScriptHat:
    def __init__(self, vjoy_id: int, hat_id: int) -> None:
        self._vjoy_id, self._hat_id = vjoy_id, hat_id

    @property
    def direction(self) -> Any:  # noqa: ANN401
        return vjoy_value(self._vjoy_id, "hat", self._hat_id)

    @direction.setter
    def direction(self, value: Any) -> None:  # noqa: ANN401
        write_vjoy(self._vjoy_id, "hat", self._hat_id, value)


class _ScriptDevice:
    """One vJoy device as a script sees it: claimed outputs only."""

    def __init__(self, vjoy_id: int) -> None:
        self.vjoy_id = int(vjoy_id)

    def axis(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> _ScriptAxis:
        if axis_id is None and linear_index is not None:
            axis_id = _linear_axis_id(self.vjoy_id, int(linear_index)) or 0
        return _ScriptAxis(self.vjoy_id, int(axis_id or 0))

    def button(self, index: int) -> _ScriptButton:
        return _ScriptButton(self.vjoy_id, int(index))

    def hat(self, index: int) -> _ScriptHat:
        return _ScriptHat(self.vjoy_id, int(index))


class ScriptVJoy:
    """The "vjoy" object user scripts get. Used like the old driver proxy
    (vjoy[1].button(3).is_pressed = True) but every read and write goes
    through the output module, so unclaimed outputs are blocked."""

    def __getitem__(self, vjoy_id: int) -> _ScriptDevice:
        return _ScriptDevice(vjoy_id)


# --- Xbox (ViGEm) -----------------------------------------------------------


def xbox_modules() -> dict[int, registry.Module]:
    """Xbox output modules by pad number."""
    _refresh_claims()
    return dict(_xbox_modules)


def xbox_module(pad_id: int) -> registry.Module | None:
    """The Xbox output module for this pad, or None when there is none."""
    _refresh_claims()
    return _xbox_modules.get(int(pad_id))


def write_xbox(pad_id: int, target: Any, value: Any) -> bool:  # noqa: ANN401
    """Send a value to an Xbox control. False when the driver refused it.

    The Xbox output module is a straight pass-through to ViGEm: every control
    on the pad is available, nothing is claimed (as in GremlinEx). Nothing
    is sent while stopped, so no pad is plugged in outside a Run (06 Q19).
    """
    if not _sending():
        return False
    try:
        from vigem.xbox import XboxProxy

        XboxProxy()[int(pad_id)].apply(target, value)
    except Exception as exc:
        _log_once(("xbox-error", int(pad_id)), f"Xbox pad {pad_id} write failed: {exc}")
        return False
    return True


def xbox_state(pad_id: int) -> dict[str, float]:
    """Every control of a pad Gremlin has plugged in; empty otherwise.
    Never plugs a pad in itself."""
    try:
        from vigem.xbox import XboxProxy

        return dict(XboxProxy().snapshot(int(pad_id)) or {})
    except Exception:
        return {}


def held_vjoy_ids() -> list[int]:
    """vJoy devices Gremlin holds open right now (opens none itself). For
    checks after Stop (gremlin.validate). Never loads the vJoy module (and
    with it vJoyInterface.dll) when it isn't loaded yet."""
    import sys

    vjoy = sys.modules.get("vjoy.vjoy")
    if vjoy is None:
        return []
    try:
        return sorted(int(k) for k in (vjoy.VJoyProxy.vjoy_devices or {}))
    except Exception:
        return []


def plugged_xbox_pads() -> list[int]:
    """Xbox pads Gremlin has plugged in right now. Never plugs one in, and
    never starts the ViGEm client when it isn't running yet."""
    import sys

    xbox = sys.modules.get("vigem.xbox")
    if xbox is None:
        return []
    try:
        from gremlin.common import SingletonMetaclass

        proxy = SingletonMetaclass._instances.get(xbox.XboxProxy)
        return sorted(int(k) for k in (getattr(proxy, "_pads", None) or {}))
    except Exception:
        return []



def xbox_slot(pad: int) -> int | None:
    """The XInput slot (1-4) that Gremlin's Xbox pad `pad` got, or None when
    the pad isn't plugged in or ViGEm has no slot for it yet. Never plugs a
    pad in or starts the ViGEm client, and never raises (02 S105, S106)."""
    import sys

    xbox = sys.modules.get("vigem.xbox")
    if xbox is None:
        return None
    try:
        from gremlin.common import SingletonMetaclass

        proxy = SingletonMetaclass._instances.get(xbox.XboxProxy)
        found = (getattr(proxy, "_pads", None) or {}).get(int(pad))
        index = found.user_index() if found is not None else None
    except Exception as exc:
        syslog.debug("Xbox pad %s slot: %s", pad, exc)
        return None
    # ViGEm's user index is XInput's 0-based dwUserIndex; slots are 1-4.
    if index is None or not 0 <= index <= 3:
        return None
    return index + 1

def xbox_available() -> bool:
    """True when ViGEmBus and ViGEmClient.dll can be used."""
    try:
        from vigem.xbox import XboxProxy

        return bool(XboxProxy().available())
    except Exception:
        return False


def xbox_driver_installed() -> bool:
    """True when the ViGEmBus driver is installed, running or not."""
    from vigem.ids import driver_installed

    return driver_installed()


def xbox_driver_version() -> str:
    """The installed ViGEmBus driver's version ("" when not installed)."""
    from vigem.ids import driver_version

    return driver_version()


def xbox_error() -> str:
    """Why the Xbox driver cannot be used ("" when it can)."""
    from vigem.ids import vigem_client_error

    return vigem_client_error()


_VIGEM_INSTALL = (
    "Install ViGEmBus 1.22 from the Nefarius releases page, then restart "
    "the program. This program does not download or bundle that installer."
)


def xbox_driver_problem() -> tuple[str, str]:
    """What is wrong with the Xbox driver, and what to do; ("", "") when it
    works. Every check of the Xbox driver uses this wording."""
    if xbox_available():
        return "", ""
    error = xbox_error()
    if error:
        return error, _VIGEM_INSTALL
    if xbox_driver_installed():
        return (
            "ViGEmBus is installed but not running",
            "Restart Windows, or reinstall ViGEmBus 1.22, then restart "
            "the program.",
        )
    return "ViGEmBus is not installed", _VIGEM_INSTALL


def vjoy_driver_problem() -> tuple[str, str]:
    """What is wrong with the vJoy driver, and what to do; ("", "") when it
    works. Every check of the vJoy driver uses this wording."""
    if vjoy_driver_found():
        return "", ""
    return (
        "vJoy is not installed or not running",
        "Install vJoy, then restart the program.",
    )


# --- lifecycle --------------------------------------------------------------


def reset_vjoy() -> None:
    """Release every vJoy device Gremlin holds."""
    _stop_keep_alive()
    held = held_vjoy_ids()
    try:
        _vjoy_proxy().reset()
    except Exception:
        syslog.exception("vJoy reset failed")
    # Released at rest (06 S17): the rest counts as written for the
    # out-of-step watch (S86-S87), else Stop reads as OUT OF STEP.
    trace.rested(held)


def reset_drivers() -> None:
    """Release every vJoy device and unplug every Xbox pad Gremlin holds."""
    reset_vjoy()
    try:
        from vigem.xbox import XboxProxy

        XboxProxy().reset()
    except Exception:
        syslog.exception("Xbox reset failed")
    clear_blocked_log()


# --- bindings the program can't send (D-05-CANT-SEND) ------------------------

# The drop-down's words for vJoy axes (1 = X ... 8 = Dial).
AXIS_WORDS = {
    1: "X Axis",
    2: "Y Axis",
    3: "Z Axis",
    4: "X Rotation",
    5: "Y Rotation",
    6: "Z Rotation",
    7: "Slider",
    8: "Dial",
}
_KIND_WORDS = {"axis": "Axes", "button": "Buttons", "hat": "Hats"}


def _kind(kind: object) -> str:
    return kind_of(kind) or str(kind)


def control_label(claim: dict | None, kind: object, control_id: int) -> str:
    """A vJoy control as the Map to vJoy drop-down names it: the output
    module's name for it, else "X Axis", "Button 3", "Hat 1"."""
    kind = _kind(kind)
    custom = claim_friendly(claim, kind, control_id)
    if custom:
        return custom
    if kind == "axis":
        return AXIS_WORDS.get(int(control_id), f"Axis {int(control_id)}")
    if kind == "hat":
        return f"Hat {int(control_id)}"
    return f"Button {int(control_id)}"


def _ranges(ids: list[int]) -> str:
    """[1..20, 25, 30..56] -> "1–20, 25, 30–56"."""
    parts: list[str] = []
    start = prev = None
    for value in sorted(set(ids)):
        if prev is not None and value == prev + 1:
            prev = value
            continue
        if start is not None:
            parts.append(str(start) if start == prev else f"{start}–{prev}")
        start = prev = value
    if start is not None:
        parts.append(str(start) if start == prev else f"{start}–{prev}")
    return ", ".join(parts)


def vjoy_turned_off(vjoy_id: int) -> bool:
    """The driver doesn't list this vJoy (turned off, or no driver)."""
    return int(vjoy_id) in _vjoy_off or not any(vjoy_driver_ids(vjoy_id).values())


def cant_send_text(vjoy_id: int, kind: object, control_id: int) -> str | None:
    """None when a Map to vJoy target can be sent; else why not, for the
    red ⚠ tooltip. Sendable means listed in the action editor's vJoy
    drop-down: the output module's claim cut to the driver (05 S118)."""
    watch_cant_send()
    vjoy_id, control_id, kind = int(vjoy_id), int(control_id), _kind(kind)
    off = vjoy_turned_off(vjoy_id)
    _refresh_claims()
    claim = _vjoy_claims.get(vjoy_id, {})
    ids = [] if off else claim_ids(driver_claim(vjoy_id, claim), kind)
    return cant_send_words(vjoy_id, kind, control_id, claim, ids, off)


def cant_send_words(
    vjoy_id: int,
    kind: object,
    control_id: int,
    claim: dict | None,
    ids: list[int],
    off: bool,
) -> str | None:
    """The can't-be-sent text from what the drop-down lists (`ids`) and
    whether the vJoy is turned off; the one wording for it."""
    vjoy_id, control_id, kind = int(vjoy_id), int(control_id), _kind(kind)
    if off:
        return f"vJoy {vjoy_id} is not Found."
    if control_id in ids:
        return None
    control = control_label(claim, kind, control_id)
    words = _KIND_WORDS.get(kind, kind)
    have = f"has {words} {_ranges(ids)}" if ids else f"has no {words}"
    return f"vJoy {vjoy_id}'s {control} is not Found (vJoy {vjoy_id} {have})."


def vjoy_targets(action: Any) -> list[tuple[int, InputType, int]]:  # noqa: ANN401
    """The vJoy outputs one action sends to (Map to vJoy, macro vJoy steps)."""
    from action_plugins.macro import MacroData
    from action_plugins.map_to_vjoy import MapToVjoyData
    from gremlin import macro

    if isinstance(action, MapToVjoyData):
        return [
            (action.vjoy_device_id, action.vjoy_input_type, action.vjoy_input_id)
        ]
    if isinstance(action, MacroData):
        return [
            (step.vjoy_id, step.input_type, step.input_id)
            for step in action.actions
            if isinstance(step, macro.VJoyAction)
        ]
    return []


# --- Map to Xbox, Map to Logical Device, Send OSC (D-05-CANT-SEND-ALL) -------


def xbox_pad_label(pad: int) -> str:
    """A pad as the Map to Xbox editor names it: its Xbox output module's
    name, else "Xbox 360 Controller" for pad 1, "Xbox pad N" otherwise."""
    module = xbox_modules().get(int(pad))
    if module is not None:
        return module.name
    return "Xbox 360 Controller" if int(pad) == 1 else f"Xbox pad {int(pad)}"


def xbox_cant_send_text(pad: int) -> str | None:
    """None when Map to Xbox can send to this pad; else "<pad> is not
    Found." (the Xbox driver, ViGEm, can't be used, or no such pad)."""
    watch_cant_send()
    from vigem.xbox import MAX_PADS

    pad = int(pad)
    if 1 <= pad <= MAX_PADS and xbox_available():
        return None
    return f"{xbox_pad_label(pad)} is not Found."


def logical_control_label(input_type: Any, input_id: Any) -> str:  # noqa: ANN401
    """A Logical Device control by its system name, as the picker shows it
    ("Button 3")."""
    return f"{InputType.to_string(input_type).capitalize()} {input_id}"


def logical_cant_send_text(action: Any) -> str | None:  # noqa: ANN401
    """None when a Map to Logical Device action's control is there; else
    "Logical Device <Control> is not Found." (the control was deleted)."""
    watch_cant_send()
    if not getattr(action, "logical_missing", False):
        return None
    label = logical_control_label(action.logical_input_type, action.logical_input_id)
    return f"Logical Device {label} is not Found."


def _logical_step_text(step: Any) -> str | None:  # noqa: ANN401
    """A macro Logical Device step whose control is gone (none chosen yet
    is the editor's own prompt, not this)."""
    if step.input_id is None or step.current_identifier() is not None:
        return None
    label = logical_control_label(step.input_type, step.input_id)
    return f"Logical Device {label} is not Found."


def osc_settings() -> tuple[dict, list[dict]]:
    """(server settings, targets) as OSC/module.json has them now."""
    from gremlin import osc_device_file

    try:
        return osc_device_file.read_server(), osc_device_file.read_targets()
    except Exception:  # noqa: BLE001 - unreadable file: OSC's defaults
        syslog.debug("OSC settings unreadable", exc_info=True)
        return {}, []


def osc_cant_send_text(
    target_id: str,
    settings: tuple[dict, list[dict]] | None = None,
    name: str = "",
) -> str | None:
    """None when Send OSC can send to this target; else "OSC target <name>
    is not Found." (not in the current Targets; `name` is the action's
    saved target name, the id only when none was saved,
    D-09-SENDOSC-TARGET-NAME) or "OSC output is Off."."""
    watch_cant_send()
    from gremlin import osc_output

    server, targets = settings if settings is not None else osc_settings()
    target_id = str(target_id)
    if target_id != osc_output.REPLY and target_id not in [
        str(t.get("id")) for t in targets
    ]:
        return f"OSC target {name or target_id} is not Found."
    if not server.get("output_enabled", True):
        return "OSC output is Off."
    return None


def cant_send_action_texts(
    action: Any, memo: dict | None = None  # noqa: ANN401
) -> list[str]:
    """Why one action's outputs can't be sent, one text per output (Map to
    vJoy, Map to Xbox, Map to Logical Device, Send OSC, macro vJoy and
    Logical Device steps); [] when all can. Nested actions are the caller's
    (profile.reachable). `memo` shares look-ups across calls."""
    watch_cant_send()
    from action_plugins.macro import MacroData
    from action_plugins.map_to_logical_device import MapToLogicalDeviceData
    from action_plugins.map_to_xbox import MapToXboxData
    from action_plugins.send_osc import SendOscData
    from gremlin import macro

    memo = {} if memo is None else memo
    texts: list[str | None] = []
    for vjoy_id, input_type, input_id in vjoy_targets(action):
        try:
            key = ("vjoy", int(vjoy_id), kind_of(input_type), int(input_id))
        except (TypeError, ValueError):
            continue
        if key not in memo:
            memo[key] = cant_send_text(*key[1:])
        texts.append(memo[key])
    if isinstance(action, MapToXboxData):
        key = ("xbox", int(action.xbox_device_id))
        if key not in memo:
            memo[key] = xbox_cant_send_text(key[1])
        texts.append(memo[key])
    elif isinstance(action, MapToLogicalDeviceData):
        texts.append(logical_cant_send_text(action))
    elif isinstance(action, SendOscData):
        if "osc" not in memo:
            memo["osc"] = osc_settings()
        texts.append(
            osc_cant_send_text(action.target, memo["osc"], action.target_name)
        )
    elif isinstance(action, MacroData):
        texts.extend(
            _logical_step_text(step)
            for step in action.actions
            if isinstance(step, macro.LogicalDeviceAction)
        )
    return [text for text in texts if text]


def _input_label(input_type: Any, input_id: Any) -> str:  # noqa: ANN401
    from gremlin import common

    try:
        return common.input_to_ui_string(input_type, input_id)
    except Exception:  # noqa: BLE001 - an input type with no ui string
        return f"{input_type} {input_id}"


def cant_send_bindings(profile: Any = None) -> list[dict]:  # noqa: ANN401
    """Every output in the profile (default: the current one) that can't be
    sent (vJoy, Xbox, Logical Device, OSC; cant_send_action_texts), nested
    actions included: device_guid, device_name, input_type, input_id,
    input_label, mode, text (the tooltip). Re-ask on signal.cantSendChanged
    (D-05-CANT-SEND-LIVE)."""
    watch_cant_send()
    from gremlin import device_initialization, shared_state
    from gremlin.profile import Profile, reachable

    profile = profile if profile is not None else shared_state.current_profile
    if profile is None:
        return []
    memo: dict = {}
    found: list[dict] = []
    for items in profile.inputs.values():
        for item in items:
            for action in reachable(Profile.roots_of([item])):
                for text in cant_send_action_texts(action, memo):
                    guid = getattr(item.device_id, "uuid", item.device_id)
                    found.append(
                        {
                            "device_guid": str(guid),
                            "device_name": device_initialization.device_name(guid),
                            "input_type": InputType.to_string(item.input_type)
                            if item.input_type is not None
                            else "",
                            "input_id": item.input_id,
                            "input_label": _input_label(
                                item.input_type, item.input_id
                            ),
                            "mode": str(item.mode or ""),
                            "text": text,
                        }
                    )
    return found
