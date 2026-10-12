# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Right-click additions in the Device Mapping Editor (07 S136, S137), off-screen.

Run in its own process (Qt teardown inside the test session can hang):

    python test/unit/rc_sel_smoke.py <out_json>

Drives the real editor through the harness host: Cut (one Undo step),
Paste Here (centre on the point, one step, selected), the editor's
Favourites / Repeat properties, signals and command forwarders, and the
right-click menu's Favourites wiring. Writes the facts to <out_json>.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PySide6 import QtQml  # noqa: E402
from rig_editor_harness import Session, _load  # noqa: E402
from smoke_exit import smoke_exit  # noqa: E402


def _ev(s: Session, code: str) -> object:
    """Evaluates code in the editor's own scope; returns the JSON result."""
    ed = getattr(s, "rc_ed", None)
    if ed is None:
        raise SystemExit("no editor")
    ctx = QtQml.QQmlEngine.contextForObject(ed)
    expr = QtQml.QQmlExpression(ctx, ed, "JSON.stringify((function(){" + code + "})())")
    out = expr.evaluate()
    if expr.hasError():
        return {"error": expr.error().toString()}
    return json.loads(out[0] if isinstance(out, tuple) else out)


def _plain_chips(s: Session, count: int) -> list[str]:
    return _ev(
        s,
        "var out = [];"
        "for (var i = 0; i < nodes.length && out.length < %d; i++) {"
        "  var n = nodes[i];"
        "  if (!isDraw(n) && !isGroup(n) && !isLocked(n) && !tablePackOf(n)"
        "      && !isTable(n)) out.push(n.id) }"
        "return out" % count,
    )


def _centre(s: Session, ids: list[str]) -> list[float]:
    return _ev(
        s,
        "var ids = %s; var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;"
        "for (var i = 0; i < ids.length; i++) { var b = nodeBox(nodeAt(ids[i]));"
        " x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);"
        " x1 = Math.max(x1, b.x + b.w); y1 = Math.max(y1, b.y + b.h) }"
        "return [(x0 + x1) / 2, (y0 + y1) / 2]" % json.dumps(ids),
    )


def main() -> None:
    out_path = Path(sys.argv[1])
    s = Session(out_path.parent, "rc_sel")
    s.hold_runs()
    # The editor object for _ev.
    s.rc_ed = s.js("ed")
    if s.rc_ed is None:
        sys.stderr.write("editor failed to load: " + " | ".join(s.warnings))
        smoke_exit(1)
    _load(s, "evo_r")
    facts: dict = {}

    # Cut: copy then delete, one Undo step; Undo brings it back.
    chips = _plain_chips(s, 3)
    facts["chips"] = chips
    one = chips[0]
    s.call("setSelection", [one])
    h0 = s.call_prop("histAt")
    s.call("cutSelection")
    s.wait(100)
    st = s.state()
    facts["cut"] = {
        "gone": all(n["id"] != one for n in st["nodes"]),
        "copied": len(s.call_prop("copiedNodes") or []),
        "steps": st["histAt"] - h0,
    }
    s.call("undo")
    s.wait(100)
    facts["cut"]["undoBack"] = any(n["id"] == one for n in s.state()["nodes"])

    # Paste Here: one item, centred on the page point, one step, selected.
    s.call("setSelection", [one])
    s.call("copySelection")
    h0 = s.call_prop("histAt")
    count0 = len(s.state()["nodes"])
    s.call("pasteAt", 0.3, 0.6)
    s.wait(200)
    st = s.state()
    sel = st["selected"]
    want = _ev(s, "return [fxToX(0.3), fyToY(0.6)]")
    facts["pasteOne"] = {
        "added": len(st["nodes"]) - count0,
        "steps": st["histAt"] - h0,
        "selectedNew": len(sel) == 1 and sel[0] != one,
        "centre": _centre(s, sel),
        "want": want,
    }

    # Paste Here with two items: the centre of their box on the point.
    two = chips[1:3]
    s.call("setSelection", two)
    s.call("copySelection")
    h0 = s.call_prop("histAt")
    s.call("pasteAt", 0.55, 0.35)
    s.wait(200)
    st = s.state()
    sel = st["selected"]
    facts["pasteTwo"] = {
        "selected": len(sel),
        "steps": st["histAt"] - h0,
        "centre": _centre(s, sel),
        "want": _ev(s, "return [fxToX(0.55), fyToY(0.35)]"),
    }

    # Properties, signals and forwarders on the editor.
    facts["props"] = _ev(
        s,
        "return { last: lastCommandId, fav: favourites, shown: favouritesShown,"
        " sig: [typeof showInLayersRequested, typeof propertiesRequested,"
        "       typeof favouriteToggled, typeof favouriteRemoved],"
        " fwd: [typeof cmdApplies, typeof cmdInfo, typeof cmdRun,"
        "       typeof cmdRepeatLabel, typeof cmdCanRepeat, typeof cmdRepeat,"
        "       typeof cutSelection, typeof pasteAt],"
        " ctx: [_ctx.mapX, _ctx.mapY] }",
    )

    # The right-click menu: Favourites on, its list follows the editor's,
    # and its signals come out of the editor's.
    facts["menu"] = _ev(
        s,
        "favourites = ['edit.cut'];"
        "var got = [];"
        "favouriteToggled.connect(function(id) { got.push('t:' + id) });"
        "favouriteRemoved.connect(function(id) { got.push('r:' + id) });"
        "_menu.favouriteToggled('edit.copy');"
        "_menu.favouriteRemoved('edit.cut');"
        "return { enabled: _menu.favouritesEnabled, ids: _menu.favouriteIds,"
        "         got: got }",
    )

    # Select All: shown, unlocked items of the plane being edited.
    facts["selectAll"] = _ev(
        s,
        "nodeAt(%s).locked = true; selectAll();"
        "var want = [];"
        "for (var i = 0; i < nodes.length; i++) { var n = nodes[i];"
        "  if (!isHidden(n) && !isLocked(n) && inEditPlane(n)) {"
        "    if (want.indexOf(n.id) < 0) want.push(n.id);"
        "    if (n.packId && want.indexOf(n.packId) < 0) want.push(n.packId) } }"
        "var got = selectedIds.slice();"
        "return { same: JSON.stringify(got) === JSON.stringify(want),"
        "         n: got.length, lockedOut: got.indexOf(%s) < 0,"
        "         info: cmdInfo('edit.cut') }" % (json.dumps(one), json.dumps(one)),
    )

    facts["warnings"] = sorted(set(s.warnings))
    out_path.write_text(json.dumps(facts, indent=1), encoding="utf-8")
    smoke_exit(0)


if __name__ == "__main__":
    main()
