# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Input and output modules as the Auto Mapper sees them."""

from __future__ import annotations

import json

from gremlin.modules import registry
from gremlin.modules.ids import guid_key
from gremlin.modules.registry import plain_slug, resolve_module_slug, trace


def _norm_guid(value: object) -> str:
    return str(value or "").strip().strip("{}")


def _scan_modules() -> list[dict]:
    rows: list[dict] = []
    for module in registry.modules():
        rows.append(
            {
                "slug": module.slug,
                "name": module.name,
                "path": module.path,
                "doc": module.doc,
                "claim": module.claim,
                "guid": _norm_guid(module.bound_guid),
                "boundName": module.bound_name,
                "isDest": module.is_output,
                "vjoyId": registry.resolve_vjoy_id(module.name, module.bound_guid),
            }
        )
    return rows


def _display_key(name: str) -> str:
    return " ".join(str(name or "").casefold().split())


def _same_device(left: dict, right: dict) -> bool:
    name = _display_key(left.get("name") or "")
    if name and name == _display_key(right.get("name") or ""):
        return True
    guid = guid_key(left.get("guid"))
    return bool(guid and guid == guid_key(right.get("guid")))


def _choose_input(group: list[dict]) -> dict:
    """Keep the file the input module is bound to. Do not delete the others."""
    for row in group:
        wanted = resolve_module_slug(row["name"], row.get("guid") or "")
        if wanted and wanted == row["slug"]:
            return row
    for row in group:
        if row["slug"] == (plain_slug(row["name"]) or "device"):
            return row
    return group[0]


def _collapse_inputs(rows: list[dict]) -> list[dict]:
    parent = list(range(len(rows)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    def union(left: int, right: int) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left != root_right:
            parent[root_right] = root_left

    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            if _same_device(rows[left], rows[right]):
                union(left, right)
    groups: dict[int, list[dict]] = {}
    for index, row in enumerate(rows):
        groups.setdefault(find(index), []).append(row)
    kept = [_choose_input(group) for group in groups.values()]
    kept.sort(key=lambda row: str(row["name"]).lower())
    return kept


def input_modules() -> list[dict]:
    rows = []
    for row in _scan_modules():
        if row["isDest"]:
            continue
        claim = row["claim"]
        if not (claim.get("buttons") or claim.get("axes") or claim.get("hats")):
            continue
        rows.append(row)
    return _collapse_inputs(rows)


def output_modules() -> list[dict]:
    rows = []
    seen: set[int] = set()
    for row in _scan_modules():
        if not row["isDest"]:
            continue
        vjoy_id = int(row["vjoyId"] or 0)
        if not vjoy_id or vjoy_id in seen:
            continue
        seen.add(vjoy_id)
        rows.append(row)
    rows.sort(key=lambda row: (int(row["vjoyId"]), str(row["name"]).lower()))
    return rows


def merge_claim_into_output(dest: dict, claim: dict) -> dict:
    """Write the input-module selection onto the output module so they match."""
    path = dest.get("path")
    doc = dest.get("doc") if isinstance(dest.get("doc"), dict) else {}
    current = dest.get("claim") or {}
    buttons = sorted(
        {int(x) for x in (current.get("buttons") or [])}
        | {int(x) for x in (claim.get("buttons") or [])}
    )
    axes = sorted(
        {int(x) for x in (current.get("axes") or [])}
        | {int(x) for x in (claim.get("axes") or [])}
    )
    hats = sorted(
        {int(x) for x in (current.get("hats") or [])}
        | {int(x) for x in (claim.get("hats") or [])}
    )
    friendly = dict(current.get("friendly") or {})
    friendly.update(dict(claim.get("friendly") or {}))
    merged = {
        "buttons": buttons,
        "axes": axes,
        "hats": hats,
        "keys": list(current.get("keys") or []),
        "friendly": friendly,
    }
    if path is None:
        dest["claim"] = merged
        return merged
    doc = dict(doc)
    doc["claim"] = merged
    try:
        path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    except OSError:
        trace("SAVE", "Auto Mapper", "merge_claim_into_output", path, "error")
        dest["claim"] = merged
        return merged
    trace("SAVE", "Auto Mapper", "merge_claim_into_output", path, "ok")
    dest["doc"] = doc
    dest["claim"] = merged
    return merged
