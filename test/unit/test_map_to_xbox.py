# -*- coding: utf-8; -*-
from unittest import mock

import pytest

from action_plugins import map_to_xbox as mx
from gremlin.types import HatDirection
from vigem import xbox


@pytest.mark.parametrize(
    "current, pressed",
    [
        ((0, 0), False),
        ((0, 1), True),
        ((-1, -1), True),
        (HatDirection.Center, False),
        (HatDirection.East, True),
        (True, True),
        (False, False),
    ],
)
def test_hat_is_pressed_only_off_center(current: object, pressed: bool) -> None:
    assert mx._is_pressed(current) is pressed


@pytest.mark.parametrize(
    "current, full, upper",
    [(-1.0, -1.0, -1.0), (0.0, 0.0, -1.0), (0.5, 0.5, 0.0), (1.0, 1.0, 1.0)],
)
def test_trigger_range(current: float, full: float, upper: float) -> None:
    assert mx._trigger_value(current, mx.TRIGGER_FULL) == pytest.approx(full)
    assert mx._trigger_value(current, mx.TRIGGER_UPPER) == pytest.approx(upper)


def test_trigger_range_is_saved_and_old_profiles_stay_full() -> None:
    data = mx.MapToXboxData()
    assert data.trigger_range == mx.TRIGGER_FULL
    data.trigger_range = mx.TRIGGER_UPPER
    node = data._to_xml()
    loaded = mx.MapToXboxData()
    loaded._from_xml(node, None)
    assert loaded.trigger_range == mx.TRIGGER_UPPER

    for prop in list(node):
        if "trigger-range" in (prop.findtext("name") or ""):
            node.remove(prop)
    old = mx.MapToXboxData()
    old._from_xml(node, None)
    assert old.trigger_range == mx.TRIGGER_FULL


def test_available_checks_again_after_a_failure() -> None:
    proxy = xbox.XboxProxy.__new__(xbox.XboxProxy)
    proxy._busp = 0
    proxy._pads = {}
    proxy._available = None
    results = [False, True]
    with mock.patch.object(xbox.XboxProxy, "_probe", side_effect=results) as probe:
        assert proxy.available() is False
        assert proxy.available() is True
        assert proxy.available() is True
    assert probe.call_count == 2


def test_old_profile_without_trigger_range_logs_no_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    node = mx.MapToXboxData()._to_xml()
    for prop in list(node):
        if "trigger-range" in (prop.findtext("name") or ""):
            node.remove(prop)
    with caplog.at_level("ERROR"):
        loaded = mx.MapToXboxData()
        loaded._from_xml(node, None)
    assert loaded.trigger_range == mx.TRIGGER_FULL
    assert "trigger-range" not in caplog.text
