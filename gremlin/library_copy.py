# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Copy to Another Stick, Change vJoy Output and Undo for the Device Library
(10 S22-S25, S30-S33, S41).

Copy works like a Device Pack import of the saved setup's pack onto the
target stick (08 S64-S79): the module file once, then the wires into each
ticked profile through library_profiles.Batch. Change vJoy Output keeps a
stick's bindings and renumbers only the vJoy its Map to vJoy actions send to,
nested actions too. Each keeps an autosave of every stick it changes first
and refuses when one can't be kept (S20); Undo puts the last change back
from those autosaves (S41). Nothing here touches devices, vJoy or ViGEm:
only module files (through the Device Pack import) and profiles.
"""

from __future__ import annotations

import re
import tempfile
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree import ElementTree

from gremlin import device_library as library
from gremlin import shared_state
from gremlin.modules import store
from gremlin.ui import device_pack

if TYPE_CHECKING:
    from gremlin.profile import Profile

# The pack pieces each part of a saved setup is (10 S11).
_PART_ITEMS = {
    "setup": ("in.checks", "in.names"),
    "button_map": ("in.layout",),
    "appearance": ("in.view", "in.catalog"),
    "calibration": ("in.calibration",),
}
# Put back by Undo too (a Copy leaves them unticked, as the pack window does).
_MAP_SETTINGS = ("in.mapview", "in.print")
_MODULE_PARTS = {"setup", "button_map", "appearance", "calibration"}
_KIND_WORD = {2: "axis", 3: "button", 4: "hat"}
# A part LS marks as a damaged module file kept as is (S20a).
_DAMAGED_SUFFIX = "_damaged"


def _damaged(setup: dict) -> bool:
    """The saved setup holds a damaged module file kept as is (S20a)."""
    return any(str(p).endswith(_DAMAGED_SUFFIX) for p in setup.get("holds") or [])


def _result(ok: bool = True, error: str = "", **extra: object) -> dict:
    out: dict = {"ok": ok, "error": error, "warnings": [], "notes": []}
    out.update(extra)
    return out


def _fail(error: str, **extra: object) -> dict:
    return _result(False, error, **extra)


# --- the Library -------------------------------------------------------------


def _find_setup(setup_key: str) -> tuple[dict, dict] | None:
    """(device, saved setup) for a saved setup key."""
    for dev in library.devices():
        for setup in dev.get("setups") or []:
            if setup.get("key") == setup_key:
                return dev, setup
    return None


def _autosave_keys(answer: dict) -> list[str]:
    keys = [str(s.get("key")) for s in answer.get("setups") or [] if s.get("key")]
    single = answer.get("setup")
    if isinstance(single, dict) and single.get("key"):
        keys.append(str(single["key"]))
    return list(dict.fromkeys(keys))


def _autosave(
    name: str, guid: str, trigger: str, reason: str, profiles: list[Path]
) -> dict:
    """library.autosave, any failure an ok False answer (S20)."""
    try:
        answer = library.autosave(name, guid, trigger, reason, list(profiles))
    except Exception as e:  # noqa: BLE001 - refused, said
        return _fail(
            f"The autosave of {name} couldn't be kept ({e}), so nothing was changed."
        )
    if not isinstance(answer, dict) or not answer.get("ok"):
        why = (
            str((answer or {}).get("error") or "it couldn't be written")
            if isinstance(answer, dict)
            else "it couldn't be written"
        )
        return _fail(
            f"The autosave of {name} couldn't be kept ({why}), so nothing was changed."
        )
    return answer


# --- sticks and profiles -----------------------------------------------------


def _connected(guid: str) -> bool:
    """A stick plugged in now: its id in the live device list (03 S90a),
    never a vJoy device or a built-in input."""
    from gremlin.modules import hardware

    want = store.guid_text(guid).strip("{}").lower()
    if not want or library.is_built_in_guid(guid):
        return False
    for dev in store.live_devices():
        if getattr(dev, "is_virtual", False) and (
            store.guid_text(getattr(dev, "device_guid", "")).strip("{}").lower() == want
        ):
            return False
    return hardware.plugged_in(guid)


def _uid(guid: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(guid).strip().strip("{}"))
    except ValueError:
        return None


def _same_path(a: Path | str, b: Path | str | None) -> bool:
    if b is None:
        return not str(a) or str(a) == "."
    try:
        return Path(a).resolve() == Path(b).resolve()
    except OSError:
        return str(a) == str(b)


def _read(path: Path) -> object:
    """The open profile when path is it, else the saved one read (a str:
    why it can't be read)."""
    from gremlin import library_profiles

    current = shared_state.current_profile
    if current is not None and _same_path(path, current.fpath):
        return current
    if not str(path) or str(path) == ".":
        return f"{_profile_name(path)}: no profile is open."
    return library_profiles.read_profile(Path(path))


def _profile_name(path: Path | str) -> str:
    return Path(path).stem if str(path) and str(path) != "." else "Untitled"


def _batch(paths: list[Path], label: str) -> object:
    from gremlin import library_profiles

    return library_profiles.Batch([Path(p) for p in paths], label)


# --- Copy to Another Stick ---------------------------------------------------


def _module_items(
    ids: list[str], parts: list[str], everything: bool = False
) -> list[str]:
    wanted: set[str] = set()
    for part in parts:
        wanted.update(_PART_ITEMS.get(part, ()))
    if "button_map" in parts:
        wanted.update(i for i in ids if i.startswith("pic:"))
        if everything:
            wanted.update(_MAP_SETTINGS)
    return [i for i in ids if i in wanted]


def _wire_items(
    pack_modes: list[str], parts: list[str], modes: list[str] | None
) -> list[str]:
    if "bindings" not in parts:
        return []
    chosen = pack_modes if modes is None else [m for m in pack_modes if m in modes]
    return ["wire:" + m for m in chosen]


def _find_device(key: str) -> dict | None:
    for dev in library.devices():
        if dev.get("key") == key:
            return dev
    return None


@contextmanager
def _scratch() -> Iterator[Path]:
    """A temporary folder for the packs of a device's current settings
    (S22): built for one copy and removed after it, never in the Library."""
    with tempfile.TemporaryDirectory(prefix="gremlin-library-copy-") as folder:
        yield Path(folder)


def _write_current(scratch: Path, data: bytes) -> Path:
    path = scratch / f"current-{len(list(scratch.iterdir())) + 1}.zip"
    path.write_bytes(data)
    return path


def _copy_checks(
    source_key: str,
    target_name: str,
    target_guid: str,
    parts: list[str],
    scratch: Path,
) -> dict:
    """What Copy needs, or why it can't run (S22). source_key is a saved
    setup, or a device: its current settings (module file now; bindings
    are taken per profile as the copy goes)."""
    found = _find_setup(source_key)
    current = None if found is not None else _find_device(source_key)
    if found is None and current is None:
        return _fail("This saved setup isn't in the Device Library.")
    source = current if current is not None else (found[0] if found else {})
    if source.get("builtIn"):
        return _fail(library.built_in_refusal(str(source.get("name") or ""), "Copy"))
    target = " ".join(str(target_name or "").split())
    if not target:
        return _fail("Choose the stick to copy to.")
    if library.is_built_in_guid(target_guid):
        return _fail(library.built_in_refusal(target, "Copy"))
    if not _connected(target_guid):
        return _fail(
            f"{target} isn't plugged in. A setup can only be copied to a stick "
            "plugged in now."
        )
    # The guid decides which stick (S7, S22): target may be its Home
    # card's name, or a twin's shared name.
    match = store.match_known_device(target, target_guid)
    if not match:
        return _fail(
            f"{target} isn't plugged in. A setup can only be copied to a stick "
            "plugged in now."
        )
    own = str(match.get("name") or library.own_name(target, target_guid))
    # The name the user reads (S17, S41): the Home card's, twins with their
    # short id; own finds the files.
    target = library.shown(target, target_guid) or target
    if not [p for p in parts if p in library.PARTS]:
        return _fail("Choose at least one part to copy.")
    if current is not None:
        if _same_stick(str(current.get("guid") or ""), target_guid):
            return _fail(
                f"{target} is the stick it would copy from: choose another stick."
            )
        built = library.current_pack(source_key, None)
        if not built.get("ok"):
            return _fail(str(built.get("error") or "Its settings couldn't be read."))
        source = current
        setup = {
            "key": source_key,
            "name": "current settings",
            "holds": list(built.get("holds") or []),
        }
        pack = _write_current(scratch, built["data"])
    else:
        assert found is not None
        source, setup = found
        pack = library.pack_path(source_key)
    if _damaged(setup):
        # S20a: never a damaged file on another stick; only the bindings.
        parts = [p for p in parts if p == "bindings"]
        if not parts:
            return _fail(
                "This saved setup's module file is damaged, so only its "
                "bindings can be copied."
            )
    ids = device_pack.pack_item_ids(pack)
    if isinstance(ids, str):
        return _fail(f"The saved setup couldn't be read: {ids}")
    return _result(
        source=source,
        setup=setup,
        target=target,
        own=own,
        pack=pack,
        ids=ids,
        parts=parts,
        current=current is not None,
    )


def _same_stick(a: str, b: str) -> bool:
    from gremlin.modules.ids import stored_guid_key

    return bool(stored_guid_key(a)) and stored_guid_key(a) == stored_guid_key(b)


def _current_wires(
    source_key: str, profile: object, scratch: Path
) -> tuple[Path, list[str]] | str:
    """The source device's bindings in profile as a pack (S22): its path and
    the modes it has bindings in; a str says why it can't."""
    built = library.current_pack(source_key, profile)  # type: ignore[arg-type]
    if not built.get("ok"):
        return str(built.get("error") or "its bindings couldn't be read")
    return _write_current(scratch, built["data"]), list(built.get("modes") or [])


def plan_copy(
    setup_key: str,
    target_name: str,
    target_guid: str,
    parts: list[str],
    profiles: list[Path],
    modes: list[str],
) -> dict:
    """What Copy would do (S23): the warnings list what won't copy because
    the target lacks it. From a device's current settings (setup_key a
    device key) it also gives what it holds ("holds") and the modes it has
    bindings in across the profiles ("sourceModes"), for the dialog."""
    with _scratch() as scratch:
        return _plan_copy(
            setup_key, target_name, target_guid, parts, profiles, modes, scratch
        )


def _plan_copy(
    setup_key: str,
    target_name: str,
    target_guid: str,
    parts: list[str],
    profiles: list[Path],
    modes: list[str],
    scratch: Path,
) -> dict:
    checked = _copy_checks(setup_key, target_name, target_guid, parts, scratch)
    if not checked["ok"]:
        return checked
    target = checked["target"]
    ids = checked["ids"]
    parts = checked["parts"]
    loaded = device_pack._read_zip(checked["pack"])
    if isinstance(loaded, str):
        return _fail(f"The saved setup couldn't be read: {loaded}")
    limits = device_pack._device_limits(target_guid)
    warnings: list[str] = []
    if limits is not None and "setup" in parts:
        buttons, axes, hats = device_pack._checked_ids(loaded["doc"])
        missing = (
            [f"Button {n}" for n in sorted(buttons - limits["button"])]
            + [f"Axis {n}" for n in sorted(axes - limits["axis"])]
            + [f"Hat {n}" for n in sorted(hats - limits["hat"])]
        )
        if missing:
            warnings.append(
                f"{target} doesn't have these controls, so they won't copy: "
                + ", ".join(missing)
                + "."
            )
    # The bindings: from the saved setup's pack, or (current settings) from
    # each profile they go into.
    # Each with the profile it goes into: its own Logical Device rows say
    # which inputs are missing there (S24).
    sources: list[tuple[dict, list[str], object]] = []
    source_modes: list[str] = []
    if checked["current"]:
        for path in profiles:
            profile = _read(Path(path))
            if isinstance(profile, str):
                warnings.append(profile)
                continue
            got = _current_wires(setup_key, profile, scratch)
            if isinstance(got, str):
                warnings.append(f"{_profile_name(path)}: {got}")
                continue
            each = device_pack._read_zip(got[0])
            if isinstance(each, str):
                continue
            sources.append((each, got[1], profile))
            source_modes.extend(m for m in got[1] if m not in source_modes)
    else:
        for path in profiles if "bindings" in parts else []:
            profile = _read(Path(path))
            if not isinstance(profile, str):
                sources.append((loaded, list(ids["modes"]), profile))
        if not sources:
            sources.append((loaded, list(ids["modes"]), None))
    left_out: list[str] = []
    counts: dict[str, int] = {}
    plan_modes: list[str] = []
    logical: dict[str, list[tuple[str, int]]] = {}
    items: list[str] = []
    for each, pack_modes, into in sources:
        wires = _wire_items(pack_modes, parts, modes)
        items.extend(w for w in wires if w not in items)
        plan = device_pack._plan_wires(
            each["wires"], set(wires), limits, device_pack._rows_of(into)
        )
        left_out.extend(x for x in plan["leftOut"] if x not in left_out)
        for mode in plan["modes"]:
            if mode not in plan_modes:
                plan_modes.append(mode)
            counts[mode] = counts.get(mode, 0) + plan["counts"].get(mode, 0)
        where = _profile_name(getattr(into, "fpath", "") or "") if into else ""
        lacking = logical.setdefault(where, [])
        lacking.extend(x for x in plan["missingLogical"] if x not in lacking)
    if left_out:
        warnings.append(
            f"Bindings on controls {target} doesn't have won't copy: "
            + ", ".join(left_out)
            + "."
        )
    if limits is None:
        warnings.append(f"What {target} has isn't known, so nothing could be checked.")
    if _damaged(checked["setup"]):
        warnings.append(
            "This saved setup's module file is damaged, so only its bindings will copy."
        )
    out = _result(
        target=target,
        source=checked["source"].get("name", ""),
        items=_module_items(ids["input"], parts) + items,
        modes=[{"name": m, "count": counts.get(m, 0)} for m in plan_modes],
        profiles=[str(p) for p in profiles],
    )
    if checked["current"]:
        holds = [h for h in checked["setup"]["holds"] if h != "bindings"]
        if source_modes:
            holds.append("bindings")
        out["holds"] = holds
        out["sourceModes"] = source_modes
    out["warnings"] = warnings
    for where, lacking in logical.items():
        if lacking:
            out["notes"].append(
                "These bindings send to Logical Device inputs that aren't "
                + (f"in {where}: " if where else "here: ")
                + ", ".join(f"{k.capitalize()} {n}" for k, n in lacking)
                + "."
            )
    return out


def copy(
    setup_key: str,
    target_name: str,
    target_guid: str,
    parts: list[str],
    profiles: list[Path],
    modes: list[str],
) -> dict:
    """Puts a saved setup, or a device's current settings (setup_key a
    device key), on a stick plugged in now (S22-S25): the target's autosave
    first, then the import (module file once, the wires into each ticked
    profile). The source never changes; current settings are built for
    this copy only and kept nowhere."""
    with _scratch() as scratch:
        return _copy(
            setup_key, target_name, target_guid, parts, profiles, modes, scratch
        )


def _exists(stored: str) -> bool:
    """A profile a saved setup came from is still there: the open one, or
    a file on disk. "" (a pack's bindings, no profile) never is."""
    if not str(stored or "").strip():
        return False
    current = shared_state.current_profile
    if current is not None and _same_path(stored, current.fpath):
        return True
    if str(stored) == ".":
        return False
    try:
        return Path(stored).is_file()
    except OSError:
        return False


def restore_to_stick(setup_key: str) -> dict:
    """Restore to This Stick… (S48): the saved setup back on its own stick
    (by its device id; it must be plugged in) as Copy does (S22-S25):
    every part it holds (calibration too: the same stick; a damaged
    module file never, S20a), into the profiles it came from that are
    still there, every mode it has. Autosave first ("Autosave: before
    Restore of <setup>"), the last change for Undo, a history line."""
    found = _find_setup(setup_key)
    if found is None:
        return _fail("This saved setup isn't in the Device Library.")
    dev, setup = found
    guid = str(dev.get("guid") or "")
    name = str(dev.get("name") or "")
    if not _connected(guid):
        return _fail(
            f"{name or 'Its stick'} isn't plugged in. A saved setup can only be "
            "restored to its stick while it is plugged in."
        )
    holds = [str(p) for p in setup.get("holds") or []]
    parts = [p for p in library.PARTS if p in holds]
    if _damaged(setup) and "bindings" not in parts:
        return _fail(
            "This saved setup's module file is damaged and it has no bindings, "
            "so there is nothing to restore."
        )
    profiles: list[Path] = []
    gone: list[str] = []
    for row in setup.get("profiles") or []:
        if not isinstance(row, dict):
            continue
        stored = str(row.get("path") or "")
        if _exists(stored):
            if Path(stored) not in profiles:
                profiles.append(Path(stored))
        elif stored.strip():
            gone.append(str(row.get("name") or _profile_name(stored)))
    try:
        with _scratch() as scratch:
            out = _copy(
                setup_key, name, guid, parts, profiles, None, scratch, restore=True
            )
    except Exception as e:  # noqa: BLE001 - refused, said
        return _fail(f"The saved setup couldn't be restored ({e}).")
    if gone and "bindings" in parts:
        out["warnings"].append(
            "These profiles it came from are no longer there, so their bindings "
            "weren't restored: " + ", ".join(gone) + "."
        )
    return out


def _copy(
    setup_key: str,
    target_name: str,
    target_guid: str,
    parts: list[str],
    profiles: list[Path],
    modes: list[str] | None,
    scratch: Path,
    restore: bool = False,
) -> dict:
    """restore: Restore to This Stick (S48), named so in the autosave, the
    Undo label and the saved setup's history."""
    checked = _copy_checks(setup_key, target_name, target_guid, parts, scratch)
    if not checked["ok"]:
        return checked
    target = checked["target"]
    own = checked["own"]
    current = bool(checked["current"])
    source_name = library.shown(
        str(checked["source"].get("name") or ""),
        str(checked["source"].get("guid") or ""),
    )
    ids = checked["ids"]
    parts = checked["parts"]
    pack = checked["pack"]
    module = _module_items(ids["input"], parts)
    wires = _wire_items(ids["modes"], parts, modes)
    bind = ("bindings" in parts) if current else bool(wires)
    if not module and not (bind and profiles):
        return _fail("The saved setup has nothing of what was ticked.")
    saved = _autosave(
        own,
        target_guid,
        "copy",
        f"Autosave: before Restore of {checked['setup'].get('name') or ''}"
        if restore
        else f"Autosave: before Copy from {source_name}",
        profiles,
    )
    if not saved["ok"]:
        return saved
    keys = _autosave_keys(saved)
    out = _result(autosaves=keys, changed=[], failed=[])
    if module:
        answer = device_pack.apply_zip(
            pack, own, {"items": module}, record_undo=False, target_guid=target_guid
        )
        if not answer.get("ok"):
            return _fail(
                str(answer.get("error") or "The module file couldn't be written."),
                autosaves=keys,
            )
        out["notes"].extend(str(answer.get("report") or "").splitlines())
    if bind and profiles:

        def change(profile: Profile, is_open: bool) -> dict:
            source, these = pack, wires
            if current:
                got = _current_wires(setup_key, profile, scratch)
                if isinstance(got, str):
                    return _fail(got)
                source, these = got[0], _wire_items(got[1], parts, modes)
                if not these:
                    return _result()
            done = device_pack.apply_zip(
                source,
                own,
                {"items": these},
                profile,
                record_undo=False,  # type: ignore[arg-type]
                target_guid=target_guid,
            )
            if not done.get("ok"):
                return _fail(
                    str(done.get("error") or "the bindings couldn't be written")
                )
            return _result(notes=[])

        done = _batch(profiles, f"Copy to {target}").apply(change)  # type: ignore[attr-defined]
        out["warnings"].extend(done.get("warnings") or [])
        out["changed"] = list(done.get("changed") or [])
        out["failed"] = list(done.get("failed") or [])
        if not module and not done.get("ok"):
            out["ok"] = False
            out["error"] = str(done.get("error") or "No profile could be changed.")
            return out
        if out["changed"]:
            out["notes"].append(
                f"Bindings copied into {len(out['changed'])} "
                + ("profile." if len(out["changed"]) == 1 else "profiles.")
            )
    # The saved setup copied ("Copy DCS F-16 to Right stick"), or the
    # device whose current settings were copied.
    what = source_name if current else str(checked["setup"].get("name") or source_name)
    label = f"{'Restore' if restore else 'Copy'} {what} to {target}"
    try:
        if not current:
            library.add_history(
                setup_key, f"{'Restored' if restore else 'Copied'} to {target}"
            )
        library.set_last_change("copy", keys, label)
    except Exception as e:  # noqa: BLE001 - the copy is done; said
        out["warnings"].append(f"The Library couldn't record the copy ({e}).")
    return out


# --- Change vJoy Output ------------------------------------------------------


def _clean_moves(moves: dict) -> dict[int, int]:
    clean: dict[int, int] = {}
    for old, new in (moves or {}).items():
        try:
            a, b = int(old), int(new)
        except (TypeError, ValueError):
            continue
        if a > 0 and b > 0 and a != b:
            clean[a] = b
    return clean


def _vjoy_actions(profile: object, uid: uuid.UUID) -> list[tuple[object, object]]:
    """(input, Map to vJoy action) for every action of the device's inputs,
    nested ones too (Condition, Chain, Tempo...)."""
    from gremlin.profile import Profile, reachable

    found = []
    for item in profile.inputs.get(uid, []) or []:  # type: ignore[attr-defined]
        for action in reachable(Profile.roots_of([item])):
            if getattr(action, "tag", "") == "map-to-vjoy":
                found.append((item, action))
    return found


def _input_key(item: object) -> tuple:
    return (
        str(getattr(item, "mode", "") or "Default"),
        int(getattr(getattr(item, "input_type", 0), "value", 0) or 0),
        str(getattr(item, "input_id", "")),
    )


def _input_label(item: object) -> str:
    return (
        device_pack._input_word(item) + f" ({getattr(item, 'mode', '') or 'Default'})"
    )


def _special(uid: uuid.UUID) -> bool:
    import dill
    from gremlin import osc

    return uid in (
        dill.UUID_Keyboard,
        dill.UUID_LogicalDevice,
        dill.UUID_Invalid,
        dill.UUID_Virtual,
        osc.OSC_DEVICE_UUID,
    )


def _device_name(profile: object, uid: uuid.UUID) -> str:
    info = profile.device_database.devices.get(uid)  # type: ignore[attr-defined]
    return str(getattr(info, "name", "") or "") or str(uid)


def _vjoy_number_ids(node: ElementTree.Element) -> list[int]:
    found = []
    for prop in node.iter("property"):
        if prop.findtext("name") == "vjoy-id":
            try:
                found.append(int((prop.findtext("value") or "").strip()))
            except ValueError:
                continue
    return found


def _macros(profile: object, uid: uuid.UUID, numbers: set[int]) -> list[str]:
    """Macros on the device's inputs that name one of these vJoys."""
    from gremlin.profile import Profile, reachable

    lines: list[str] = []
    for item in profile.inputs.get(uid, []) or []:  # type: ignore[attr-defined]
        for action in reachable(Profile.roots_of([item])):
            if getattr(action, "tag", "") != "macro":
                continue
            try:
                node = action.to_xml()
            except Exception:  # noqa: BLE001 - not readable, not listed
                continue
            if node is None:
                continue
            hit = sorted(set(_vjoy_number_ids(node)) & numbers)
            if hit:
                lines.append(
                    f"The macro on {_input_label(item)} sends to "
                    + ", ".join(f"vJoy {n}" for n in hit)
                    + "; it isn't changed, check it yourself."
                )
    return lines


def _scripts(profile: object, numbers: set[int]) -> list[str]:
    """User scripts whose variables or code name one of these vJoys."""
    lines: list[str] = []
    try:
        root = profile.scripts.to_xml()  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 - nothing to list
        return lines
    for node in root.findall("script"):
        name = path_text = ""
        for prop in node.findall("property"):
            if prop.findtext("name") == "name":
                name = prop.findtext("value") or ""
            elif prop.findtext("name") == "path":
                path_text = prop.findtext("value") or ""
        hit = set(_vjoy_number_ids(node)) & numbers
        try:
            code = (
                Path(path_text).read_text(encoding="utf-8", errors="replace")
                if path_text
                else ""
            )
        except OSError:
            code = ""
        for match in re.finditer(r"vjoy\s*\[\s*(\d+)\s*\]", code, re.IGNORECASE):
            if int(match.group(1)) in numbers:
                hit.add(int(match.group(1)))
        if hit:
            # The file and the instance: "mine.py (Instance 1)".
            file_name = Path(path_text).name if path_text else ""
            label = (
                f"{file_name} ({name})" if file_name and name else (file_name or name)
            )
            lines.append(
                f"The user script {label} names "
                + ", ".join(f"vJoy {n}" for n in sorted(hit))
                + "; it isn't changed, check it yourself."
            )
    return lines


def _unclaimed(profile: object, uid: uuid.UUID, moves: dict[int, int]) -> list[str]:
    """Bindings that would send to an output the target vJoy's output
    module doesn't claim (S31)."""
    from gremlin.modules import output

    lines: list[str] = []
    for item, action in _vjoy_actions(profile, uid):
        old = int(getattr(action, "vjoy_device_id", 0) or 0)
        if old not in moves:
            continue
        new = moves[old]
        kind = _KIND_WORD.get(
            int(getattr(getattr(action, "vjoy_input_type", 0), "value", 0) or 0), ""
        )
        number = int(getattr(action, "vjoy_input_id", 0) or 0)
        if not kind or output.vjoy_allows(new, kind, number):
            continue
        lines.append(
            f"{_input_label(item)} would send to vJoy {new} "
            f"{kind.capitalize()} {number}, "
            f"which vJoy {new}'s output module doesn't claim, so it would send nothing."
        )
    return lines


def plan_output(
    device_name: str,
    guid: str,
    moves: dict[int, int],
    swap_other: bool,
    profiles: list[Path],
) -> dict:
    """What Change vJoy Output would do (S30-S31): a row per vJoy the stick
    sends to ("changes" or "stays"), the other sticks on the target vJoys,
    and warnings."""
    if library.is_built_in_guid(guid):
        return _fail(library.built_in_refusal(device_name, "Change vJoy Output"))
    uid = _uid(guid)
    if uid is None:
        return _fail(f"{device_name} has no device id.")
    clean = _clean_moves(moves)
    back = {new: old for old, new in clean.items()}
    used: dict[int, set] = {}
    others: dict[tuple[str, int], dict] = {}
    warnings: list[str] = []
    for path in profiles:
        profile = _read(Path(path))
        if isinstance(profile, str):
            warnings.append(f"{profile} It will be left as it is.")
            continue
        for item, action in _vjoy_actions(profile, uid):
            number = int(getattr(action, "vjoy_device_id", 0) or 0)
            used.setdefault(number, set()).add((str(path),) + _input_key(item))
        for other in list(profile.inputs):  # type: ignore[attr-defined]
            if other == uid or _special(other):
                continue
            for item, action in _vjoy_actions(profile, other):
                number = int(getattr(action, "vjoy_device_id", 0) or 0)
                if number not in back:
                    continue
                row = others.setdefault(
                    (str(other), number),
                    {
                        "guid": str(other),
                        "name": _device_name(profile, other),
                        "vjoy": number,
                        "to": back[number],
                        "inputs": set(),
                    },
                )
                row["inputs"].add((str(path),) + _input_key(item))
        warnings.extend(_unclaimed(profile, uid, clean))
        numbers = set(clean)
        if swap_other:
            numbers |= set(back)
            for other in list(profile.inputs):  # type: ignore[attr-defined]
                if other != uid and not _special(other):
                    warnings.extend(_unclaimed(profile, other, back))
                    warnings.extend(_macros(profile, other, set(back)))
        warnings.extend(_macros(profile, uid, set(clean)))
        warnings.extend(_scripts(profile, numbers))
    rows = []
    for number in sorted(used):
        to = clean.get(number, number)
        rows.append(
            {
                "vjoy": number,
                "inputs": len(used[number]),
                "to": to,
                "changes": to != number,
                "text": "changes" if to != number else "stays",
            }
        )
    other_rows = []
    for row in others.values():
        row["inputs"] = len(row["inputs"])
        other_rows.append(row)
    other_rows.sort(key=lambda r: (r["vjoy"], r["name"]))
    out = _result(rows=rows, others=other_rows, moves=clean)
    out["warnings"] = list(dict.fromkeys(warnings))
    if not clean:
        out["notes"].append("Nothing changes: every vJoy stays where it is.")
    return out


def _retarget_inputs(profile: object, uid: uuid.UUID, moves: dict[int, int]) -> int:
    """The device's inputs that send to a moved vJoy are put back with their
    Map to vJoy actions renumbered (nested ones too; an action another
    device shares is copied, so that device keeps it). Returns how many."""
    items = []
    seen: set[int] = set()
    for item, action in _vjoy_actions(profile, uid):
        if (
            int(getattr(action, "vjoy_device_id", 0) or 0) in moves
            and id(item) not in seen
        ):
            seen.add(id(item))
            items.append(item)
    if not items:
        return 0
    inputs: list[str] = []
    actions: dict[str, str] = {}
    for item in items:
        snap = profile.input_snapshot(item)  # type: ignore[attr-defined]
        if not snap:
            continue
        inputs.append(snap["input"])
        for block in snap["actions"]:
            key = str(ElementTree.fromstring(block).get("id") or len(actions))
            actions.setdefault(key, block)
    blocks = device_pack._retarget_vjoy(list(actions.values()), moves)
    with profile.library.change():  # type: ignore[attr-defined]
        profile.drop_inputs(uid, items)  # type: ignore[attr-defined]
        profile.add_inputs(uid, inputs, blocks)  # type: ignore[attr-defined]
    return len(items)


def _moves_text(moves: dict[int, int]) -> str:
    return ", ".join(f"vJoy {a} → {b}" for a, b in sorted(moves.items()))


def change_output(
    device_name: str,
    guid: str,
    moves: dict[int, int],
    swap_other: bool,
    profiles: list[Path],
) -> dict:
    """Changes which vJoy the stick's Map to vJoy actions send to (S30-S32),
    and with swap_other the other sticks on the target vJoys the other way.
    Each stick that changes is autosaved first."""
    if library.is_built_in_guid(guid):
        return _fail(library.built_in_refusal(device_name, "Change vJoy Output"))
    uid = _uid(guid)
    if uid is None:
        return _fail(f"{device_name} has no device id.")
    clean = _clean_moves(moves)
    if not clean:
        return _fail("Choose a vJoy to change to.")
    if not profiles:
        return _fail("Tick at least one profile.")
    shown = library.shown(device_name, guid) or device_name
    back = {new: old for old, new in clean.items()}
    plan = plan_output(device_name, guid, clean, swap_other, profiles)
    if not plan["ok"]:
        return plan
    others = plan["others"] if swap_other else []
    reason = f"Autosave: before Change vJoy Output ({_moves_text(clean)})"
    keys: list[str] = []
    sticks = [(device_name, guid)] + list(
        dict.fromkeys((str(r["name"]), str(r["guid"])) for r in others)
    )
    for name, stick_guid in sticks:
        saved = _autosave(name, stick_guid, "output", reason, profiles)
        if not saved["ok"]:
            return saved
        keys.extend(_autosave_keys(saved))
    other_ids = [u for u in (_uid(g) for _, g in sticks[1:]) if u is not None]

    def change(profile: Profile, is_open: bool) -> dict:
        count = _retarget_inputs(profile, uid, clean)
        for other in other_ids:
            _retarget_inputs(profile, other, back)
        return _result(
            notes=[
                f"{_profile_name(getattr(profile, 'fpath', '') or '')}: "
                f"{count} inputs of {shown} changed."
            ]
        )

    done = _batch(profiles, f"Change vJoy Output of {shown}").apply(change)  # type: ignore[attr-defined]
    out = _result(
        autosaves=keys,
        changed=list(done.get("changed") or []),
        failed=list(done.get("failed") or []),
    )
    out["notes"].extend(done.get("notes") or [])
    out["warnings"].extend(done.get("warnings") or [])
    out["warnings"].extend(w for w in plan["warnings"] if w not in out["warnings"])
    if not done.get("ok"):
        out["ok"] = False
        out["error"] = str(done.get("error") or "No profile could be changed.")
        return out
    try:
        library.set_last_change(
            "output",
            keys,
            f"Change vJoy Output of {shown} ({_moves_text(clean)})",
        )
    except Exception as e:  # noqa: BLE001 - the change is done; said
        out["warnings"].append(f"The Library couldn't record the change ({e}).")
    return out


# --- Undo --------------------------------------------------------------------


def _put_module_back(
    setup: dict, own: str, guid: str, pack: Path, items: list[str], out: dict
) -> str:
    """The stick's module file as the autosave kept it (S25, S41): exactly
    its bytes, or none when it had none. "" when done, else why not."""
    kept = str(setup.get("moduleFile") or "")
    # By its id alone: an unplugged twin's file, never the other twin's.
    path = store.path_for_id(own, guid)
    if not kept:
        if path.is_file():
            try:
                store.delete_path(path, "Device Library")
            except OSError as e:
                return f"{own}'s module file couldn't be removed ({e})."
            out["notes"].append(f"Removed {own}'s module file: it had none before.")
        return ""
    try:
        exact = library.module_bytes(str(setup.get("key")))
    except KeyError:
        exact = None
    if items:
        # The pictures (and the parts), then the file exactly as it was.
        answer = device_pack.apply_zip(
            pack,
            own,
            {"items": items},
            record_undo=False,
            fresh=True,
            target_guid=guid,
        )
        if not answer.get("ok"):
            return str(
                answer.get("error") or f"{own}'s module file couldn't be put back."
            )
    if exact is not None:
        try:
            store.replace(path, exact, "Device Library", force=True)
        except OSError as e:
            return f"{own}'s module file couldn't be put back ({e})."
    out["notes"].append(f"Put back {own}'s module file.")
    return ""


def _restore(
    dev: dict, setup: dict, module: bool = True, bindings: bool = True
) -> dict:
    """Copies a saved setup back onto its own stick: every part it holds,
    into the profiles it came from. Its modes replace the stick's; modes it
    has no bindings in are emptied (it held all of them). An autosave also
    knows what the stick didn't have ("covers"): those parts are removed,
    a missing module file comes back missing (S25, S41)."""
    guid = str(dev.get("guid") or "")
    own = library.own_name(str(dev.get("name") or ""), guid)
    name = library.shown(str(dev.get("name") or ""), guid)
    holds = [str(p) for p in setup.get("holds") or []]
    covers = [str(p) for p in setup.get("covers") or []] if "covers" in setup else []
    try:
        pack = library.pack_path(str(setup.get("key")))
    except KeyError:
        return _fail(
            f"{setup.get('name') or 'The autosave'} is no longer in the Device "
            "Library, so nothing was put back."
        )
    ids = device_pack.pack_item_ids(pack)
    if isinstance(ids, str):
        return _fail(f"{setup.get('name') or 'The autosave'} couldn't be read: {ids}")
    out = _result(changed=[], failed=[])
    items = _module_items(ids["input"], holds, everything=True) if module else []
    exact = bool(covers) and bool(_MODULE_PARTS & set(covers))
    if module and _damaged(setup):
        # S20a: the damaged file is put back on its own stick only as it was;
        # that is the Library store's to do, not an import.
        items = []
        exact = False
        out["warnings"].append(
            f"{name}'s module file was damaged when it was kept, so it wasn't put back."
        )
    if module and exact:
        failed = _put_module_back(setup, own, guid, pack, items, out)
        if failed:
            return _fail(failed)
        items = items or ["exact"]
    elif items:
        fresh = _MODULE_PARTS <= set(holds)
        answer = device_pack.apply_zip(
            pack,
            own,
            {"items": items},
            record_undo=False,
            fresh=fresh,
            target_guid=guid,
        )
        if not answer.get("ok"):
            return _fail(
                str(
                    answer.get("error") or f"{name}'s module file couldn't be put back."
                )
            )
        out["notes"].append(f"Put back {name}'s module file.")
    paths = [
        Path(str(p.get("path") or ""))
        for p in setup.get("profiles") or []
        if isinstance(p, dict)
    ]
    uid = _uid(guid)
    wanted = "bindings" in holds or "bindings" in covers
    if bindings and wanted and paths and uid is not None:
        pack_modes = list(ids["modes"]) if "bindings" in holds else []
        wires = ["wire:" + m for m in pack_modes]

        def change(profile: Profile, is_open: bool) -> dict:
            doomed = [
                item
                for item in profile.inputs.get(uid, []) or []  # type: ignore[attr-defined]
                if str(getattr(item, "mode", "") or "Default") not in pack_modes
            ]
            if doomed:
                profile.drop_inputs(uid, doomed)  # type: ignore[attr-defined]
            if wires:
                got = device_pack.apply_zip(
                    pack,
                    own,
                    {"items": wires},
                    profile,
                    record_undo=False,  # type: ignore[arg-type]
                    target_guid=guid,
                )
                if not got.get("ok"):
                    raise RuntimeError(
                        str(got.get("error") or "the bindings couldn't be put back")
                    )
            return _result()

        done = _batch(paths, f"Undo for {name}").apply(change)  # type: ignore[attr-defined]
        out["warnings"].extend(done.get("warnings") or [])
        out["changed"] = list(done.get("changed") or [])
        out["failed"] = list(done.get("failed") or [])
        if not done.get("ok") and not items:
            out["ok"] = False
            out["error"] = str(done.get("error") or "No profile could be changed.")
    return out


def restore(setup_key: str) -> dict:
    """Copies an autosave back onto its own stick: every part it holds, into
    the profiles it came from (S41). Never raises: refused with a message."""
    found = _find_setup(setup_key)
    if found is None:
        return _fail("This saved setup isn't in the Device Library.")
    try:
        return _restore(*found)
    except Exception as e:  # noqa: BLE001 - refused, said
        return _fail(f"The saved setup couldn't be put back ({e}).")


def _gone(keys: list[str]) -> bool:
    """An autosave, or its pack on disk, is no longer there."""
    for key in keys:
        try:
            if not library.pack_path(str(key)).is_file():
                return True
        except KeyError:
            return True
    return False


def undo_last() -> dict:
    """Puts the last Copy, Swap or Change vJoy Output back from the
    autosaves it kept (S41). Undo is a change too: each stick is autosaved
    first ("Autosave: before Undo"). Never raises: refused with a message."""
    return undo_change(None)


def undo_change(last: dict | None) -> dict:
    """Puts one Copy, Swap, Change vJoy Output or Restore back from the
    autosaves it kept: last is the change as library.last_change() gave it
    right after it (10 S53: the window's Undo steps), None the last one.
    Never raises: refused with a message."""
    try:
        return _undo_last(library.last_change() if last is None else dict(last))
    except Exception as e:  # noqa: BLE001 - refused, said
        return _fail(f"Undo couldn't put the change back ({e}).")


def _undo_last(last: dict | None) -> dict:
    if not last or not last.get("autosaves"):
        return _fail("There is nothing to undo.")
    found = []
    for key in last["autosaves"]:
        hit = _find_setup(str(key))
        if hit is None:
            return _fail(
                "An autosave this needs is no longer in the Device Library, "
                "so nothing was put back."
            )
        found.append(hit)
    if _gone([str(k) for k in last["autosaves"]]):
        return _fail(
            "An autosave this needs can't be found in the Device Library "
            "folder, so nothing was put back."
        )
    op = str(last.get("op") or "copy")
    label = str(last.get("label") or op)
    if op == "swap" and isinstance(last.get("detail"), dict):
        return _undo_swap(last["detail"], found, label, bool(last.get("undone")))
    trigger = op if op in library.TRIGGERS else "copy"
    by_device: dict[str, list[tuple[dict, dict]]] = {}
    for dev, setup in found:
        by_device.setdefault(str(dev.get("key")), []).append((dev, setup))
    keys: list[str] = []
    for pairs in by_device.values():
        dev = pairs[0][0]
        paths: list[Path] = []
        for _, setup in pairs:
            for row in setup.get("profiles") or []:
                if (
                    isinstance(row, dict)
                    and Path(str(row.get("path") or "")) not in paths
                ):
                    paths.append(Path(str(row.get("path") or "")))
        saved = _autosave(
            str(dev.get("name") or ""),
            str(dev.get("guid") or ""),
            trigger,
            "Autosave: before Undo",
            paths,
        )
        if not saved["ok"]:
            return saved
        keys.extend(_autosave_keys(saved))
    out = _result(autosaves=keys, changed=[], failed=[])
    for pairs in by_device.values():
        for index, (dev, setup) in enumerate(pairs):
            # The module file once per stick; the bindings per autosave.
            answer = _restore(dev, setup, module=index == 0)
            _merge(out, answer)
    if not out["notes"] and not out["changed"]:
        out["ok"] = False
        out["error"] = "Nothing could be put back." + (
            " " + " ".join(out["warnings"]) if out["warnings"] else ""
        )
        return out
    try:
        # The change's own label; undone: the Edit item reads "Redo <change>"
        # until another change (D-10-REDO-LABEL).
        library.set_last_change(op, keys, label, undone=not bool(last.get("undone")))
    except Exception as e:  # noqa: BLE001 - the undo is done; said
        out["warnings"].append(f"The Library couldn't record the undo ({e}).")
    return out


def _merge(out: dict, answer: dict) -> None:
    out["notes"].extend(answer.get("notes") or [])
    out["warnings"].extend(answer.get("warnings") or [])
    out["changed"].extend(answer.get("changed") or [])
    out["failed"].extend(answer.get("failed") or [])
    if not answer.get("ok"):
        out["warnings"].append(str(answer.get("error") or ""))


def _controls(raw: object) -> dict[str, set[int]]:
    found: dict[str, set[int]] = {}
    for kind, numbers in (raw if isinstance(raw, dict) else {}).items():
        found[str(kind)] = {int(n) for n in numbers or []}
    return found


def _undo_swap(
    detail: dict, found: list[tuple[dict, dict]], label: str, undone: bool = False
) -> dict:
    """Undo of a swap (S28, S41): each stick's module file back exactly from
    its autosave, then the bindings swapped back with the same profiles and
    controls, so the references in other actions and the script variables
    the swap moved go back too. Undoing this swaps again."""
    from gremlin import swap_devices
    from gremlin.modules.ids import stored_guid_key

    try:
        first = (str(detail["first"][0]), str(detail["first"][1]))
        second = (str(detail["second"][0]), str(detail["second"][1]))
        parts = [str(p) for p in detail.get("parts") or []]
        paths = [Path(str(p)) for p in detail.get("profiles") or []]
        limits = (
            _controls(detail.get("has", [{}, {}])[0]),
            _controls(detail["has"][1]),
        )
    except (KeyError, IndexError, TypeError, ValueError):
        return _fail("The swap to undo isn't recorded fully, so nothing was put back.")
    ident_a, ident_b = _uid(first[1]), _uid(second[1])
    if ident_a is None or ident_b is None:
        return _fail("The swap to undo isn't recorded fully, so nothing was put back.")
    keys: list[str] = []
    for here in (first, second):
        saved = _autosave(here[0], here[1], "swap", "Autosave: before Undo", paths)
        if not saved["ok"]:
            return saved
        keys.extend(_autosave_keys(saved))
    out = _result(autosaves=keys, changed=[], failed=[])
    if any(p in _MODULE_PARTS for p in parts):
        for here in (first, second):
            want = stored_guid_key(here[1])
            pair = next(
                (
                    (dev, setup)
                    for dev, setup in found
                    if stored_guid_key(str(dev.get("guid") or "")) == want
                ),
                None,
            )
            if pair is None:
                out["warnings"].append(
                    f"{library.shown(*here)}'s module file has no autosave."
                )
                continue
            _merge(out, _restore(*pair, module=True, bindings=False))
    if "bindings" in parts and paths:

        def change(profile: Profile, is_open: bool) -> dict:
            done = swap_devices.swap_devices(profile, ident_a, ident_b, limits)
            return _result(notes=[done.as_string()])

        done = _batch(paths, f"Undo {label}").apply(change)  # type: ignore[attr-defined]
        out["warnings"].extend(done.get("warnings") or [])
        out["changed"].extend(done.get("changed") or [])
        out["failed"].extend(done.get("failed") or [])
        if not done.get("ok") and done.get("error"):
            out["warnings"].append(str(done["error"]))
        # Redo swaps again only the profiles this put back (S41).
        detail = {**detail, "profiles": [str(p) for p in done.get("changed") or []]}
    if not out["notes"] and not out["changed"]:
        out["ok"] = False
        out["error"] = "Nothing could be put back." + (
            " " + " ".join(out["warnings"]) if out["warnings"] else ""
        )
        return out
    try:
        library.set_last_change("swap", keys, label, detail, undone=not undone)
    except Exception as e:  # noqa: BLE001 - the undo is done; said
        out["warnings"].append(f"The Library couldn't record the undo ({e}).")
    return out
