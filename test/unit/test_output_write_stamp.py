# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Acquiring or releasing a vJoy device, and plugging in or removing an Xbox
pad, count as a write for "last vJoy/Xbox write" (12 S42,
D-12-WAKE-VJOY-NUMBER): output.last_write_age_s() counts from them.

The real output paths (_open_vjoy, reset_vjoy, reset_drivers, write_xbox) run
on a fake vJoy proxy and a fake ViGEm module with a stepped gremlin.clock.
No real vJoy, ViGEm or Windows calls.
"""

from __future__ import annotations

import sys
from collections.abc import Iterator
from types import SimpleNamespace
from typing import Any

import pytest

from gremlin import clock, run_scope
from gremlin.modules import output


class _Device:
    def invalidate(self) -> None:
        pass


class _Fakes:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.now = [1000.0]
        self.fail_open = False
        self.fail_apply = False
        self.pads: dict[int, object] = {}
        fakes = self

        class VJoyProxy:
            vjoy_devices: dict[int, _Device] = {}

            def __getitem__(self, vid: int) -> _Device:
                if vid in VJoyProxy.vjoy_devices:
                    return VJoyProxy.vjoy_devices[vid]
                if fakes.fail_open:
                    raise RuntimeError("vJoy open failed")
                device = _Device()
                VJoyProxy.vjoy_devices = {**VJoyProxy.vjoy_devices, vid: device}
                return device

            @classmethod
            def reset(cls) -> None:
                cls.vjoy_devices = {}

        class Pad:
            def apply(self, target: object, value: object) -> None:
                if fakes.fail_apply:
                    raise RuntimeError("apply failed")

        class XboxProxy:
            def __getitem__(self, pad: int) -> Pad:
                return fakes.pads.setdefault(int(pad), Pad())  # type: ignore[return-value]

            def reset(self) -> None:
                fakes.pads.clear()

        self.vjoy = VJoyProxy
        monkeypatch.setattr(clock, "monotonic", lambda: fakes.now[0])
        monkeypatch.setattr(output, "_vjoy_proxy", lambda: VJoyProxy)
        monkeypatch.setattr(output, "vjoy_driver_found", lambda: False)
        monkeypatch.setattr(
            output, "held_vjoy_ids", lambda: sorted(VJoyProxy.vjoy_devices)
        )
        monkeypatch.setattr(output, "_keep_alive", {})
        monkeypatch.setattr(output, "_vjoy_failed_at", {})
        monkeypatch.setattr(output, "_last_write_at", None, raising=False)
        monkeypatch.setitem(
            sys.modules, "vigem.xbox", SimpleNamespace(XboxProxy=XboxProxy)
        )
        monkeypatch.setattr(output, "plugged_xbox_pads", lambda: sorted(fakes.pads))
        monkeypatch.setattr(output, "xbox_pads_on", lambda: [1, 2])

    def age(self) -> Any:  # noqa: ANN401
        return output.last_write_age_s()


@pytest.fixture
def fakes(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Fakes]:
    run_scope._reset_for_tests()  # noqa: SLF001
    run_scope.begin()
    try:
        yield _Fakes(monkeypatch)
    finally:
        run_scope.stop()
        run_scope._reset_for_tests()  # noqa: SLF001


def test_acquiring_a_vjoy_device_counts_as_a_write(fakes: _Fakes) -> None:
    assert output._open_vjoy(2) is not None  # noqa: SLF001
    fakes.now[0] += 3.0
    assert fakes.age() == pytest.approx(3.0)


def test_a_device_already_held_is_not_a_new_acquire(fakes: _Fakes) -> None:
    output._open_vjoy(2)  # noqa: SLF001
    fakes.now[0] += 10.0
    output._open_vjoy(2)  # noqa: SLF001 - a look-up, not an acquire
    assert fakes.age() == pytest.approx(10.0)


def test_a_failed_acquire_does_not_count(fakes: _Fakes) -> None:
    fakes.fail_open = True
    assert output._open_vjoy(2) is None  # noqa: SLF001
    assert fakes.age() is None


def test_releasing_vjoy_devices_counts_as_a_write(fakes: _Fakes) -> None:
    output._open_vjoy(2)  # noqa: SLF001
    fakes.now[0] += 10.0
    output.reset_vjoy()
    fakes.now[0] += 4.0
    assert fakes.age() == pytest.approx(4.0)


def test_a_release_with_nothing_held_does_not_count(fakes: _Fakes) -> None:
    output.reset_vjoy()
    assert fakes.age() is None


def test_plugging_in_a_pad_counts_even_when_the_value_fails(fakes: _Fakes) -> None:
    fakes.fail_apply = True
    assert output.write_xbox(2, "A", True) is False
    assert 2 in fakes.pads
    fakes.now[0] += 1.5
    assert fakes.age() == pytest.approx(1.5)


def test_a_failed_value_on_a_pad_already_plugged_does_not_count(
    fakes: _Fakes,
) -> None:
    assert output.write_xbox(1, "A", True) is True
    fakes.now[0] += 6.0
    fakes.fail_apply = True
    assert output.write_xbox(1, "A", False) is False
    assert fakes.age() == pytest.approx(6.0)


def test_removing_pads_counts_as_a_write(fakes: _Fakes) -> None:
    output.write_xbox(1, "A", True)
    fakes.now[0] += 10.0
    output.reset_drivers()
    assert fakes.pads == {}
    fakes.now[0] += 2.0
    assert fakes.age() == pytest.approx(2.0)


def test_stop_with_nothing_held_or_plugged_does_not_count(fakes: _Fakes) -> None:
    output.reset_drivers()
    assert fakes.age() is None
