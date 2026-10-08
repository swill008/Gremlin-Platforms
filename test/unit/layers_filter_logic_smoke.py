# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Drives the Button Map editor's Layers filter off-screen (07 S102): the
rows, counts and Enter-to-select for kinds and search text. Prints the
results as JSON; test_layers_filter_logic.py runs it in its own process.

    python test/unit/layers_filter_logic_smoke.py
"""

from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import rig_editor_harness as h  # noqa: E402


def _call(s: h.Session, name: str, *args: object) -> object:
    """Calls an editor function; "ERROR" when it is missing or throws."""
    out = s.js("call", name, json.dumps(list(args)))
    s.wait(30)
    if out is None:
        return "ERROR"
    return json.loads(out)


def _chip(base: dict, id_: str, kind: str, hw: int, friendly: str, dy: float) -> dict:
    n = copy.deepcopy(base)
    n.update(id=id_, kind=kind, hwId=hw, friendly=friendly, label="")
    n["chipFy"] = n["chipFy"] + dy
    n["hotFy"] = n["hotFy"] + dy
    n["leaders"] = [
        {
            "id": id_ + "_L0",
            "from": {"type": "chip", "id": id_, "pin": n.get("pin", "right")},
            "to": {"type": "hot", "id": id_},
            "spines": [],
        }
    ]
    return n


def _draw(s: h.Session, tool: str, a: tuple, b: tuple) -> str:
    s.call("setDrawTool", tool)
    s.drag(s.point(*a), s.point(*b))
    s.call("setDrawTool", "")
    return s.state()["selected"][0]


def main() -> None:
    s = h.Session(Path(os.environ.get("TEMP", ".")), "layers_filter")
    out: dict[str, object] = {}
    h._load(s, "evo_r")
    nodes = s.state()["nodes"]
    b3 = next(n for n in nodes if n["id"] == "b3")
    # An unnamed hat, a renamed hat and a renamed button.
    nodes += [
        _chip(b3, "h1", "hat", 1, "", 0.30),
        _chip(b3, "h2", "hat", 2, "Trim", 0.34),
        _chip(b3, "b40", "btn", 40, "Fire", 0.38),
    ]
    s.js("setNodes", json.dumps(nodes))
    s.wait(300)
    s.call("seedHist")
    rect = _draw(s, "rect", (0.05, 0.85), (0.12, 0.92))
    line = _draw(s, "line", (0.14, 0.85), (0.22, 0.92))
    s.call("setSelection", [])
    out["ids"] = {"rect": rect, "line": line}
    # What a chip shows: its action.
    s.set_prop("chipTextMode", "Action")
    s.set_prop("actionLabels", {"btn:5": "Weapon release"})

    def rows(state: object, expanded: dict | None = None) -> object:
        return _call(s, "layerRows", state, expanded or {})

    out["old-all"] = rows("all")
    out["old-all-open"] = rows("all", {"b3": True})
    out["old-chips"] = rows("chips")
    out["old-drawings"] = rows("drawings")
    empty = {"kinds": [], "query": ""}
    out["empty"] = rows(empty)
    out["empty-open"] = rows(empty, {"b3": True})
    out["hotspots"] = rows({"kinds": ["hotspot"], "query": ""})
    out["shapes"] = rows({"kinds": ["shape"], "query": ""})
    queries = ("hat", "HAT ", "button", "hotspot", "fire", "weapon", "rect", "photo")
    for q in (*queries, "zzz"):
        out["q:" + q] = rows({"kinds": [], "query": q})
    out["chip+hat"] = rows({"kinds": ["chip"], "query": "hat"})
    out["shape+hat"] = rows({"kinds": ["shape"], "query": "hat"})
    out["chip+button"] = rows({"kinds": ["chip"], "query": "button 21"})
    out["open+filter"] = rows({"kinds": ["chip"], "query": "trim"}, {"h2": True})

    out["counts-empty"] = _call(s, "layerCounts", empty)
    out["counts-hat"] = _call(s, "layerCounts", {"kinds": [], "query": "hat"})
    hot_state = {"kinds": ["hotspot"], "query": ""}
    out["counts-hotspots"] = _call(s, "layerCounts", hot_state)
    out["counts-zzz"] = _call(s, "layerCounts", {"kinds": [], "query": "zzz"})
    out["all-rows"] = rows("all", {n["id"]: True for n in nodes})

    before = s.state()
    out["select-hat"] = _call(s, "selectLayerMatches", {"kinds": [], "query": "hat"})
    after = s.state()
    out["select-hat-ids"] = after["selected"]
    out["select-hat-steps"] = [
        before["histAt"], after["histAt"], before["histLen"], after["histLen"]
    ]
    member_state = {"kinds": [], "query": "button 21"}
    out["select-member"] = _call(s, "selectLayerMatches", member_state)
    out["select-member-ids"] = s.state()["selected"]
    photo_state = {"kinds": ["photo"], "query": ""}
    out["select-photo"] = _call(s, "selectLayerMatches", photo_state)
    out["can-delete-member"] = _call(s, "canDeleteLayer", "p2122", "member:0")
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
