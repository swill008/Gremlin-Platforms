# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import abc
import ctypes
import ctypes.wintypes
import functools
import math
import threading
import uuid
from typing import TYPE_CHECKING

from gremlin import clock, run_scope, threads, trace
from gremlin.common import SingletonDecorator
from gremlin.types import MouseButton

if TYPE_CHECKING:
    from gremlin.event_handler import Event


"""Defines flags used when specifying MOUSEINPUT structures.

https://msdn.microsoft.com/en-us/library/ms646273(v=VS.85).aspx
"""
WHEEL_DELTA = 120
XBUTTON1 = 0x0001
XBUTTON2 = 0x0002
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_HWHEEL = 0x01000
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_MOVE_NOCOALESCE = 0x2000
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_XDOWN = 0x0080
MOUSEEVENTF_XUP = 0x0100


"""Defines data structure type for INPUT structures.

https://msdn.microsoft.com/en-us/library/ms646270(v=vs.85).aspx
"""
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1


class Vector2:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    @classmethod
    def from_angle(cls, angle: float) -> Vector2:
        """Converts an angle in degree into a 2D vector.

        Args:
            angle: angular direction in degree

        Returns:
            2D vector representing the direction
        """
        angle_rad = math.radians(angle)
        return Vector2(math.cos(angle_rad), math.sin(angle_rad))

    @classmethod
    def from_compass_direction(cls, degree: float) -> Vector2:
        """A screen direction (y grows downwards) from a compass heading in
        degree: 0 up, 90 right."""
        return cls.from_angle(degree - 90.0)

    def magnitude(self) -> float:
        return math.sqrt(self.x**2 + self.y**2)

    def normalize(self) -> Vector2:
        """Returns a unit vector representation of the instance's direction.

        Returns:
            Unit length vector with the same direction
        """
        magnitude = self.magnitude()
        if magnitude < 0.00001:
            return Vector2(0, 0)
        return Vector2(self.x / magnitude, self.y / magnitude)

    def __add__(self, other: Vector2) -> Vector2:
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other: Vector2) -> Vector2:
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> Vector2:
        return Vector2(self.x * scalar, self.y * scalar)

    def __str__(self) -> str:
        return f"[{self.x}, {self.y}]"


# Motion is sent at a fixed 100 Hz (R9c: no option).
TICK_INTERVAL = 0.01

# A late tick catches up on at most this many ticks: a stall doesn't make the
# cursor jump.
_MAX_TICKS_BEHIND = 5

# How long an idle loop waits before it looks at its stop flag again.
_IDLE_WAIT = 0.5

# One motion piece: the Map to Mouse action's id and the input driving it.
type MotionKey = tuple[uuid.UUID, Event]


class MotionSource(abc.ABC):
    """One input's share of the cursor motion."""

    @abc.abstractmethod
    def velocity(self, delta_t: float) -> Vector2:
        """The velocity (px/s) for the next delta_t seconds; advances any
        ramp by delta_t."""

    @abc.abstractmethod
    def describe(self) -> str:
        """Trace text for this piece."""


class ConstantVelocity(MotionSource):
    """A velocity the input sets directly (an axis)."""

    def __init__(self, velocity: Vector2) -> None:
        self.current = velocity

    def velocity(self, delta_t: float) -> Vector2:
        return self.current

    def describe(self) -> str:
        return (
            f"Mouse motion {self.current.magnitude():.0f} px/s"
            f" heading {_heading(self.current)}°"
        )


class IncreasingVelocity(MotionSource):
    """A speed ramping from min_speed to max_speed along a direction (a
    button or hat; each has its own ramp)."""

    def __init__(
        self,
        direction: Vector2,
        min_speed: float,
        max_speed: float,
        time_to_max_speed: float,
    ) -> None:
        self.direction = direction
        if max_speed < min_speed:
            min_speed, max_speed = max_speed, min_speed
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.time_to_max_speed = time_to_max_speed
        self.speed = min_speed
        # A tiny ramp time would divide by almost nothing.
        if time_to_max_speed < 0.01:
            self.acceleration = 1e6
        else:
            self.acceleration = (max_speed - min_speed) / time_to_max_speed

    def velocity(self, delta_t: float) -> Vector2:
        # This step at the speed reached so far, then ramp up.
        current = self.direction * self.speed
        self.speed = min(self.max_speed, self.speed + self.acceleration * delta_t)
        return current

    def describe(self) -> str:
        if self.min_speed == self.max_speed:
            speed = f"{self.max_speed:.0f} px/s"
        else:
            speed = (
                f"{self.min_speed:.0f} to {self.max_speed:.0f} px/s"
                f" over {self.time_to_max_speed:g} s"
            )
        return f"Mouse motion {speed} heading {_heading(self.direction)}°"


def _heading(vector: Vector2) -> int:
    """Compass heading of a screen vector: 0 up, 90 right."""
    return round(math.degrees(math.atan2(vector.x, -vector.y))) % 360


def _integration_step(
    now: float, last_time: float, next_tick: float, interval: float
) -> tuple[float, float]:
    """The time to move for this tick and when the next tick is due.

    A late tick catches up on at most _MAX_TICKS_BEHIND ticks, and the next
    tick is never scheduled in the past.
    """
    delta_t = min(now - last_time, _MAX_TICKS_BEHIND * interval)
    return delta_t, max(next_tick + interval, now)


@SingletonDecorator
class MouseMotionManager:
    """Adds up every input's motion piece into one cursor motion.

    Pieces are keyed by (action id, input); the loop sends their vector sum
    at 100 Hz, carrying the part of a pixel left over to the next tick. The
    lock covers the bookkeeping only, never SendInput.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._sources: dict[MotionKey, MotionSource] = {}
        self._residual = Vector2(0.0, 0.0)
        self._has_sources = threading.Event()
        # Clear while a move is being sent: reset() waits for it.
        self._send_done = threading.Event()
        self._send_done.set()
        self._is_running = False
        self._thread: threading.Thread | None = None

    def set_velocity(self, key: MotionKey, velocity: Vector2) -> None:
        """Sets the piece of key to a constant velocity (px/s); zero removes it."""
        if velocity.magnitude() < 1e-6:
            self.clear(key)
            return
        with self._lock:
            old = self._sources.get(key)
            if isinstance(old, ConstantVelocity) and _same(old.current, velocity):
                return
            source = ConstantVelocity(velocity)
            self._sources[key] = source
            self._has_sources.set()
        _trace(source.describe())

    def set_accelerated_motion(
        self,
        key: MotionKey,
        direction: Vector2,
        min_speed: float,
        max_speed: float,
        time_to_max_speed: float,
    ) -> None:
        """Starts a ramping piece for key; one that exists keeps the speed it
        reached and only changes direction."""
        with self._lock:
            source = self._sources.get(key)
            if isinstance(source, IncreasingVelocity):
                if _same(source.direction, direction):
                    return
                source.direction = direction
            else:
                source = IncreasingVelocity(
                    direction, min_speed, max_speed, time_to_max_speed
                )
                self._sources[key] = source
            self._has_sources.set()
            text = source.describe()
        _trace(text)

    def clear(self, key: MotionKey) -> None:
        """Removes the piece of key (other pieces keep moving)."""
        with self._lock:
            if self._sources.pop(key, None) is None:
                return
            if not self._sources:
                self._go_idle()
        _trace("Mouse motion stopped")

    def reset(self) -> None:
        """Drops every piece; no move is sent after this returns."""
        with self._lock:
            self._sources.clear()
            self._go_idle()
        # A move worked out just before is let finish (bounded).
        if threading.current_thread() is not self._thread:
            self._send_done.wait(0.2)

    def start(self) -> None:
        """Starts the loop that sends the motion."""
        if self._thread is not None and self._thread.is_alive():
            return
        self.reset()
        # Set here, not in the thread: a stop() right after start() must not
        # be undone when the thread starts.
        self._is_running = True
        self._thread = threads.start(
            "mouse motion", self._control_loop, stop=self._ask_to_stop
        )

    def _ask_to_stop(self) -> None:
        self._is_running = False
        self._has_sources.set()  # wakes an idle loop

    def stop(self) -> None:
        """Ends the loop (bounded) and drops all motion."""
        self._ask_to_stop()
        thread = self._thread
        if thread is not None and thread.is_alive():
            if thread is not threading.current_thread():
                thread.join(timeout=2.0)
        self._thread = None
        self.reset()

    def _go_idle(self) -> None:
        """No motion: the loop waits; the carried part of a pixel goes.
        The caller holds the lock."""
        self._residual = Vector2(0.0, 0.0)
        self._has_sources.clear()

    def _step(self, delta_t: float) -> tuple[int, int]:
        """Whole pixels to move for delta_t seconds of every piece's motion."""
        with self._lock:
            return self._step_locked(delta_t)

    def _step_locked(self, delta_t: float) -> tuple[int, int]:
        total = Vector2(0.0, 0.0)
        for source in self._sources.values():
            total += source.velocity(delta_t)
        self._residual += total * delta_t
        pixels_x = _whole(self._residual.x)
        pixels_y = _whole(self._residual.y)
        # The part of a pixel left over moves with the next tick.
        self._residual = Vector2(
            self._residual.x - pixels_x, self._residual.y - pixels_y
        )
        return pixels_x, pixels_y

    def _control_loop(self) -> None:
        last_time = next_tick = clock.monotonic()
        while self._is_running:
            if not self._has_sources.is_set():
                self._has_sources.wait(_IDLE_WAIT)
                last_time = next_tick = clock.monotonic()
                continue
            now = clock.monotonic()
            delta_t, next_tick = _integration_step(
                now, last_time, next_tick, TICK_INTERVAL
            )
            last_time = now
            with self._lock:
                if not self._is_running or not self._sources:
                    continue
                delta_x, delta_y = self._step_locked(delta_t)
                moving = bool(delta_x or delta_y)
                if moving:
                    self._send_done.clear()
            if moving:
                try:
                    mouse_relative_motion(delta_x, delta_y)
                finally:
                    self._send_done.set()
            clock.sleep(max(0.0, next_tick - clock.monotonic()))


def _whole(value: float) -> int:
    """Whole pixels in value, towards zero; 2.9999999 (a float sum's error)
    counts as 3."""
    return math.trunc(value + math.copysign(1e-9, value))


def _same(a: Vector2, b: Vector2) -> bool:
    return abs(a.x - b.x) < 1e-6 and abs(a.y - b.y) < 1e-6


def _trace(text: str) -> None:
    """A Trace OUTPUT line for the input being handled (G-c)."""
    if trace.enabled():
        trace.mouse(text)


class _MOUSEINPUT(ctypes.Structure):
    """Defines the MOUSEINPUT structure.

    https://msdn.microsoft.com/en-us/library/ms646273(v=VS.85).aspx
    """

    _fields_ = (
        ("dx", ctypes.wintypes.LONG),
        ("dy", ctypes.wintypes.LONG),
        ("mouseData", ctypes.wintypes.DWORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
    )


class _KEYBDINPUT(ctypes.Structure):
    """Defines the KEYBDINPUT structure.

    https://msdn.microsoft.com/en-us/library/ms646271(v=vs.85).aspx
    """

    _fields_ = (
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("wExtraInfo", ctypes.POINTER(ctypes.wintypes.ULONG)),
    )


class _INPUTunion(ctypes.Union):
    """Defines the INPUT union type.

    https://msdn.microsoft.com/en-us/library/ms646270(v=vs.85).aspx
    """

    _fields_ = (("mi", _MOUSEINPUT), ("ki", _KEYBDINPUT))


class _INPUT(ctypes.Structure):
    """Defines the INPUT structure.

    https://msdn.microsoft.com/en-us/library/ms646270(v=vs.85).aspx
    """

    _fields_ = (("type", ctypes.wintypes.DWORD), ("union", _INPUTunion))


def mouse_relative_motion(dx: int, dy: int) -> None:
    _send_input(_mouse_input(MOUSEEVENTF_MOVE, dx, dy))


def _note_button(button: MouseButton, is_pressed: bool) -> None:
    """A button pressed during a Run is held in run_scope (the one list of
    held keys and buttons) until it is released: by whoever pressed it, by
    the macro that pressed it ending early, or at Stop."""
    if is_pressed:
        run_scope.hold(
            run_scope.current_owner(),
            "mouse",
            button,
            functools.partial(mouse_release, button),
        )
    else:
        run_scope.let_go(run_scope.current_owner(), "mouse", button)


def mouse_press(button: MouseButton) -> None:
    _note_button(button, True)
    _trace(f"Mouse {button.name} = pressed")
    if button == MouseButton.Left:
        _send_input(_mouse_input(MOUSEEVENTF_LEFTDOWN))
    elif button == MouseButton.Right:
        _send_input(_mouse_input(MOUSEEVENTF_RIGHTDOWN))
    elif button == MouseButton.Middle:
        _send_input(_mouse_input(MOUSEEVENTF_MIDDLEDOWN))
    elif button == MouseButton.Back:
        _send_input(_mouse_input(MOUSEEVENTF_XDOWN, data=XBUTTON1))
    elif button == MouseButton.Forward:
        _send_input(_mouse_input(MOUSEEVENTF_XDOWN, data=XBUTTON2))


def mouse_release(button: MouseButton) -> None:
    _note_button(button, False)
    _trace(f"Mouse {button.name} = released")
    if button == MouseButton.Left:
        _send_input(_mouse_input(MOUSEEVENTF_LEFTUP))
    elif button == MouseButton.Right:
        _send_input(_mouse_input(MOUSEEVENTF_RIGHTUP))
    elif button == MouseButton.Middle:
        _send_input(_mouse_input(MOUSEEVENTF_MIDDLEUP))
    elif button == MouseButton.Back:
        _send_input(_mouse_input(MOUSEEVENTF_XUP, data=XBUTTON1))
    elif button == MouseButton.Forward:
        _send_input(_mouse_input(MOUSEEVENTF_XUP, data=XBUTTON2))


def mouse_wheel(motion: int) -> None:
    _trace(f"Mouse wheel {'down' if motion > 0 else 'up'}")
    _send_input(_mouse_input(MOUSEEVENTF_WHEEL, data=-motion * WHEEL_DELTA))


def _mouse_input(flags: int, dx: int = 0, dy: int = 0, data: int = 0) -> _INPUT:
    return _INPUT(
        INPUT_MOUSE, _INPUTunion(mi=_MOUSEINPUT(dx, dy, data, flags, 0, None))
    )


def _send_input(*inputs: _INPUT) -> int:
    nInputs = len(inputs)
    LPINPUT = _INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.c_int(ctypes.sizeof(_INPUT))

    return ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)
