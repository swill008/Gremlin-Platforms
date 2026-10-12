# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Xbox Setup's number of pads (D-XBOX-PADS): one Xbox output module per
pad, only the pads that are on are sent to, the bindings on pads about to
go, and one Xbox card on Home."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin import device_initialization, run_scope, shared_state
from gremlin.modules import output, registry
from gremlin.signal import signal
from gremlin.types import InputType
from test.unit._device_folders import put_module
from vigem.xbox import XboxTarget

B = InputType.JoystickButton
_STICK = uuid.UUID("{31111111-2222-3333-4444-555555555555}")


class _FakePad:
    def __init__(self) -> None:
        self.applied: list[tuple] = []

    def apply(self, target: XboxTarget, value: object) -> None:
        self.applied.append((target, value))


class _FakeProxy:
    pads: dict[int, _FakePad] = {}

    def __getitem__(self, pad_id: int) -> _FakePad:
        return _FakeProxy.pads.setdefault(pad_id, _FakePad())


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    """The program's modules folder with the pad 1 module, as today."""
    registry._cache.clear()
    put_module(
        tmp_path,
        "Xbox 360 Controller",
        {"device": "Xbox 360 Controller", "direction": "dest"},
    )
    _FakeProxy.pads = {}
    with (
        mock.patch("gremlin.modules.store.folder", return_value=tmp_path),
        mock.patch("vigem.xbox.XboxProxy", _FakeProxy),
        mock.patch.object(output, "xbox_available", lambda: True),
    ):
        output.refresh()
        yield tmp_path
    registry._cache.clear()
    output.refresh()


@pytest.fixture
def running() -> Iterator[None]:
    run_scope.begin()
    output.clear_blocked_log()
    yield
    run_scope.stop()
    run_scope._reset_for_tests()


def _xbox_names() -> list[str]:
    return sorted(
        m.name for m in registry.outputs() if output.is_xbox_module(m.name)
    )


def test_count_up_makes_the_pad_modules(folder: Path) -> None:
    told: list[bool] = []
    signal.xboxPadsChanged.connect(lambda: told.append(True))
    try:
        assert output.xbox_pad_count() == 1
        assert output.xbox_pads_on() == [1]
        output.set_xbox_pad_count(3)
    finally:
        signal.xboxPadsChanged.disconnect()
    assert _xbox_names() == ["Xbox 360 2", "Xbox 360 3", "Xbox 360 Controller"]
    assert output.xbox_pad_count() == 3
    assert output.xbox_pads_on() == [1, 2, 3]
    assert sorted(output.xbox_modules()) == [1, 2, 3]
    assert told == [True]


def test_count_down_removes_the_pads_above(folder: Path) -> None:
    output.set_xbox_pad_count(4)
    output.set_xbox_pad_count(2)
    assert _xbox_names() == ["Xbox 360 2", "Xbox 360 Controller"]
    assert output.xbox_pads_on() == [1, 2]
    output.set_xbox_pad_count(0)  # pad 1 is always on
    assert _xbox_names() == ["Xbox 360 Controller"]
    assert output.xbox_pads_on() == [1]


def test_only_pads_that_are_on_are_sent_to(folder: Path, running: None) -> None:
    with mock.patch.object(output.syslog, "warning") as warn:
        assert not output.write_xbox(2, XboxTarget.A, True)
        assert not output.write_xbox(2, XboxTarget.B, True)
    assert 2 not in _FakeProxy.pads
    # Logged once per Run.
    assert warn.call_count == 1
    assert "Xbox Setup" in warn.call_args[0][0]
    output.set_xbox_pad_count(2)
    assert output.write_xbox(2, XboxTarget.A, True)
    assert _FakeProxy.pads[2].applied == [(XboxTarget.A, True)]


def test_cant_send_text_names_xbox_setup(folder: Path) -> None:
    assert output.xbox_cant_send_text(1) is None
    assert (
        output.xbox_cant_send_text(3)
        == "Xbox 360 3 is off in Xbox Setup (pad 1 on)."
    )
    output.set_xbox_pad_count(2)
    assert (
        output.xbox_cant_send_text(3)
        == "Xbox 360 3 is off in Xbox Setup (pads 1-2 on)."
    )
    assert output.xbox_cant_send_text(2) is None


def _xbox(pad: int, target: XboxTarget) -> object:
    from action_plugins.map_to_xbox import MapToXboxData

    action = MapToXboxData(B)
    action.xbox_device_id = pad
    action.xbox_target = target
    return action


def _item(input_id: int, root: object, mode: str = "Default") -> SimpleNamespace:
    return SimpleNamespace(
        device_id=_STICK,
        input_type=B,
        input_id=input_id,
        mode=mode,
        action_sequences=[SimpleNamespace(root_action=root)],
    )


def test_bindings_on_pads_lists_every_mode_and_nested(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from action_plugins.chain import ChainData

    chain = ChainData(B)
    chain.chain_sequences = [[_xbox(3, XboxTarget.B)]]
    profile = SimpleNamespace(
        inputs={
            _STICK: [
                _item(1, _xbox(1, XboxTarget.A)),
                _item(2, _xbox(2, XboxTarget.A)),
                _item(3, chain, mode="Landing"),
            ]
        }
    )
    monkeypatch.setattr(shared_state, "current_profile", profile)
    monkeypatch.setattr(device_initialization, "device_name", lambda guid: "Stick")
    output.set_xbox_pad_count(3)
    texts = output.xbox_bindings_on_pads([2, 3])
    a, b = XboxTarget.A.label, XboxTarget.B.label
    assert texts == [
        f"Stick · Button 2 → Xbox 360 2 · {a} (Default)",
        f"Stick · Button 3 → Xbox 360 3 · {b} (Landing)",
    ]
    assert output.xbox_bindings_on_pads([4]) == []


def test_home_has_one_xbox_card(folder: Path) -> None:
    from gremlin.ui.module_model import ModuleListModel

    output.set_xbox_pad_count(4)
    with (
        mock.patch.object(device_initialization, "physical_devices", lambda: []),
        mock.patch.object(device_initialization, "vjoy_devices", lambda: []),
    ):
        model = ModuleListModel()
        model._reload()
    xbox = [row for row in model._rows if row.tab == "xbox"]
    assert [row.raw_name for row in xbox] == ["Xbox 360 Controller"]
    assert not any("Xbox 360 2" in row.raw_name for row in model._rows)
