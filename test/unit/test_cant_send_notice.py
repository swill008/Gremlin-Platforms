# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Profile load names the bindings that can't be sent (D-04-CANT-SEND-NOTICE):
one plain notice per load, grouped by source device with counts; none when
every binding can be sent; built from live data at each load."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import device_initialization
from gremlin.modules import output
from gremlin.types import InputType
from gremlin.ui import backend

sys.path.append(".")

B = InputType.JoystickButton
_STICK = uuid.UUID("{31111111-2222-3333-4444-555555555555}")
_OSC = uuid.UUID("{61111111-2222-3333-4444-555555555555}")
_NAMES = {str(_STICK): "VKBSim NXT", str(_OSC): "OSC"}


@pytest.fixture
def vjoy(monkeypatch: pytest.MonkeyPatch) -> dict:
    """vJoy 1 in the driver (64 buttons); claims in state["claims"]."""
    state: dict = {"claims": {}}

    def devices() -> list[SimpleNamespace]:
        return [SimpleNamespace(vjoy_id=1, axis_map=[], button_count=64, hat_count=0)]

    monkeypatch.setattr(device_initialization, "vjoy_devices", devices)
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", devices)
    monkeypatch.setattr(
        device_initialization, "device_name", lambda guid: _NAMES[str(guid)]
    )
    monkeypatch.setattr(output, "vjoy_layout", lambda vid: (8, 64, 0))
    monkeypatch.setattr(output, "vjoy_axis_ids", lambda vid: set(range(1, 9)))
    monkeypatch.setattr(output, "_refresh_claims", lambda force=False: None)
    monkeypatch.setattr(output, "_vjoy_claims", state["claims"])
    monkeypatch.setattr(output, "_vjoy_off", set())
    return state


def _map(vjoy_id: int, input_id: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = input_id
    return action


def _item(device: uuid.UUID, input_id: int, target: int) -> SimpleNamespace:
    return SimpleNamespace(
        device_id=device,
        input_type=B,
        input_id=input_id,
        mode="Default",
        action_sequences=[SimpleNamespace(root_action=_map(1, target))],
    )


def _profile() -> SimpleNamespace:
    """Stick buttons 1-3 send vJoy 1 buttons 1-3; OSC button 1 sends button 9."""
    return SimpleNamespace(
        inputs={
            _STICK: [_item(_STICK, i, i) for i in (1, 2, 3)],
            _OSC: [_item(_OSC, 1, 9)],
        },
        load_warnings=[],
        from_xml=lambda path: None,
    )


def _load(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[tuple[str, str]]:
    """Runs the real load step (Backend._read_profile) on a profile; the
    notices it shows."""
    shown: list[tuple[str, str]] = []
    fake_signal = SimpleNamespace(
        showNotification=SimpleNamespace(emit=lambda t, x: shown.append((t, x)))
    )
    monkeypatch.setattr(backend, "signal", fake_signal)
    monkeypatch.setattr(sys, "path", list(sys.path))
    model = SimpleNamespace(profile=None)
    # Only backend's name for the profile module: output still uses the real
    # Profile.roots_of.
    monkeypatch.setattr(backend, "profile", SimpleNamespace(Profile=_profile))
    backend.Backend.klass._read_profile(model, str(tmp_path / "p.xml"))  # pyright: ignore[reportArgumentType]
    return shown


def test_load_names_bindings_that_cant_be_sent_once(
    vjoy: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    vjoy["claims"][1] = {"buttons": [1]}
    shown = _load(monkeypatch, tmp_path)
    assert shown == [
        ("Open Profile", "VKBSim NXT: 2 binding outputs not found. OSC: 1.")
    ]


def test_clean_profile_has_no_notice(
    vjoy: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    vjoy["claims"][1] = {"buttons": [1, 2, 3, 9]}
    assert _load(monkeypatch, tmp_path) == []


def test_notice_follows_live_claims_at_each_load(
    vjoy: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    vjoy["claims"][1] = {"buttons": [1]}
    assert _load(monkeypatch, tmp_path)[0][1] == (
        "VKBSim NXT: 2 binding outputs not found. OSC: 1."
    )
    vjoy["claims"][1]["buttons"] = [1, 2, 3]
    assert _load(monkeypatch, tmp_path) == [
        ("Open Profile", "OSC: 1 binding output not found.")
    ]


def test_notice_never_breaks_a_load(
    vjoy: dict, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def broken(profile: object = None) -> list:
        raise RuntimeError("boom")

    monkeypatch.setattr(output, "cant_send_bindings", broken)
    assert _load(monkeypatch, tmp_path) == []
