# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Out-of-step check for control tracing (D-01-TRACE, contract item 6).

While tracing is on, once a second, for every device ticked for the check:
(a) each ticked axis is read from the driver and compared with the last RAW
value the program received; (b) each vJoy axis the trace saw written is read
back and compared with what was written. Apart for over a second gives one
OUT OF STEP warning per episode. A ticked stick with no input for 4 s gets
one EVENT (info) per quiet spell. Reading only; never raises.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Any

from gremlin import clock, threads, trace
from gremlin.modules.wiring import AXIS_SHORT

syslog = logging.getLogger("system")

INTERVAL = 1.0
# Apart for longer than this before it is called out of step (seconds).
GRACE = 1.0
STICK_TOLERANCE = 0.05
VJOY_TOLERANCE = 0.02
QUIET_S = 4.0

_lock = threading.Lock()
_timer: threading.Timer | None = None
_running = False
# Key -> when it was first seen apart (monotonic); in _warned once warned.
_apart_since: dict[tuple, float] = {}
_warned: set[tuple] = set()
# Device -> the last RAW time it was told quiet at (once per quiet spell).
_told_quiet: dict[uuid.UUID, float] = {}


# --- start / stop --------------------------------------------------------------


def running() -> bool:
    return _running


def start() -> None:
    global _running
    with _lock:
        if _running:
            return
        _running = True
        _apart_since.clear()
        _warned.clear()
        _told_quiet.clear()
        _schedule()


def stop() -> None:
    global _running, _timer
    with _lock:
        _running = False
        timer, _timer = _timer, None
    if timer is not None:
        timer.cancel()


def _schedule() -> None:
    global _timer
    # Caller holds _lock.
    _timer = threads.timer("Trace out-of-step check", INTERVAL, _tick)


def _tick() -> None:
    try:
        check()
    except Exception:
        syslog.debug("Trace out-of-step check failed", exc_info=True)
    with _lock:
        if _running:
            _schedule()


def _on_change(*_args: object) -> None:
    if trace.enabled():
        start()
    else:
        stop()


def install() -> None:
    """Follows tracing on/off from now on (the watch runs while it is on)."""
    trace.on_change(_on_change)
    _on_change()


# --- the check -----------------------------------------------------------------


def _axis_name(axis_id: int) -> str:
    return AXIS_SHORT.get(int(axis_id), f"axis {axis_id}")


def _clock_text(when: float) -> str:
    import time

    try:
        return time.strftime("%H:%M:%S", time.localtime(when))
    except (OverflowError, OSError, ValueError):
        return "?"


def _apart(key: tuple, is_apart: bool, now: float) -> bool:
    """True once when key has been apart for over GRACE (one per episode)."""
    if not is_apart:
        _apart_since.pop(key, None)
        _warned.discard(key)
        return False
    first = _apart_since.setdefault(key, now)
    if now - first > GRACE and key not in _warned:
        _warned.add(key)
        return True
    return False


def _calibrated(guid: Any, axis_index: int) -> float:  # noqa: ANN401
    """The stick's axis now, calibrated the way RAW values are."""
    import dill
    from gremlin import event_handler, util

    raw = int(dill.DILL.get_axis(guid, axis_index))
    # The listener's calibrations, if it exists (never made from this thread).
    listener = getattr(event_handler.EventListener, "instance", None)
    calibrations = getattr(listener, "_calibrations", None) or {}
    calibration = calibrations.get((guid, axis_index))
    if calibration is not None:
        return float(calibration(raw))
    return float(util.with_default_center_calibration(raw))


def _device(device_uuid: uuid.UUID) -> Any | None:  # noqa: ANN401
    from gremlin import device_initialization

    for dev in device_initialization.physical_devices() + list(
        device_initialization.vjoy_devices()
    ):
        if dev.device_guid.uuid == device_uuid:
            return dev
    return None


def _axis_indices(dev: Any) -> list[int]:  # noqa: ANN401
    return [
        entry.axis_index for entry in dev.axis_map if int(entry.axis_index) > 0
    ]


def _check_stick(device_uuid: uuid.UUID, now: float) -> None:
    dev = _device(device_uuid)
    if dev is None:
        return
    ticks = trace.device_ticks(device_uuid)
    axes = _axis_indices(dev) if ticks.get("all") else sorted(ticks.get("axis", ()))
    latest: float | None = None
    for axis_index in axes:
        last = trace.last_raw(device_uuid, "axis", axis_index)
        if last is None:
            continue
        value, when = last
        latest = when if latest is None else max(latest, when)
        try:
            polled = _calibrated(dev.device_guid, axis_index)
        except Exception:
            continue
        key = ("stick", device_uuid, axis_index)
        if _apart(key, abs(polled - value) > STICK_TOLERANCE, now):
            label = trace.control_label(device_uuid, "axis", axis_index)
            trace.warn(
                trace.OUT_OF_STEP,
                label,
                f"stick reads {polled:.3f} (polled), last input event {value:.3f} "
                f"at {_clock_text(when)} · the program isn't getting this "
                "stick's moves",
            )
    _check_quiet(device_uuid, dev, latest)


def _check_quiet(device_uuid: uuid.UUID, dev: Any, latest: float | None) -> None:  # noqa: ANN401
    """One EVENT per quiet spell of a ticked stick (info only)."""
    since = trace.since()
    start_at = latest if latest is not None else since
    if start_at is None:
        return
    if clock.now() - start_at <= QUIET_S:
        return
    if _told_quiet.get(device_uuid) == start_at:
        return
    _told_quiet[device_uuid] = start_at
    trace.event(
        f"{getattr(dev, 'name', 'stick')}: no input from this stick for "
        f"{QUIET_S:.1f} s while plugged in (info only: a still stick is normal)"
    )


def _vjoy_read_back(vjoy_id: int, axis_id: int) -> float:
    """The vJoy axis as Windows sees it (its joystick in the driver's list),
    else what the output module holds."""
    from gremlin import device_initialization, util

    for dev in device_initialization.vjoy_devices():
        if dev.vjoy_id == vjoy_id:
            import dill

            raw = int(dill.DILL.get_axis(dev.device_guid, axis_id))
            return float(util.with_default_center_calibration(raw))
    from gremlin.modules import output

    return float(output.vjoy_value(vjoy_id, "axis", axis_id))


def _check_vjoy(now: float) -> None:
    # Every vJoy axis the trace saw written (16 devices x 8 axes: cheap).
    for vjoy_id in range(1, 17):
        for axis_id in AXIS_SHORT:
            last = trace.last_written(vjoy_id, "axis", axis_id)
            if last is None:
                continue
            written = float(last[0])
            try:
                shows = _vjoy_read_back(vjoy_id, axis_id)
            except Exception:
                continue
            key = ("vjoy", vjoy_id, axis_id)
            name = f"vJoy {vjoy_id} {_axis_name(axis_id)}"
            if _apart(key, abs(shows - written) > VJOY_TOLERANCE, now):
                trace.warn(
                    trace.OUT_OF_STEP,
                    name,
                    f"{name} shows {shows:.3f}, last written {written:.3f}",
                )


def check(now: float | None = None) -> None:
    """One pass of the check (the timer runs it every second)."""
    if not trace.enabled():
        return
    if now is None:
        now = clock.monotonic()
    checked = False
    for device_uuid in trace.ticked_devices():
        try:
            if not trace.oos_ticked(device_uuid):
                continue
            checked = True
            _check_stick(device_uuid, now)
        except Exception:
            syslog.debug("Trace out-of-step check failed", exc_info=True)
    if checked:
        try:
            _check_vjoy(now)
        except Exception:
            syslog.debug("Trace vJoy read-back failed", exc_info=True)
