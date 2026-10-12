# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC's own module file (decision D-09-OSC-FILE).

Every profile uses one OSC address list, kept under "inputs" in
its module file, <modules>/OSC/module.json (its own folder, 03 S128; found by
its id; "OSC/module.json" in trace lines), with the server and behaviour settings
under "server";
the file's other keys are left as they are. Writes go through
gremlin.modules.store, so module-file History records them.

Main thread only.
"""

from __future__ import annotations

import ipaddress
import logging
import re
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gremlin import trace
from gremlin.error import quiet
from gremlin.modules import store

if TYPE_CHECKING:
    from gremlin.osc_rows import OscRows

KEY = "inputs"
SERVER_KEY = "server"
WHO = "OSC"
# Your names for OSC's inputs are the claim's friendly names under this.
NAME_PREFIX = "osc:"

SERVER_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "host": "",
    "port": 8001,
    "autorelease_no_arg": True,
    "autorelease_delay_ms": 250,
    "pad_args": False,
    # Output, feedback and discovery (D-09-OSC-OUTPUT/FEEDBACK/DISCOVERY).
    "output_enabled": True,
    "reply_to_sender": True,
    "announce": False,
    "find_devices": False,
    "feedback_enabled": True,
    "resend_run": True,
    "resend_mode": True,
    "resend_profile": True,
    "sync_enabled": True,
    "sync_address": "/gremlin/sync",
    "feedback_rate": 50,
    # Senders OSC accepts (S160): IP addresses and CIDR ranges; empty =
    # everyone.
    "allow_senders": [],
}

TARGETS_KEY = "targets"
FEEDBACK_KEY = "feedback"
REPLY = "reply"
DEFAULT_TARGET = "Default"
DEFAULT_TARGET_HOST = "127.0.0.1"
DEFAULT_TARGET_PORT = 8000
# Keys of the old layout, not read or kept (AD7, unreleased program).
_OLD_SERVER_KEYS = ("output_host", "output_port")
# action_state: an action's on/off by action id (S157); paused: the
# profile's Running / Paused, on while paused.
SOURCE_KINDS = (
    "mode",
    "vjoy_button",
    "vjoy_axis",
    "logical",
    "osc_input",
    "action_state",
    "paused",
)
VALUE_TYPES = ("auto", "int", "float", "bool", "text")
# Feedback row templates (D-09-OSC-COMPANION).
TEMPLATES = ("companion_variable", "companion_text", "companion_color")
# Companion's OSC API (Settings > OSC > OSC Listener).
COMPANION_TARGET = "Companion"
COMPANION_HOST = "127.0.0.1"
COMPANION_PORT = 12321
_BOOL_KEYS = (
    "output_enabled",
    "reply_to_sender",
    "announce",
    "find_devices",
    "feedback_enabled",
    "resend_run",
    "resend_mode",
    "resend_profile",
    "sync_enabled",
)


def path() -> Path:
    """The module file in OSC's folder (may not exist yet)."""
    return store.module_file(WHO, str(_osc_id()))


def _write_path() -> Path:
    """path(), its folder made first (with its device.json) for a write."""
    store.ensure_device_dir(WHO, str(_osc_id()))
    return path()


def _osc_id() -> uuid.UUID:
    from gremlin.modules import ids

    return ids.OSC


def _trace(text: str, **kwargs: object) -> None:
    """A "Setup and files" trace line (D-09-OSC-TRACE)."""
    trace.osc("setup", text, **kwargs)  # type: ignore[arg-type]


_WHY = re.compile(r"\): (.*?)\.? It is kept in the file")


def _note_cleaned(raw: object) -> None:
    """Trace each server value the file had that clean_server changed to
    its default ("port abc cleaned to 8001")."""
    if not trace.osc_on("setup") or not isinstance(raw, dict):
        return
    cleaned = clean_server(raw)
    for key, default in SERVER_DEFAULTS.items():
        if key not in raw or key == "allow_senders":
            continue
        given = raw[key]
        if (
            cleaned[key] == default
            and str(given).strip().lower() != str(default).lower()
            and not (isinstance(given, bool) and given == default)
        ):
            _trace(f"{key} {given} cleaned to {default}")
    senders = raw.get("allow_senders")
    for item in senders if isinstance(senders, list) else []:
        if sender_entry(item) is None:
            _trace(f"allow_senders {item} dropped (not an IP address or range)")


def _identity() -> dict:
    from gremlin.modules import ids

    return {
        "kind": "control.hardware",
        "device": WHO,
        "direction": "source",
        "boundName": WHO,
        "boundGuidLocal": str(ids.OSC).upper(),
    }


def _rows(rows: OscRows | None) -> OscRows:
    if rows is not None:
        return rows
    from gremlin.osc import OscDevice

    return OscDevice().rows


def _clean(inputs: object) -> list[dict]:
    """The input rows as a list of dicts, whatever was read (a to_dict()
    result or the list itself)."""
    if isinstance(inputs, dict):
        inputs = inputs.get(KEY)
    if not isinstance(inputs, list):
        return []
    return [dict(r) for r in inputs if isinstance(r, dict)]


def _raw(inputs: object) -> list:
    """The file's input entries as they are, unreadable ones too (AD1)."""
    if isinstance(inputs, dict):
        inputs = inputs.get(KEY)
    return list(inputs) if isinstance(inputs, list) else []


def _with_unreadable(inputs: list[dict], rows: object) -> list:
    """inputs with the entries the rows couldn't read put back in their
    places (AD1), so a Save never drops a row of the file."""
    out: list = list(inputs)
    for index, entry in sorted(
        getattr(rows, "unreadable", None) or [], key=lambda pair: pair[0]
    ):
        out.insert(min(index, len(out)), entry)
    return out


def _number(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _flag(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("true", "1", "yes", "on"):
            return True
        if text in ("false", "0", "no", "off", ""):
            return False
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _port(value: object, default: int) -> int:
    number = _number(str(value or "").replace(",", "").strip() or None)
    return number if number is not None and 1 <= number <= 65535 else default


def _delay(value: object, default: int) -> int:
    try:
        delay = int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default
    return max(0, min(delay, 10000))


def clean_server(raw: object) -> dict:
    """Server settings with every key, defaults for missing or bad values;
    unknown keys are kept, the old layout's keys dropped (AD7)."""
    given = dict(raw) if isinstance(raw, dict) else {}
    out = {k: v for k, v in given.items() if k not in _OLD_SERVER_KEYS}
    d = SERVER_DEFAULTS
    out["enabled"] = _flag(given.get("enabled"), d["enabled"])
    out["host"] = str(given.get("host") or "").strip()
    out["port"] = _port(given.get("port"), d["port"])
    out["autorelease_no_arg"] = _flag(
        given.get("autorelease_no_arg"), d["autorelease_no_arg"]
    )
    out["autorelease_delay_ms"] = _delay(
        given.get("autorelease_delay_ms"), d["autorelease_delay_ms"]
    )
    out["pad_args"] = _flag(given.get("pad_args"), d["pad_args"])
    for key in _BOOL_KEYS:
        out[key] = _flag(given.get(key), d[key])
    address = str(given.get("sync_address") or "").strip()
    out["sync_address"] = address if address.startswith("/") else d["sync_address"]
    out["feedback_rate"] = _rate(given.get("feedback_rate"), d["feedback_rate"])
    out["allow_senders"] = clean_senders(given.get("allow_senders"))
    return out


def sender_entry(text: object) -> str | None:
    """An allow-list entry in its usual form ("192.168.1.5",
    "192.168.1.0/24"), or None when it is neither an IP address nor a CIDR
    range. Host bits of a range are dropped (192.168.1.7/24 is the /24)."""
    raw = str(text if text is not None else "").strip()
    if not raw:
        return None
    try:
        if "/" in raw:
            return str(ipaddress.ip_network(raw, strict=False))
        return str(ipaddress.ip_address(raw))
    except ValueError:
        return None


def clean_senders(raw: object) -> list[str]:
    """The allow-list: entries in their usual form, bad ones dropped, each
    once, in the order given."""
    if isinstance(raw, (str, bytes)) or not isinstance(raw, (list, tuple)):
        return []
    out: list[str] = []
    for item in raw:
        entry = sender_entry(item)
        if entry is not None and entry not in out:
            out.append(entry)
    return out


def _rate(value: object, default: int) -> int:
    try:
        rate = int(float(str(value).replace(",", "").strip()))
    except (TypeError, ValueError):
        return default
    return rate if rate >= 1 else default


def _float(value: object, default: float) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def new_id() -> str:
    return uuid.uuid4().hex


# Fixed: the "Default" target keeps one id everywhere.
_ORIGIN = uuid.UUID("0b8e6a52-3f4d-4c1e-a7d9-91c2f5e83b47")


def default_target() -> dict:
    """The "Default" target, 127.0.0.1:8000 (S9, S96)."""
    return {
        "id": uuid.uuid5(_ORIGIN, "target:default").hex,
        "name": DEFAULT_TARGET,
        "host": DEFAULT_TARGET_HOST,
        "port": DEFAULT_TARGET_PORT,
    }


def clean_targets(raw: object) -> list[dict]:
    """Targets as {id, name, host, port}: rows that aren't dicts are dropped,
    a missing id is made, a bad port becomes 8000; ids are unique."""
    out: list[dict] = []
    seen: set[str] = set()
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        row = dict(entry)
        tid = str(row.get("id") or "").strip()
        if not tid or tid in seen or tid == REPLY:
            tid = new_id()
        seen.add(tid)
        row["id"] = tid
        row["name"] = str(row.get("name") or "").strip()
        row["host"] = str(row.get("host") or "").strip()
        row["port"] = _port(row.get("port"), DEFAULT_TARGET_PORT)
        out.append(row)
    return out


def _source(raw: object) -> dict:
    given = raw if isinstance(raw, dict) else {}
    kind = str(given.get("kind") or "")
    if kind not in SOURCE_KINDS:
        kind = "mode"

    def part(value: object) -> int | str | None:
        if value is None or value == "":
            return None
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        return str(value)

    out: dict = {
        "kind": kind,
        "device": part(given.get("device")),
        "input": part(given.get("input")),
    }
    # action_state's action id; kept only when set.
    action = str(given.get("action") or "").strip()
    if action:
        out["action"] = action
    return out


def clean_feedback(raw: object) -> list[dict]:
    """Feedback rows with every key (see the OSC contract); defaults for
    missing or bad values; unknown keys are kept."""
    out: list[dict] = []
    seen: set[str] = set()
    for entry in raw if isinstance(raw, list) else []:
        if not isinstance(entry, dict):
            continue
        row = dict(entry)
        fid = str(row.get("id") or "").strip()
        if not fid or fid in seen:
            fid = new_id()
        seen.add(fid)
        row["id"] = fid
        row["enabled"] = _flag(row.get("enabled"), True)
        row["source"] = _source(row.get("source"))
        row["target"] = str(row.get("target") or REPLY).strip() or REPLY
        row["address"] = str(row.get("address") or "").strip()
        row["min"] = _float(row.get("min"), 0.0)
        row["max"] = _float(row.get("max"), 1.0)
        kind = str(row.get("type") or "auto").strip().lower()
        row["type"] = kind if kind in VALUE_TYPES else "auto"
        # Off/on values and template: kept only when set (rows without them
        # stay as they were written).
        for key in ("off_value", "on_value"):
            value = _off_on(row.pop(key, None))
            if value is not None:
                row[key] = value
        template = row.pop("template", None)
        if template in TEMPLATES:
            row["template"] = template
        # Show under this input (S153): an OSC input uid, kept only when set.
        under = str(row.pop("input", None) or "").strip()
        if under:
            row["input"] = under
        out.append(row)
    return out


def _off_on(value: object) -> str | int | float | None:
    """An off/on value: None (not set: Min/Max are sent), a number, or
    text such as "#2a7a46"."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    return text or None


def find_companion_target(targets: list[dict] | None = None) -> dict | None:
    """The target named "Companion", else one at 127.0.0.1:12321."""
    targets = read_targets() if targets is None else targets
    for target in targets:
        if str(target.get("name") or "").casefold() == COMPANION_TARGET.casefold():
            return target
    for target in targets:
        here = (target.get("host"), target.get("port"))
        if here == (COMPANION_HOST, COMPANION_PORT):
            return target
    return None


def ensure_companion_target(who: str = "") -> dict:
    """The Companion target, added (127.0.0.1:12321) when there is none.
    Raises OSError when the write failed."""
    targets = read_targets()
    found = find_companion_target(targets)
    if found is not None:
        return found
    target = {
        "id": new_id(),
        "name": COMPANION_TARGET,
        "host": COMPANION_HOST,
        "port": COMPANION_PORT,
    }
    write_targets([*targets, target], who)
    return find_companion_target() or target


def read_inputs() -> list[dict]:
    """The file's input rows; empty when the file is missing or damaged."""
    return _clean(store.read_path(path()).get(KEY))


def read_server() -> dict:
    """The file's server settings, defaults filled in (all defaults when the
    file is missing or damaged)."""
    return clean_server(store.read_path(path()).get(SERVER_KEY))


def read_targets() -> list[dict]:
    """The file's targets. A file without "targets" gives the one "Default"
    target (written on the next write)."""
    doc = store.read_path(path())
    if TARGETS_KEY not in doc:
        return [default_target()]
    return clean_targets(doc.get(TARGETS_KEY))


def read_feedback() -> list[dict]:
    """The file's feedback rows; empty when there are none."""
    return clean_feedback(store.read_path(path()).get(FEEDBACK_KEY))


def _write_key(key: str, value: object, who: str, signal_name: str) -> bool:
    same: list[bool] = []

    def change(doc: dict) -> bool:
        if doc.get(key) == value:
            same.append(True)
            return False
        _put_identity(doc)
        doc[key] = value
        return True

    count = len(value) if isinstance(value, list) else 0
    what = f"{count} {_KEY_TEXT.get(key, key)}"
    if not store.update_path(_write_path(), change, who or WHO):
        _trace(
            f"OSC/module.json not written ({what} unchanged)"
            if same
            else "OSC/module.json not saved: the file is damaged (refused)",
            warning=not same,
        )
        return False
    _trace(f"OSC/module.json saved ({what})")
    _emit(signal_name)
    return True


_KEY_TEXT = {TARGETS_KEY: "targets", FEEDBACK_KEY: "feedback rows"}


def write_targets(targets: list[dict], who: str = "") -> bool:
    """Writes the targets list, keeping the rest of the file. True when
    written; False when unchanged or a damaged file was refused. Raises
    OSError when the write failed. Says oscServerSettingsChanged."""
    return _write_key(
        TARGETS_KEY, clean_targets(targets), who, "oscServerSettingsChanged"
    )


def write_feedback(rows: list[dict], who: str = "") -> bool:
    """Writes the feedback rows, keeping the rest of the file. True when
    written; False when unchanged or a damaged file was refused. Raises
    OSError when the write failed. Says oscFeedbackChanged."""
    return _write_key(FEEDBACK_KEY, clean_feedback(rows), who, "oscFeedbackChanged")


def load(rows: OscRows | None = None) -> dict:
    """Fills OSC's rows (or rows) from the file and gives the server
    settings. A missing file is an empty list; the file is made on the
    first save. An entry that can't be read is skipped (named in the rows'
    load_warnings, also logged) and kept for Save (AD1)."""
    file = path()
    doc = store.read_path(file)
    if not file.exists():
        _trace("OSC/module.json missing: defaults used (made on the first save)")
    target = _rows(rows)
    # Each unreadable row is said once, below; no error traceback per row.
    with quiet():
        target.load_dict({KEY: _raw(doc.get(KEY))})
    warnings = list(getattr(target, "load_warnings", []) or [])
    places = [i for i, _ in getattr(target, "unreadable", None) or []]
    for n, warning in enumerate(warnings):
        logging.getLogger("system").warning(warning)
        found = _WHY.search(warning)
        place = places[n] + 1 if n < len(places) else n + 1
        why = found.group(1) if found else warning
        _trace(f"row {place} unreadable: {why} (kept in the file)", warning=True)
    _note_cleaned(doc.get(SERVER_KEY))
    if trace.osc_on("setup"):
        targets = doc.get(TARGETS_KEY) if TARGETS_KEY in doc else [default_target()]
        skipped = f", {len(places)} unreadable" if places else ""
        _trace(
            f"OSC/module.json loaded ({len(_raw(doc.get(KEY))) - len(places)} inputs, "
            f"{len(clean_targets(targets))} targets{skipped})"
        )
    target.layout = store.normalize_layout(doc.get(store.LAYOUT_KEY))
    target.names = _read_names(doc)
    # What the file held: a save writes only the names the page changed,
    # so names written another way (Module Setup, Device Pack) are kept.
    target.names_loaded = dict(target.names)
    target.mark_saved()
    return clean_server(doc.get(SERVER_KEY))


def _read_names(doc: dict) -> dict[str, str]:
    """Your names for OSC's inputs: the claim's "osc:<uid>" friendly names."""
    claim = doc.get("claim")
    friendly = claim.get("friendly") if isinstance(claim, dict) else None
    names: dict[str, str] = {}
    for key, value in (friendly or {}).items():
        key_text, text = str(key), str(value or "").strip()
        if key_text.startswith(NAME_PREFIX) and key_text != NAME_PREFIX and text:
            names[key_text] = text
    return names


def _put_layout(
    doc: dict, layout: dict, names: dict[str, str], loaded: dict[str, str]
) -> None:
    """The page's groups, order and names into the file's "layout" key and
    the claim's "osc:<uid>" friendly names. Only names the page changed
    since it read the file are written or removed; others are kept."""
    if not layout or layout == store.empty_layout():
        doc.pop(store.LAYOUT_KEY, None)
    else:
        doc[store.LAYOUT_KEY] = layout
    claim = doc.get("claim")
    if not isinstance(claim, dict):
        claim = doc["claim"] = {}
    friendly = claim.get("friendly")
    if not isinstance(friendly, dict):
        friendly = {}
    friendly = dict(friendly)
    for key in loaded:
        if key not in names:
            friendly.pop(key, None)
    for key, name in names.items():
        if name and loaded.get(key) != name:
            friendly[key] = name
    if friendly:
        claim["friendly"] = friendly
    else:
        claim.pop("friendly", None)
    if not claim:
        doc.pop("claim", None)


def _put_identity(doc: dict) -> None:
    # What makes it OSC's module file for the Library and Import; kept as
    # they are when already there.
    for key, value in _identity().items():
        if not doc.get(key):
            doc[key] = value


def save(rows: OscRows | None = None, who: str = "") -> bool:
    """Writes the input rows into the file, keeping its other keys (the
    server settings too) and the entries the last load couldn't read, in
    their places (AD1). False when a damaged file was refused (said in the
    error dialog); raises OSError when the write failed."""
    source = _rows(rows)
    inputs = _with_unreadable(_clean(source.to_dict()), source)
    layout = store.normalize_layout(source.layout)
    names = dict(source.names)
    loaded = dict(getattr(source, "names_loaded", {}) or {})

    def change(doc: dict) -> None:
        _put_identity(doc)
        doc[KEY] = inputs
        _put_layout(doc, layout, names, loaded)

    if not store.update_path(_write_path(), change, who or WHO):
        _trace("OSC/module.json not saved: the file is damaged (refused)", warning=True)
        return False
    _trace(f"OSC/module.json saved ({len(inputs)} inputs)")
    source.names_loaded = names
    source.mark_saved()
    return True


def save_if_dirty(who: str = "") -> bool:
    """Saves OSC's rows when they changed; True when written."""
    rows = _rows(None)
    if not rows.dirty:
        return False
    return save(rows, who)


def _emit(name: str) -> None:
    from gremlin.signal import signal

    sig = getattr(signal, name, None)
    if sig is not None:
        sig.emit()


def write_server(settings: dict, who: str = "") -> bool:
    """Writes the server settings (missing keys get defaults), keeping the
    rest of the file. True when written; False when unchanged or a damaged
    file was refused. Raises OSError when the write failed. Says
    oscServerSettingsChanged so the server applies them at once."""
    server = clean_server(settings)

    same: list[bool] = []

    def change(doc: dict) -> bool:
        if doc.get(SERVER_KEY) == server:
            same.append(True)
            return False
        _put_identity(doc)
        doc[SERVER_KEY] = server
        return True

    if not store.update_path(_write_path(), change, who or WHO):
        _trace(
            "OSC/module.json not written (server settings unchanged)"
            if same
            else "OSC/module.json not saved: the file is damaged (refused)",
            warning=not same,
        )
        return False
    _trace("OSC/module.json saved (server settings)")
    _emit("oscServerSettingsChanged")
    return True
