# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Xbox pad face picture on the Xbox Output View (D-FIXLIST-B1 item 9): the
picture is program art in gfx/, loaded beside qml/ and never from a device
folder; "Xbox face image missing" shows whenever it can't be loaded, an
empty source included.
Spec: 02/06 (Xbox Output View), D-FIXLIST-B1 (9)."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_HERE = pathlib.Path(__file__).resolve().parent
_SMOKE = _HERE / "b1_xbox_face_smoke.py"
_ROOT = _HERE.parents[1]
_FACE = _ROOT / "qml" / "Xbox360Face.qml"
_MISSING = "Xbox face image missing"
_READY, _NULL, _ERROR = 1, 0, 3


def _run(tmp_path: pathlib.Path, face: pathlib.Path, mode: str) -> dict:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE), str(face), mode], cwd=_ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", timeout=90,
    )
    lines = [line for line in done.stdout.splitlines() if line.startswith("{")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[-1])


def test_picture_is_program_art_in_gfx() -> None:
    assert (_ROOT / "gfx" / "xbox360_two_panel.jpg").is_file()
    for spec in ("joystick_gremlin.spec",):
        text = (_ROOT / spec).read_text(encoding="utf-8")
        assert '("gfx", "gfx")' in text


def test_face_shows_the_picture_with_an_empty_data_folder(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, _FACE, "keep")
    assert out["status"] == _READY, out
    assert out["source"].endswith("/gfx/xbox360_two_panel.jpg"), out
    assert _MISSING not in out["texts"], out


def test_missing_picture_shows_the_note(tmp_path: pathlib.Path) -> None:
    # The face on its own, with no gfx folder beside it.
    alone = tmp_path / "qml" / "Xbox360Face.qml"
    alone.parent.mkdir()
    shutil.copy(_FACE, alone)
    out = _run(tmp_path, alone, "keep")
    assert out["status"] == _ERROR, out
    assert _MISSING in out["texts"], out


def test_empty_source_shows_the_note(tmp_path: pathlib.Path) -> None:
    out = _run(tmp_path, _FACE, "empty")
    assert out["status"] == _NULL, out
    assert _MISSING in out["texts"], out
