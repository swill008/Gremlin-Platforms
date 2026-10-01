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
import threading
import time
from typing import Any

from gremlin.modules import registry
from gremlin.modules.claim import claim_allows, claim_ids

syslog = logging.getLogger("system")

# Claims are re-read from the module files at most this often (seconds).
_CLAIM_TTL = 1.0

_lock = threading.Lock()
_claims_at = 0.0
_vjoy_claims: dict[int, dict] = {}
_blocked: set[tuple] = set()


# --- claims -----------------------------------------------------------------


def _refresh_claims(force: bool = False) -> None:
    global _claims_at, _vjoy_claims
    now = time.monotonic()
    if not force and now - _claims_at < _CLAIM_TTL:
        return
    with _lock:
        if not force and now - _claims_at < _CLAIM_TTL:
            return
        vjoy: dict[int, dict] = {}
        try:
            outputs = registry.outputs()
        except Exception:
            outputs = []
        for module in outputs:
            if is_xbox_module(module.name):
                continue
            vjoy_id = registry.resolve_vjoy_id(module.name, module.bound_guid)
            if vjoy_id and vjoy_id not in vjoy:
                vjoy[vjoy_id] = module.claim
        _vjoy_claims = vjoy
        _claims_at = time.monotonic()


def refresh() -> None:
    """Re-read every output module now (on activation and after a save)."""
    _refresh_claims(force=True)


def vjoy_claim(vjoy_id: int) -> dict:
    """The claim of the output module that drives this vJoy device."""
    _refresh_claims()
    return _vjoy_claims.get(int(vjoy_id), {})


def vjoy_allows(vjoy_id: int, kind: str, input_id: int) -> bool:
    return claim_allows(vjoy_claim(vjoy_id), kind, input_id)


def is_xbox_module(name: str) -> bool:
    return "xbox" in str(name or "").lower()


# --- logging ----------------------------------------------------------------


def _log_once(key: tuple, message: str) -> None:
    if key in _blocked:
        return
    _blocked.add(key)
    syslog.warning(message)


def clear_blocked_log() -> None:
    """Allow each blocked output to be logged again (new run)."""
    _blocked.clear()


# --- vJoy -------------------------------------------------------------------


def _vjoy_proxy() -> Any:  # noqa: ANN401
    from vjoy.vjoy import VJoyProxy

    return VJoyProxy


def _open_vjoy(vjoy_id: int) -> Any | None:  # noqa: ANN401
    """The vJoy device, opened for Gremlin if it is not yet. None if it fails."""
    try:
        return _vjoy_proxy()()[int(vjoy_id)]
    except Exception as exc:
        _log_once(("vjoy-open", int(vjoy_id)), f"vJoy {vjoy_id} unavailable: {exc}")
        return None


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
    if not _passes(vjoy_id, kind, input_id):
        return False
    dev = _open_vjoy(vjoy_id)
    if dev is None:
        return False
    if not _has(dev, kind, input_id):
        _log_once(
            ("vjoy-missing", int(vjoy_id), kind, input_id),
            f"Output blocked: vJoy {vjoy_id} has no {kind} {input_id}.",
        )
        return False
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
        return False
    return True


def write_vjoy_axis_linear(vjoy_id: int, linear_index: int, value: float) -> bool:
    """Write an axis given by its position in the axis list (1 = first axis)."""
    dev = _open_vjoy(vjoy_id)
    if dev is None or not dev.is_axis_valid(linear_index=int(linear_index)):
        return False
    return write_vjoy(vjoy_id, "axis", dev.axis_id(int(linear_index)), value)


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
    """Current value of a claimed vJoy output; neutral when unclaimed or missing."""
    input_id = int(input_id)
    if not vjoy_allows(vjoy_id, kind, input_id):
        return _neutral(kind)
    dev = _open_vjoy(vjoy_id)
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


def vjoy_owned(vjoy_id: int) -> bool:
    """True while Gremlin holds this vJoy device."""
    dev = _opened_vjoy(vjoy_id)
    try:
        return dev is not None and bool(dev.is_owned())
    except Exception:
        return False


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


def vjoy_exists(vjoy_id: int) -> bool:
    """True when the vJoy driver has this device enabled."""
    try:
        from vjoy import vjoy

        return bool(vjoy.device_exists(int(vjoy_id)))
    except Exception:
        return False


# --- Xbox (ViGEm) -----------------------------------------------------------


def xbox_available() -> bool:
    """True when ViGEmBus and ViGEmClient.dll can be used."""
    try:
        from vigem.xbox import XboxProxy

        return bool(XboxProxy().available())
    except Exception:
        return False


def xbox_error() -> str:
    """Why the Xbox driver cannot be used ("" when it can)."""
    from vigem.ids import vigem_client_error

    return vigem_client_error()


# --- lifecycle --------------------------------------------------------------


def reset_drivers() -> None:
    """Release every vJoy device and unplug every Xbox pad Gremlin holds."""
    try:
        _vjoy_proxy().reset()
    except Exception:
        syslog.exception("vJoy reset failed")
    try:
        from vigem.xbox import XboxProxy

        XboxProxy().reset()
    except Exception:
        syslog.exception("Xbox reset failed")
    clear_blocked_log()
