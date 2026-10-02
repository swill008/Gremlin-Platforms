# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Xbox is an output module: only claimed controls reach the ViGEm driver."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from gremlin.modules import output, registry
from gremlin.modules.claim import claim_is_empty, claim_xbox, read_claim
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
    registry._cache.clear()
    output.clear_blocked_log()
    doc = {
        "device": "Xbox 360 Controller",
        "direction": "dest",
        "claim": {"xbox": ["a"]},
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
    output.clear_blocked_log()


def test_xbox_claim_is_read_by_name() -> None:
    claim = read_claim({"claim": {"xbox": ["A", "a", " left_trigger ", ""]}})
    assert claim_xbox(claim) == ["a", "left_trigger"]
    assert not claim_is_empty(claim)
    assert read_claim({})["xbox"] == []


def test_claimed_control_reaches_the_pad(folder: Path) -> None:
    assert output.write_xbox(1, XboxTarget.A, True)
    assert _FakeProxy.pad.applied == [(XboxTarget.A, True)]


def test_unclaimed_control_is_blocked_and_logged_once(
    folder: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.WARNING, logger="system"):
        for _ in range(3):
            assert not output.write_xbox(1, XboxTarget.B, True)
    assert _FakeProxy.pad.applied == []
    assert len([r for r in caplog.records if "Xbox pad 1" in r.getMessage()]) == 1


def test_pad_without_an_output_module_sends_nothing(folder: Path) -> None:
    assert output.xbox_module(2) is None
    assert not output.write_xbox(2, XboxTarget.A, True)


def test_viewer_state_shows_claimed_controls_only(folder: Path) -> None:
    assert output.xbox_state(1) == {"a": 1.0}


def test_claim_is_saved_to_the_module_file(folder: Path) -> None:
    assert output.set_xbox_claim(1, ["a", "left_trigger"])
    path = folder / "xbox_360_controller.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["claim"]["xbox"] == ["a", "left_trigger"]
    assert saved["device"] == "Xbox 360 Controller"
    assert output.xbox_claim(1) == ["a", "left_trigger"]


def test_pad_number_comes_from_the_name() -> None:
    assert output.xbox_pad_of("Xbox 360 Controller") == 1
    assert output.xbox_pad_of("Xbox 360 3") == 3


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


def _map_to_xbox(pad: int, target: XboxTarget) -> object:
    from types import SimpleNamespace

    return SimpleNamespace(
        _data=SimpleNamespace(xbox_device_id=pad, xbox_target=target)
    )


def test_map_to_xbox_lists_xbox_output_modules(folder: Path) -> None:
    from action_plugins.map_to_xbox import MapToXboxModel

    pads = MapToXboxModel._get_pad_choices(_map_to_xbox(1, XboxTarget.A))
    assert pads == [{"value": 1, "label": "Xbox 360 Controller"}]
    # A saved pad without an output module stays listed, marked.
    pads = MapToXboxModel._get_pad_choices(_map_to_xbox(2, XboxTarget.A))
    assert pads[0] == {"value": 2, "label": "Xbox pad 2 (no output module)"}


def test_map_to_xbox_lists_claimed_controls(folder: Path) -> None:
    from action_plugins.map_to_xbox import MapToXboxModel

    claimed = MapToXboxModel._get_target_choices(_map_to_xbox(1, XboxTarget.A))
    assert [c["value"] for c in claimed] == ["a"]
    flagged = MapToXboxModel._get_target_choices(_map_to_xbox(1, XboxTarget.B))
    assert flagged[0] == {"value": "b", "label": "B (not claimed)"}
