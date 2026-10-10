# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Output guards: nothing is sent while stopped (06 S4, Q19), a vJoy device
is opened only for a claimed write (S49/S51), and a vJoy hat failure is a
VJoyError (AUD-LINT-02)."""

from __future__ import annotations

from collections.abc import Iterator
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import run_scope
from gremlin.error import VJoyError
from gremlin.modules import output
from gremlin.types import HatDirection
from vigem.xbox import XboxTarget
from vjoy import vjoy


class _FakePad:
    def __init__(self) -> None:
        self.applied: list[tuple] = []

    def apply(self, target: XboxTarget, value: object) -> None:
        self.applied.append((target, value))


class _FakeXboxProxy:
    pad = _FakePad()
    made = 0

    def __init__(self) -> None:
        _FakeXboxProxy.made += 1

    def __getitem__(self, pad_id: int) -> _FakePad:
        return _FakeXboxProxy.pad


class _FakeVJoy:
    def __init__(self) -> None:
        self.written: list[tuple] = []

    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        return True

    def is_button_valid(self, index: int) -> bool:
        return True

    def axis_id(self, linear_index: int) -> int:
        return linear_index

    def axis(self, axis_id: int | None = None) -> SimpleNamespace:
        dev = self

        class _Axis:
            @property
            def value(self) -> float:
                return 0.0

            @value.setter
            def value(self, v: float) -> None:
                dev.written.append(("axis", axis_id, v))

        return _Axis()  # type: ignore[return-value]

    def button(self, index: int) -> SimpleNamespace:
        dev = self

        class _Button:
            @property
            def is_pressed(self) -> bool:
                return False

            @is_pressed.setter
            def is_pressed(self, v: bool) -> None:
                dev.written.append(("button", index, v))

        return _Button()  # type: ignore[return-value]


@pytest.fixture
def xbox() -> Iterator[type[_FakeXboxProxy]]:
    _FakeXboxProxy.pad = _FakePad()
    _FakeXboxProxy.made = 0
    with mock.patch("vigem.xbox.XboxProxy", _FakeXboxProxy):
        yield _FakeXboxProxy


@pytest.fixture
def vjoy_dev() -> Iterator[tuple[_FakeVJoy, mock.MagicMock]]:
    dev = _FakeVJoy()
    with (
        mock.patch.object(output, "_open_vjoy", return_value=dev) as opener,
        mock.patch.object(output, "vjoy_allows", return_value=True),
        mock.patch.object(output, "vjoy_claim", return_value={"axes": [1, 2]}),
    ):
        yield dev, opener


@pytest.fixture
def stopped() -> Iterator[None]:
    run_scope.begin()
    run_scope.stop()
    yield
    run_scope._reset_for_tests()


@pytest.fixture
def running() -> Iterator[None]:
    run_scope.begin()
    yield
    run_scope.stop()
    run_scope._reset_for_tests()


# --- 06 S4 / Q19: nothing is sent while stopped ------------------------------


def test_xbox_write_after_stop_plugs_no_pad(
    xbox: type[_FakeXboxProxy], stopped: None
) -> None:
    assert not output.write_xbox(1, XboxTarget.A, True)
    assert xbox.pad.applied == []
    # The pad isn't even asked for: asking plugs it in.
    assert xbox.made == 0


def test_xbox_write_during_a_run_reaches_the_pad(
    xbox: type[_FakeXboxProxy], running: None
) -> None:
    assert output.write_xbox(1, XboxTarget.A, True)
    assert xbox.pad.applied == [(XboxTarget.A, True)]


def test_vjoy_write_after_stop_sends_nothing(
    vjoy_dev: tuple[_FakeVJoy, mock.MagicMock], stopped: None
) -> None:
    dev, opener = vjoy_dev
    assert not output.write_vjoy(1, "button", 3, True)
    assert not output.write_vjoy(1, "axis", 1, 0.5)
    assert dev.written == []
    opener.assert_not_called()


def test_vjoy_write_during_a_run_is_sent(
    vjoy_dev: tuple[_FakeVJoy, mock.MagicMock], running: None
) -> None:
    dev, _opener = vjoy_dev
    assert output.write_vjoy(1, "button", 3, True)
    assert dev.written == [("button", 3, True)]


def test_writes_made_by_stop_itself_still_go_out(
    xbox: type[_FakeXboxProxy], vjoy_dev: tuple[_FakeVJoy, mock.MagicMock]
) -> None:
    # Stop's own steps (release held buttons, neutral values) send while
    # stopping; after Stop ends, nothing does.
    dev, _opener = vjoy_dev
    run_scope.begin()
    run_scope.on_stop(
        run_scope.Stage.RELEASE_HELD,
        "release",
        lambda: output.release_vjoy_button(1, 3),
    )
    try:
        run_scope.stop()
    finally:
        run_scope._reset_for_tests()
    assert dev.written == [("button", 3, False)]


# --- S49/S51: a device is opened only for a claimed write --------------------


def test_linear_axis_write_unclaimed_opens_no_device() -> None:
    run_scope.begin()
    try:
        with (
            mock.patch.object(output, "_open_vjoy") as opener,
            mock.patch.object(output, "vjoy_allows", return_value=False),
            mock.patch.object(output, "vjoy_claim", return_value={}),
        ):
            assert not output.write_vjoy_axis_linear(1, 1, 0.5)
            opener.assert_not_called()
    finally:
        run_scope.stop()
        run_scope._reset_for_tests()


def test_script_axis_lookup_unclaimed_opens_no_device() -> None:
    with (
        mock.patch.object(output, "_open_vjoy") as opener,
        mock.patch.object(output, "vjoy_allows", return_value=False),
        mock.patch.object(output, "vjoy_claim", return_value={}),
    ):
        output.ScriptVJoy()[1].axis(linear_index=1)
        opener.assert_not_called()


def test_linear_axis_write_claimed_is_sent(
    vjoy_dev: tuple[_FakeVJoy, mock.MagicMock], running: None
) -> None:
    dev, _opener = vjoy_dev
    assert output.write_vjoy_axis_linear(1, 2, 0.5)
    assert dev.written == [("axis", 2, 0.5)]


# --- AUD-LINT-02: a vJoy hat failure is a VJoyError --------------------------


def _hat(hat_type: vjoy.HatType) -> vjoy.Hat:
    dev = SimpleNamespace(vjoy_id=1, ensure_ownership=lambda: None, used=lambda: None)
    with mock.patch.object(vjoy, "VJoyStateCache"):
        return vjoy.Hat(dev, 2, hat_type)  # type: ignore[arg-type]


def test_hat_driver_refusal_is_a_vjoy_error() -> None:
    hat = _hat(vjoy.HatType.Discrete)
    with mock.patch.object(
        vjoy.VJoyInterface, "SetDiscPov", lambda *a: False, create=True
    ):
        with pytest.raises(VJoyError):
            hat.direction = HatDirection.North


def test_hat_bad_direction_is_a_vjoy_error() -> None:
    hat = _hat(vjoy.HatType.Discrete)
    with pytest.raises(VJoyError):
        hat.direction = HatDirection.East  # not one of the four discrete ones


def test_hat_bad_type_is_a_vjoy_error() -> None:
    hat = _hat(vjoy.HatType.Discrete)
    hat.hat_type = None  # type: ignore[assignment]
    with pytest.raises(VJoyError):
        hat.direction = HatDirection.North
