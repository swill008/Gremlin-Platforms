# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Swap with Another Stick (10 F, S26-S29): two connected sticks exchange the
ticked parts. Module-file parts go through modules/store.py, bindings
through swap_devices on each ticked profile (library_profiles.Batch). Both
sticks get an autosave first; Undo is library_copy.undo_last (S41)."""

from __future__ import annotations

import copy
import logging
import uuid
from pathlib import Path

from gremlin import shared_state, swap_devices
from gremlin.modules import device_class, store
from gremlin.modules.claim import kind_of
from gremlin.profile import Profile

Stick = tuple[str, str]  # (device name, device id text)
Controls = swap_devices.Controls

_MODULE_PARTS = ("setup", "button_map", "appearance", "calibration")
_KIND_WORD = {"button": "Button", "axis": "Axis", "hat": "Hat"}
_BUCKET = {"button": "buttons", "axis": "axes", "hat": "hats"}
# The Button Map's keys in a module file: the map, the photo, its view and
# print settings.
_MAP_KEYS = ("nodes", "image", "photo", "ui")
_APPEARANCE_KEYS = ("view", "catalog")


def _refused_word(ident: uuid.UUID) -> str:
    """What the refusal calls a device that isn't a stick (S26, S29): "the
    Keyboard", "the Logical Device", "OSC", "the Xbox controller", "vJoy".
    By id only (03 S90b)."""
    kind = device_class.device_kind(ident)
    if kind == "xbox":
        return "the Xbox controller"
    name = device_class.display_name(kind)
    return name if kind == device_class.VJOY or name.isupper() else f"the {name}"


def _result(ok: bool = True, error: str = "", **extra: object) -> dict:
    out: dict = {"ok": ok, "error": error, "warnings": [], "notes": []}
    out.update(extra)
    return out


def _uuid(guid: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(guid or "").strip())
    except ValueError:
        return None


def _controls(guid: str) -> Controls | None:
    """What a connected stick has; None when it isn't connected."""
    found = store.connected_input_ids(guid)
    if found is None:
        return None
    buttons, axes, hats = found
    return {"button": set(buttons), "axis": set(axes), "hat": set(hats)}


def _own(stick: Stick) -> Stick:
    """The stick by its own name, which finds its module file: the name
    given may be its Home card's; the device id decides (S7)."""
    from gremlin import device_library as library

    return (library.own_name(stick[0], stick[1]) or stick[0], stick[1])


def _refusal(first: Stick, second: Stick) -> str:
    """Why these two can't be swapped (S26, S29); "" when they can."""
    for name, guid in (first, second):
        ident = _uuid(guid)
        if ident is None:
            return (
                f"{name or 'This device'} has no device id: only a stick "
                "plugged in now can be swapped."
            )
        if not device_class.can("swap", ident):
            return f"Swap can't be used with {_refused_word(ident)}."
    if _uuid(first[1]) == _uuid(second[1]):
        return "A stick can't be swapped with itself."
    for name, guid in (first, second):
        if _controls(guid) is None:
            return f"{name} isn't connected: both sticks must be plugged in to swap."
    return ""


def _list_controls(kind_numbers: list[tuple[str, int]]) -> str:
    return ", ".join(f"{_KIND_WORD[kind]} {number}" for kind, number in kind_numbers)


def _lacking(
    numbers: dict[str, set[int]], other_has: Controls
) -> list[tuple[str, int]]:
    return [
        (kind, number)
        for kind in ("button", "axis", "hat")
        for number in sorted(numbers.get(kind, set()) - other_has.get(kind, set()))
    ]


def _bound_controls(profile: object, ident: uuid.UUID) -> dict[str, set[int]]:
    """The buttons, axes and hats of a device that have bindings in a profile."""
    found: dict[str, set[int]] = {"button": set(), "axis": set(), "hat": set()}
    for item in getattr(profile, "inputs", {}).get(ident, []):
        if not item.action_sequences:
            continue
        kind = kind_of(item.input_type)
        if kind in found:
            try:
                found[kind].add(int(item.input_id))
            except (TypeError, ValueError):
                continue
    return found


def _claimed(doc: dict) -> dict[str, set[int]]:
    claim = doc.get("claim") if isinstance(doc.get("claim"), dict) else {}
    out: dict[str, set[int]] = {}
    for kind, bucket in _BUCKET.items():
        out[kind] = set(_ints(claim.get(bucket)))  # type: ignore[union-attr]
    calibration = doc.get("calibration")
    if isinstance(calibration, dict):
        out["axis"] |= set(_ints(calibration.keys()))
    return out


def _ints(values: object) -> list[int]:
    out: list[int] = []
    for raw in values or []:  # type: ignore[union-attr]
        try:
            number = int(raw)
        except (TypeError, ValueError):
            continue
        if number > 0:
            out.append(number)
    return out


def _open_profile(path: Path) -> object | None:
    current = shared_state.current_profile
    if current is None:
        return None
    if not str(path) or str(path) == ".":
        return current if current.fpath is None else None  # the unsaved open profile
    if current.fpath is None:
        return None
    try:
        same = Path(current.fpath).resolve() == Path(path).resolve()
    except OSError:
        same = False
    return current if same else None


def _read_profile(path: Path) -> object | str:
    """The open profile when path is it, else the saved one (library_profiles)."""
    opened = _open_profile(path)
    if opened is not None:
        return opened
    from gremlin import library_profiles

    return library_profiles.read_profile(Path(path))


def _name(path: Path | str) -> str:
    return Path(path).stem if str(path) and str(path) != "." else "Untitled"


def _reference_warnings(
    profile: object, path: Path, first: Stick, second: Stick, has: dict
) -> list[str]:
    """Actions and script variables that refer to a control of one stick the
    other lacks: the reference moves with the swap anyway (S27,
    D-10-SWAP-REFS), so they are listed, not changed."""
    by_id = {_uuid(first[1]): (first, second), _uuid(second[1]): (second, first)}
    out: list[str] = []
    for label, device, kind, number in swap_devices.device_references(profile):  # type: ignore[arg-type]
        pair = by_id.get(device)
        if pair is None:
            continue
        here, there = pair
        if number in has[there].get(kind, set()):
            continue
        word = _KIND_WORD[kind]
        text = (
            f"{label} in {_name(path)} refers to {here[0]} {word} {number}; "
            f"{there[0]} has no {word} {number}. The reference moves with the "
            "swap and isn't changed: check it."
        )
        if text not in out:
            out.append(text)
    return out


def plan_swap(
    first: Stick, second: Stick, parts: list[str], profiles: list[Path]
) -> dict:
    """What Swap would leave where it is (S27): for both directions, the
    controls one stick has (set up, or with bindings in a ticked profile)
    that the other lacks. Those stay where they were."""
    refused = _refusal(_shown(first), _shown(second))
    if refused:
        return _result(False, refused)
    return _plan(first, second, parts, profiles)


def _shown(stick: Stick) -> Stick:
    """The stick by the name the user sees (S17): the Home card's, twins
    with their short id; the device id stays."""
    from gremlin import device_library as library

    return (library.shown(*stick), stick[1])


def _plan(first: Stick, second: Stick, parts: list[str], profiles: list[Path]) -> dict:
    own = {first[1]: _own(first), second[1]: _own(second)}
    first, second = _shown(first), _shown(second)
    out = _result()
    has = {first: _controls(first[1]) or {}, second: _controls(second[1]) or {}}
    pairs = ((first, second), (second, first))
    if any(part in parts for part in ("setup", "calibration")):
        for here, there in pairs:
            doc = store.read_path(store.path_for_id(*own[here[1]]))
            missing = _lacking(_claimed(doc), has[there])
            if missing:
                out["warnings"].append(
                    f"{there[0]} has no {_list_controls(missing)}: {here[0]}'s setup "
                    "for them stays where it was."
                )
    if "bindings" in parts:
        for path in profiles:
            profile = _read_profile(path)
            if isinstance(profile, str):
                out["warnings"].append(f"{profile} It won't change.")
                continue
            for here, there in pairs:
                ident = _uuid(here[1])
                if ident is None:
                    continue
                missing = _lacking(_bound_controls(profile, ident), has[there])
                if missing:
                    out["warnings"].append(
                        f"{there[0]} has no {_list_controls(missing)}: {here[0]}'s "
                        f"bindings on them in {_name(path)} stay where they were."
                    )
            out["warnings"] += _reference_warnings(profile, path, first, second, has)
    return out


# --- module file parts -----------------------------------------------------------


def _exchange_setup(a: dict, b: dict, shared: Controls) -> None:
    """Checked controls and friendly names, for the controls both sticks have."""
    claim_a = a["claim"] = a["claim"] if isinstance(a.get("claim"), dict) else {}
    claim_b = b["claim"] = b["claim"] if isinstance(b.get("claim"), dict) else {}
    names_a = claim_a["friendly"] = (
        claim_a["friendly"] if isinstance(claim_a.get("friendly"), dict) else {}
    )
    names_b = claim_b["friendly"] = (
        claim_b["friendly"] if isinstance(claim_b.get("friendly"), dict) else {}
    )
    for kind, bucket in _BUCKET.items():
        both = shared.get(kind, set())
        have_a = set(_ints(claim_a.get(bucket)))
        have_b = set(_ints(claim_b.get(bucket)))
        claim_a[bucket] = sorted((have_a - both) | (have_b & both))
        claim_b[bucket] = sorted((have_b - both) | (have_a & both))
        for number in both:
            key = f"{kind}:{number}"
            label_a, label_b = names_a.pop(key, None), names_b.pop(key, None)
            if label_b is not None:
                names_a[key] = label_b
            if label_a is not None:
                names_b[key] = label_a


def _exchange_calibration(a: dict, b: dict, shared: Controls) -> None:
    raw_a, raw_b = a.get("calibration"), b.get("calibration")
    cal_a: dict = raw_a if isinstance(raw_a, dict) else {}
    cal_b: dict = raw_b if isinstance(raw_b, dict) else {}
    for number in shared.get("axis", set()):
        key = str(number)
        value_a, value_b = cal_a.pop(key, None), cal_b.pop(key, None)
        if value_b is not None:
            cal_a[key] = value_b
        if value_a is not None:
            cal_b[key] = value_a
    a["calibration"] = cal_a
    b["calibration"] = cal_b


def _exchange_keys(a: dict, b: dict, keys: tuple[str, ...]) -> None:
    for key in keys:
        value_a, value_b = a.pop(key, None), b.pop(key, None)
        if value_b is not None:
            a[key] = value_b
        if value_a is not None:
            b[key] = value_a


def _move_pictures(
    doc: dict, from_slug: str, to_slug: str, files: list[tuple[Path, bytes]]
) -> None:
    """The pictures in from_slug's picture folder that doc's Button Map names
    go to to_slug's folder (read now, written later); doc names them there."""

    def moved(ref: str) -> str:
        text = store.module_relative(ref)
        prefix = f"{from_slug}/"
        if not text.lower().startswith(prefix.lower()):
            return ref  # elsewhere (the picture library, a file: URL): shared
        found = store.find_picture(text)
        if found is None:
            return ref
        name = Path(text).name
        files.append((store.pictures_dir_of(to_slug) / name, found.read_bytes()))
        return store.picture_ref(to_slug, name)

    if doc.get("image"):
        image = str(doc["image"])
        doc["image"] = moved(image if "/" in image else f"{from_slug}/{image}")
    for node in doc.get("nodes") or []:
        if isinstance(node, dict) and node.get("src"):
            node["src"] = moved(str(node["src"]))


def _swapped_docs(
    first: Stick, second: Stick, parts: list[str], shared: Controls
) -> tuple[Path, Path, dict, dict, list[tuple[Path, bytes]]] | str:
    """Both module files after the exchange, and the pictures to write; a
    reason when it can't be done."""
    path_a, path_b = store.path_for_id(*first), store.path_for_id(*second)
    for (name, _), path in ((first, path_a), (second, path_b)):
        reason = store.damage_of(path) if path.is_file() else ""
        if reason:
            return f"{name}'s module file is damaged ({reason}): nothing was swapped."
    doc_a = copy.deepcopy(store.read_path(path_a))
    doc_b = copy.deepcopy(store.read_path(path_b))
    files: list[tuple[Path, bytes]] = []
    if "setup" in parts:
        _exchange_setup(doc_a, doc_b, shared)
    if "calibration" in parts:
        _exchange_calibration(doc_a, doc_b, shared)
    if "appearance" in parts:
        _exchange_keys(doc_a, doc_b, _APPEARANCE_KEYS)
    if "button_map" in parts:
        slug_a, slug_b = path_a.stem, path_b.stem
        maps_a = {key: doc_a[key] for key in _MAP_KEYS if key in doc_a}
        maps_b = {key: doc_b[key] for key in _MAP_KEYS if key in doc_b}
        try:
            _move_pictures(maps_a, slug_a, slug_b, files)
            _move_pictures(maps_b, slug_b, slug_a, files)
        except OSError as failed:
            return (
                f"A Button Map picture can't be read ({failed}): nothing was swapped."
            )
        for key in _MAP_KEYS:
            doc_a.pop(key, None)
            doc_b.pop(key, None)
        doc_a.update(maps_b)
        doc_b.update(maps_a)
    for doc, (name, guid) in ((doc_a, first), (doc_b, second)):
        doc.setdefault("kind", "control.hardware")
        doc.setdefault("device", name)
    return path_a, path_b, doc_a, doc_b, files


Before = list[tuple[Path, "bytes | None"]]


def _put_back(before: Before) -> bool:
    """The module files and pictures as they were. False when a module file
    couldn't be; a new picture that can't be removed yet (Windows may hold
    a file just written) only stays unused beside it, and is logged."""
    whole = True
    for path, data in reversed(before):
        try:
            if data is None:
                if path.is_file():
                    store.delete_path(path, "Device Library")
            else:
                store.replace(path, data, "Device Library", force=True)
        except OSError:
            logging.getLogger("system").exception(f"Swap: {path} couldn't be put back")
            if data is not None or path.suffix.lower() == ".json":
                whole = False
    return whole


def _write_module_parts(
    first: Stick, second: Stick, parts: list[str], shared: Controls, before: Before
) -> str:
    """Writes both module files (and moved pictures); "" when done, else why
    not. A failed write puts back what was written. before gets what each
    file held, so the swap can be put back later (S26)."""
    built = _swapped_docs(first, second, parts, shared)
    if isinstance(built, str):
        return built
    path_a, path_b, doc_a, doc_b, files = built
    if path_a == path_b:
        return ""  # one module file for both: its parts are already the same
    before += [(p, p.read_bytes() if p.is_file() else None) for p in (path_a, path_b)]
    before += [(p, p.read_bytes() if p.is_file() else None) for p, _ in files]
    try:
        for dest, data in files:
            store.put_picture_at(dest, data)
        store.write_json(path_a, doc_a, "Device Library")
        store.write_json(path_b, doc_b, "Device Library")
    except OSError as failed:
        _put_back(before)
        before.clear()
        return f"The module files can't be written ({failed}): nothing was swapped."
    return ""


# --- the swap ------------------------------------------------------------------


def _autosave_keys(result: dict) -> list[str]:
    keys = [str(s.get("key")) for s in result.get("setups") or [] if s.get("key")]
    if not keys and result.get("setup", {}).get("key"):
        keys = [str(result["setup"]["key"])]
    if not keys and result.get("key"):
        keys = [str(result["key"])]
    return keys


def swap(first: Stick, second: Stick, parts: list[str], profiles: list[Path]) -> dict:
    """Swap with Another Stick (S26, S28): both sticks' autosaves first (a
    failure refuses, S20), then the ticked module-file parts, then the
    bindings in each ticked profile (references in actions and script
    variables too). Controls one stick lacks stay where they were (S27).
    When no profile could be changed, the module files go back and the swap
    is refused: nothing changed. Runs on the Qt main thread when the open
    profile is ticked (it changes in memory, library_profiles.Batch)."""
    refused = _refusal(_shown(first), _shown(second))
    if refused:
        return _result(False, refused)
    from gremlin import device_library as library

    # The names the user reads: the Home card's, twins with their short id
    # (S17, S41); the device id decides which stick.
    shown = {first: _shown(first)[0], second: _shown(second)[0]}
    autosaves: list[str] = []
    for here, there in ((first, second), (second, first)):
        kept = library.autosave(
            here[0],
            here[1],
            "swap",
            f"Autosave: before Swap with {shown[there]}",
            list(profiles),
        )
        if not kept.get("ok"):
            reason = kept.get("error") or "it couldn't be written"
            return _result(
                False,
                f"The autosave of {shown[here]} couldn't be kept ({reason}): "
                "nothing was swapped.",
            )
        autosaves += _autosave_keys(kept)
    has_a, has_b = _controls(first[1]) or {}, _controls(second[1]) or {}
    shared = {kind: has_a.get(kind, set()) & has_b.get(kind, set()) for kind in _BUCKET}
    out = _plan(first, second, parts, profiles)
    out["autosaves"] = autosaves
    before: Before = []
    if any(part in parts for part in _MODULE_PARTS):
        failed = _write_module_parts(_own(first), _own(second), parts, shared, before)
        if failed:
            return _result(False, failed, autosaves=autosaves)
    label = f"Swap {shown[first]} with {shown[second]}"
    changed: list[str] = []
    if "bindings" in parts and profiles:
        ident_a, ident_b = _uuid(first[1]), _uuid(second[1])
        assert ident_a is not None and ident_b is not None  # _refusal checked

        def change(profile: Profile, is_open: bool) -> dict:
            done = swap_devices.swap_devices(profile, ident_a, ident_b, (has_a, has_b))
            where = Path(str(getattr(profile, "fpath", "") or "")).stem
            return {
                "notes": [f"{where}: {done.as_string()}" if where else done.as_string()]
            }

        from gremlin import library_profiles

        batch = library_profiles.Batch([Path(p) for p in profiles], label)
        applied = batch.apply(change)
        # The plan's read warnings are said again by the batch.
        out["warnings"] = [
            w for w in out["warnings"] if not w.endswith("It won't change.")
        ]
        out["warnings"] += list(applied.get("warnings") or [])
        out["notes"] += list(applied.get("notes") or [])
        changed = [str(p) for p in applied.get("changed") or []]
        if not applied.get("ok", True):
            # No profile changed (S26, S34): the module files go back, so
            # nothing is swapped and there is nothing to undo.
            error = str(applied.get("error") or "No profile could be changed.")
            if _put_back(before):
                return _result(
                    False,
                    f"{error} Nothing was swapped.",
                    warnings=out["warnings"],
                    autosaves=autosaves,
                )
            out["ok"] = False
            out["error"] = (
                f"{error} The module files couldn't all be put back: "
                "Undo puts them back."
            )
    # What Undo needs to swap back exactly (S28, S41): only the profiles
    # this swap changed (a profile it left as it was is never swapped back).
    detail = {
        "first": list(first),
        "second": list(second),
        "parts": list(parts),
        "profiles": changed,
        "has": [
            {kind: sorted(numbers) for kind, numbers in has_a.items()},
            {kind: sorted(numbers) for kind, numbers in has_b.items()},
        ],
    }
    library.set_last_change("swap", autosaves, label, detail)
    out["label"] = label
    return out
