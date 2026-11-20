"""01 S182: the program hands threads over every 0.5 ms before the input
thread starts."""

import sys
from unittest import mock

import joystick_gremlin


def test_the_input_thread_start_sets_a_short_switch_interval() -> None:
    before = sys.getswitchinterval()
    try:
        with mock.patch("gremlin.input_thread.start"):
            joystick_gremlin._start_input_thread()
        assert joystick_gremlin.SWITCH_INTERVAL_S == 0.0005
        assert abs(sys.getswitchinterval() - 0.0005) < 1e-9
    finally:
        sys.setswitchinterval(before)
