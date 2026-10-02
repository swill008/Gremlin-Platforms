# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Xbox output module is a pass-through to the ViGEm driver: every
control is available and nothing is claimed (as in GremlinEx)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

from gremlin.modules import output, registry
from gremlin.modules.claim import read_claim
from vigem.xbox import XboxTarget

_ROOT = Path(__file__).resolve().parents[2]


class _FakePad:
    def __init__(self) -> None:
        self.applied: list[tuple] = []

    def apply(self, target: XboxTarget, value: object) -> None:
        self.applied.append((target, value))


class _FakeProxy:
    pad = _FakePad()

    def __getitem__(self, pad_id: int) -> _FakePad:
        return _FakeProxy.pad

    def snapshot(self, pad_id: int) -> dict[str, float]:
        return {"a": 1.0, "b": 1.0, "left_trigger": 0.5}


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    """An Xbox module with an empty claim, like the user's file."""
    registry._cache.clear()
    doc = {
        "device": "Xbox 360 Controller",
        "direction": "dest",
        "claim": {"buttons": [], "axes": [], "hats": [], "keys": []},
    }
    path = tmp_path / "xbox_360_controller.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    _FakeProxy.pad = _FakePad()
    with (
        mock.patch.object(registry, "_folder", return_value=tmp_path),
        mock.patch("vigem.xbox.XboxProxy", _FakeProxy),
    ):
        output.refresh()
        yield tmp_path
    registry._cache.clear()
    output.refresh()


def test_every_control_reaches_the_pad(folder: Path) -> None:
    for target in (XboxTarget.A, XboxTarget.LEFT_TRIGGER, XboxTarget.DPAD):
        assert output.write_xbox(1, target, 1.0)
    assert [t for t, _v in _FakeProxy.pad.applied] == [
        XboxTarget.A,
        XboxTarget.LEFT_TRIGGER,
        XboxTarget.DPAD,
    ]


def test_old_pads_still_send(folder: Path) -> None:
    # A saved pad 2 has no module file; it still sends, as in 1.0.1.
    assert output.write_xbox(2, XboxTarget.A, True)


def test_viewer_sees_every_control(folder: Path) -> None:
    assert output.xbox_state(1) == {"a": 1.0, "b": 1.0, "left_trigger": 0.5}


def test_an_old_xbox_claim_in_a_file_is_ignored() -> None:
    assert "xbox" not in read_claim({"claim": {"xbox": ["a"]}})


def test_pad_number_comes_from_the_name() -> None:
    assert output.xbox_pad_of("Xbox 360 Controller") == 1
    assert output.xbox_pad_of("Xbox 360 3") == 3


def _map_to_xbox(pad: int, target: XboxTarget) -> SimpleNamespace:
    return SimpleNamespace(
        _data=SimpleNamespace(xbox_device_id=pad, xbox_target=target)
    )


def test_map_to_xbox_offers_every_control(folder: Path) -> None:
    from action_plugins.map_to_xbox import MapToXboxModel

    choices = MapToXboxModel._get_target_choices(_map_to_xbox(1, XboxTarget.B))
    assert [c["value"] for c in choices] == [t.value for t in XboxTarget]
    assert all("claimed" not in c["label"] for c in choices)


def test_map_to_xbox_pads(folder: Path) -> None:
    from action_plugins.map_to_xbox import MapToXboxModel

    pads = MapToXboxModel._get_pad_choices(_map_to_xbox(1, XboxTarget.A))
    assert pads == [{"value": 1, "label": "Xbox 360 Controller"}]
    pads = MapToXboxModel._get_pad_choices(_map_to_xbox(2, XboxTarget.A))
    assert pads == [
        {"value": 1, "label": "Xbox 360 Controller"},
        {"value": 2, "label": "Xbox pad 2"},
    ]


def test_no_xbox_code_reads_a_claim() -> None:
    for rel in (
        "gremlin/modules/output.py",
        "gremlin/modules/wiring.py",
        "action_plugins/map_to_xbox/__init__.py",
        "gremlin/ui/xbox_device_model.py",
        "qml/XboxDevice.qml",
    ):
        text = (_ROOT / rel).read_text(encoding="utf-8")
        for word in ("xbox_claim", "xbox_allows", "claim_xbox", "setClaimed"):
            assert word not in text, (rel, word)


def test_only_the_output_module_holds_the_xbox_driver() -> None:
    files = [
        *_ROOT.joinpath("gremlin").rglob("*.py"),
        *_ROOT.joinpath("action_plugins").rglob("*.py"),
        _ROOT / "joystick_gremlin.py",
    ]
    owner = _ROOT / "gremlin" / "modules" / "output.py"
    hits = []
    for path in files:
        if path == owner:
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            if "XboxProxy" in line and not line.lstrip().startswith("#"):
                hits.append(f"{path.relative_to(_ROOT)}: {line.strip()}")
    assert hits == []
