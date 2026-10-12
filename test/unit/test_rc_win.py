# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor window's part of the right-click additions (07 S136,
S137), off-screen in its own process and user folder (rc_win_smoke.py).

- Every menu-bar command row and the Edit rows Cut, Copy, Paste, Duplicate,
  Delete and Select All have a star (dmeStar_<id>); on hover it shows, and a
  click on it adds the favourite (stored, and handed to the editor) without
  running the row; the editor's favouriteToggled / favouriteRemoved reach
  the store.
- The Edit rows and the keys run through rig_commands.js, so Repeat sees
  them (the editor's lastCommandId); Cut is one Undo step.
- Show in Layers unfolds Layers and scrolls the item's row into view and
  lights it, clearing a search that hid it; Properties... unfolds Layers
  with Properties shown.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "rc_win_smoke.py"


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("rc_win")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        QT_FORCE_STDERR_LOGGING="1",
        QT_QPA_FONTDIR=os.environ.get(
            "QT_QPA_FONTDIR",
            os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
        ),
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=240,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        raise RuntimeError(smoke_report.explain(done))
    out = json.loads(lines[-1][len("RESULT ") :])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    out["_stderr"] = (done.stderr or "") + (done.stdout or "")
    return out


def _ok(value: object) -> object:
    if isinstance(value, dict) and "error" in value:
        raise AssertionError(value.get("traceback") or value["error"])
    return value


def test_edits(seen: dict) -> None:
    assert seen["editing"] is True


def test_star_on_edit_and_command_rows(seen: dict) -> None:
    stars = _ok(seen["stars"])
    assert isinstance(stars, dict)
    for cid, name in stars.items():
        assert name == f"dmeStar_{cid}", cid


def test_star_click_adds_and_runs_nothing(seen: dict) -> None:
    star = _ok(seen["star"])
    assert isinstance(star, dict)
    assert star["shown-on-hover"] is True
    assert star["stored"] == ["edit.duplicate"]
    assert star["editor"] == ["edit.duplicate"]
    assert star["star-text"] == "\u2605"
    assert star["ran-nothing"] is True
    assert star["after-second"] == []


def test_editor_signals_reach_the_store(seen: dict) -> None:
    star = _ok(seen["star"])
    assert isinstance(star, dict)
    assert star["from-editor"] == ["rotatePlus"]
    assert star["editor-after"] == ["rotatePlus"]
    assert star["removed-from-editor"] == []
    assert star["shown-count"] == 5


def test_edit_rows_and_keys_run_through_commands(seen: dict) -> None:
    c = _ok(seen["commands"])
    assert isinstance(c, dict)
    assert c["menu-duplicate"] == "edit.duplicate"
    assert c["key-duplicate"] == "edit.duplicate"
    assert c["key-lock"] == "lock"
    assert c["menu-cut"] == "edit.cut"
    assert c["key-delete"] == "edit.delete"
    assert c["cut-steps"] == 1
    assert c["cut-removed"] == 1
    # Every item on the plane: the 30 chips (and any picture layer).
    assert c["key-select-all"] >= 30


def test_show_in_layers(seen: dict) -> None:
    s = _ok(seen["show-in-layers"])
    assert isinstance(s, dict)
    assert s["folded"] is True
    assert s["open"] is True
    assert s["revealed-id"] == "b1"
    # b1 is the bottom of 30 chips: far below the first screenful.
    assert s["revealed"]["index"] >= 29
    assert s["revealed"]["inView"] is True
    assert s["search-cleared"] is True
    assert s["revealed-2"]["index"] == s["revealed"]["index"] - 1
    assert s["revealed-2"]["inView"] is True


def test_properties_requested(seen: dict) -> None:
    p = _ok(seen["properties"])
    assert p == {"open": True, "propsOn": True, "propsShown": True}


def test_no_binding_overwrite_from_the_star(seen: dict) -> None:
    bad = [
        ln
        for ln in seen["_stderr"].splitlines()
        if "DialogDeviceMappingEditor.qml" in ln or "RigLayersPanel.qml" in ln
    ]
    assert bad == []
