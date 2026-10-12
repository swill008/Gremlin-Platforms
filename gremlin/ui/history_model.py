# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The History window (Tools > History): every saved change, newest first,
grouped by day, with what it was before and after, and Restore.

Restore puts a version back through the normal save paths. What it saves
is kept as one entry linked to the entry restored ("of"), which the window
doesn't list: the restored entry shows a tag instead ("Restored · 19:47",
"Reapplied · 19:48"), so the list stays as it is. An input's actions go
back into the open profile as an unsaved change (save it to keep it). A
module file or a setting is saved at once, as its editor does. A whole
profile is written as a copy next to the profile, to open with File > Load
Profile. The list never reloads under the user: changes recorded meanwhile
wait as "N new changes" until Show (showNew).
"""

from __future__ import annotations

import json
import logging
import re
import zlib
from datetime import date, datetime, timedelta
from pathlib import Path
from xml.etree import ElementTree

from PySide6 import QtCore

import gremlin.ui.type_aliases as ta
from gremlin import clock, history, history_profile, shared_state, text_diff, util
from gremlin.ui.option import entry_title

QML_IMPORT_NAME = "Gremlin.UI"
QML_IMPORT_MAJOR_VERSION = 1

_UUID = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
_ROLES = (
    "entryId",
    "when",
    "areaName",
    "title",
    "danger",
    "day",
    "time",
    "groupKey",
    "groupSize",
    "groupFirst",
    "groupOpen",
    "tag",
    "effect",
)
# 08 S12b: a Device Library entry's area, and what Restore of one does.
LIBRARY_AREA = "Device Library"
LIBRARY_NOTE = (
    "Restoring puts back the Device Library's list and its saved setups together."
)
CLEARED_NOTE = (
    "Everything in History before this point was deleted. "
    "Nothing before it can be restored or undone."
)


def _when(at: float) -> str:
    try:
        return datetime.fromtimestamp(float(at)).strftime("%Y-%m-%d %H:%M")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def _time(at: float) -> str:
    try:
        return datetime.fromtimestamp(float(at)).strftime("%H:%M")
    except (TypeError, ValueError, OSError, OverflowError):
        return ""


def _day(at: float, today: date | None = None) -> str:
    """ "Today", "Yesterday" or the date ("2026-10-09")."""
    try:
        day = datetime.fromtimestamp(float(at)).date()
    except (TypeError, ValueError, OSError, OverflowError):
        return ""
    today = today or datetime.fromtimestamp(clock.now()).date()
    if day == today:
        return "Today"
    if day == today - timedelta(days=1):
        return "Yesterday"
    return day.isoformat()


def _thing(entry: dict) -> str:
    """What an entry changed, for folding repeated changes to it into one
    row; "" never folds (a group, a clearing)."""
    kind, area = entry.get("kind"), str(entry.get("area") or "")
    subject = entry.get("subject") or {}
    if kind in (history.GROUP_KIND, history.CLEARED_KIND, history.RESTORE_KIND):
        return ""
    if area == "profile" and kind == "input":
        parts = ("profile", "deviceId", "inputType", "inputId", "mode")
        return "input|" + "|".join(_norm(subject.get(k)) for k in parts)
    if area == "profile":
        return f"profile|{kind}|{_norm(subject.get('profile'))}"
    if area == "settings":
        keys = subject.get("keys")
        keys = sorted(str(k) for k in keys) if isinstance(keys, list) else []
        return "settings|" + ",".join(keys) if keys else ""
    if kind == "library":
        return "library|" + _norm(entry.get("title"))
    # A module file is one thing whichever area its save landed in (a
    # map-only change is "Device Mapping Editor", others "Module files"):
    # S28 folds by the file, never by the area.
    device = _id(subject.get("deviceId")) or _norm(subject.get("fileName"))
    return f"module|{device}" if device else ""


def _side(value: object) -> dict | None:
    """A side the window reads as an object; any other type (a hand-edited
    or damaged line) reads as not there (08 S21)."""
    return value if isinstance(value, dict) else None


def _unpacked(side: object) -> str | None:
    """A profile side's packed text; None when it can't be unpacked."""
    try:
        return history_profile.unpack_text((_side(side) or {}).get("packed"))
    except (ValueError, TypeError, zlib.error):
        return None


def _norm(value: object) -> str:
    """For comparing: case, spacing and a GUID's braces don't matter."""
    return " ".join(str(value or "").split()).strip("{}").lower()


def _subjects(entry: dict) -> list[dict]:
    """The entry's subject and, for a group, each part's."""
    found = [entry.get("subject") or {}]
    if entry.get("kind") == "group":
        for side in (entry.get("after"), entry.get("before")):
            for part in side if isinstance(side, list) else []:
                if isinstance(part, dict) and isinstance(part.get("subject"), dict):
                    found.append(part["subject"])
    return found


def _id(value: object) -> str:
    """A device id for comparing: a GUID however written ("{abcd-ef}") and
    its id key ("ABCDEF") are the same."""
    return _norm(value).replace("-", "")


def _of_device_id(subject: dict, device_id: str, name: str) -> bool:
    """08 S43: a module-file entry (it has a fileName) of the device with
    this id. An entry from before device folders has no id: its device
    name decides."""
    if not subject.get("fileName"):
        return False
    theirs = _id(subject.get("deviceId"))
    if theirs:
        return bool(device_id) and theirs == _id(device_id)
    return bool(name) and _norm(subject.get("device")) == _norm(name)


def _about_device(subject: dict, want: dict) -> bool:
    """10 S56: a change to the device's module file, or a Device Library
    change that lists it (subject "devices": [{guid, name}]), by its id
    (by name only when either has no id)."""
    file_name = _norm(want.get("fileName"))
    if file_name and _norm(subject.get("fileName")) == file_name:
        return True
    device_id = str(want.get("deviceId") or want.get("guid") or "")
    if (device_id or want.get("name")) and _of_device_id(
        subject, device_id, str(want.get("name") or "")
    ):
        return True
    guid, name = _norm(want.get("guid")), _norm(want.get("name"))
    for dev in subject.get("devices") or []:
        if not isinstance(dev, dict):
            continue
        theirs = _norm(dev.get("guid"))
        if guid and theirs:
            if theirs == guid:
                return True
        elif name and _norm(dev.get("name")) == name:
            return True
    return False


def _matches(entry: dict, wanted: dict) -> bool:
    subject = entry.get("subject") or {}
    for key, value in wanted.items():
        if key == "area":
            if value and entry.get("area") != value:
                return False
            continue
        if key == "profile":
            # A path however written (case, slashes, relative): GL-194.
            if not util.same_path(subject.get("profile"), value):
                return False
            continue
        if key == "ofDevice":
            want = value if isinstance(value, dict) else {}
            if not any(_about_device(s, want) for s in _subjects(entry)):
                return False
            continue
        if key == "deviceName":
            continue  # only the fallback of "deviceId" for old entries
        if key == "deviceId":
            if subject.get("deviceId"):
                if _id(subject.get("deviceId")) != _id(value):
                    return False
            elif not _of_device_id(subject, "", str(wanted.get("deviceName") or "")):
                return False
            continue
        if _norm(subject.get(key, "")) != _norm(value):
            return False
    return True


# --- readable before / after -------------------------------------------------


def _plugin_name(tag: str) -> str:
    try:
        from gremlin.plugin_manager import PluginManager

        return str(PluginManager().tag_map[tag].name)
    except Exception:
        return tag


def _action_lines(
    node: ElementTree.Element, actions: dict[str, ElementTree.Element], depth: int
) -> list[str]:
    props = []
    for prop in node.findall("property"):
        name = (prop.findtext("name") or "").strip()
        if name in ("action-label", "activation-mode") or not name:
            continue
        props.append(
            f"{name.replace('-', ' ')} {(prop.findtext('value') or '').strip()}"
        )
    line = "  " * depth + _plugin_name(node.get("type") or "")
    if props:
        line += " (" + ", ".join(props) + ")"
    lines = [line]
    for element in node.iter():
        if element is node:
            continue
        text = (element.text or "").strip().lower()
        if _UUID.match(text) and text in actions:
            lines.extend(_action_lines(actions[text], actions, depth + 1))
    return lines


def _input_text(doc: object) -> str:
    if not doc:
        return "No actions."
    if not isinstance(doc, dict) or not isinstance(doc.get("actions") or [], list):
        return "Can't be read."
    try:
        node = ElementTree.fromstring(doc["input"])
        actions = {}
        for block in doc.get("actions") or []:
            action = ElementTree.fromstring(block)
            actions[(action.get("id") or "").lower()] = action
    except (ElementTree.ParseError, KeyError, TypeError):
        return "Can't be read."
    lines = []
    for config in node.findall("action-configuration"):
        root_id = (config.findtext("root-action") or "").strip().lower()
        if root_id in actions:
            lines.extend(_action_lines(actions[root_id], actions, 0))
    return "\n".join(lines) or "No actions."


def _module_text(side: object, parts: list[str]) -> str:
    side = _side(side)
    if not side or side.get("text") is None:
        return "No file."
    try:
        doc = json.loads(str(side["text"]))
    except (ValueError, RecursionError):
        return "Can't be read."
    if not isinstance(doc, dict):
        return "Can't be read."
    # In the Device Pack's words, not raw JSON (08 Q13, GL-192).
    from gremlin.ui.device_pack import module_text

    shown = [key for key in parts if key in doc] if parts else None
    return module_text(doc, shown) or "Not set."


def _settings_text(side: object) -> str:
    side = _side(side)
    if not side:
        return ""
    from gremlin.ui.option import shown_choice

    def shown(key: str, value: object) -> object:
        parts = key.split("/")
        if len(parts) != 3:
            return value
        return shown_choice((parts[0], parts[1], parts[2]), value)

    # Each setting by the name and choice Options shows ("Plugins folder",
    # "Stop" for a stored "Disable").
    return "\n".join(
        f"{entry_title(key.rsplit('/', 1)[-1], key)}: {shown(key, value)}"
        for key, value in side.items()
    )


def _title(entry: dict) -> str:
    """An entry's title. A settings entry's is made from its keys, so one
    written before a name changed reads as a new one does."""
    keys = (entry.get("subject") or {}).get("keys")
    if entry.get("area") == "settings" and keys and isinstance(keys, list):
        from gremlin.config import settings_history_title

        return settings_history_title(keys)
    return str(entry.get("title", ""))


def _is_library(entry: dict) -> bool:
    """A Device Library entry, or a group with one among its parts."""
    if entry.get("kind") == "library":
        return True
    if entry.get("kind") == history.GROUP_KIND:
        return any(p.get("kind") == "library" for p in _parts(entry))
    return False


def _area_name(entry: dict) -> str:
    """The area the window shows: "Device Library" for its entries."""
    if _is_library(entry):
        return LIBRARY_AREA
    area = str(entry.get("area") or "")
    return history.AREAS.get(area, area)


def _size_text(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{round(size / (1024 * 1024))} MB"
    if size >= 1024:
        return f"{round(size / 1024)} KB"
    return f"{size} bytes"


def describe(entry: dict) -> dict:
    """What the window shows for an entry, and what can be put back."""
    kind = entry.get("kind")
    area = entry.get("area")
    before, after = entry.get("before"), entry.get("after")
    note = ""
    panes = False
    danger = False
    if kind == history.CLEARED_KIND:
        # 08 S12b: what was deleted; nothing to put back.
        subject = entry.get("subject") or {}
        count = int(subject.get("entries") or 0)
        deleted = (
            f"{count} change{'' if count == 1 else 's'} and "
            f"{_size_text(int(subject.get('bytes') or 0))} of kept copies deleted."
        )
        texts = (deleted, deleted)
        can = (False, False)
        note = CLEARED_NOTE
        danger = True
    elif kind == history.GROUP_KIND:
        # One action of several steps (10 S51): each step under its title.
        parts = [describe(part) for part in _parts(entry)]
        texts = tuple(
            "\n\n".join(f"{p['title']}\n{p[which]}" for p in parts)
            for which in ("before", "after")
        )
        can = (
            any(p["canRestoreBefore"] for p in parts),
            any(p["canRestoreAfter"] for p in parts),
        )
        note = "Puts back every part of it at once."
        if _is_library(entry):
            note = LIBRARY_NOTE
        panes = any(p["closesPanes"] for p in parts)
    elif area == "profile" and kind == "input":
        texts = (_input_text(before), _input_text(after))
        can = (True, True)
        note = "Goes back into the open profile, unsaved."
        # The action panes close first (05 Q8): a pane's OK would write
        # its old copy back over the restored actions.
        panes = True
    elif area == "profile" and kind == "section":
        texts = (before or "Not there.", after or "Not there.")
        can = (False, False)
        note = "Put this back with Restore on the profile's save, below it in the list."
    elif area == "profile":
        size = [len(_unpacked(side) or "") for side in (before, after)]
        texts = tuple(
            f"The whole profile ({round(n / 1024)} KB)." if n else "Not kept."
            for n in size
        )
        can = (size[0] > 0, size[1] > 0)
        note = (
            "Written as a copy next to the profile, to open with File > Load Profile."
        )
    elif area == "settings":
        texts = (_settings_text(before), _settings_text(after))
        can = (bool(_side(before)), bool(_side(after)))
        note = "Saved at once."
    elif kind == "library":
        # The Device Library's list and saved setups (10 S51, 08 S12a).
        from gremlin import device_library

        before, after = _side(before), _side(after)
        texts = (
            device_library.history_text(before),
            device_library.history_text(after),
        )
        can = (before is not None, after is not None)
        note = LIBRARY_NOTE
    else:
        named = (entry.get("subject") or {}).get("parts")
        parts = [str(p) for p in named] if isinstance(named, list) else []
        before, after = _side(before), _side(after)
        texts = (_module_text(before, parts), _module_text(after, parts))
        can = (
            bool(before and before.get("text") is not None),
            bool(after and after.get("text") is not None),
        )
        note = "Saved at once, with its pictures."
    # What changed, row for row and word by word (08 S104).
    diff = text_diff.rows(texts[0], texts[1])
    effects = tuple(
        _effect(entry, which, ok)
        for which, ok in zip(("before", "after"), can, strict=True)
    )
    return {
        "title": _title(entry),
        "when": _when(entry.get("at", 0)),
        "area": _area_name(entry),
        "danger": danger,
        "before": texts[0],
        "after": texts[1],
        "canRestoreBefore": can[0],
        "canRestoreAfter": can[1],
        "note": note,
        "closesPanes": panes,
        "diffRows": diff,
        "diffBlocks": text_diff.blocks(diff),
        "effect": effects[0],
        "effectAfter": effects[1],
    }


def _thing_words(entry: dict) -> str:
    """What the entry is about, in a few words ("EVO OT L's module file")."""
    kind, area = entry.get("kind"), entry.get("area")
    subject = entry.get("subject") or {}
    if area == "profile" and kind == "input":
        name = subject.get("profileName") or "the profile"
        return f"this input's actions in {name}"
    if area == "profile":
        return f"{subject.get('profileName') or 'the profile'}"
    if area == "settings":
        keys = subject.get("keys")
        names = [
            entry_title(str(k).rsplit("/", 1)[-1], str(k))
            for k in (keys if isinstance(keys, list) else [])
        ]
        if len(names) == 1:
            return f"the setting {names[0]}"
        return "the settings " + ", ".join(names) if names else "these settings"
    if kind == "library":
        return "the Device Library's setups and files this change touched"
    device = " ".join(str(subject.get("device") or "").split())
    if not device and subject.get("fileName"):
        device = Path(str(subject.get("fileName"))).stem
    return f"{device}'s module file" if device else "the module file"


def _effect(entry: dict, which: str, can: bool) -> str:
    """In plain words, what Restore to before (or after) this change does."""
    if entry.get("kind") == history.CLEARED_KIND:
        return "Nothing to restore: History before this point was deleted."
    if entry.get("area") == "profile" and entry.get("kind") == "section":
        return (
            "This part can't be restored on its own. Restore the profile's "
            "save below it in the list."
        )
    if not can:
        return f"There is no version from {which} this change to put back."
    when = f"as it was {which} this change"
    kind, area = entry.get("kind"), entry.get("area")
    if kind == history.GROUP_KIND:
        count = len(_parts(entry))
        return f"Puts back all {count} parts of this change, {when}, at once."
    if area == "profile" and kind == "input":
        return (
            f"Puts {_thing_words(entry)} back {when}, into the open profile. "
            "Save the profile to keep it."
        )
    if area == "profile":
        return (
            f"Writes {_thing_words(entry)} {when} as a copy next to it, to "
            "open with File > Load Profile. The profile itself is not changed."
        )
    if area == "settings":
        return f"Sets {_thing_words(entry)} back {when}. Saved at once."
    if kind == "library":
        return (
            f"Puts {_thing_words(entry)} back {when}. Later changes stay. "
            "Saved at once."
        )
    return f"Puts {_thing_words(entry)} back {when}, with its pictures. Saved at once."


# --- restore -------------------------------------------------------------------


def _changed_everywhere() -> None:
    from gremlin.signal import signal

    signal.configChanged.emit()
    signal.profileChanged.emit()


def _restore_input(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.types import InputType
    from gremlin.ui.input_pairing import parse_guid

    profile = shared_state.current_profile
    subject = entry.get("subject") or {}
    if profile is None:
        return False, "No profile is open."
    if not util.same_path(profile.fpath, subject.get("profile")):
        return False, f"Open {subject.get('profileName') or 'that profile'} first."
    uid = parse_guid(str(subject.get("deviceId") or ""))
    if uid is None:
        return False, "That device isn't known."
    kind = InputType.to_enum(str(subject.get("inputType")))
    number = int(str(subject.get("inputId")))
    mode = str(subject.get("mode") or "Default")
    profile.put_input(uid, kind, number, mode, side)
    _changed_everywhere()
    return True, "Put back into the open profile. Save the profile to keep it."


def _restore_profile(entry: dict, side: dict | None, which: str) -> tuple[bool, str]:
    from gremlin.modules import module_file

    text = _unpacked(side)
    if not text:
        return False, "That version of the profile isn't kept any more."
    original = _profile_path(entry)
    stamp = datetime.fromtimestamp(float(entry.get("at") or 0)).strftime(
        "%Y-%m-%d %H.%M.%S"
    )
    # Its own name: Before and After (and two saves in one second) never
    # overwrite each other or another file.
    base = f"{original.stem} (history {stamp} {which})"
    copy = original.with_name(base + original.suffix)
    number = 2
    while copy.exists():
        copy = original.with_name(f"{base} {number}{original.suffix}")
        number += 1
    module_file.write_text(copy, text, encoding="utf-8-sig", newline="")
    # The copy is the user's: kept until they delete it (as Delete File
    # copies, 08 Q17; GL-277).
    return True, (
        f"Written as {copy}. Open it with File > Load Profile. "
        "It stays next to the profile until you delete it."
    )


def _profile_path(entry: dict) -> Path:
    return Path(str((entry.get("subject") or {}).get("profile") or "profile.xml"))


def _outside_folders(entry: dict) -> list[Path]:
    """AD6: the folders a profile Restore of this entry (or its parts) would
    write into that are neither the profiles folder nor the folder the
    profile is still in. An entry's path is only what its line says."""
    found: list[Path] = []
    for item in _parts(entry) if entry.get("kind") == history.GROUP_KIND else [entry]:
        if item.get("area") != "profile" or item.get("kind") == "input":
            continue
        original = _profile_path(item)
        folder = original.parent
        if original.is_file() or util.is_inside(folder, util.profiles_dir()):
            continue
        if folder not in found:
            found.append(folder)
    return found


def _restore_target(subject: dict, doc: dict) -> Path:
    """08 S43: the device's folder today, found by its id (it may have been
    renamed since), else the folder named after the device (made now)."""
    from gremlin.modules import store

    guid = str(doc.get("boundGuidLocal") or "").strip()
    device_id = str(subject.get("deviceId") or "").strip()
    for key in (guid, device_id):
        found = store.dir_of_id(key) if key else None
        if found is not None:
            return found
    device = (
        " ".join(str(subject.get("device") or doc.get("device") or "").split())
        or Path(str(subject.get("fileName") or "Device")).stem
    )
    if not guid and device_id and not device_id.startswith("name:"):
        guid = device_id
    return store.ensure_device_dir(device, guid)


def _swap_refs(node: object, refs: dict[str, str]) -> object:
    """The document with each picture ref ("image", an image shape's "src")
    swapped for its new form."""
    if isinstance(node, list):
        return [_swap_refs(item, refs) for item in node]
    if not isinstance(node, dict):
        return node
    out = {}
    for key, value in node.items():
        if key in ("image", "src") and isinstance(value, str) and value in refs:
            out[key] = refs[value]
        else:
            out[key] = _swap_refs(value, refs)
    return out


def _restore_module(entry: dict, side: dict | None) -> tuple[bool, str]:
    from gremlin.modules import store

    if not side or side.get("text") is None:
        return False, "There is no file to put back."
    subject = entry.get("subject") or {}
    text = str(side["text"])
    try:
        doc = json.loads(text)
    except (ValueError, RecursionError):
        doc = None
    doc = doc if isinstance(doc, dict) else None
    folder = _restore_target(subject, doc or {})
    path = store.module_file_in(folder)
    # Refs from before device folders ("<slug>/photo.png") as they are
    # today ("pictures/photo.png"); exactly that version otherwise, also a
    # damaged file (one way to mend it).
    refs = {}
    if doc is not None:
        refs = {
            ref: store.normal_ref(ref)
            for ref in store.named_refs(doc)
            if store.normal_ref(ref) != ref
        }
        if refs:
            text = json.dumps(_swap_refs(doc, refs), indent=2) + "\n"
    missing = []
    # What each picture was, to put back when the module file can't be
    # written: its pictures then still match it (AUD-FILES-05).
    was: dict[Path, bytes | None] = {}
    for picture in side.get("pictures") or []:
        if not isinstance(picture, dict):
            continue
        ref = str(picture.get("ref") or "")
        kept = history.kept_file(str(picture.get("keptFile") or ""))
        try:
            if kept is None:
                raise FileNotFoundError(ref)
            dest = store.picture_path(folder, store.normal_ref(ref))
            if dest not in was:
                was[dest] = dest.read_bytes() if dest.is_file() else None
            store.put_picture_at(dest, kept)
        except OSError:
            # The device's background picture is made again from the map
            # after the restore (07 S157), so a missing copy of it is no loss.
            if store.normal_ref(ref) != store.picture_ref(store.DEVICE_PHOTO):
                missing.append(ref)
    shown = f"{folder.name}/{path.name}"
    try:
        # History keeps the restore as a new entry.
        store.write_text(path, text, "History")
    except OSError as exc:
        _put_pictures_back(was)
        return False, f"{shown} could not be put back. {exc}"
    _changed_everywhere()
    if missing:
        return True, (
            f"Put back {shown}, without these pictures (no copy was "
            f"kept): {', '.join(missing)}."
        )
    return True, f"Put back {shown}."


def _put_pictures_back(was: dict[Path, bytes | None]) -> None:
    """The pictures as they were before a Restore that failed (no History:
    nothing was changed in the end)."""
    from gremlin.modules import module_file

    for dest, data in was.items():
        try:
            if data is None:
                dest.unlink(missing_ok=True)
            else:
                module_file.write_bytes(dest, data)
        except OSError:
            logging.getLogger("system").exception(
                "History: %s could not be put back as it was", dest
            )


def _restore_settings(side: dict | None) -> tuple[bool, str]:
    from gremlin.config import Configuration
    from gremlin.signal import signal
    from gremlin.util import _property_from_string, property_from_string

    cfg = Configuration()
    # Every value is worked out first: one that can't be read puts back
    # nothing (it used to apply the ones before it).
    values = []
    for key, value in (side or {}).items():
        section, group, name = key.split("/", 2)
        if not cfg.exists(section, group, name):
            continue
        kind = cfg.data_type(section, group, name)
        if kind in _property_from_string:
            text = json.dumps(value) if not isinstance(value, str) else value
            value = property_from_string(kind, text)
        # A list or a dict (action priorities) is kept as itself.
        values.append((section, group, name, value))
    for section, group, name, value in values:
        if not _apply_at_once(section, group, name, value):
            cfg.set(section, group, name, value)
    # device_aliases announces names that changed (D-01-OWNER-NOTICES).
    signal.configChanged.emit()
    return True, "Settings put back."


def _apply_at_once(section: str, group: str, name: str, value: object) -> bool:
    """A setting that acts at once (Diagnostic logs, UI scale) is put back
    through its Options control, so it applies now as it does there (01 Q7,
    GL-115). False: an ordinary setting, for Configuration.set."""
    from gremlin.ui import log_option, ui_scale_option

    key = (section, group, name)
    if key == (log_option.LOG_SECTION, log_option.LOG_GROUP, log_option.LOG_NAME):
        log_option.LogLevelModel().setLevel(str(value))
        return True
    if key == (
        ui_scale_option.SCALE_SECTION,
        ui_scale_option.SCALE_GROUP,
        ui_scale_option.SCALE_NAME,
    ):
        try:
            scale = int(str(value))
        except ValueError:
            return False
        ui_scale_option.UiScaleModel().setScale(scale)
        return True
    return False


def _parts(entry: dict) -> list[dict]:
    """A group entry's parts as entries of their own, in the order made."""
    befores = entry.get("before") or []
    afters = entry.get("after") or []
    parts = []
    for first, second in zip(befores, afters, strict=False):
        if not isinstance(first, dict) or not isinstance(second, dict):
            continue  # history._sound keeps these out; a part never raises
        parts.append(
            {
                "id": entry.get("id"),
                "at": entry.get("at"),
                "area": first.get("area"),
                "kind": first.get("kind"),
                "title": first.get("title"),
                "subject": first.get("subject"),
                "before": first.get("side"),
                "after": second.get("side"),
            }
        )
    return parts


def _restore_group(entry: dict, which: str) -> tuple[bool, str]:
    """Each part that can be put back, as one new entry: "before" from the
    last step back to the first, "after" from the first on."""
    parts = _parts(entry)
    if which == "before":
        parts.reverse()
    key = "canRestoreBefore" if which == "before" else "canRestoreAfter"
    token = history.begin_group(history.restore_title(entry, which))
    messages: list[str] = []
    try:
        for part in parts:
            if not describe(part)[key]:
                continue
            ok, message = _restore_one(part, which)
            if not ok:
                return False, message
            messages.append(message)
    finally:
        history.end_group(token)
    return True, " ".join(messages) or "Put back."


def _restore_one(entry: dict, which: str) -> tuple[bool, str]:
    side = entry.get(which)
    area, kind = entry.get("area"), entry.get("kind")
    if kind == history.GROUP_KIND:
        return _restore_group(entry, which)
    if area == "profile" and kind == "input":
        return _restore_input(entry, side)
    if area == "profile":
        return _restore_profile(entry, side, which)
    if area == "settings":
        return _restore_settings(side)
    if kind == "library":
        from gremlin import device_library

        return device_library.restore_history(entry, side)
    return _restore_module(entry, side)


def restore(entry_id: str, which: str, outside_ok: bool = False) -> dict:
    """Puts back the "before" or "after" version of an entry. A profile copy
    for a folder outside the profiles folder, where the profile isn't any
    more, is asked about first (AD6): {"ok": False, "ask": True, "message"}
    and nothing is written; outside_ok is the user's yes."""
    entry = history.entry(entry_id)
    if entry is None:
        return {"ok": False, "message": "That change isn't in the history any more."}
    if not describe(entry)[
        "canRestoreBefore" if which == "before" else "canRestoreAfter"
    ]:
        return {"ok": False, "message": "That version can't be put back."}
    outside = [] if outside_ok else _outside_folders(entry)
    if outside:
        where = ", ".join(str(f) for f in outside)
        return {
            "ok": False,
            "ask": True,
            "message": (
                f"Write the restored profile to {where}? It is outside your "
                "profiles folder and the profile's own folder."
            ),
        }
    # One entry for the restore, linked to the entry it restored (a restore
    # of a restore names the first original): the window tags that one.
    original_id = str(entry.get("of") or entry_id)
    original = history.entry(original_id) if entry.get("of") else entry
    token = history.begin_group(
        history.restore_title(original or entry, which),
        str(entry.get("area") or "modules"),
        extra={"of": original_id, "restore": which},
    )
    ok = False
    try:
        ok, message = _restore_one(entry, which)
    except Exception as exc:
        message = f"It couldn't be put back: {exc}"
    finally:
        if not ok:
            history.drop_link(token)
        history.end_group(token)
    return {"ok": ok, "message": message}


def _tags(entries: list[dict]) -> dict[str, str]:
    """Each restored entry's tag from its latest restore: "Restored · 19:47"
    or "Reapplied · 19:48"."""
    tags: dict[str, tuple[float, str]] = {}
    for item in entries:
        if not history.is_restore(item):
            continue
        at = float(item.get("at") or 0)
        word = history.restore_word(str(item.get("restore") or "before"))
        ids = item.get("ofAll")
        ids = [str(i) for i in ids] if isinstance(ids, list) else []
        ids.append(str(item.get("of")))
        for entry_id in ids:
            if entry_id not in tags or tags[entry_id][0] < at:
                tags[entry_id] = (at, f"{word} · {_time(at)}")
    return {key: value[1] for key, value in tags.items()}


@ta.QmlElement
class HistoryModel(QtCore.QAbstractListModel):
    """The entries for the History window, filtered, grouped by day, with
    repeated changes to one thing folded into one row. The rows never change
    under the user: a restore tags its entry in place, and changes recorded
    meanwhile wait (newCount) until showNew()."""

    filterChanged = QtCore.Signal()
    # The change detail() last read: its rows and blocks changed.
    diffChanged = QtCore.Signal()
    newCountChanged = QtCore.Signal()
    # From the History writer thread: an entry was written.
    _written = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._diff_rows: list[dict] = []
        self._diff_blocks: list[int] = []
        # Every entry read, restores too.
        self._all: list[dict] = []
        # What the list shows (filtered, no restores), each with its run.
        self._shown: list[dict] = []
        self._runs: dict[str, dict] = {}
        self._open: set[str] = set()
        self._rows: list[dict] = []
        self._tags: dict[str, str] = {}
        # Each row's effect, worked out once (describe() reads the sides).
        self._effects: dict[str, str] = {}
        self._new = 0
        self._filter: dict = {}
        self._search = ""
        # History writes come in bursts: read once they settle.
        self._later = QtCore.QTimer(self)
        self._later.setSingleShot(True)
        self._later.setInterval(300)
        self._later.timeout.connect(self.refresh)
        self._written.connect(
            self._later.start, QtCore.Qt.ConnectionType.QueuedConnection
        )
        self._listener = self._written.emit
        history.add_written_listener(self._listener)
        self.destroyed.connect(
            lambda *_: history.remove_written_listener(self._listener)
        )

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return {
            QtCore.Qt.ItemDataRole.UserRole + i: QtCore.QByteArray(name.encode())
            for i, name in enumerate(_ROLES, start=1)
        }

    def _role(self, name: str) -> int:
        return QtCore.Qt.ItemDataRole.UserRole + _ROLES.index(name) + 1

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def data(
        self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole
    ) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self._rows):
            return None
        entry = self._rows[index.row()]
        name = (
            _ROLES[role - QtCore.Qt.ItemDataRole.UserRole - 1]
            if role > QtCore.Qt.ItemDataRole.UserRole
            and role - QtCore.Qt.ItemDataRole.UserRole <= len(_ROLES)
            else ""
        )
        entry_id = str(entry.get("id", ""))
        run = self._runs.get(entry_id) or {}
        if name == "entryId":
            return entry_id
        if name == "when":
            return _when(entry.get("at", 0))
        if name == "areaName":
            return _area_name(entry)
        if name == "danger":
            return entry.get("kind") == history.CLEARED_KIND
        if name == "title":
            return _title(entry)
        if name == "day":
            return _day(entry.get("at", 0))
        if name == "time":
            return _time(entry.get("at", 0))
        if name == "groupKey":
            return run.get("key", entry_id)
        if name == "groupSize":
            return run.get("size", 1)
        if name == "groupFirst":
            return run.get("first", True)
        if name == "groupOpen":
            return run.get("key", entry_id) in self._open
        if name == "tag":
            return self._tags.get(entry_id, "")
        if name == "effect":
            if entry_id not in self._effects:
                self._effects[entry_id] = describe(entry)["effect"]
            return self._effects[entry_id]
        return None

    # --- what shows ----------------------------------------------------------

    def _visible(self) -> list[dict]:
        words = self._search.lower().split()
        return [
            e
            for e in self._all
            if not history.is_restore(e)
            and _matches(e, self._filter)
            and all(
                w in (_title(e) + " " + json.dumps(e.get("subject"))).lower()
                for w in words
            )
        ]

    def _set_shown(self, shown: list[dict]) -> None:
        """shown and its runs: next to each other, the same day and the same
        thing (_thing) fold into one run keyed by its newest entry's id."""
        self._shown = shown
        self._runs = {}
        head: dict | None = None
        for entry in shown:
            entry_id = str(entry.get("id", ""))
            thing = _thing(entry)
            day = _day(entry.get("at", 0))
            if (
                head is not None
                and thing
                and head["thing"] == thing
                and head["day"] == day
            ):
                head["size"] += 1
                self._runs[entry_id] = {"run": head, "first": False}
                continue
            head = {"key": entry_id, "thing": thing, "day": day, "size": 1}
            self._runs[entry_id] = {"run": head, "first": True}
        for entry_id, place in self._runs.items():
            run = place["run"]
            self._runs[entry_id] = {
                "key": run["key"],
                "size": run["size"],
                "first": place["first"],
            }
        keys = {run["key"] for run in self._runs.values()}
        self._open &= keys

    def _row_list(self) -> list[dict]:
        rows = []
        for entry in self._shown:
            run = self._runs[str(entry.get("id", ""))]
            if run["first"] or run["key"] in self._open:
                rows.append(entry)
        return rows

    def _set_new(self, count: int) -> None:
        if count != self._new:
            self._new = count
            self.newCountChanged.emit()

    @QtCore.Slot()
    def reload(self) -> None:
        """Reads History and shows it all again (on open, after a filter
        or a clearing)."""
        self._all = history.entries()
        self._apply()

    def _apply(self) -> None:
        self.beginResetModel()
        self._tags = _tags(self._all)
        self._set_shown(self._visible())
        self._rows = self._row_list()
        self.endResetModel()
        self._set_new(0)

    @QtCore.Slot()
    def refresh(self) -> None:
        """Reads History again without changing the rows: tags change in
        place, and newCount counts what waits for showNew()."""
        self._all = history.entries()
        tags = _tags(self._all)
        changed, self._tags = self._tags, tags
        role = self._role("tag")
        for row, entry in enumerate(self._rows):
            entry_id = str(entry.get("id", ""))
            if changed.get(entry_id, "") != tags.get(entry_id, ""):
                index = self.index(row, 0)
                self.dataChanged.emit(index, index, [role])
        shown = {str(e.get("id", "")) for e in self._shown}
        self._set_new(
            sum(1 for e in self._visible() if str(e.get("id", "")) not in shown)
        )

    @QtCore.Slot()
    def showNew(self) -> None:
        """The changes waiting (newCount) join the top of the list. The rows
        already there stay as they are when the new ones only go above
        them; a new change to the thing of the top row regroups (reset)."""
        old_rows = [str(e.get("id", "")) for e in self._rows]
        old_runs = {key: dict(value) for key, value in self._runs.items()}
        shown = self._visible()
        known = {str(e.get("id", "")) for e in self._shown}
        if not any(str(e.get("id", "")) not in known for e in shown):
            self._set_new(0)
            return
        self._set_shown(shown)
        rows = self._row_list()
        ids = [str(e.get("id", "")) for e in rows]
        added = len(ids) - len(old_rows)
        same = (
            added > 0
            and ids[added:] == old_rows
            and all(self._runs[i] == old_runs.get(i) for i in old_rows)
        )
        if same:
            self.beginInsertRows(QtCore.QModelIndex(), 0, added - 1)
            self._rows = rows
            self.endInsertRows()
        else:
            self.beginResetModel()
            self._rows = rows
            self.endResetModel()
        self._set_new(0)

    @QtCore.Slot(str)
    def toggleGroup(self, key: str) -> None:
        """Opens or closes the run with this groupKey: its other changes
        show under its first row, or go."""
        head = next(
            (row for row, e in enumerate(self._rows) if str(e.get("id")) == key),
            -1,
        )
        if head < 0 or self._runs.get(key, {}).get("size", 1) < 2:
            return
        members = [
            e
            for e in self._shown
            if self._runs[str(e.get("id", ""))]["key"] == key
            and not self._runs[str(e.get("id", ""))]["first"]
        ]
        if key in self._open:
            self.beginRemoveRows(QtCore.QModelIndex(), head + 1, head + len(members))
            self._open.discard(key)
            del self._rows[head + 1 : head + 1 + len(members)]
            self.endRemoveRows()
        else:
            self.beginInsertRows(QtCore.QModelIndex(), head + 1, head + len(members))
            self._open.add(key)
            self._rows[head + 1 : head + 1] = members
            self.endInsertRows()
        index = self.index(head, 0)
        self.dataChanged.emit(index, index, [self._role("groupOpen")])

    def _new_count(self) -> int:
        return self._new

    newCount = QtCore.Property(int, fget=_new_count, notify=newCountChanged)

    @QtCore.Slot(str)
    def setFilter(self, text: str) -> None:
        """Which entries show: {"area", "device", "inputType", "inputId",
        "mode", "ofDevice", "deviceId" (with "deviceName" for module-file
        entries from before device folders)}, each optional."""
        try:
            wanted = json.loads(text) if text else {}
        except (ValueError, RecursionError):
            wanted = {}
        self._filter = wanted if isinstance(wanted, dict) else {}
        self._apply()
        self.filterChanged.emit()

    @QtCore.Slot(str)
    def setSearch(self, text: str) -> None:
        self._search = str(text or "")
        self._apply()

    @QtCore.Slot(str, result=str)
    def detail(self, entry_id: str) -> str:
        entry = next((e for e in self._all if e.get("id") == entry_id), None)
        shown = describe(entry) if entry else {}
        if entry:
            shown["tag"] = self._tags.get(entry_id, "")
            shown["time"] = _time(entry.get("at", 0))
            shown["day"] = _day(entry.get("at", 0))
        # Kept for diffRows / diffBlocks, the same rows as in the text.
        self._diff_rows = list(shown.get("diffRows") or [])
        self._diff_blocks = list(shown.get("diffBlocks") or [])
        self.diffChanged.emit()
        return json.dumps(shown)

    @QtCore.Slot(str, str, result=str)
    def restore(self, entry_id: str, which: str) -> str:
        """{"ok", "message"}; with "ask": true nothing was written and the
        message is the question for restoreOutside (AD6). The entry's tag
        changes in place; no row is added."""
        result = restore(entry_id, which)
        if result.get("ok"):
            self.refresh()
        return json.dumps(result)

    @QtCore.Slot(str, str, result=str)
    def restoreOutside(self, entry_id: str, which: str) -> str:
        """restore() after the user said yes to writing a profile copy
        outside the profiles folder (AD6)."""
        result = restore(entry_id, which, outside_ok=True)
        if result.get("ok"):
            self.refresh()
        return json.dumps(result)

    @QtCore.Slot(result=str)
    def summary(self) -> str:
        """What Clear History would delete (08 S12b): {"entries", "bytes",
        "size"} with size in words ("38 MB")."""
        found = history.summary()
        return json.dumps({**found, "size": _size_text(int(found["bytes"]))})

    @QtCore.Slot(result=str)
    def clearAll(self) -> str:
        """Clear History (08 S12b): {"ok", "error", "entries", "bytes"}; the
        list is read again."""
        result = history.clear_all()
        self.reload()
        return json.dumps(result)

    def _filter_text(self) -> str:
        return json.dumps(self._filter)

    filterText = QtCore.Property(str, fget=_filter_text, notify=filterChanged)

    def _rows_of_diff(self) -> list:
        return self._diff_rows

    def _blocks_of_diff(self) -> list:
        return self._diff_blocks

    # The change detail() last read, aligned row for row (text_diff.rows),
    # and the first row of each change block (text_diff.blocks).
    diffRows = QtCore.Property(list, fget=_rows_of_diff, notify=diffChanged)
    diffBlocks = QtCore.Property(list, fget=_blocks_of_diff, notify=diffChanged)
