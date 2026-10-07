# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The module files in the data folder's modules folder: read once, classified
once (input or output), and found by bound device or name.

A file is re-read only when it changes on disk, so callers always see what
was last saved.
"""

from __future__ import annotations

import json
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path

from gremlin.modules.claim import read_claim
from gremlin.modules.ids import guid_key, stored_guid_key

_OUTPUT_WORDS = ("dest", "target", "output")
_INPUT_WORDS = ("source", "input")


@dataclass(frozen=True)
class Module:
    """One module file."""

    slug: str
    path: Path
    doc: dict = field(compare=False, repr=False)
    name: str
    bound_guid: str
    bound_name: str
    direction: str
    claim: dict = field(compare=False, repr=False)

    @property
    def is_output(self) -> bool:
        return self.direction == "dest"


def plain_slug(device_name: str) -> str:
    """File-name form of a device name: lower case, runs of other characters
    become one underscore, a trailing .json is dropped."""
    raw = str(device_name or "").strip().lower()
    if raw.endswith(".json"):
        raw = raw[:-5]
    out: list[str] = []
    for ch in raw:
        if ch.isalnum():
            out.append(ch)
        elif out and out[-1] != "_":
            out.append("_")
    return "".join(out).strip("_")


# The names Gremlin gives its own Xbox output modules: "Xbox 360 Controller",
# "Xbox 360 2", "Xbox pad 2", and the tab's "xbox". A real Xbox pad is named
# differently by Windows ("Controller (XBOX 360 For Windows)", "Xbox Wireless
# Controller") and is an input.
_GREMLIN_XBOX = re.compile(r"^xbox(?:_360_controller|_360_[1-4]|_pad_[1-4])?$")


def is_gremlin_xbox_name(name: str) -> bool:
    """True for the name (or file name) of Gremlin's own Xbox output module."""
    return bool(_GREMLIN_XBOX.match(plain_slug(name)))


def is_output_name(name: str) -> bool:
    """vJoy and Gremlin's Xbox modules are outputs, whatever their file says."""
    slug = plain_slug(name)
    return slug.startswith("vjoy") or is_gremlin_xbox_name(name)


def module_direction(doc: dict | None, slug: str = "", name: str = "") -> str:
    """"dest" for an output module, "source" for an input module.

    A file marked dest / target / output is an output; a vJoy or Xbox module is
    always an output; anything else is an input.
    """
    raw = str((doc or {}).get("direction") or "").strip().lower()
    if raw in _OUTPUT_WORDS:
        return "dest"
    named = str((doc or {}).get("device") or name or slug or "")
    if is_output_name(named) or is_output_name(slug):
        return "dest"
    return "source"


def vjoy_id_from_name(name: str) -> int:
    """The vJoy number in a module name: the first run of digits ("vJoy 1 (2)"
    is vJoy 1). 0 when the name has none."""
    match = re.search(r"(\d+)", str(name or ""))
    return int(match.group(1)) if match else 0


def resolve_vjoy_id(name: str, bound_guid: str = "") -> int:
    """The vJoy device an output module drives: its bound device when that is a
    vJoy output, otherwise the number in its name if that vJoy exists. 0 when
    neither matches."""
    from gremlin import device_initialization

    try:
        devices = list(device_initialization.output_vjoy_devices() or [])
    except Exception:
        devices = []
    want = guid_key(bound_guid)
    if want:
        for device in devices:
            if guid_key(getattr(device, "device_guid", "")) == want:
                return int(device.vjoy_id)
    guess = vjoy_id_from_name(name)
    if guess and guess in {int(device.vjoy_id) for device in devices}:
        return guess
    return 0


def trace(action: str, window: str, function: str, path: object, result: str) -> None:
    """Write a line to the live debug log. That log is a UI window, so it is
    loaded only when a module file is read or saved."""
    from gremlin.ui.live_debug import trace as live_trace

    live_trace(action, window, function, path, result)


# Which module file each device uses: guid (or name:slug) -> slug.

def _guid_for_name(device_name: str) -> str:
    """The id of the connected device with this name. A vJoy is also found by
    "vJoy <n>", the name its module file has (it reports "vJoy Device"):
    without that, a call with no id for a vJoy had no id to check a file's
    binding against, and it opened another vJoy's file."""
    wanted = (device_name or "").strip().lower()
    if not wanted:
        return ""
    try:
        from gremlin import device_initialization
        devices = list(device_initialization.physical_devices() or [])
        vjoys = list(device_initialization.vjoy_devices() or [])
    except Exception:
        devices, vjoys = [], []
    for dev in devices + vjoys:
        name = str(getattr(dev, "name", "") or "")
        if name.strip().lower() != wanted:
            continue
        return stored_guid_key(getattr(dev, "device_guid", ""))
    for dev in vjoys:
        if f"vjoy {getattr(dev, 'vjoy_id', '')}" == " ".join(wanted.split()):
            return stored_guid_key(getattr(dev, "device_guid", ""))
    return ""


def _binding_store() -> dict[str, str]:
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    cfg = Configuration()
    section, group, name = "global", "internal", "module-file-bindings"
    # Register every launch. An existing value is kept. Skipping this when
    # the key already exists leaves it unregistered, and purge_unused deletes it.
    cfg.register(
        section,
        group,
        name,
        PropertyType.String,
        "{}",
        "Input module file chosen for each device.",
        {},
        False,
    )
    try:
        data = json.loads(cfg.value(section, group, name) or "{}")
    except (TypeError, json.JSONDecodeError):
        data = {}
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items() if key and value}


def _name_key(device_name: str) -> str:
    slug = plain_slug(device_name)
    return f"name:{slug}" if slug else ""


def _connected_names() -> dict[str, set[str]]:
    """Each connected device's name (casefolded) -> the ids that have it.
    A vJoy is also listed as "vjoy <n>", the name its module file has."""
    try:
        from gremlin import device_initialization

        sticks = list(device_initialization.physical_devices() or [])
        vjoys = list(device_initialization.vjoy_devices() or [])
    except Exception:
        return {}
    names: dict[str, set[str]] = {}

    def add(name: str, dev: object) -> None:
        key = " ".join(str(name or "").split()).casefold()
        if key:
            names.setdefault(key, set()).add(guid_key(getattr(dev, "device_guid", "")))

    for dev in sticks + vjoys:
        add(str(getattr(dev, "name", "") or ""), dev)
    for dev in vjoys:
        add(f"vJoy {getattr(dev, 'vjoy_id', '')}", dev)
    return names


def _belongs_elsewhere(slug: str, want: str, device_name: str) -> bool:
    """True when the module file slug belongs to another device: it is bound
    to another device (its boundGuidLocal), or it is named after another
    connected device, or after another vJoy. Twins once both saved into one
    file; each now gets its own, and one vJoy never opens another's file."""
    module = next((m for m in modules() if m.slug == slug), None)
    if module is None:
        return False
    other = guid_key(module.bound_guid)
    if want and other and other != want:
        return True
    named = " ".join(module.name.split()).casefold()
    this = " ".join(str(device_name or "").split()).casefold()
    if not named or named == this:
        return False
    vjoys = all(plain_slug(n).startswith("vjoy") for n in (module.name, device_name))
    if vjoys and vjoy_id_from_name(module.name) != vjoy_id_from_name(device_name):
        return True
    owners = _connected_names().get(named, set())
    return bool(owners - {want})


def resolve_module_slug(device_name: str, guid: str = "") -> str:
    """The module file a device uses. The one rule Module Setup, the Button
    Map, Run and Calibration share (they used to differ, so a stick's ticks
    could do nothing at Run):
    1. the file saved for this device (its id);
    2. a file bound to this exact device (boundGuidLocal), when it names
       this device or there is no file of the device's own name (the device
       was renamed); so a stale id never pulls in another device's file;
    3. the file saved for this device name;
    4. the file named after the device (twins are named "<name> (2)").
    Steps 1-3 skip a file that belongs to another device (_belongs_elsewhere):
    both twins once saved to one file, and the second one kept opening it.
    """
    data = _binding_store()
    key = stored_guid_key(guid) or _guid_for_name(device_name)
    want = guid_key(key)
    own = plain_slug(device_name) or "device"
    saved = plain_slug(data.get(key, "")) if key else ""
    if saved and not _belongs_elsewhere(saved, want, device_name):
        return saved
    if want:
        wanted_name = " ".join(str(device_name or "").split()).casefold()
        own_exists = (_folder() / f"{own}.json").is_file()
        for module in sorted(modules(), key=lambda m: m.slug != own):
            if guid_key(module.bound_guid) != want:
                continue
            names = {module.name.casefold(), module.bound_name.casefold()}
            if not (module.slug == own or wanted_name in names or not own_exists):
                continue
            if not _belongs_elsewhere(module.slug, want, device_name):
                return module.slug
    name_key = _name_key(device_name)
    by_name = plain_slug(data.get(name_key, "")) if name_key else ""
    if by_name and not _belongs_elsewhere(by_name, want, device_name):
        return by_name
    return own


def device_has_name(guid: str, device_name: str) -> bool:
    """True when a connected device (stick or vJoy) with this id has this
    name. (Twin sticks share a name: the first one's id isn't the only one.)"""
    want = guid_key(guid)
    wanted = (device_name or "").strip().lower()
    if not want or not wanted:
        return False
    try:
        from gremlin import device_initialization

        devices = list(device_initialization.physical_devices() or [])
        devices.extend(device_initialization.vjoy_devices() or [])
    except Exception:
        return False
    return any(
        guid_key(getattr(dev, "device_guid", "")) == want
        and str(getattr(dev, "name", "") or "").strip().lower() == wanted
        for dev in devices
    )


# path -> ((mtime_ns, size), Module | None)
_cache: dict[Path, tuple[tuple[int, int], Module | None]] = {}
# modules() runs on the main thread and on action threads (output claims):
# one reader at a time walks and changes _cache (GL-038).
_cache_lock = threading.RLock()


def _folder() -> Path:
    # The store owns where module files are (one place to point elsewhere).
    from gremlin.modules import store

    return store.folder()


def read_doc(path: Path) -> dict | None:
    """A module (or other JSON) file's content, or None when it is missing,
    can't be read or isn't a JSON object. A damaged file (bad text, or not
    UTF-8) is skipped and named in the log: readers that caught only bad
    JSON stopped on a file that wasn't UTF-8."""
    try:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError:
        return None
    except ValueError as exc:
        import logging

        logging.getLogger("system").warning(f"Skipped damaged file {path}: {exc}")
        return None
    return doc if isinstance(doc, dict) else None


def _read(path: Path) -> Module | None:
    doc = read_doc(path)
    if doc is None:
        return None
    slug = path.stem.lower()
    name = str(doc.get("device") or doc.get("boundName") or path.stem).strip()
    if not name:
        return None
    return Module(
        slug=slug,
        path=path,
        doc=doc,
        name=name,
        bound_guid=str(doc.get("boundGuidLocal") or "").strip(),
        bound_name=str(doc.get("boundName") or name).strip(),
        direction=module_direction(doc, slug, name),
        claim=read_claim(doc),
    )


def modules() -> list[Module]:
    """Every module file, sorted by file name."""
    folder = _folder()
    if not folder.is_dir():
        return []
    with _cache_lock:
        cache = _cache
        seen: set[Path] = set()
        out: list[Module] = []
        for path in sorted(folder.glob("*.json")):
            seen.add(path)
            try:
                stat = path.stat()
            except OSError:
                continue
            stamp = (stat.st_mtime_ns, stat.st_size)
            cached = cache.get(path)
            if cached is None or cached[0] != stamp:
                cached = (stamp, _read(path))
                cache[path] = cached
            if cached[1] is not None:
                out.append(cached[1])
        for gone in [p for p in cache if p not in seen]:
            cache.pop(gone, None)
        return out


def inputs() -> list[Module]:
    return [m for m in modules() if not m.is_output]


def outputs() -> list[Module]:
    return [m for m in modules() if m.is_output]


def output_for_vjoy(vjoy_id: int) -> Module | None:
    """The output module that drives this vJoy device."""
    for module in outputs():
        if resolve_vjoy_id(module.name, module.bound_guid) == int(vjoy_id):
            return module
    return None


def find_path(path: Path) -> Module | None:
    """The module read from this file (None: missing or damaged)."""
    path = Path(path)
    for module in modules():
        if module.path == path:
            return module
    return None


def for_device(device_name: str, guid: str = "") -> Module | None:
    """The module file a device uses (store.path_for: the one rule, a stale
    id filtered out first)."""
    from gremlin.modules import store

    return find_path(store.path_for(device_name, guid))


# Public doors for the module file store and other callers (the underscore
# names stay for this module's own use).


def guid_for_name(device_name: str) -> str:
    """The id of the connected device with this name ("" when none)."""
    return _guid_for_name(device_name)


def binding_store() -> dict[str, str]:
    """The saved module file choices: device id or name:<slug> -> slug."""
    return _binding_store()


def name_key(device_name: str) -> str:
    """The file choice key of a device name ("name:<slug>")."""
    return _name_key(device_name)


def connected_names() -> dict[str, set[str]]:
    """Each connected device's name (casefolded) -> the ids that have it."""
    return _connected_names()


def folder() -> Path:
    """The modules folder (the store's)."""
    return _folder()
