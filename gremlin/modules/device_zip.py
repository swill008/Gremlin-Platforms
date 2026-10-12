# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""A device folder as one file to share (08 S111, D-03-DEVICE-FOLDERS).

Export zips one device's folder into "<shown name>.gmap" (Export / Import
Device's only file, D-FIXLIST-B2); Import As a new device unpacks one into a
new device folder ("(2)" for a taken name, 03 S132), only the ticked pieces.
The bindings are an optional part. A device map template travels the same way as
".gtemplate".

.gmap layout::

    gmap.json             {"format": "gremlin-device", "version": 1, "device",
                           "deviceName", "id", "direction", "exportedAt", "app",
                           "parts": ["folder"] or ["folder", "bindings"]
                           (Device Library, no module file: ["bindings"]
                           or []), "madeBy", "note", "modes" (the modes
                           whose wires are in it; [] without bindings),
                           "damaged": "<why>" (keep_damaged only)}
    module.json           the module file, boundGuidLocal/boundName stripped
                          (none when parts has no "folder")
    pictures/<file>       only the pictures the module file names
    bindings/wires.json   the Device Pack's wires (only when ticked)
    bindings/outputs/<folder>.json   the output modules those wires send to
    bindings/outputs/<folder>/pictures/<file>   the pictures each names

Never in it: device.json, recovery.json, imported/, *.bad-*, the edit's
temporary folder.

.gtemplate layout: template.json + pictures/<file>.

The bindings belong to the Device Pack (gremlin.ui.device_pack); this
module never imports the UI, so its callers hand in the wires collected
for export (device_pack.collect_wires). On import the Device Pack puts
them into the profile itself (device_pack.import_as_new -> apply_zip).
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from gremlin.modules import module_file, store
from gremlin.modules.pack_checks import too_big, wires_problem

GMAP_EXT = ".gmap"
GTEMPLATE_EXT = ".gtemplate"
GMAP_JSON = "gmap.json"
GMAP_FORMAT = "gremlin-device"
GMAP_VERSION = 1
TEMPLATE_JSON = "template.json"
_PICTURES = "pictures/"
_WIRES = "bindings/wires.json"
_OUTPUTS = "bindings/outputs/"
_WHO = "Device Export"

# A device id: a GUID with or without braces and dashes (an id key is the
# upper-case form without them, ids.stored_guid_key).
_GUID_RE = re.compile(r"^[0-9a-fA-F]{32}$")
# An action's id in a wire block (uuid text, any case).
_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)

_NO_FILE = "This device has no module file yet."


# --- picture references -------------------------------------------------------


def replace_strings(value: object, mapping: dict[str, str]) -> object:
    """value with every string that is a key of mapping replaced."""
    if isinstance(value, dict):
        return {k: replace_strings(v, mapping) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_strings(v, mapping) for v in value]
    if isinstance(value, str) and value in mapping:
        return mapping[value]
    return value


def _normal_doc(doc: dict) -> tuple[dict, list[str]]:
    """The doc with every picture it names as "pictures/<file>", and those
    refs (each once, in order)."""
    mapping = {ref: store.normal_ref(ref) for ref in store.named_refs(doc)}
    refs = list(dict.fromkeys(mapping.values()))
    return replace_strings(doc, mapping), refs  # type: ignore[return-value]


def _picture_name(ref: str) -> str:
    """The file name a "pictures/<file>" ref stands for ("" for a URL or an
    absolute path, which never travel)."""
    text = str(ref or "").replace("\\", "/")
    if not text.startswith(_PICTURES):
        return ""
    name = text[len(_PICTURES) :]
    return name if name and "/" not in name else ""


def _zip_pictures(zf: zipfile.ZipFile, base: Path, refs: list[str]) -> None:
    """Adds the named pictures that exist under base/pictures/."""
    for ref in refs:
        name = _picture_name(ref)
        if not name:
            continue
        src = store.picture_path(base, ref)
        if src is not None and Path(src).is_file():
            zf.writestr(_PICTURES + name, Path(src).read_bytes())


# --- export ---------------------------------------------------------------------


def braced_guid(text: str) -> str:
    """A device id (an id key too) as "{XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX}"."""
    h = str(text or "").strip().replace("{", "").replace("}", "").replace("-", "")
    h = h.upper()
    return "{" + f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}" + "}"


def guid_like(text: str) -> bool:
    """text is a device id (not a "name:" key)."""
    plain = str(text or "").strip().replace("{", "").replace("}", "").replace("-", "")
    return bool(_GUID_RE.match(plain))


def _output_doc(name: str) -> tuple[str, dict, Path, list[str]] | None:
    """An output module the wires send to: (its folder name, its document
    without this machine's binding, its folder, the pictures it names as
    "pictures/<file>")."""
    from gremlin.modules.registry import is_output_name

    match = store.match_known_device(name)
    guid = str(match["guid"]) if match and match.get("guid") else ""
    path = store.module_file(name, guid)
    doc = store.read_path(path) if path.is_file() else {}
    if not doc:
        return None
    doc, refs = _normal_doc(doc)
    doc.pop("boundGuidLocal", None)
    doc.pop("boundName", None)
    doc["device"] = name
    if is_output_name(name):
        doc["direction"] = "dest"
    slug = path.parent.name
    doc["pack"] = {"exportedName": name, "exportedGuid": guid, "slug": slug}
    return slug, doc, path.parent, refs


def _mode_name(mode: object) -> str:
    return str((mode.get("name") if isinstance(mode, dict) else "") or "Default")


def _action_id(block: object) -> str:
    """An action block's own id ("" when it can't be read)."""
    try:
        return str(ElementTree.fromstring(str(block)).get("id") or "").lower()
    except ElementTree.ParseError:
        return ""


def _ids_in(block: object) -> set[str]:
    """Every id an input or action block names, in any tag (<root-action>,
    <action-id>, ...) or attribute; only_modes keeps those that are actions.
    An action block's own id is left out."""
    found = {m.lower() for m in _UUID_RE.findall(str(block))}
    own = _action_id(block)
    if own:
        found.discard(own)
    return found


def only_modes(wires: dict, modes: list[str] | None) -> dict:
    """wires with only these modes' inputs (None: all): their tree entries
    and the parents above them, the actions those inputs reach, and the OSC
    rows they use. Its "outputs" list stays as given."""
    if modes is None:
        return wires
    keep = [m for m in wires.get("modes") or [] if _mode_name(m) in modes]
    out = dict(wires)
    out["modes"] = keep
    tree = wires.get("tree") or {}
    kept_tree: dict = {}
    pending = [_mode_name(m) for m in keep]
    while pending:
        name = pending.pop()
        if name in kept_tree or name not in tree:
            continue
        kept_tree[name] = tree[name]
        if tree[name]:
            pending.append(str(tree[name]))
    out["tree"] = kept_tree
    blocks = [str(b) for m in keep for b in (m.get("inputs") or [])]
    by_id = {_action_id(a): a for a in wires.get("actions") or []}
    wanted: set[str] = set()
    pending = [i for b in blocks for i in _ids_in(b)]
    while pending:
        ident = pending.pop()
        if ident in wanted:
            continue
        wanted.add(ident)
        if ident in by_id:
            pending.extend(_ids_in(by_id[ident]))
    out["actions"] = [a for a in wires.get("actions") or [] if _action_id(a) in wanted]
    if wires.get("osc"):
        text = "\n".join(blocks)
        osc = [
            row
            for row in wires["osc"]
            if not isinstance(row, dict) or str(row.get("uid") or "") in text
        ]
        if osc:
            out["osc"] = osc
        else:
            out.pop("osc", None)
    return out


def _bindings(
    wires: dict,
) -> tuple[dict | None, list[tuple[str, dict, Path, list[str]]]]:
    """The bindings part of the device's wires and the output modules they
    send to."""
    if not wires.get("modes"):
        return None, []
    part = {
        "modes": wires["modes"],
        "actions": wires["actions"],
        "tree": wires["tree"],
    }
    if wires.get("osc"):
        part["osc"] = wires["osc"]
    outputs = []
    for output_name in wires.get("outputs") or []:
        built = _output_doc(output_name)
        if built is not None:
            outputs.append(built)
    return part, outputs


def build_gmap(
    device_name: str,
    guid: str,
    wires: dict | None,
    *,
    keep_damaged: bool = False,
    no_file_ok: bool = False,
    made_by: str = "",
    note: str = "",
    modes: list[str] | None = None,
) -> bytes | str:
    """The .gmap of a device's folder; a str when it can't be made (no
    module file, or a damaged one). wires: the device's wires
    (device_pack.collect_wires; None: no bindings part). keep_damaged (the
    Device Library's autosave, 10 S20a): a damaged module file goes in as
    it is, its reason in gmap.json["damaged"]. no_file_ok (the Device
    Library's saved setups of a stick with no module file here): no folder
    part, only its bindings (parts ["bindings"], or [] without them).
    made_by, note: shown when the file is imported (gmap.json "madeBy",
    "note"). modes: the modes whose wires go in (None: every mode); the
    label's "modes" names them. The output modules the wires send to go in
    with the pictures they name (D-FIXLIST-B2)."""
    from gremlin.util import get_code_version

    name = " ".join(str(device_name or "").split())
    guid = str(guid or "").strip()
    if not name:
        return "Choose a device."
    base = store.device_dir(name, guid)
    path = store.module_file_in(base)
    has_file = path.is_file()
    if not has_file and not no_file_ok:
        return _NO_FILE
    damaged = store.damage_of(path) if has_file else ""
    if damaged and not keep_damaged:
        return (
            f"The module file of {base.name} is damaged ({damaged}), so it "
            "can't be exported. Choose Start Fresh on the device's card first "
            "(the damaged file is kept)."
        )
    label = {
        "format": GMAP_FORMAT,
        "version": GMAP_VERSION,
        "device": store.shown_name_of(name, guid),
        "deviceName": name,
        "id": store.id_key(name, guid),
        "direction": store.direction_for(name, guid),
        "exportedAt": datetime.now().isoformat(timespec="seconds"),
        "app": get_code_version(),
        "parts": ["folder"] if has_file else [],
        "madeBy": " ".join(str(made_by or "").split()),
        "note": str(note or "").strip(),
        "modes": [],
    }
    part: dict | None = None
    outputs: list[tuple[str, dict, Path, list[str]]] = []
    if wires is not None:
        label["parts"] = [*label["parts"], "bindings"]
        part, outputs = _bindings(only_modes(wires, modes))
        if part is not None:
            label["modes"] = [_mode_name(m) for m in part["modes"]]
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        if not has_file:
            zf.writestr(GMAP_JSON, json.dumps(label, indent=2) + "\n")
        elif damaged:
            label["damaged"] = damaged
            zf.writestr(GMAP_JSON, json.dumps(label, indent=2) + "\n")
            zf.writestr(store.MODULE_FILE, path.read_bytes())
        else:
            doc, refs = _normal_doc(store.read_path(path))
            doc.pop("boundGuidLocal", None)
            doc.pop("boundName", None)
            zf.writestr(GMAP_JSON, json.dumps(label, indent=2) + "\n")
            zf.writestr(store.MODULE_FILE, json.dumps(doc, indent=2) + "\n")
            _zip_pictures(zf, base, refs)
        if part is not None:
            zf.writestr(_WIRES, json.dumps(part, indent=2) + "\n")
        for slug, out_doc, out_base, out_refs in outputs:
            zf.writestr(f"{_OUTPUTS}{slug}.json", json.dumps(out_doc, indent=2) + "\n")
            for ref in out_refs:
                pic = _picture_name(ref)
                src = store.picture_path(out_base, ref) if pic else None
                if src is not None and Path(src).is_file():
                    zf.writestr(
                        f"{_OUTPUTS}{slug}/{_PICTURES}{pic}", Path(src).read_bytes()
                    )
    return blob.getvalue()


def _write_out(out: Path, data: bytes, lead: str) -> str:
    """Writes data to out atomically and reads it back ("" or why not)."""
    if store.is_inside(out):
        return (
            f"{lead} {out.name} can't be saved inside the program's modules "
            f"folder ({store.folder()}). Choose another folder."
        )
    if not out.parent.is_dir():
        return f"{lead} The folder {out.parent} does not exist."
    try:
        # A temporary file, then a swap: never half a file over an older one.
        module_file.write_bytes(out, data)
    except OSError as exc:
        why = exc.strerror or exc
        return f"{lead} {out.name} could not be written in {out.parent}: {why}."
    try:
        with zipfile.ZipFile(out, "r") as zf:
            zf.testzip()
    except (OSError, zipfile.BadZipFile) as exc:
        return f"{lead} {out.name} was written but could not be read back ({exc})."
    return ""


def export_device(
    device_name: str,
    guid: str,
    out_path: Path,
    wires: dict | None,
    *,
    made_by: str = "",
    note: str = "",
    modes: list[str] | None = None,
) -> str:
    """Saves the device's folder as out_path (a .gmap); "" or why not.
    wires, made_by, note, modes: as build_gmap. Refused inside the modules
    folder (08 S111)."""
    out = Path(out_path)
    if out.suffix.lower() != GMAP_EXT:
        out = out.with_name(out.name + GMAP_EXT)
    lead = "Export failed."
    if store.is_inside(out):
        return _write_out(out, b"", lead)
    built = build_gmap(
        device_name, guid, wires, made_by=made_by, note=note, modes=modes
    )
    if isinstance(built, str):
        return f"{lead} {built}"
    return _write_out(out, built, lead)


# --- reading ----------------------------------------------------------------------


def _json(zf: zipfile.ZipFile, name: str) -> object:
    try:
        return json.loads(zf.read(name).decode("utf-8"))
    except (ValueError, RecursionError, UnicodeDecodeError) as exc:
        raise ValueError(f"Its {name} could not be read ({exc}).") from exc


def _safe_member(name: str) -> str:
    """A pictures/ member's plain file name ("" for anything else: folders,
    "..", deeper paths)."""
    if not name.startswith(_PICTURES) or name.endswith("/"):
        return ""
    rest = name[len(_PICTURES) :]
    if not rest or "/" in rest or "\\" in rest or rest in (".", ".."):
        return ""
    return rest


def has_folder(label: dict) -> bool:
    """A .gmap holds a device folder (module.json and pictures); one
    without a "folder" part holds only bindings."""
    parts = label.get("parts")
    return not isinstance(parts, list) or "folder" in parts


def read_gmap(zip_path: Path) -> dict | str:
    """A .gmap's parts, or why it can't be read (the Device Pack's checks,
    08 S110): {"gmap": dict, "module": dict | None (None when exported
    damaged; {} with no folder part, a Device Library setup of a stick with
    no module file), "moduleBytes": bytes, "pictures": {file: bytes},
    "wires": dict | None, "outputs": {folder: dict}, "outputPictures":
    {folder: {file: bytes}}, "madeBy": str, "note": str, "modes": [mode
    names] (D-FIXLIST-B2), "bytes": the file's size}."""
    try:
        with zipfile.ZipFile(Path(zip_path), "r") as zf:
            big = too_big(zf)
            if big:
                return big
            names = zf.namelist()
            if GMAP_JSON not in names:
                return "This is not a device folder file: it has no gmap.json."
            label = _json(zf, GMAP_JSON)
            if not isinstance(label, dict) or label.get("format") != GMAP_FORMAT:
                return "This is not a device folder file: its gmap.json is not one."
            try:
                version = int(label.get("version") or 1)
            except (TypeError, ValueError):
                version = 1
            if version > GMAP_VERSION:
                app = str(label.get("app") or "").strip()
                by = f" (version {app})" if app else ""
                return (
                    f"This file was made by a newer Gremlin-Platforms{by}. "
                    "Update the program to import it."
                )
            module: dict | None = None
            if not has_folder(label):
                raw = b""
                module = {}
            elif store.MODULE_FILE not in names:
                return "This file can't be read. It has no module.json."
            else:
                raw = zf.read(store.MODULE_FILE)
            if has_folder(label) and not label.get("damaged"):
                module = _json(zf, store.MODULE_FILE)  # type: ignore[assignment]
                if not isinstance(module, dict):
                    return "This file can't be read. Its module.json is not a document."
            wires = None
            if _WIRES in names:
                wires = _json(zf, _WIRES)
                problem = wires_problem(wires)
                if problem:
                    problem = problem.replace("wires.json", _WIRES)
                    return f"This file can't be read. {problem}"
            outputs: dict[str, dict] = {}
            pictures: dict[str, bytes] = {}
            output_pictures: dict[str, dict[str, bytes]] = {}
            for name in names:
                if name.startswith(_OUTPUTS):
                    rest = name[len(_OUTPUTS) :]
                    if "/" not in rest and rest.lower().endswith(".json"):
                        doc = _json(zf, name)
                        if not isinstance(doc, dict):
                            return (
                                f"This file can't be read. Its {name} is not "
                                "a document."
                            )
                        outputs[rest[: -len(".json")]] = doc
                        continue
                    slug, _, inner = rest.partition("/")
                    file = _safe_member(inner)
                    if slug and slug not in (".", "..") and "\\" not in slug and file:
                        output_pictures.setdefault(slug, {})[file] = zf.read(name)
                    continue
                file = _safe_member(name)
                if file:
                    pictures[file] = zf.read(name)
            # Only the pictures of an output module that is in the file.
            output_pictures = {
                slug: files
                for slug, files in output_pictures.items()
                if slug in outputs
            }
            size = Path(zip_path).stat().st_size
    except zipfile.BadZipFile:
        return "Not a valid zip."
    except ValueError as exc:
        return f"This file can't be read. {exc}"
    except Exception as exc:  # noqa: BLE001 - a file from outside
        return f"This file can't be read ({exc})."
    return {
        "gmap": label,
        "module": module,
        "moduleBytes": raw,
        "pictures": pictures,
        "wires": wires,
        "outputs": outputs,
        "outputPictures": output_pictures,
        "madeBy": " ".join(str(label.get("madeBy") or "").split()),
        "note": str(label.get("note") or "").strip(),
        "modes": _label_modes(label, wires),
        "bytes": size,
    }


def _label_modes(label: dict, wires: object) -> list[str]:
    """The modes whose wires the file holds: its label's, else its wires'."""
    named = label.get("modes")
    if isinstance(named, list):
        return [str(m) for m in named]
    if isinstance(wires, dict):
        return [_mode_name(m) for m in wires.get("modes") or []]
    return []


# --- import ---------------------------------------------------------------------


def _result(
    key: str = "",
    error: str = "",
    folder: Path | None = None,
    written: list[tuple[Path, bytes | None]] | None = None,
) -> dict:
    return {
        "key": key,
        "error": error,
        "folder": folder,
        "written": list(written or []),
    }


def _folder_of(name: str, guid: str, key: str) -> Path | None:
    """The folder this device already has here, by its id alone: another
    id while a twin of its name is connected is still its own id, never
    the connected twin's folder (store.guid_filter would call it stale)."""
    if store.stored_guid_key(guid):
        return store.dir_of_id(key)
    return store.device_dir(name, guid)


def _new_folder(
    name: str, guid: str, key: str, existing: Path | None
) -> tuple[Path, Path | None]:
    """The device folder to unpack into and the folder made for it (None:
    it was there). A device with an id gets a folder of its own by that id
    ("(2)" when its name is taken, 03 S132); its device.json names the
    device, not the folder, so a twin finds it by name and id."""
    if existing is not None and existing.is_dir():
        return existing, None
    if not store.stored_guid_key(guid):
        created = existing is None or not existing.is_dir()
        base = store.ensure_device_dir(name, guid)
        return base, (base if created else None)
    base = store.folder() / store.unique_name(store.folder_name_for(name), key)
    base.mkdir(parents=True, exist_ok=True)
    store._write_id(base, key, name)
    return base, base


def import_device(
    zip_path: Path,
    target_name: str = "",
    target_guid: str = "",
    pieces: dict | None = None,
) -> dict:
    """Export / Import Device's "As a new device" (D-FIXLIST-B2): unpacks a
    .gmap into a new device folder. The device is target_name/target_guid,
    else the one the file was exported from. A folder name taken by another
    device gets "(2)" (03 S132); a device that already has a module file is
    refused (nothing is replaced).

    pieces (None: everything in the file): the window's ticks.
    "module": the module document to write (built from the ticked module,
    map and print pieces); None: no module file; absent: the file's own.
    "pictures": the picture files to write; absent: the ones the written
    module names. The bindings are not written here: the Device Pack's
    import_as_new puts them in afterwards (apply_zip), and the whole import
    (folder and wires) is one Undo Import step (user decision 3a,
    2026-10-11).

    Returns {"key": the device's id key ("" when refused), "error": "" or
    why not (or what was left out), "folder": the folder this import made
    (None: it was there already, or none was made), "written": every file
    it wrote as (path, None) (none was there before)}."""
    loaded = read_gmap(Path(zip_path))
    if isinstance(loaded, str):
        return _result(error=loaded)
    label = loaded["gmap"]
    name = " ".join(
        str(target_name or label.get("deviceName") or label.get("device") or "").split()
    )
    if not name:
        return _result(error="This file has no device name.")
    guid = str(target_guid or "").strip()
    if not guid and not target_name:
        exported = str(label.get("id") or "").strip()
        guid = braced_guid(exported) if guid_like(exported) else ""
    key = store.id_key(name, guid)
    if not has_folder(label):
        # Only bindings (a Device Library setup of a stick with no module
        # file): no device folder is made; the caller puts the bindings in.
        return _result(key)
    existing = _folder_of(name, guid, key)
    if existing is not None and store.module_file_in(existing).is_file():
        return _result(
            error=(
                f"Nothing was imported: {store.shown_name_of(name, guid)} already "
                f"has a device folder, {existing.name}. Delete it first, or import "
                "the file onto another device."
            )
        )
    if pieces is not None and "module" in pieces:
        doc = pieces.get("module")
        write_module = isinstance(doc, dict)
        raw = b""
    else:
        doc = loaded["module"]
        write_module = True
        raw = loaded["moduleBytes"]
    if pieces is not None and "pictures" in pieces:
        wanted = {str(p) for p in pieces.get("pictures") or []}
    elif pieces is None or (write_module and doc is None):
        wanted = set(loaded["pictures"])
    elif isinstance(doc, dict):
        wanted = {_picture_name(store.normal_ref(r)) for r in store.named_refs(doc)}
    else:
        wanted = set()
    files = {f: data for f, data in loaded["pictures"].items() if f in wanted}
    try:
        base, made = _new_folder(name, guid, key, existing)
    except OSError as exc:
        return _result(error=f"The device folder could not be made: {exc}.")
    pictures = base / store.PICTURES
    # Every file this import writes, for Undo Import (none was there before).
    written: list[tuple[Path, bytes | None]] = []
    try:
        for file, data in files.items():
            written.append((pictures / file, None))
            store.put_picture_at(pictures / file, data)
        if write_module:
            written.append((store.module_file_in(base), None))
            if doc is None:
                # Exported damaged (keep_damaged): its bytes as they were.
                store.write_file(store.module_file_in(base), raw)
            else:
                doc = dict(doc)
                doc["device"] = name
                if guid:
                    doc["boundGuidLocal"] = guid
                store.replace(
                    store.module_file_in(base),
                    (json.dumps(doc, indent=2) + "\n").encode("utf-8"),
                    _WHO,
                )
    except (OSError, module_file.ModuleFileDamaged) as exc:
        return _result(
            error=f"The device folder {base.name} could not be written: {exc}.",
            folder=made,
            written=written,
        )
    return _result(key, "", made, written)


# --- templates (.gtemplate) -----------------------------------------------------


def _read_template_doc(data: bytes) -> dict | None:
    try:
        doc = json.loads(data.decode("utf-8"))
    except (ValueError, RecursionError, UnicodeDecodeError):
        return None
    if not isinstance(doc, dict) or not isinstance(doc.get("nodes"), list):
        return None
    return doc if doc["nodes"] else None


def build_gtemplate(name: str) -> bytes:
    """The .gtemplate of a saved template: template.json and the pictures it
    names. Raises OSError when the template can't be read."""
    base = store.template_dir(name)
    path = base / TEMPLATE_JSON
    doc = _read_template_doc(path.read_bytes())
    if doc is None:
        raise OSError(f"{path} is not a template")
    doc, refs = _normal_doc(doc)
    blob = io.BytesIO()
    with zipfile.ZipFile(blob, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(TEMPLATE_JSON, json.dumps(doc, indent=1) + "\n")
        _zip_pictures(zf, base, refs)
    return blob.getvalue()


def _old_picture(ref: str, near: Path) -> Path | None:
    """Where an old plain template's picture is, if it still exists:
    a file: URL or absolute path as it is, else the modules folder or the
    template's own folder."""
    text = str(ref or "").strip()
    if not text:
        return None
    if text.lower().startswith("file:"):
        # The store's reader of file: URLs (the modules package doesn't use
        # the UI's to_local_path).
        candidates = [store._local_path(text)]
    elif Path(text).is_absolute():
        candidates = [Path(text)]
    else:
        candidates = [store.folder() / text, near / text]
    for candidate in candidates:
        try:
            if candidate.is_file():
                return candidate
        except OSError:
            continue
    return None


def _free_template_name(base_name: str) -> str:
    name = base_name
    number = 2
    while (store.template_dir(name) / TEMPLATE_JSON).exists():
        name = f"{base_name} {number}"
        number += 1
    return name


def import_gtemplate(path: Path) -> str:
    """Adds a shared template (.gtemplate, or an old plain .json one) to the
    saved templates; its name, or "" when the file is not a template. A
    taken name gets a number. An old .json template brings whichever of its
    pictures still exist; the rest stay named (shown as missing)."""
    path = Path(path)
    pictures: dict[str, bytes] = {}
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path, "r") as zf:
                if too_big(zf) or TEMPLATE_JSON not in zf.namelist():
                    return ""
                doc = _read_template_doc(zf.read(TEMPLATE_JSON))
                if doc is None:
                    return ""
                for member in zf.namelist():
                    file = _safe_member(member)
                    if file:
                        pictures[file] = zf.read(member)
            doc, _refs = _normal_doc(doc)
        else:
            doc = _read_template_doc(path.read_bytes())
            if doc is None:
                return ""
            mapping: dict[str, str] = {}
            for ref in store.named_refs(doc):
                new_ref = store.normal_ref(ref)
                mapping[ref] = new_ref
                found = _old_picture(ref, path.parent)
                file = _picture_name(new_ref)
                if found is not None and file and file not in pictures:
                    pictures[file] = found.read_bytes()
            replaced = replace_strings(doc, mapping)
            if isinstance(replaced, dict):
                doc = replaced
    except (OSError, zipfile.BadZipFile):
        return ""
    base_name = str(doc.get("name") or path.stem).strip() or "Template"
    name = _free_template_name(base_name)
    doc["name"] = name
    base = store.template_dir(name)
    try:
        for file, data in pictures.items():
            module_file.write_bytes(base / store.PICTURES / file, data)
        module_file.write_bytes(
            base / TEMPLATE_JSON, json.dumps(doc, indent=1).encode("utf-8")
        )
    except OSError:
        return ""
    return name
