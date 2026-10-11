# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""ONE-TIME (tracker OT-2): a map saved before the planes opens with its
old photo as the bottom background picture, in memory only (07 S125,
D-07-PLANES-ANSWERS P3a)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from PySide6 import QtGui

from gremlin.modules import planes_once, store

_LAYOUTS = Path(__file__).parent / "rig_editor_golden" / "layouts"


def _layout(name: str) -> dict:
    return json.loads((_LAYOUTS / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["evo_l", "evo_r", "legacy"])
def test_old_maps_get_their_photo_as_the_bottom_layer(name: str) -> None:
    doc = _layout(name)
    nodes = copy.deepcopy(doc["nodes"])
    assert planes_once.old_photo_to_layer(doc, None) is True
    for key in planes_once.OLD_PHOTO_KEYS:
        assert key not in doc
    bottom = doc["nodes"][0]
    assert bottom["plane"] == "background" and bottom["shape"] == "image"
    assert bottom["src"] == "pictures/photo.jpg"
    assert doc["nodes"][1:] == nodes
    assert store.device_photo_ref(doc) == "pictures/photo.jpg"
    # Again: nothing more to do.
    assert planes_once.old_photo_to_layer(doc, None) is False


def test_geometry_follows_the_old_pose() -> None:
    """evo_r: 1348x1380 photo at scale 1.33 in the middle of the frame."""
    doc = _layout("evo_r")
    planes_once.old_photo_to_layer(doc, None)
    node = doc["nodes"][0]
    # Height-bound in the 24000x13500 frame.
    height = 13500 * 1.33
    width = 1348 * (13500 / 1380) * 1.33
    assert node["fh"] == pytest.approx(height / 18000)
    assert node["fw"] == pytest.approx(width / 32000)
    assert node["fx"] + node["fw"] / 2 == pytest.approx(0.5)
    assert node["fy"] + node["fh"] / 2 == pytest.approx(0.5)
    assert node["rot"] == 0 and node["opacity"] == 1
    assert "look" not in node and "hidden" not in node


def test_offset_turn_look_and_flags(tmp_path: Path) -> None:
    (tmp_path / store.PICTURES).mkdir()
    image = QtGui.QImage(320, 180, QtGui.QImage.Format.Format_RGB32)
    image.fill(0)
    assert image.save(str(tmp_path / store.PICTURES / "p.png"))
    doc = {
        "image": "pictures/p.png",
        "photo": {
            "scale": 0.5,
            "offX": 0.1,
            "offY": -0.2,
            "rot": 30,
            "fade": 0.4,
            "bright": 0.3,
            "contrast": -0.5,
            "grey": 0.7,
            "hidden": True,
            "locked": True,
        },
        "nodes": [{"id": "c", "kind": "chip"}],
    }
    assert planes_once.old_photo_to_layer(doc, tmp_path)
    node = doc["nodes"][0]
    # 16:9 picture fills the 16:9 frame; half size; centre moved.
    assert node["fw"] == pytest.approx(0.375)
    assert node["fh"] == pytest.approx(0.375)
    assert node["fx"] + node["fw"] / 2 == pytest.approx(0.6)
    assert node["fy"] + node["fh"] / 2 == pytest.approx(0.3)
    assert node["rot"] == 30
    assert node["opacity"] == pytest.approx(0.6)
    assert node["look"] == {"bright": 0.3, "contrast": -0.5, "grey": 0.7}
    assert node["hidden"] is True and node["locked"] is True
    assert doc["nodes"][1] == {"id": "c", "kind": "chip"}


def test_a_map_with_a_background_picture_only_loses_the_old_keys() -> None:
    bg = {"id": "b", "shape": "image", "src": "pictures/b.png", "plane": "background"}
    doc = {"image": "pictures/old.png", "photo": {}, "nodes": [bg]}
    assert planes_once.old_photo_to_layer(doc)
    assert doc == {"nodes": [bg]}


def test_a_photo_pose_without_a_picture_adds_nothing() -> None:
    doc = {"photo": {"scale": 1}, "nodes": []}
    assert planes_once.old_photo_to_layer(doc)
    assert doc == {"nodes": []}


def test_todays_map_is_left_alone() -> None:
    doc = {"nodes": [{"id": "c"}]}
    assert planes_once.old_photo_to_layer(doc) is False
    assert doc == {"nodes": [{"id": "c"}]}
