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
    "Steam is running and can see your sticks: Steam Input may pass them to other "
    "programs. Add steam.exe to HidHide's Block list, or turn off Steam Input for "
    "your game."
)

# Section headings, shown as written (TW12). Devices Gremlin doesn't know go
# under the heading for their kind.
SECTION_STICKS = "YOUR CONTROLLERS"
SECTION_VJOY = "GREMLIN'S VIRTUAL JOYSTICKS (vJoy)"
SECTION_XBOX = "XBOX CONTROLLERS"
SECTION_HID = "ALL GAME DEVICES IN WINDOWS (list only)"
SECTION_ORDER = (SECTION_STICKS, SECTION_VJOY, SECTION_XBOX)

PASS_HEAD = "✓ Pass: programs see only what they should"
FAIL_HEAD = "✗ Problem:"

TAG_HIDDEN = "Hidden from programs"
TAG_VISIBLE = "Programs can see it"
TAG_UNUSED = "Programs can see it · not in use"
TAG_BAD = "Programs can see it: should be hidden"
TAG_MISSING = "Programs can't see it: should be shown"
TAG_UNKNOWN = "Not set up in Gremlin"

DETAIL_HIDDEN = "Hidden from programs, so there's nothing to show."
DETAIL_MISSING = "Missing: programs can't see it."
DETAIL_NOT_SEEN = "This window can't see it."

SHOULD_HIDDEN = "Should be: hidden from programs"
SHOULD_VISIBLE = "Should be: seen by programs"

HINT_BAD = "Tick it on Gremlin's HidHide page, then press Restart tester."
HINT_MISSING = "Check it's plugged in and that Gremlin's output for it is on."


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
            return TAG_BAD
        if self.verdict == "missing":
            return TAG_MISSING
        if self.verdict == "unknown":
            return TAG_UNKNOWN
        if self.verdict == "ok":
            if self.expect == "hidden":
                return TAG_HIDDEN
            return TAG_VISIBLE if self.used else TAG_UNUSED
        return ""

    @property
    def detail(self) -> str:
        """The line in place of live values when this window doesn't see it."""
        if self.seen:
            return ""
        if self.verdict == "ok" and self.expect == "hidden":
            return DETAIL_HIDDEN
        if self.verdict == "missing":
            return DETAIL_MISSING
        return DETAIL_NOT_SEEN

    @property
    def should_be(self) -> str:
        return {"hidden": SHOULD_HIDDEN, "visible": SHOULD_VISIBLE}.get(
            self.expect, ""
        )

    @property
    def hint(self) -> str:
        """How to fix a failing row (S1)."""
        return {"bad": HINT_BAD, "missing": HINT_MISSING}.get(self.verdict, "")


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
    pool: list[SeenDevice],
    guid: str,
    vid: int,
    pid: int,
    name: str,
    instance_ids: list[str] | None = None,
) -> SeenDevice | None:
    """Removes and returns the seen device that is this one: by its HID
    instance path first; else by GUID, else VID/PID + name, but never a
    device whose own path says it's another (twins share a name, and
    DirectInput may give one twin the other's GUID in this process)."""
    paths = {str(i).upper() for i in instance_ids or [] if i}

    def other(device: SeenDevice) -> bool:
        return bool(paths and device.instance_id and device.instance_id not in paths)

    if paths:
        for device in pool:
            if device.instance_id and device.instance_id in paths:
                pool.remove(device)
                return device
    if guid:
        wanted = normalise_guid(guid)
        for device in pool:
            if device.guid and device.guid == wanted and not other(device):
                pool.remove(device)
                return device
    if vid or pid:
        wanted_name = _norm_name(name)
        for device in pool:
            if (
                device.vid == vid
                and device.pid == pid
                and _norm_name(device.name) == wanted_name
                and not other(device)
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


_TESTS = "This window tests what a blocked program sees. "


def context_line(expected: dict | None) -> str:
    """The blue line: what this window shows and why (TW3)."""
    if expected is None:
        return PLAIN_LINE
    written = str(expected.get("written", ""))
    try:
        stamp = datetime.datetime.fromisoformat(written).strftime("%H:%M")
    except ValueError:
        stamp = written or "unknown"
    tail = f" (Gremlin's list from {stamp})"
    hidhide = expected.get("hidhide") or {}
    if not hidhide.get("present"):
        return "HidHide isn't installed, so nothing is hidden from programs." + tail
    if not hidhide.get("cloak"):
        return "HidHide is off, so nothing is hidden from programs." + tail
    mode = str(hidhide.get("mode", "block")).casefold()
    on_list = bool(hidhide.get("tester_on_list"))
    if mode == "allow":
        if on_list:
            return (
                "This window is on HidHide's Allow list, so it sees your hidden "
                "sticks too." + tail
            )
        return (
            _TESTS + "It isn't on HidHide's list, so in Allow mode your hidden "
            "sticks should not show up here." + tail
        )
    if on_list:
        return (
            _TESTS + "It's on HidHide's Block list, so your hidden sticks should "
            "not show up here." + tail
        )
    return (
        "This window isn't on HidHide's Block list, so it sees your hidden sticks "
        "too. Add it to the list on Gremlin's HidHide page to test like a blocked "
        "program." + tail
    )


def _section_for(device: SeenDevice) -> tuple[str, str]:
    """(kind, section) for a device Gremlin didn't list."""
    if device.kind == "xinput":
        return "xbox", SECTION_XBOX
    if device.is_vjoy:
        return "vjoy", SECTION_VJOY
    return "other", SECTION_STICKS


def _by_section(rows: list[Row]) -> list[Row]:
    """Rows grouped under their headings, in heading order (stable)."""
    return sorted(
        rows,
        key=lambda r: SECTION_ORDER.index(r.section)
        if r.section in SECTION_ORDER
        else len(SECTION_ORDER),
    )


def _plain_rows(seen: list[SeenDevice]) -> list[Row]:
    rows = []
    for device in seen:
        kind, section = _section_for(device)
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
    return _by_section(rows)


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
            list(stick.get("instance_ids") or []),
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
        _kind, section = _section_for(device)
        rows.append(
            Row(
                "other",
                device.name,
                "",
                True,
                "unknown",
                key=device.key,
                section=section,
                windows_name=device.name,
                in_gremlin="not part of Gremlin's setup",
                ids=_ids(device),
                device=device,
            )
        )

    rows = _by_section(rows)
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
    "xbox": ("Xbox controller", "Xbox controllers"),
    "other": ("device", "devices"),
}


def _count(n: int, kind: str) -> str:
    one, many = _NOUNS[kind]
    return f"{n} {one if n == 1 else many}"


def _counted(rows: list[Row], verdict: str) -> str:
    parts = []
    for kind in ("stick", "vjoy", "xbox"):
        n = sum(1 for r in rows if r.kind == kind and r.verdict == verdict)
        if n:
            parts.append(_count(n, kind))
    if len(parts) > 1:
        return ", ".join(parts[:-1]) + " and " + parts[-1]
    return parts[0] if parts else ""


def summarise(rows: list[Row]) -> str:
    """Fail: what's wrong in plain words (TW2); pass: "N hidden · M shown"
    (the top line adds the brackets, TW1)."""
    parts = []
    bad = _counted(rows, "bad")
    if bad:
        parts.append(f"programs can see {bad} that should be hidden")
    missing = _counted(rows, "missing")
    if missing:
        parts.append(f"programs can't see {missing} that should be shown")
    if parts:
        return "; ".join(parts)
    hidden = sum(1 for r in rows if r.verdict == "ok" and r.expect == "hidden")
    shown = sum(1 for r in rows if r.verdict == "ok" and r.expect != "hidden")
    return f"{hidden} hidden · {shown} shown"


def top_line(verdict: Verdict) -> str:
    """The verdict line as one sentence (TW1, TW2); "" with no comparison."""
    if verdict.verdict == "pass":
        return f"{PASS_HEAD} ({verdict.summary})"
    if verdict.verdict == "fail":
        return f"{FAIL_HEAD} {verdict.summary}"
    return ""


def expected_path(gremlin_dir: str | os.PathLike) -> Path:
    return Path(gremlin_dir) / "tester" / EXPECTED_NAME


def result_text(verdict: Verdict, context: str | None = None) -> str:
    """Copy result: verdict + every row as plain text (contract item 8)."""
    head = top_line(verdict) or "No comparison"
    lines = [f"Gremlin Input Tester: {head}"]
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
        if row.hint:
            lines.append(f"      {row.hint}")
    return "\n".join(lines) + "\n"


STALE_WHATS = ("program list", "cloak", "hidden devices", "mode")


def stale_since(
    expected: dict | None, started_at: datetime.datetime
) -> tuple[str, str] | None:
    """(what, "HH:MM:SS") when Gremlin changed HidHide after this tester
    started (addendum 2026-10-10 item 3), else None. HidHide checks a device
    only when it's opened, so what this process sees may be out of date."""
    if not expected:
        return None
    raw = expected.get("hidhide_changed_at")
    if not raw:
        return None
    try:
        changed = datetime.datetime.fromisoformat(str(raw))
    except ValueError:
        return None
    if changed.tzinfo is not None:
        changed = changed.astimezone().replace(tzinfo=None)
    if started_at.tzinfo is not None:
        started_at = started_at.astimezone().replace(tzinfo=None)
    if changed <= started_at:
        return None
    what = str(expected.get("hidhide_change") or "")
    if what not in STALE_WHATS:
        what = "settings"
    return what, changed.strftime("%H:%M:%S")
