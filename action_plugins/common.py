# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import uuid
from typing import Any

import dill
from gremlin import clock, run_scope, util
from gremlin.types import (
    AxisNames,
    InputType,
)


def joystick_label(device_guid: uuid.UUID, input_type: InputType, input_id: int) -> str:
    device = dill.DILL().get_device_information_by_guid(
        dill.GUID.from_uuid(device_guid)
    )
    label = f"{device.name}"
    if input_type == InputType.JoystickAxis:
        label += f" - {AxisNames.to_string(AxisNames(input_id))}"
    elif input_type == InputType.JoystickButton:
        label += f" - Button {input_id}"
    elif input_type == InputType.JoystickHat:
        label += f" - Hat {input_id}"

    return label


class RelativeAxisLoop:
    """The relative axis mode of Map to vJoy and Map to Logical Device: the
    stick's deflection moves the output axis a little every step, in a loop
    that belongs to the Run (05 RB15, 06 Q17).

    The functor gives the axis (_relative_read, _relative_write and
    _relative_ok) and the loop's name; the rest is shared.
    """

    SCALING_MULTIPLIER = 1 / 1000.0
    THREAD_SLEEP_DURATION_S = 0.01
    # Shown in the thread's name.
    _loop_name = "relative axis"
    # Errors from the axis that end the loop quietly.
    _loop_errors: tuple[type[BaseException], ...] = ()

    def _init_relative(self) -> None:
        self.thread_running = False
        self.should_stop_thread = False
        self.thread_last_update = clock.now()
        self.thread = None
        self.axis_delta_value = 0.0
        self.axis_value = 0.0

    def _relative_read(self) -> float:
        """The output axis's value now."""
        raise NotImplementedError

    def _relative_write(self, value: float) -> bool:
        """Sets the output axis; False ends the loop (nothing to drive)."""
        raise NotImplementedError

    def _relative_ok(self) -> bool:
        """The output can still be driven."""
        return True

    def _relative_input(
        self,
        event_value: Any,  # noqa: ANN401
        current: Any,  # noqa: ANN401
        scaling: float,
    ) -> None:
        """A new deflection (the event's and the action's value): sets the
        step and starts the loop if needed."""
        self.should_stop_thread = abs(event_value) < 0.05
        self.axis_delta_value = current * (scaling * self.SCALING_MULTIPLIER)
        self.thread_last_update = clock.now()
        if self.thread_running is False:
            self._start_loop()

    def _start_loop(self) -> None:
        """Starts the relative axis loop for this Run.

        A loop still ending (released and moved again at once) is not
        waited for on the main thread: it is no longer the current one and
        ends at its next step (06 RB20).
        """
        token = object()
        self._loop_token = token
        # Set here, not in the thread: a second event before the thread
        # starts must not start another.
        self.thread_running = True
        self.thread = run_scope.loop(
            self._loop_name,
            self.relative_axis_thread,
            token,
            stop=self._ask_to_stop,
        )

    def _ask_to_stop(self) -> None:
        """Ends the relative axis loop after its current step."""
        self.thread_running = False

    def _current(self, run: int, token: object) -> bool:
        """This loop still runs: its Run goes on (06 Q17), it wasn't asked
        to stop and no newer loop replaced it."""
        return (
            self.thread_running
            and getattr(self, "_loop_token", None) is token
            and run_scope.alive(run)
        )

    def _end(self, token: object, should_stop: bool = False) -> None:
        """This loop ends; the flags are left alone if a newer one runs."""
        if getattr(self, "_loop_token", None) is token:
            self.thread_running = False
            if should_stop:
                self.should_stop_thread = True

    def relative_axis_thread(self, run: int, token: object = None) -> None:
        """Moves the axis each step; ends with its Run (run: the Run's
        number, token: this loop's own)."""
        # This loop's own value: a loop still ending must not change the one
        # that replaced it (self.axis_value is set only while current).
        value = self._relative_read()
        self.axis_value = value
        # Stop (or Stop and Run again) ends it: it used to go on sending
        # into the next Run.
        while self._current(run, token):
            if not self._relative_ok():
                self._end(token)
                return
            try:
                # The axis was changed by something else since the last
                # step: the loop ends.
                if abs(self._relative_read() - value) > 0.0001:
                    self._end(token, should_stop=True)
                    return

                value = util.clamp(value + self.axis_delta_value, -1.0, 1.0)
                # Stop may have come during this step: nothing is written
                # after it (it would open vJoy again).
                if not self._current(run, token):
                    return
                self.axis_value = value
                if not self._relative_write(value):
                    self._end(token)
                    return

                if (
                    self.should_stop_thread
                    and self.thread_last_update + 1.0 < clock.now()
                ):
                    self._end(token)
                clock.sleep(self.THREAD_SLEEP_DURATION_S)
            except self._loop_errors:
                self._end(token)
                return
