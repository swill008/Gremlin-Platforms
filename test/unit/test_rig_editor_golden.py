# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Golden tests for the Button Map editor.

rig_editor_harness.py drives the editor through fixed sessions in its own
process. Every step's editor state, and a few screenshots, must match the
goldens in rig_editor_golden/. When a change is meant to alter the result,
rewrite the goldens and review the diff:

    set RIG_GOLDEN_UPDATE=1 && pytest test/unit/test_rig_editor_golden.py
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
from PySide6 import QtGui

_HERE = pathlib.Path(__file__).parent
_HARNESS = _HERE / "rig_editor_harness.py"
_GOLDEN = _HERE / "rig_editor_golden"
_UPDATE = os.environ.get("RIG_GOLDEN_UPDATE") == "1"

# Same code renders the same pixels; a half-drawn ellipse outline alone
# changes ~770. The slack covers stray anti-aliasing on another machine.
_PIXEL_TOLERANCE = 32
_MAX_DIFFERENT_PIXELS = 50

pytestmark = pytest.mark.skipif(
    sys.platform != "win32", reason="goldens are rendered with Windows fonts"
)


def _normalize(doc: dict) -> dict:
    """Ids carry a clock and a random number: number them by first use,
    also inside other strings ("<id>_L0"). Floats are rounded."""
    ids: list[str] = []
    for step in doc["steps"]:
        for node in step["state"]["nodes"]:
            if node["id"] not in ids:
                ids.append(node["id"])
        for selected in step["state"]["selected"]:
            if selected not in ids:
                ids.append(selected)
    names = {old: f"ID{i}" for i, old in enumerate(ids)}
    longest_first = sorted(ids, key=len, reverse=True)

    def walk(value: object) -> object:
        if isinstance(value, dict):
            return {k: walk(v) for k, v in value.items()}
        if isinstance(value, list):
            return [walk(v) for v in value]
        if isinstance(value, str):
            for old in longest_first:
                if old in value:
                    value = value.replace(old, names[old])
            return value
        if isinstance(value, float):
            return round(value, 5)
        return value

    out = walk(doc)
    # File names stay, line numbers do not: moving code must not fail this.
    out["warnings"] = sorted(
        re.sub(r":\d+(:\d+)?:", ":", re.sub(r"file:///\S*?/qml/", "qml/", w))
        for w in out.get("warnings", [])
    )
    return out


def _first_difference(want: object, got: object, path: str = "") -> str:
    if type(want) is not type(got):
        return f"{path}: {want!r} != {got!r}"
    if isinstance(want, dict):
        for key in sorted(set(want) | set(got)):
            if key not in want or key not in got:
                return f"{path}.{key}: only in {'golden' if key in want else 'run'}"
            diff = _first_difference(want[key], got[key], f"{path}.{key}")
            if diff:
                return diff
        return ""
    if isinstance(want, list):
        if len(want) != len(got):
            return f"{path}: {len(want)} items in golden, {len(got)} in run"
        for i, (a, b) in enumerate(zip(want, got)):
            diff = _first_difference(a, b, f"{path}[{i}]")
            if diff:
                return diff
        return ""
    return "" if want == got else f"{path}: {want!r} != {got!r}"


def _pixels(path: pathlib.Path) -> tuple[int, int, bytes]:
    image = QtGui.QImage(str(path))
    assert not image.isNull(), path
    image = image.convertToFormat(QtGui.QImage.Format.Format_RGB32)
    return image.width(), image.height(), bytes(image.constBits())


def _different_pixels(want: pathlib.Path, got: pathlib.Path) -> int:
    w1, h1, a = _pixels(want)
    w2, h2, b = _pixels(got)
    if (w1, h1) != (w2, h2):
        return w1 * h1
    tol = _PIXEL_TOLERANCE
    return sum(
        1
        for i in range(0, len(a), 4)
        if abs(a[i] - b[i]) > tol
        or abs(a[i + 1] - b[i + 1]) > tol
        or abs(a[i + 2] - b[i + 2]) > tol
    )


def _run(scenario: str, out_dir: pathlib.Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(_HARNESS), scenario, str(out_dir)],
        capture_output=True,
        text=True,
        timeout=240,
    )
    report = out_dir / f"{scenario}.json"
    assert result.returncode == 0 and report.exists(), result.stderr[-2000:]
    return json.loads(report.read_text(encoding="utf-8"))


@pytest.mark.parametrize("scenario", ["load_l", "session_r"])
def test_editor_matches_golden(scenario: str, tmp_path: pathlib.Path) -> None:
    run = _normalize(_run(scenario, tmp_path))
    images = sorted(tmp_path.glob(f"{scenario}-*.png"))
    golden_json = _GOLDEN / f"{scenario}.json"

    if _UPDATE:
        _GOLDEN.mkdir(exist_ok=True)
        golden_json.write_text(
            json.dumps(run, indent=1, sort_keys=True) + "\n", encoding="utf-8"
        )
        for old in _GOLDEN.glob(f"{scenario}-*.png"):
            old.unlink()
        for image in images:
            shutil.copy(image, _GOLDEN / image.name)
        pytest.skip("goldens rewritten")

    golden = json.loads(golden_json.read_text(encoding="utf-8"))
    assert [s["step"] for s in run["steps"]] == [s["step"] for s in golden["steps"]]
    for want, got in zip(golden["steps"], run["steps"]):
        diff = _first_difference(want["state"], got["state"])
        assert not diff, f"step {want['step']!r} differs at {diff}"
    assert run["warnings"] == golden["warnings"]

    golden_images = sorted(p.name for p in _GOLDEN.glob(f"{scenario}-*.png"))
    assert [p.name for p in images] == golden_images
    for image in images:
        count = _different_pixels(_GOLDEN / image.name, image)
        assert count <= _MAX_DIFFERENT_PIXELS, (
            f"{image.name}: {count} pixels differ from the golden"
        )
