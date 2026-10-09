# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC's own module file (decision D-09-OSC-FILE).

Every profile uses one OSC address list, kept under "inputs" in
<modules>/osc.json, with the server and behaviour settings under "server";
the file's other keys are left as they are. Writes go through
gremlin.modules.store, so module-file History records them.

Version 14/15 profiles carried their own rows: merge_profile_rows adds them
to the file and gives the uid each old (type, number) now points at. While
such a profile loads, profile.py puts that map in current_uid_map.

Main thread only.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from gremlin.modules import store

if TYPE_CHECKING:
    from gremlin.osc_rows import OscRows

SLUG = "osc"
KEY = "inputs"
SERVER_KEY = "server"
WHO = "OSC"

SERVER_DEFAULTS: dict[str, Any] = {
    "enabled": True,
    "host": "",
    "port": 8001,
    "output_host": "127.0.0.1",
    "output_port": 8000,
    "autorelease_no_arg": True,
    "autorelease_delay_ms": 250,
    "pad_args": False,
}

# configuration osc/connection/<name> -> server key (first start only).
_CONFIG_NAMES = {
    "enabled": "enabled",
    "host": "host",
    "port": "port",
    "output-host": "output_host",
    "output-port": "output_port",
    "autorelease-no-arg": "autorelease_no_arg",
    "autorelease-delay": "autorelease_delay_ms",
    "pad-args": "pad_args",
}

syslog = logging.getLogger("system")

# (type name, number) in the old profile being loaded -> uid in the file.
current_uid_map: dict[tuple[str, int], str] | None = None


@dataclass
class MergeResult:
    uid_map: dict[tuple[str, int], str] = field(default_factory=dict)
    added: list[str] = field(default_factory=list)


def path() -> Path:
    return store.path_of(SLUG)


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
    unknown keys are kept."""
    given = dict(raw) if isinstance(raw, dict) else {}
    out = dict(given)
    d = SERVER_DEFAULTS
    out["enabled"] = _flag(given.get("enabled"), d["enabled"])
    out["host"] = str(given.get("host") or "").strip()
    out["port"] = _port(given.get("port"), d["port"])
    out["output_host"] = str(given.get("output_host") or d["output_host"]).strip()
    out["output_port"] = _port(given.get("output_port"), d["output_port"])
    out["autorelease_no_arg"] = _flag(
        given.get("autorelease_no_arg"), d["autorelease_no_arg"]
    )
    out["autorelease_delay_ms"] = _delay(
        given.get("autorelease_delay_ms"), d["autorelease_delay_ms"]
    )
    out["pad_args"] = _flag(given.get("pad_args"), d["pad_args"])
    return out


def read_inputs() -> list[dict]:
    """The file's input rows; empty when the file is missing or damaged."""
    return _clean(store.read_path(path()).get(KEY))


def read_server() -> dict:
    """The file's server settings, defaults filled in (all defaults when the
    file is missing or damaged)."""
    return clean_server(store.read_path(path()).get(SERVER_KEY))


def load(rows: OscRows | None = None) -> dict:
    """Fills OSC's rows (or rows) from the file and gives the server
    settings. A missing file is an empty list; the file is made on the
    first save."""
    doc = store.read_path(path())
    target = _rows(rows)
    target.load_dict({KEY: _clean(doc.get(KEY))})
    target.mark_saved()
    convert_friendly_keys(target)
    return clean_server(doc.get(SERVER_KEY))


def _uid_key(rows: OscRows, key: str) -> str:
    """ "osc:<uid>" for an old "button:N"/"axis:N" friendly key whose input
    the rows have; "" otherwise."""
    from gremlin.modules.claim import type_of

    kind, _, raw = str(key).partition(":")
    number = _number(raw)
    if kind not in ("button", "axis") or number is None:
        return ""
    uid_of = getattr(rows, "uid_of", None)
    uid = uid_of(type_of(kind), number) if uid_of is not None else None
    return f"osc:{uid}" if uid else ""


def convert_friendly_keys(rows: OscRows | None = None) -> bool:
    """Moves the file's old "button:N"/"axis:N" friendly names to
    "osc:<uid>" keys, by the rows read from the same file. Keys with no row
    are left as they are. True when the file was written."""
    target = _rows(rows)

    def change(doc: dict) -> bool:
        claim = doc.get("claim")
        names = claim.get("friendly") if isinstance(claim, dict) else None
        if not isinstance(claim, dict) or not isinstance(names, dict):
            return False
        moved = {}
        for key, value in names.items():
            new_key = _uid_key(target, key)
            if new_key and not names.get(new_key):
                moved[key] = new_key
        if not moved:
            return False
        claim["friendly"] = {moved.get(k, k): v for k, v in names.items()}
        return True

    if not path().is_file():
        return False
    return store.update_path(path(), change, WHO, report=False)


def _put_identity(doc: dict) -> None:
    # What makes it OSC's module file for the Library and Import; kept as
    # they are when already there.
    for key, value in _identity().items():
        if not doc.get(key):
            doc[key] = value


def save(rows: OscRows | None = None, who: str = "") -> bool:
    """Writes the input rows into the file, keeping its other keys (the
    server settings too). False when a damaged file was refused (said in the
    error dialog); raises OSError when the write failed."""
    source = _rows(rows)
    inputs = _clean(source.to_dict())

    def change(doc: dict) -> None:
        _put_identity(doc)
        doc[KEY] = inputs

    if not store.update_path(path(), change, who or WHO):
        return False
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

    def change(doc: dict) -> bool:
        if doc.get(SERVER_KEY) == server:
            return False
        _put_identity(doc)
        doc[SERVER_KEY] = server
        return True

    if not store.update_path(path(), change, who or WHO):
        return False
    _emit("oscServerSettingsChanged")
    return True


def _origin_uid(kind: str, number: int, address: str) -> str:
    """The uid an old row without one gets: the same every time, so a dry
    run (Library browsing) and the later real merge agree."""
    return uuid.uuid5(_ORIGIN, f"{kind}:{number}:{address}").hex


_ORIGIN = uuid.UUID("0b8e6a52-3f4d-4c1e-a7d9-91c2f5e83b47")


def _address(row: dict) -> str:
    return str(row.get("label") or "").strip().casefold()


def _value(item: object) -> object:
    """A data value as OscRows compares it: numbers as numbers, else text."""
    try:
        return float(str(item).strip())
    except (TypeError, ValueError):
        return str(item)


def match_key(row: dict) -> tuple:
    """What makes an OSC input unique (OscRows refuses a second one): type,
    address (casefold), command mode, data and source. Old rows have none of
    the last three: "message", [] and 0."""
    data = row.get("data") or []
    if not isinstance(data, list):
        data = [data]
    return (
        str(row.get("type") or ""),
        _address(row),
        str(row.get("cmd_mode") or "message"),
        tuple(_value(d) for d in data),
        _number(row.get("source")) or 0,
    )


def merge_rows(
    file_inputs: list[dict], profile_inputs: object
) -> tuple[list[dict], MergeResult]:
    """Decision 3 on plain rows: a profile row whose uid the file has, or
    with the same match key (type, address, command mode, data, source) as a
    file row, is that row whatever its number; the old (type, number) maps
    to its uid so references follow. Any other is added under its own number
    when free, else the lowest free number of its type, with its own uid
    (the one it carries, else one made from type, number and address). No
    two rows ever share a key; nothing is removed."""
    merged = [dict(r) for r in _clean(file_inputs)]
    result = MergeResult()
    for entry in merged:
        if not entry.get("uid"):
            entry["uid"] = uuid.uuid4().hex
    used = {(str(r.get("type")), _number(r.get("id"))) for r in merged}
    keys = {match_key(r): r for r in reversed(merged)}
    for entry in _clean(profile_inputs):
        kind = str(entry.get("type") or "")
        number = _number(entry.get("id"))
        if not kind or number is None:
            continue
        carried = str(entry.get("uid") or "")
        same = None
        if carried:
            same = next((r for r in merged if str(r.get("uid")) == carried), None)
        if same is None:
            same = keys.get(match_key(entry))
        if same is not None:
            result.uid_map[(kind, number)] = str(same["uid"])
            continue
        if not carried:
            carried = _origin_uid(kind, number, _address(entry))
        new_number = number
        if (kind, new_number) in used or new_number < 1:
            new_number = 1
            while (kind, new_number) in used:
                new_number += 1
        added = dict(entry)
        added.update(uid=carried, type=kind, id=new_number)
        merged.append(added)
        used.add((kind, new_number))
        keys[match_key(added)] = added
        result.uid_map[(kind, number)] = carried
        result.added.append(str(entry.get("label") or ""))
    return merged, result


def merge_profile_rows(
    profile_dict: object, dry_run: bool = False, *, rows: OscRows | None = None
) -> MergeResult:
    """Adds an old profile's OSC rows (profile_dict, in the to_dict layout)
    to OSC's rows and its file. The file is written at once when the result
    differs from it. dry_run gives the same result and changes nothing (a
    profile read without binding, such as Library browsing)."""
    target = _rows(rows)
    merged, result = merge_rows(_clean(target.to_dict()), profile_dict)
    if dry_run:
        return result
    if result.added:
        target.load_dict({KEY: merged})
    # A matching row only in memory (not saved yet) still reaches the file.
    if _clean(target.to_dict()) != read_inputs():
        save(target, WHO)
    return result


def backup_old(profile_path: Path, version: int | str) -> Path | None:
    """Keeps the old profile as <name>.xml.v<version>.bak beside it, only if
    there isn't one already. The backup's path, or None when none was made."""
    source = Path(profile_path)
    backup = source.with_name(f"{source.name}.v{version}.bak")
    if backup.exists() or not source.is_file():
        return None
    try:
        # A profile copy, not a module file: copy beside it, then rename.
        part = backup.with_name(backup.name + ".part")
        shutil.copyfile(source, part)
        os.replace(part, backup)
    except OSError:
        syslog.exception("The old profile backup could not be written: %s", backup)
        return None
    return backup


def _own_addresses() -> set[str]:
    from gremlin.osc import local_ipv4_addresses

    return {ip for ip in local_ipv4_addresses() if ip != "127.0.0.1"}


def _config_values() -> dict:
    """The configuration's osc/connection settings that are set."""
    from gremlin.config import Configuration
    from gremlin.osc import osc_option

    cfg = Configuration()
    found: dict = {}
    for name, key in _CONFIG_NAMES.items():
        try:
            value = osc_option(cfg, name)
        except Exception:  # noqa: BLE001 - an unreadable option keeps its default
            syslog.exception("OSC: configuration option %s could not be read", name)
            continue
        if value is not None:
            found[key] = value
    return found


def migrate_settings_from_config() -> bool:
    """First start: copies configuration osc/connection/* into the file's
    "server" once (only while it has none). A saved host equal to this PC's
    own address becomes "" (all addresses), so a changed DHCP address keeps
    working. Only settings that differ from the defaults are a reason to
    write: with none, nothing is written (read_server() gives the defaults
    and the file is made on the first real save), so a fresh install has no
    OSC file. True when written; a damaged file is left alone."""
    if store.damage_of(path()):
        return False
    if SERVER_KEY in store.read_path(path()):
        return False
    values = _config_values()
    host = str(values.get("host") or "").strip()
    if host and (host == "0.0.0.0" or host in _own_addresses()):
        values["host"] = ""
    server = clean_server(values)
    if all(server[key] == value for key, value in SERVER_DEFAULTS.items()):
        return False

    def change(doc: dict) -> bool:
        if SERVER_KEY in doc:
            return False
        _put_identity(doc)
        doc[SERVER_KEY] = server
        return True

    return store.update_path(path(), change, WHO, report=False)
