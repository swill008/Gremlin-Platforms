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
_vjoy_names: dict[int, str] = {}
_xbox_modules: dict[int, registry.Module] = {}
_vjoy_modules: dict[int, registry.Module] = {}
_blocked: set[tuple] = set()

# A vJoy that failed to open is tried again at most this often (seconds).
_VJOY_RETRY = 3.0
_vjoy_failed_at: dict[int, float] = {}
_told_busy: set[int] = set()


# --- claims -----------------------------------------------------------------


def _refresh_claims(force: bool = False) -> None:
    global _claims_at, _vjoy_claims, _vjoy_names, _vjoy_modules, _xbox_modules
    now = time.monotonic()
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
            outputs = []
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
        _claims_at = time.monotonic()


def refresh() -> None:
    """Re-read every output module now (on activation and after a save)."""
    _refresh_claims(force=True)


def vjoy_claim(vjoy_id: int) -> dict:
    """The claim of the output module that drives this vJoy device."""
    _refresh_claims()
    return _vjoy_claims.get(int(vjoy_id), {})


def vjoy_modules() -> list[tuple[int, registry.Module]]:
    """vJoy output modules, one per vJoy device, by vJoy number (read fresh)."""
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


def _log_once(key: tuple, message: str) -> None:
    if key in _blocked:
        return
    _blocked.add(key)
    syslog.warning(message)


def clear_blocked_log() -> None:
    """Allow each blocked output to be logged again (new run)."""
    _blocked.clear()
    _vjoy_failed_at.clear()
    _told_busy.clear()


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
    failed_at = _vjoy_failed_at.get(vid)
    if failed_at is not None and time.monotonic() - failed_at < _VJOY_RETRY:
        return None
    try:
        dev = _vjoy_proxy()()[vid]
    except Exception as exc:
        from gremlin.error import VJoyBusyError

        _vjoy_failed_at[vid] = time.monotonic()
        if isinstance(exc, VJoyBusyError):
            _log_once(
                ("vjoy-open", vid),
                f"vJoy {vid} is in use by another program. Its outputs won't "
                "move until that program lets it go.",
            )
            if vid not in _told_busy:
                _told_busy.add(vid)
                from gremlin.signal import display_error

                display_error(
                    f"vJoy {vid} is in use by another program.",
                    "Its outputs won't move until that program lets it go.",
                )
        else:
            _log_once(("vjoy-open", vid), f"vJoy {vid} unavailable: {exc}")
        return None
    if _vjoy_failed_at.pop(vid, None) is not None:
        syslog.info(f"vJoy {vid} opened")
    return dev


def vjoy_ids() -> list[int]:
    """The vJoy devices set up in the driver (1-16)."""
    from vjoy import vjoy

    return [i for i in range(1, 17) if vjoy.device_exists(i)]


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
            dev = _open_vjoy(self.vjoy_id)
            valid = dev is not None and dev.is_axis_valid(linear_index=linear_index)
            axis_id = dev.axis_id(linear_index) if valid else 0
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
    on the pad is available, nothing is claimed (as in GremlinEx).
    """
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


# --- lifecycle --------------------------------------------------------------


def reset_vjoy() -> None:
    """Release every vJoy device Gremlin holds."""
    try:
        _vjoy_proxy().reset()
    except Exception:
        syslog.exception("vJoy reset failed")


def reset_drivers() -> None:
    """Release every vJoy device and unplug every Xbox pad Gremlin holds."""
    reset_vjoy()
    try:
        from vigem.xbox import XboxProxy

        XboxProxy().reset()
    except Exception:
        syslog.exception("Xbox reset failed")
    clear_blocked_log()
