# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Virtual Xbox 360 pads fed through ViGEmBus."""

from __future__ import annotations

import enum
import logging
import threading
from typing import Any

from gremlin.common import SingletonMetaclass
from gremlin.error import GremlinError
from gremlin.types import HatDirection
from gremlin.util import clamp
from vigem import vigem_client
from vigem.vigem_commons import VIGEM_ERRORS, XUSB_BUTTON, XUSB_REPORT

_LOG = logging.getLogger("system")
VIGEM_OK = VIGEM_ERRORS.VIGEM_ERROR_NONE.value
MAX_PADS = 4


class XboxError(GremlinError):
    def __init__(self, value: str) -> None:
        super().__init__(value)


class XboxTarget(enum.Enum):
    LEFT_STICK_X = "left_stick_x"
    LEFT_STICK_Y = "left_stick_y"
    RIGHT_STICK_X = "right_stick_x"
    RIGHT_STICK_Y = "right_stick_y"
    LEFT_TRIGGER = "left_trigger"
    RIGHT_TRIGGER = "right_trigger"
    A = "a"
    B = "b"
    X = "x"
    Y = "y"
    LEFT_SHOULDER = "left_shoulder"
    RIGHT_SHOULDER = "right_shoulder"
    LEFT_THUMB = "left_thumb"
    RIGHT_THUMB = "right_thumb"
    START = "start"
    BACK = "back"
    GUIDE = "guide"
    DPAD_UP = "dpad_up"
    DPAD_DOWN = "dpad_down"
    DPAD_LEFT = "dpad_left"
    DPAD_RIGHT = "dpad_right"
    DPAD = "dpad"

    @property
    def label(self) -> str:
        return _TARGET_LABELS[self]

    @property
    def kind(self) -> str:
        if self in _STICKS:
            return "stick"
        if self in _TRIGGERS:
            return "trigger"
        if self is XboxTarget.DPAD:
            return "hat"
        return "button"

    @classmethod
    def from_string(cls, value: str) -> XboxTarget:
        key = str(value or "").strip().lower().replace("-", "_")
        for item in cls:
            if item.value == key:
                return item
        raise XboxError(f"Unknown Xbox target '{value}'")


_TARGET_LABELS = {
    XboxTarget.LEFT_STICK_X: "Left Stick X",
    XboxTarget.LEFT_STICK_Y: "Left Stick Y",
    XboxTarget.RIGHT_STICK_X: "Right Stick X",
    XboxTarget.RIGHT_STICK_Y: "Right Stick Y",
    XboxTarget.LEFT_TRIGGER: "Left Trigger",
    XboxTarget.RIGHT_TRIGGER: "Right Trigger",
    XboxTarget.A: "A",
    XboxTarget.B: "B",
    XboxTarget.X: "X",
    XboxTarget.Y: "Y",
    XboxTarget.LEFT_SHOULDER: "LB",
    XboxTarget.RIGHT_SHOULDER: "RB",
    XboxTarget.LEFT_THUMB: "LS",
    XboxTarget.RIGHT_THUMB: "RS",
    XboxTarget.START: "Start",
    XboxTarget.BACK: "Back",
    XboxTarget.GUIDE: "Guide",
    XboxTarget.DPAD_UP: "DPad Up",
    XboxTarget.DPAD_DOWN: "DPad Down",
    XboxTarget.DPAD_LEFT: "DPad Left",
    XboxTarget.DPAD_RIGHT: "DPad Right",
    XboxTarget.DPAD: "DPad",
}
_STICKS = {
    XboxTarget.LEFT_STICK_X,
    XboxTarget.LEFT_STICK_Y,
    XboxTarget.RIGHT_STICK_X,
    XboxTarget.RIGHT_STICK_Y,
}
_TRIGGERS = {XboxTarget.LEFT_TRIGGER, XboxTarget.RIGHT_TRIGGER}
_BUTTON_MASK = {
    XboxTarget.A: XUSB_BUTTON.XUSB_GAMEPAD_A,
    XboxTarget.B: XUSB_BUTTON.XUSB_GAMEPAD_B,
    XboxTarget.X: XUSB_BUTTON.XUSB_GAMEPAD_X,
    XboxTarget.Y: XUSB_BUTTON.XUSB_GAMEPAD_Y,
    XboxTarget.LEFT_SHOULDER: XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER,
    XboxTarget.RIGHT_SHOULDER: XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER,
    XboxTarget.LEFT_THUMB: XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB,
    XboxTarget.RIGHT_THUMB: XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB,
    XboxTarget.START: XUSB_BUTTON.XUSB_GAMEPAD_START,
    XboxTarget.BACK: XUSB_BUTTON.XUSB_GAMEPAD_BACK,
    XboxTarget.GUIDE: XUSB_BUTTON.XUSB_GAMEPAD_GUIDE,
    XboxTarget.DPAD_UP: XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP,
    XboxTarget.DPAD_DOWN: XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN,
    XboxTarget.DPAD_LEFT: XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT,
    XboxTarget.DPAD_RIGHT: XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT,
}
_HAT_BITS = {
    HatDirection.Center: 0,
    HatDirection.North: int(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP),
    HatDirection.South: int(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN),
    HatDirection.West: int(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT),
    HatDirection.East: int(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT),
    HatDirection.NorthEast: int(
        XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
    ),
    HatDirection.SouthEast: int(
        XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
    ),
    HatDirection.SouthWest: int(
        XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT
    ),
    HatDirection.NorthWest: int(
        XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT
    ),
}
_DPAD_MASK = int(
    XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP
    | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN
    | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT
    | XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT
)


def _stick_to_short(value: float) -> int:
    scaled = int(round(clamp(float(value), -1.0, 1.0) * 32767))
    return max(-32768, min(32767, scaled))


def _trigger_to_byte(value: float) -> int:
    return int(round(clamp(float(value), 0.0, 1.0) * 255))


def _as_hat(value: Any) -> HatDirection:
    if isinstance(value, HatDirection):
        return value
    if value is None:
        return HatDirection.Center
    if isinstance(value, bool):
        return HatDirection.North if value else HatDirection.Center
    if isinstance(value, tuple):
        try:
            return HatDirection.to_enum(value)
        except Exception:
            return HatDirection.Center
    text = str(value).strip().lower()
    if text in {"", "false", "none", "center", "0", "off"}:
        return HatDirection.Center
    if text in {"true", "1", "on"}:
        return HatDirection.North
    try:
        return HatDirection.to_enum(text)
    except Exception:
        return HatDirection.Center


class XboxPad:
    def __init__(self, pad_id: int, busp: int) -> None:
        self.pad_id = pad_id
        self._busp = busp
        self._lib = vigem_client.client()
        if self._lib is None:
            raise XboxError(vigem_client.load_error() or "ViGEmClient.dll missing")
        self._devicep = self._lib.vigem_target_x360_alloc()
        if not self._devicep:
            raise XboxError(f"Xbox pad {pad_id}: target alloc failed")
        # The device this pad becomes is the next one with the Xbox ID.
        from vigem import own_pads

        own_pads.before_plug()
        err = self._lib.vigem_target_add(self._busp, self._devicep)
        if err != VIGEM_OK:
            self._lib.vigem_target_free(self._devicep)
            raise XboxError(f"Xbox pad {pad_id}: plug-in failed ({err:#x})")
        self.report = XUSB_REPORT(0, 0, 0, 0, 0, 0, 0)
        self.update()

    def close(self) -> None:
        if self._lib is None or not self._devicep:
            return
        try:
            self._lib.vigem_target_remove(self._busp, self._devicep)
        except Exception:
            pass
        try:
            self._lib.vigem_target_free(self._devicep)
        except Exception:
            pass
        self._devicep = 0

    def update(self) -> None:
        if self._lib is None or not self._devicep:
            return
        err = self._lib.vigem_target_x360_update(self._busp, self._devicep, self.report)
        if err != VIGEM_OK:
            _LOG.warning("Xbox pad %s update failed (%#x)", self.pad_id, err)

    def apply(self, target: XboxTarget, value: Any) -> None:
        if target in _STICKS:
            raw = _stick_to_short(float(value))
            if target is XboxTarget.LEFT_STICK_X:
                self.report.sThumbLX = raw
            elif target is XboxTarget.LEFT_STICK_Y:
                self.report.sThumbLY = raw
            elif target is XboxTarget.RIGHT_STICK_X:
                self.report.sThumbRX = raw
            else:
                self.report.sThumbRY = raw
        elif target in _TRIGGERS:
            raw = _trigger_to_byte((float(value) + 1.0) * 0.5)
            if target is XboxTarget.LEFT_TRIGGER:
                self.report.bLeftTrigger = raw
            else:
                self.report.bRightTrigger = raw
        elif target is XboxTarget.DPAD:
            bits = _HAT_BITS.get(_as_hat(value), 0)
            self.report.wButtons = (self.report.wButtons & ~_DPAD_MASK) | bits
        else:
            mask = int(_BUTTON_MASK[target])
            pressed = bool(value)
            if pressed:
                self.report.wButtons = self.report.wButtons | mask
            else:
                self.report.wButtons = self.report.wButtons & ~mask
        self.update()


class XboxProxy(metaclass=SingletonMetaclass):
    def __init__(self) -> None:
        self._busp = 0
        self._pads: dict[int, XboxPad] = {}
        # Held while a pad is looked up or plugged in, and while all are
        # unplugged: two threads could each plug in pad N (a ghost pad).
        self._lock = threading.RLock()
        self._available: bool | None = None

    def available(self) -> bool:
        # Remember only success, so installing ViGEmBus later is picked up.
        if not self._available:
            self._available = self._probe()
        return self._available

    def _probe(self) -> bool:
        lib = vigem_client.client()
        if lib is None:
            return False
        busp = lib.vigem_alloc()
        if not busp:
            return False
        try:
            err = lib.vigem_connect(busp)
            return err == VIGEM_OK
        finally:
            try:
                lib.vigem_disconnect(busp)
            except Exception:
                pass
            lib.vigem_free(busp)

    def _ensure_bus(self) -> int:
        if self._busp:
            return self._busp
        lib = vigem_client.client()
        if lib is None:
            raise XboxError(vigem_client.load_error() or "ViGEmClient.dll missing")
        busp = lib.vigem_alloc()
        if not busp:
            raise XboxError("vigem_alloc failed")
        err = lib.vigem_connect(busp)
        if err != VIGEM_OK:
            lib.vigem_free(busp)
            raise XboxError(
                f"ViGEmBus connect failed ({err:#x}). Install ViGEmBus 1.22.0."
            )
        self._busp = busp
        self._available = True
        return self._busp

    def __getitem__(self, pad_id: int) -> XboxPad:
        ident = int(pad_id)
        if ident < 1 or ident > MAX_PADS:
            raise XboxError(f"Xbox pad id must be 1-{MAX_PADS}, got {ident}")
        with self._lock:
            pad = self._pads.get(ident)
            if pad is None:
                pad = XboxPad(ident, self._ensure_bus())
                self._pads[ident] = pad
            return pad

    def snapshot(self, pad_id: int) -> dict[str, float] | None:
        """Last report for an existing pad. Does not plug a new pad."""
        pad = self._pads.get(int(pad_id))
        if pad is None:
            return None
        report = pad.report
        buttons = int(report.wButtons)

        def _btn(mask: XUSB_BUTTON) -> float:
            return 1.0 if buttons & int(mask) else 0.0

        def _stick(raw: int) -> float:
            return max(-1.0, min(1.0, float(raw) / 32767.0)) if raw else 0.0

        return {
            "left_stick_x": _stick(int(report.sThumbLX)),
            "left_stick_y": _stick(int(report.sThumbLY)),
            "right_stick_x": _stick(int(report.sThumbRX)),
            "right_stick_y": _stick(int(report.sThumbRY)),
            "left_trigger": float(report.bLeftTrigger) / 255.0,
            "right_trigger": float(report.bRightTrigger) / 255.0,
            "a": _btn(XUSB_BUTTON.XUSB_GAMEPAD_A),
            "b": _btn(XUSB_BUTTON.XUSB_GAMEPAD_B),
            "x": _btn(XUSB_BUTTON.XUSB_GAMEPAD_X),
            "y": _btn(XUSB_BUTTON.XUSB_GAMEPAD_Y),
            "left_shoulder": _btn(XUSB_BUTTON.XUSB_GAMEPAD_LEFT_SHOULDER),
            "right_shoulder": _btn(XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_SHOULDER),
            "left_thumb": _btn(XUSB_BUTTON.XUSB_GAMEPAD_LEFT_THUMB),
            "right_thumb": _btn(XUSB_BUTTON.XUSB_GAMEPAD_RIGHT_THUMB),
            "start": _btn(XUSB_BUTTON.XUSB_GAMEPAD_START),
            "back": _btn(XUSB_BUTTON.XUSB_GAMEPAD_BACK),
            "guide": _btn(XUSB_BUTTON.XUSB_GAMEPAD_GUIDE),
            "dpad_up": _btn(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_UP),
            "dpad_down": _btn(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_DOWN),
            "dpad_left": _btn(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_LEFT),
            "dpad_right": _btn(XUSB_BUTTON.XUSB_GAMEPAD_DPAD_RIGHT),
            "dpad": 1.0 if buttons & _DPAD_MASK else 0.0,
        }

    def reset(self) -> None:
        with self._lock:
            lib = vigem_client.client()
            for pad in list(self._pads.values()):
                pad.close()
            self._pads.clear()
            if lib is not None and self._busp:
                try:
                    lib.vigem_disconnect(self._busp)
                except Exception:
                    pass
                try:
                    lib.vigem_free(self._busp)
                except Exception:
                    pass
            self._busp = 0
