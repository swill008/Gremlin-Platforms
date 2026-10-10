# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The program asks ViGEm which XInput slot each of its Xbox pads got and
writes it into the Input Tester's expected.json (02 S105, S106;
D-02-TESTER-XBOX-SLOT). Fake ViGEm library: no driver is loaded."""

from __future__ import annotations

import ctypes
import json
import pathlib
from types import SimpleNamespace

import pytest

from gremlin.common import SingletonMetaclass
from gremlin.modules import output
from test.unit.test_input_tester_link import (  # noqa: F401 - the fixtures
    hidhide,
    setup,
)
from vigem import xbox as vx

VIGEM_OK = vx.VIGEM_OK


class _FakeLib:
    """vigem_target_x360_get_user_index as ViGEmClient.dll has it: fills a
    ULONG with the 0-based XInput user index, returns VIGEM_ERROR."""

    def __init__(self, index: int | None, error: int = VIGEM_OK) -> None:
        self.index = index
        self.error = error
        self.raise_it = False

    def vigem_target_x360_get_user_index(
        self, busp: int, devicep: int, ref: object
    ) -> int:
        if self.raise_it:
            raise OSError("access violation")
        if self.error == VIGEM_OK:
            ctypes.cast(ref, ctypes.POINTER(ctypes.c_ulong))[0] = self.index
        return self.error


def _pad(lib: _FakeLib, pad_id: int) -> vx.XboxPad:
    pad = object.__new__(vx.XboxPad)
    pad.pad_id = pad_id
    pad._busp = 0x10
    pad._lib = lib
    pad._devicep = 0x20 + pad_id
    return pad


@pytest.fixture
def proxy(monkeypatch: pytest.MonkeyPatch) -> vx.XboxProxy:
    """A fresh XboxProxy with no pads plugged in (never touches the driver)."""
    fresh = object.__new__(vx.XboxProxy)
    fresh.__init__()
    monkeypatch.setitem(SingletonMetaclass._instances, vx.XboxProxy, fresh)
    return fresh


def test_slot_is_the_reported_user_index_plus_one(proxy: vx.XboxProxy) -> None:
    proxy._pads[1] = _pad(_FakeLib(2), 1)
    proxy._pads[2] = _pad(_FakeLib(0), 2)
    assert output.xbox_slot(1) == 3
    assert output.xbox_slot(2) == 1


def test_a_pad_not_plugged_in_has_no_slot(proxy: vx.XboxProxy) -> None:
    assert output.xbox_slot(1) is None
    assert proxy._pads == {}  # asking never plugs a pad in


def test_a_driver_error_or_no_slot_yet_is_none(proxy: vx.XboxProxy) -> None:
    proxy._pads[1] = _pad(_FakeLib(None, error=0xE0000001), 1)
    assert output.xbox_slot(1) is None
    raising = _FakeLib(0)
    raising.raise_it = True
    proxy._pads[2] = _pad(raising, 2)
    assert output.xbox_slot(2) is None
    proxy._pads[3] = _pad(_FakeLib(7), 3)  # out of XInput's 0-3 range
    assert output.xbox_slot(3) is None


def test_a_closed_pad_has_no_slot(proxy: vx.XboxProxy) -> None:
    pad = _pad(_FakeLib(1), 1)
    pad._devicep = 0
    proxy._pads[1] = pad
    assert output.xbox_slot(1) is None


def test_expected_json_carries_the_xinput_slot(
    setup: SimpleNamespace,  # noqa: F811
    proxy: vx.XboxProxy,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import input_tester_link as link

    proxy._pads[1] = _pad(_FakeLib(1), 1)
    monkeypatch.setattr(output, "_xbox_modules", {1: object(), 2: object()})
    assert link.write_expected() is True
    got = json.loads(
        (pathlib.Path(setup.data) / "tester" / "expected.json").read_text("utf-8")
    )
    assert got["xbox"] == [
        {"pad": 1, "on": True, "expect": "visible", "xinput": 2},
        {"pad": 2, "on": False, "expect": "", "xinput": None},
    ]
