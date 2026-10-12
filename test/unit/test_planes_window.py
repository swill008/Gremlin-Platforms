# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor window's background and foreground planes
(D-07-BACKGROUND-PLANES, D-07-PLANES-ANSWERS): the Background menu, Background
mode (no switch, no Undo / Redo row; banner, Done, Esc, Ctrl+B, status),
the plane view program settings (07 S114, S115, S120; P4a), Add Picture
to Background, Clear Background, Save and Cancel with both planes, Copy the
background too (07 S76) and Space + left-drag panning (07 S14).

The window part runs the real window off-screen (planes_window_smoke.py) in
its own process.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Iterator

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]
_WINDOW = _ROOT / "qml" / "DialogDeviceMappingEditor.qml"


@pytest.fixture
def config() -> Iterator[None]:
    """The program's settings; the plane view settings put back after."""
    from gremlin.ui import device_map_options as bmo

    bmo.register()
    kept = {name: bmo.value(name) for name, *_r in bmo.VIEW_SETTINGS}
    yield
    for name, value in kept.items():
        bmo.set_value(name, value)


def test_plane_view_settings_are_program_settings(config: None) -> None:
    """07 S114, S115, S120 (P4a): the four plane view settings are registered
    with their defaults, readable and settable by name, and not listed in
    Options."""
    from gremlin.ui import device_map_options as bmo

    for name, _kind, default, *_r in bmo.VIEW_SETTINGS:
        bmo.set_value(name, default)
    assert bmo.value("bm-fg-faint") is True
    assert bmo.value("bm-bg-hidden") is False
    assert bmo.value("bm-bg-opacity") == pytest.approx(1.0)
    assert bmo.value("bm-bg-hint-seen") is False
    bmo.set_value("bm-bg-hint-seen", True)
    assert bmo.value("bm-bg-hint-seen") is True
    shown = {name for _g, name, *_r in bmo.OPTIONS}
    assert not any(name.startswith("bm-") for name in shown)


def test_plane_view_settings_reach_qml(config: None) -> None:
    from gremlin.ui import device_map_options as bmo

    opts = bmo.DeviceMapOptions()
    values = opts.values
    for key in ("bm-fg-faint", "bm-bg-hidden", "bm-bg-opacity", "bm-bg-hint-seen"):
        assert key in values
    assert not any(e["key"].startswith("bm-") for e in opts.entries)
    opts.set("bm-bg-opacity", 3)
    assert bmo.value("bm-bg-opacity") == pytest.approx(1.0)
    opts.set("bm-bg-opacity", 0.25)
    assert bmo.value("bm-bg-opacity") == pytest.approx(0.25)


def test_window_has_no_photo_special_cases() -> None:
    """07 S39, S42: the Photo menu, Adjust Photo…, Move Photo, Reset Photo
    and the photo's own state in Save, recovery and Cancel are gone."""
    text = _WINDOW.read_text(encoding="utf-8")
    for gone in (
        "_photoAdj",
        "_photoMenu",
        "Move Photo",
        "Adjust Photo",
        "Reset Photo",
        "Choose Photo",
        "Clear Photo",
        "photoBag",
        "applyPhoto",
        "storedImage",
        "liveImage",
        "_lookTimer",
        "putPhotoBack",
        "copyImage",
    ):
        assert gone not in text, gone


def test_planes_in_the_window(tmp_path: pathlib.Path) -> None:
    out = tmp_path
    result = proc_tree.run(
        [sys.executable, str(_HERE / "planes_window_smoke.py"), str(out)],
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=150,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen", "PYTHONIOENCODING": "utf-8"},
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-2000:] + result.stderr[-2000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert errors == []
    mine = [
        line
        for line in lines
        if line.startswith("WARN") and "DialogDeviceMappingEditor.qml" in line
    ]
    assert mine == []
    r = {
        line.split(" ", 2)[1]: (line.split(" ", 2) + [""])[2]
        for line in lines
        if line.startswith("RESULT ")
    }
    assert r["photo-adjust-gone"] == "True"
    assert r["photo-menu-gone"] == "True"
    # 07 S39: the Background menu, its items only while editing.
    menu = r["bg-menu"].split("|")
    assert menu[0] == "Background" and menu[1] == "false"
    assert menu[2:] == [
        "Edit Background",
        "Add Picture to Background…",
        "Clear Background",
    ]
    assert r["bg-menu-editing"] == "True"
    # 07 S127: the bottom background picture is the device's photo.
    assert r["bottom-photo"] == "True"
    # 07 S113, S114, S117: mode, banner, Done, first-time hint, status.
    assert r["plane-start"] == "foreground false"
    assert r["status-fg"] == "Foreground"
    assert r["look"] == "true"
    assert r["moved"] == "Moved to Background|Undo|foreground"
    assert r["banner"] == "True Editing the background —|Done"
    assert r["hint-first"] == "True True"
    assert r["status-bg"] == "Background"
    # 07 S113, 01 S143: no Foreground | Background switch, no Undo / Redo row.
    assert r["no-switch"] == "True True True True"
    assert r["after-done"] == "foreground False"
    assert r["hint-second"] == "False"
    assert r["esc"] == "foreground"
    assert r["ctrl-b"] == "background"
    assert r["ctrl-b-back"] == "foreground"
    # 07 S121: Ctrl+Shift+B through the real window, both ways.
    assert r["ctrl-shift-b"] == (
        "background|Moved to Background|foreground|Moved to Foreground"
    )
    # 07 S115, S120 (P4a): program settings, both ways.
    assert r["faint-off"] == "False False"
    assert r["faint-kept"] == "True"
    assert r["hidden-kept"] == "True Foreground · Background hidden"
    assert r["opacity-kept"] == "0.40"
    assert r["opacity-applied"] == "1.00"
    assert r["opacity-pending"] == "0.20 0.20"
    # 07 S40, S30, S57: the top background layer, fitted to the photo
    # frame, an unsaved change, one Undo step.
    assert r["clean-before"] == "False"
    assert r["added"] == "background true true"
    assert r["dirty-after-add"] == "True"
    assert r["add-undo"] == "true"
    # 07 S41: every background layer, one step; Undo puts them back.
    assert r["clear"] == "0 1 2"
    # Save: both planes in the nodes, no photo keys, no view settings.
    assert r["saved"] == "False False background|foreground False"
    # 07 S26: Cancel puts the saved map back; leaving Edit is Foreground.
    assert r["cancel"] == "True"
    assert r["plane-after-edit"] == "foreground"
    # 07 S76: Copy the background too, off by default.
    assert r["copy-tick"] == "Copy the background too|False"
    kept = r["copy-keep"].split(",")
    assert "bg1:background" in kept and "c1:fg" in kept and "sbg:background" not in kept
    kept = r["copy-keep-mirror"].split(",")
    assert "bg1:background" in kept and "c1:fg" in kept and "sbg:background" not in kept
    taken = r["copy-with-bg"].split(",")
    assert taken == ["c1:fg", "sbg:background"]
    # 07 S14: Space + left-drag pans in Edit.
    assert r["space-pan"] == "True True False"
