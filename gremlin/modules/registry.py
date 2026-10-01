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
from dataclasses import dataclass, field
from pathlib import Path

from gremlin.modules.claim import read_claim
from gremlin.modules.ids import guid_key

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


def is_output_name(name: str) -> bool:
    """vJoy and Xbox modules are outputs, whatever their file says."""
    slug = plain_slug(name)
    lower = " ".join(str(name or "").split()).lower()
    return slug.startswith("vjoy") or slug.startswith("xbox") or "xbox" in lower


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


# path -> ((mtime_ns, size), Module | None)
_cache: dict[Path, tuple[tuple[int, int], Module | None]] = {}


def _folder() -> Path:
    from gremlin.util import modules_dir

    return Path(modules_dir())


def _read(path: Path) -> Module | None:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    if not isinstance(doc, dict):
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
    seen: set[Path] = set()
    out: list[Module] = []
    for path in sorted(folder.glob("*.json")):
        seen.add(path)
        try:
            stat = path.stat()
        except OSError:
            continue
        stamp = (stat.st_mtime_ns, stat.st_size)
        cached = _cache.get(path)
        if cached is None or cached[0] != stamp:
            cached = (stamp, _read(path))
            _cache[path] = cached
        if cached[1] is not None:
            out.append(cached[1])
    for gone in [p for p in _cache if p not in seen]:
        _cache.pop(gone, None)
    return out


def inputs() -> list[Module]:
    return [m for m in modules() if not m.is_output]


def outputs() -> list[Module]:
    return [m for m in modules() if m.is_output]


def find(guid: object = "", name: str = "") -> Module | None:
    """A module by bound device first, then by name (file name or device name)."""
    key = guid_key(guid)
    all_modules = modules()
    if key:
        for module in all_modules:
            if guid_key(module.bound_guid) == key:
                return module
    wanted = " ".join(str(name or "").split()).casefold()
    if wanted:
        slug = plain_slug(name)
        for module in all_modules:
            if module.slug == slug or module.name.casefold() == wanted:
                return module
    return None


def output_for_vjoy(vjoy_id: int) -> Module | None:
    """The output module that drives this vJoy device."""
    for module in outputs():
        if resolve_vjoy_id(module.name, module.bound_guid) == int(vjoy_id):
            return module
    return None
