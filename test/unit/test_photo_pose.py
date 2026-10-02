# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Button Map photo pose as saved in a module file."""

from __future__ import annotations

import sys

sys.path.append(".")

from gremlin.ui.hardware_profile import _photo_pose


def test_defaults_and_clamps() -> None:
    assert _photo_pose(None) == {"scale": 1.0, "offX": 0.0, "offY": 0.0, "rot": 0.0}
    pose = _photo_pose({"scale": 9, "offX": -5, "offY": 0.5, "rot": "bad"})
    assert pose == {"scale": 4.0, "offX": -1.0, "offY": 0.5, "rot": 0.0}


def test_layers_flags_kept_only_when_on() -> None:
    # The Layers panel hides or locks the photo; off is not written.
    pose = _photo_pose({"scale": 1, "hidden": True, "locked": True})
    assert pose["hidden"] is True and pose["locked"] is True
    pose = _photo_pose({"scale": 1, "hidden": False, "locked": "yes"})
    assert "hidden" not in pose and "locked" not in pose


def test_look_kept_clamped_and_only_when_changed() -> None:
    pose = _photo_pose({"bright": 0.3, "contrast": -2, "grey": 1, "fade": 5})
    assert pose["bright"] == 0.3
    assert pose["contrast"] == -1.0
    assert pose["grey"] == 1.0
    assert pose["fade"] == 0.9
    pose = _photo_pose({"bright": 0, "grey": "bad"})
    assert "bright" not in pose and "grey" not in pose
