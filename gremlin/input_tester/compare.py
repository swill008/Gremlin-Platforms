# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Seen devices against Gremlin's expected.json (contract items 3-5, 7)."""

from __future__ import annotations

import datetime
import json
import ntpath
import os
from dataclasses import dataclass, field
from pathlib import Path

from gremlin.input_tester.devices import VJOY_PID, VJOY_VID, SeenDevice, normalise_guid

EXPECTED_NAME = "expected.json"

PLAIN_LINE = (
    "Open it from Gremlin (Tools › Viewers › Input Tester…) to compare against what "
    "Gremlin expects."
)
STEAM_LINE = (
    "Steam is running and can see your sticks: Steam Input may pass them to games."
)

SECTION_STICKS = "Physical sticks (from Gremlin)"
SECTION_VJOY = "vJoy devices (Gremlin's output)"
SECTION_XBOX = "Xbox pads (XInput)"
SECTION_OTHER = "Other devices this program sees"
SECTION_PLAIN_DI = "DirectInput devices"


@dataclass
class Row:
    kind: str  # "stick" | "vjoy" | "xbox" | "other"
    name: str
    expect: str  # "hidden" | "visible" | ""
    seen: bool
    verdict: str  # "ok" | "bad" | "missing" | "unknown" | ""
    key: str = ""  # SeenDevice.key when seen, else "exp:<kind>:<n>"
    section: str = ""
    windows_name: str = ""
    in_gremlin: str = ""
    ids: str = ""
    used: bool = True
    device: SeenDevice | None = None
    feeds: str = ""

    @property
    def tag(self) -> str:
        if self.verdict == "bad":
            return "VISIBLE · should be hidden"
        if self.verdict == "missing":
            return "missing"
        if self.verdict == "unknown":
            return "not known to Gremlin"
        if self.verdict == "ok":
            if self.expect == "hidden":
                return "hidden"
            return "visible" if self.used else "visible · not used by Gremlin"
        return ""


@dataclass
class Verdict:
    verdict: str  # "pass" | "fail" | "none"
    summary: str
    rows: list[Row]
    steam: dict = field(default_factory=lambda: {"running": False, "on_list": False})
    steam_warning: str = ""
    context: str = PLAIN_LINE


def load_expected(path: str | os.PathLike) -> dict | None:
    """expected.json, or None when it is missing or not readable."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _norm_name(name: str) -> str:
    return " ".join(str(name).split()).casefold()


def _ids(device: SeenDevice) -> str:
    parts = []
    if device.vid or device.pid:
        parts.append(f"VID {device.vid:04X} · PID {device.pid:04X}")
    if device.guid:
        parts.append(device.guid)
    if device.pad:
        parts.append(f"XInput pad {device.pad}")
    return " · ".join(parts)


def _take(
    pool: list[SeenDevice], guid: str, vid: int, pid: int, name: str
) -> SeenDevice | None:
    """Removes and returns the seen device matching by GUID, else VID/PID + name."""
    if guid:
        wanted = normalise_guid(guid)
        for device in pool:
            if device.guid and device.guid == wanted:
                pool.remove(device)
                return device
    if vid or pid:
        wanted_name = _norm_name(name)
        for device in pool:
            if (
                device.vid == vid
                and device.pid == pid
                and _norm_name(device.name) == wanted_name
            ):
                pool.remove(device)
                return device
    return None


def _verdict_for(expect: str, seen: bool) -> str:
    """expect "" (e.g. an Xbox pad that isn't plugged in): no verdict."""
    if not expect:
        return ""
    if expect == "hidden":
        return "bad" if seen else "ok"
    return "ok" if seen else "missing"


def _apps_have(apps: list, file_name: str) -> bool:
    wanted = file_name.casefold()
    return any(ntpath.basename(str(app)).casefold() == wanted for app in apps)


def steam_state(expected: dict | None, running: bool) -> tuple[dict, str]:
    """(result's steam entry, amber warning or "")."""
    hidhide = (expected or {}).get("hidhide") or {}
    on_list = _apps_have(hidhide.get("apps") or [], "steam.exe")
    state = {"running": bool(running), "on_list": on_list}
    if expected is None or not running:
        return state, ""
    mode = str(hidhide.get("mode", "block")).casefold()
    if not (hidhide.get("present") and hidhide.get("cloak")):
        return state, ""
    sees = (mode == "block" and not on_list) or (mode == "allow" and on_list)
    return state, STEAM_LINE if sees else ""


def context_line(expected: dict | None) -> str:
    if expected is None:
        return PLAIN_LINE
    written = str(expected.get("written", ""))
    try:
        stamp = datetime.datetime.fromisoformat(written).strftime("%H:%M:%S")
    except ValueError:
        stamp = written or "unknown"
    head = f"Compared with Gremlin's devices (updated {stamp}). "
    hidhide = expected.get("hidhide") or {}
    if not hidhide.get("present"):
        return head + "HidHide isn't installed, so nothing is hidden."
    if not hidhide.get("cloak"):
        return head + "HidHide is off, so nothing is hidden."
    mode = str(hidhide.get("mode", "block")).casefold()
    on_list = bool(hidhide.get("tester_on_list"))
    if mode == "allow":
        if on_list:
            return (
                head + "This program is on HidHide's Allow list, "
                "so it sees hidden sticks too."
            )
        return (
            head + "This program isn't on HidHide's Allow list, "
            "so hidden sticks must not show here."
        )
    if on_list:
        return (
            head + "This program is on HidHide's Block list, "
            "so hidden sticks must not show here."
        )
    return head + (
        "This program isn't on HidHide's Block list, so it sees hidden sticks too. "
        "Add it to the list on Gremlin's HidHide page to test like a game."
    )


def _plain_rows(seen: list[SeenDevice]) -> list[Row]:
    rows = []
    for device in seen:
        if device.kind == "xinput":
            kind, section = "xbox", SECTION_XBOX
        else:
            kind = "vjoy" if device.is_vjoy else "other"
            section = SECTION_PLAIN_DI
        rows.append(
            Row(
                kind,
                device.name,
                "",
                True,
                "",
                key=device.key,
                section=section,
                windows_name=device.name,
                ids=_ids(device),
                device=device,
            )
        )
    rows.sort(key=lambda r: r.section == SECTION_XBOX)
    return rows


def compare(expected: dict | None, seen: list[SeenDevice], steam: bool) -> Verdict:
    """Verdict per row and overall. expected None: plain tester, no verdicts."""
    steam_entry, steam_warning = steam_state(expected, steam)
    if expected is None:
        return Verdict("none", "", _plain_rows(seen), steam_entry, "", PLAIN_LINE)

    pool = [d for d in seen if d.kind == "directinput"]
    pads = {d.pad: d for d in seen if d.kind == "xinput"}
    rows: list[Row] = []

    for n, stick in enumerate(expected.get("sticks") or []):
        expect = stick.get("expect", "visible")
        windows_name = stick.get("windows_name", "")
        device = _take(
            pool,
            stick.get("guid", ""),
            int(stick.get("vid", 0) or 0),
            int(stick.get("pid", 0) or 0),
            windows_name,
        )
        feeds = ", ".join(stick.get("feeds") or [])
        row = Row(
            "stick",
            stick.get("name") or windows_name,
            expect,
            device is not None,
            _verdict_for(expect, device is not None),
            key=device.key if device else f"exp:stick:{n}",
            section=SECTION_STICKS,
            windows_name=windows_name,
            in_gremlin=(
                f"{stick.get('name', '')} · feeds {feeds}"
                if feeds
                else stick.get("name", "")
            ),
            feeds=feeds,
            ids=_ids(device)
            if device
            else f"VID {int(stick.get('vid', 0) or 0):04X} · "
            f"PID {int(stick.get('pid', 0) or 0):04X} · {stick.get('guid', '')}".rstrip(
                " ·"
            ),
            device=device,
        )
        rows.append(row)

    for n, vj in enumerate(expected.get("vjoy") or []):
        expect = vj.get("expect", "visible")
        device = _take(pool, vj.get("guid", ""), VJOY_VID, VJOY_PID, "vJoy Device")
        fed_by = ", ".join(vj.get("fed_by") or [])
        rows.append(
            Row(
                "vjoy",
                f"vJoy Device {vj.get('id', n + 1)}",
                expect,
                device is not None,
                _verdict_for(expect, device is not None),
                key=device.key if device else f"exp:vjoy:{n}",
                section=SECTION_VJOY,
                windows_name=device.name if device else "vJoy Device",
                in_gremlin=(
                    f"vJoy {vj.get('id')} output module · driven from {fed_by}"
                    if fed_by
                    else "no profile output"
                ),
                ids=_ids(device) if device else str(vj.get("guid", "")),
                used=bool(vj.get("used", True)),
                device=device,
            )
        )

    for n, pad in enumerate(expected.get("xbox") or []):
        number = int(pad.get("pad", n + 1))
        expect = pad.get("expect", "visible")
        device = pads.pop(number, None)
        rows.append(
            Row(
                "xbox",
                f"Xbox pad {number}",
                expect,
                device is not None,
                _verdict_for(expect, device is not None),
                key=device.key if device else f"exp:xbox:{n}",
                section=SECTION_XBOX,
                in_gremlin="Gremlin's Xbox output (ViGEm)",
                ids=f"XInput pad {number}",
                device=device,
            )
        )

    for device in pool + list(pads.values()):
        rows.append(
            Row(
                "other",
                device.name,
                "",
                True,
                "unknown",
                key=device.key,
                section=SECTION_OTHER,
                windows_name=device.name,
                in_gremlin="not part of Gremlin's setup",
                ids=_ids(device),
                device=device,
            )
        )

    bad = [r for r in rows if r.verdict == "bad"]
    missing = [r for r in rows if r.verdict == "missing"]
    verdict = "fail" if bad or missing else "pass"
    return Verdict(
        verdict,
        summarise(rows),
        rows,
        steam_entry,
        steam_warning,
        context_line(expected),
    )


_NOUNS = {
    "stick": ("stick", "sticks"),
    "vjoy": ("vJoy device", "vJoy devices"),
    "xbox": ("Xbox pad", "Xbox pads"),
    "other": ("device", "devices"),
}


def _count(n: int, kind: str) -> str:
    one, many = _NOUNS[kind]
    return f"{n} {one if n == 1 else many}"


def summarise(rows: list[Row]) -> str:
    parts = []
    for kind in ("stick", "vjoy", "xbox"):
        n = sum(1 for r in rows if r.kind == kind and r.verdict == "bad")
        if n:
            parts.append(f"{_count(n, kind)} visible that should be hidden")
    for kind in ("stick", "vjoy", "xbox"):
        n = sum(1 for r in rows if r.kind == kind and r.verdict == "missing")
        if n:
            parts.append(f"{_count(n, kind)} missing")
    hidden = sum(1 for r in rows if r.verdict == "ok" and r.expect == "hidden")
    visible = sum(1 for r in rows if r.verdict == "ok" and r.expect != "hidden")
    unknown = sum(1 for r in rows if r.verdict == "unknown")
    if hidden:
        parts.append(f"{hidden} hidden")
    if visible:
        parts.append(f"{visible} visible")
    if unknown:
        parts.append(f"{unknown} not known to Gremlin")
    return " · ".join(parts)


def expected_path(gremlin_dir: str | os.PathLike) -> Path:
    return Path(gremlin_dir) / "tester" / EXPECTED_NAME


def result_text(verdict: Verdict, context: str | None = None) -> str:
    """Copy result: verdict + every row as plain text (contract item 8)."""
    head = {"pass": "✓ Pass", "fail": "✗ Fail"}.get(verdict.verdict, "No comparison")
    lines = [f"Gremlin Input Tester: {head}"]
    if verdict.summary:
        lines.append(verdict.summary)
    lines.append(verdict.context if context is None else context)
    if verdict.steam_warning:
        lines.append(verdict.steam_warning)
    section = None
    for row in verdict.rows:
        if row.section != section:
            section = row.section
            lines.append("")
            lines.append(section)
        mark = {"ok": "✓", "bad": "✗", "missing": "✗", "unknown": "?"}.get(
            row.verdict, "-"
        )
        tag = f" — {row.tag}" if row.tag else ""
        ids = f" ({row.ids})" if row.ids else ""
        lines.append(f"  {mark} {row.name}{tag}{ids}")
    return "\n".join(lines) + "\n"
