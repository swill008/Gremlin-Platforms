# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Off-screen check of the Device Mapping Editor's grid box, run by
test_grid_box.py in its own process:

    python test/unit/grid_box_smoke.py <out_dir> [qml_dir]

Zooms out so the view shows past the editor, then compares the window with
the grid on and off: the grid reaches 10 % of the editor's size past each
side, with a border on its edge, and nothing beyond. An export is the same
with the grid on or off. Writes <out_dir>/grid_box.json.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as harness  # noqa: E402
from PySide6 import QtGui  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402


def _diff_cols(
    a: QtGui.QImage, b: QtGui.QImage, x0: int, x1: int, y0: int, y1: int
) -> int:
    """Pixels that differ in the box [x0, x1) x [y0, y1)."""
    n = 0
    for x in range(max(0, x0), min(a.width(), x1)):
        for y in range(max(0, y0), min(a.height(), y1)):
            if a.pixel(x, y) != b.pixel(x, y):
                n += 1
    return n


def _rows_with_diff(
    a: QtGui.QImage, b: QtGui.QImage, xs: range, y0: int, y1: int
) -> int:
    return sum(
        1 for y in range(y0, y1) if any(a.pixel(x, y) != b.pixel(x, y) for x in xs)
    )


def _cols_with_diff(
    a: QtGui.QImage, b: QtGui.QImage, ys: range, x0: int, x1: int
) -> int:
    return sum(
        1 for x in range(x0, x1) if any(a.pixel(x, y) != b.pixel(x, y) for y in ys)
    )


def _export(s: harness.Session, path: Path) -> QtGui.QImage:
    s.js("exportGrab", str(path), 1)
    for _ in range(100):
        if s.js("exportResult"):
            break
        s.wait(50)
    return QtGui.QImage(str(path))


def main() -> None:
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    if len(sys.argv) > 2:
        harness.QML = Path(sys.argv[2])
    s = harness.Session(out_dir, "grid_box")
    s.hold_runs()
    harness._load(s, "evo_r")
    s.call("setSelection", [])
    s.js("setZoom", 0.6, 0, 0)
    s.wait(300)

    ew = s.call_prop("width")
    eh = s.call_prop("height")
    left, top = json.loads(s.js("edPt", 0, 0))
    right, bottom = json.loads(s.js("edPt", ew, eh))
    k = (right - left) / ew
    ox, oy = 0.1 * ew * k, 0.1 * eh * k
    gl, gt, gr, gb = left - ox, top - oy, right + ox, bottom + oy

    s.set_prop("gridOn", True)
    s.wait(200)
    on = s.win.grabWindow()
    on.save(str(out_dir / "grid_box-on.png"))
    s.set_prop("gridOn", False)
    s.wait(200)
    off = s.win.grabWindow()
    off.save(str(out_dir / "grid_box-off.png"))

    mid_y = range(round(top) + 20, round(bottom) - 20)
    mid_x = range(round(left) + 20, round(right) - 20)
    res = {
        "editor": [left, top, right, bottom],
        "gridBox": [gl, gt, gr, gb],
        "window": [on.width(), on.height()],
        # Between the editor's edge and the grid box's edge: grid lines.
        "bandRight": _diff_cols(
            on, off, round(right) + 3, round(gr) - 3, mid_y.start, mid_y.stop
        ),
        "bandBelow": _diff_cols(
            on, off, mid_x.start, mid_x.stop, round(bottom) + 3, round(gb) - 3
        ),
        "bandLeft": _diff_cols(
            on, off, round(gl) + 3, round(left) - 3, mid_y.start, mid_y.stop
        ),
        # Past the grid box: nothing.
        "beyondRight": _diff_cols(
            on, off, round(gr) + 3, round(gr) + 60, round(gt), round(gb)
        ),
        "beyondBelow": _diff_cols(
            on, off, round(gl), round(gr), round(gb) + 3, round(gb) + 60
        ),
        # The border: every row along the right edge and every column along
        # the bottom edge differs within a pixel or two of it.
        "borderRightRows": _rows_with_diff(
            on, off, range(round(gr) - 2, round(gr) + 1), mid_y.start, mid_y.stop
        ),
        "borderBelowCols": _cols_with_diff(
            on, off, range(round(gb) - 2, round(gb) + 1), mid_x.start, mid_x.stop
        ),
        "rowsChecked": len(mid_y),
        "colsChecked": len(mid_x),
    }

    # Exports: the same picture, at the editor's own size, grid on or off.
    s.js("resetView")
    s.wait(200)
    s.set_prop("gridOn", True)
    s.wait(150)
    e_on = _export(s, out_dir / "grid_box-export-on.png")
    s.wait(200)
    s.set_prop("gridOn", False)
    s.wait(150)
    e_off = _export(s, out_dir / "grid_box-export-off.png")
    res["exportSize"] = [e_on.width(), e_on.height()]
    res["editorSize"] = [ew, eh]
    res["exportSame"] = e_on == e_off
    res["warnings"] = sorted(set(s.warnings))
    (out_dir / "grid_box.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    smoke_exit(0)


if __name__ == "__main__":
    main()
