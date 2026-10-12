# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterator
from pathlib import Path

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin import (
    clock,
    config,
    device_initialization,
    event_handler,
)
from gremlin import shared_state
from gremlin.shared_state import runtime_active
from gremlin.signal import signal
from gremlin.types import InputType, PropertyType
from gremlin import keyboard as gremlin_keyboard
from gremlin.ui.live_debug import trace
from gremlin.modules.ids import guid_key
from gremlin.modules import ids, module_file, store
from gremlin.modules.claim import (
    claim_friendly,
    key_id,
    kind_of,
    read_claim,
)
from gremlin.modules.registry import (
    is_gremlin_xbox_name,
    is_output_name,
    read_doc,
    vjoy_id_from_name,
)
from gremlin.ui.hardware_profile import (
    PAGE_SIZE,
    HardwareProfile,
    delete_module_file,
    delete_device,
    delete_preview,
    persist_log,
)
from gremlin.modules import hardware

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

# Built-in device rows; upper-case text as already written to module files.
KEYBOARD_GUID = str(ids.KEYBOARD).upper()
OSC_GUID = str(ids.OSC).upper()
XBOX_GUID = str(ids.XBOX).upper()
LOGICAL_GUID = str(ids.LOGICAL_DEVICE).upper()


def osc_friendly_key(uid: str) -> str:
    """Where an OSC input's friendly name is kept in OSC's claim: by its
    permanent uid (D-09-OSC-FILE point 2)."""
    return f"osc:{uid}"


# The window Module Setup's imports (and their Undo) belong to.
_IMPORT_WINDOW = "Configure Module"

_CFG_SECTION = "display"
_CFG_GROUP = "status"
_CFG_HIDDEN = "hidden-slugs"
_CFG_ORDER = "card-order"
_CFG_SHOW_STUBS = "show-stubs"
_CFG_SPLIT = "split-mode"
_CFG_COMPACT = "compact-view"
_CFG_SPLIT_RATIO = "split-ratio"
_CFG_STACKS = "card-stacks"
_CFG_SIZES = "card-sizes"
_CFG_KEPT_STUBS = "kept-stubs"


def _ensure_display_options() -> None:
    cfg = config.Configuration()

    def _reg(name, dtype, initial, desc, props=None, expose: bool = True) -> None:
        try:
            cfg.register(
                _CFG_SECTION,
                _CFG_GROUP,
                name,
                dtype,
                initial,
                desc,
                props or {},
                expose,
            )
        except Exception as exc:
            import logging
            logging.getLogger("system").warning("status option %s: %s", name, exc)

    _reg(_CFG_HIDDEN, PropertyType.String, "", "Ignored Status card slugs (comma separated).", expose=False)
    _reg(
        _CFG_SHOW_STUBS,
        PropertyType.Bool,
        True,
        "Show a card for each device without a module.",
    )
    _reg(_CFG_ORDER, PropertyType.String, "", "Status card order (comma separated slugs).", expose=False)
    _reg(
        _CFG_COMPACT,
        PropertyType.Bool,
        False,
        "Status compact cards: text only, no photo.",
    )
    _reg(
        _CFG_SPLIT,
        PropertyType.String,
        "none",
        "Status split: none, vertical, or horizontal.",
        expose=False,
    )
    _reg(
        _CFG_SPLIT_RATIO,
        PropertyType.Float,
        0.5,
        "Status splitter position (0.2–0.8).",
        {"min": 0.2, "max": 0.8},
        expose=False,
    )
    _reg(_CFG_STACKS, PropertyType.String, "", "Status card stacks (slug+slug|slug).", expose=False)
    _reg(_CFG_SIZES, PropertyType.String, "", "Status card sizes (slug=WxH).", expose=False)
    _reg(
        _CFG_KEPT_STUBS,
        PropertyType.String,
        "",
        "Devices kept visible as stubs after Delete Device.",
        expose=False,
    )


def _write_status(name: str, value) -> None:
    _ensure_display_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, name, value)
    except Exception as exc:
        import logging
        logging.getLogger("system").warning("status save %s: %s", name, exc)


def _hidden_slugs() -> set[str]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_HIDDEN) or "")
    return {p.strip() for p in raw.split(",") if p.strip()}


def _kept_stubs() -> set[str]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_KEPT_STUBS) or "")
    return {p.strip() for p in raw.split(",") if p.strip()}


def _set_kept_stubs(slugs: set[str]) -> None:
    _write_status(_CFG_KEPT_STUBS, ",".join(sorted(slugs)))


def _remember_stub(slug: str) -> None:
    if not slug:
        return
    kept = _kept_stubs()
    if slug in kept:
        return
    kept.add(slug)
    _set_kept_stubs(kept)


def _show_unconfigured(
    slug: str, saved: bool, show_stubs: bool, kept: set[str], released: set[str]
) -> bool:
    """Whether a device's card shows. Reads only: a kept card whose device
    has a module again goes into released, written after the reload."""
    if saved:
        if slug in kept:
            released.add(slug)
        return True
    return show_stubs or slug in kept


def _set_hidden(slugs: set[str]) -> None:
    _ensure_display_options()
    _write_status(_CFG_HIDDEN, ",".join(sorted(slugs)))


def collect_bound_names(
    source_guid_to_name: dict[str, str],
    dest_vjoy_to_name: dict[int, str],
    xbox_name: str,
    maps: list[tuple[str, str, int]],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    """Group profile wires into unique device names per source GUID and dest key."""
    src_bound: dict[str, list[str]] = {}
    dest_bound: dict[str, list[str]] = {}

    def add(bucket: dict[str, list[str]], key: str, value: str) -> None:
        if not key or not value:
            return
        items = bucket.setdefault(key, [])
        if value not in items:
            items.append(value)

    for guid, kind, dest_id in maps:
        src_name = source_guid_to_name.get(guid, "")
        if kind == "xbox":
            dest_name = xbox_name or "Xbox 360 Controller"
            dest_key = "xbox"
        else:
            dest_name = dest_vjoy_to_name.get(int(dest_id), f"vJoy {dest_id}")
            dest_key = f"vjoy:{int(dest_id)}"
        add(src_bound, guid, dest_name)
        add(dest_bound, dest_key, src_name)
    return src_bound, dest_bound


def _profile_wire_maps() -> list[tuple[str, str, int]]:
    try:
        from gremlin import shared_state
        from gremlin.ui.input_pairing import _maps_for_item
    except Exception:
        return []
    profile = getattr(shared_state, "current_profile", None)
    if profile is None:
        return []
    out: list[tuple[str, str, int]] = []
    for uid, items in (getattr(profile, "inputs", None) or {}).items():
        guid = guid_key(uid)
        for item in items or []:
            try:
                mapped = _maps_for_item(item)
            except Exception:
                continue
            for vjoy_id, vtype, _hid in mapped:
                kind = "xbox" if vtype is None else "vjoy"
                try:
                    out.append((guid, kind, int(vjoy_id)))
                except (TypeError, ValueError):
                    continue
    return out


def _raw(row: object) -> str:
    """The card's device name as its module file and vJoy number know it;
    the shown name may be the user's own (10 S7)."""
    return str(getattr(row, "raw_name", "") or getattr(row, "name", "") or "")


def _shown(key: str, raw: str) -> str:
    """The user's name for the device, else its own (10 S7): the one owner,
    gremlin.device_aliases, as the device list and editors use."""
    from gremlin import device_aliases

    return device_aliases.display_name(key, raw) if key else raw


def apply_bound_targets(rows: list) -> None:
    guid_to_name = {
        guid_key(getattr(row, "guid", "")): getattr(row, "name", "")
        for row in rows
        if getattr(row, "direction", "") == "source"
    }
    vjoy_to_name: dict[int, str] = {}
    xbox_name = ""
    for row in rows:
        if getattr(row, "direction", "") != "dest":
            continue
        name = str(getattr(row, "name", "") or "")
        raw = _raw(row)
        tab = str(getattr(row, "tab", "") or "")
        if tab == "xbox" or is_gremlin_xbox_name(raw):
            xbox_name = name
            continue
        vjoy_id = vjoy_id_from_name(raw)
        if vjoy_id:
            vjoy_to_name[vjoy_id] = name
    src_bound, dest_bound = collect_bound_names(
        guid_to_name, vjoy_to_name, xbox_name, _profile_wire_maps()
    )
    for row in rows:
        direction = getattr(row, "direction", "")
        raw = _raw(row)
        tab = str(getattr(row, "tab", "") or "")
        if direction == "source":
            names = src_bound.get(guid_key(getattr(row, "guid", "")), [])
        elif tab == "xbox" or is_gremlin_xbox_name(raw):
            names = dest_bound.get("xbox", [])
        else:
            vjoy_id = vjoy_id_from_name(raw)
            names = dest_bound.get(f"vjoy:{vjoy_id}", []) if vjoy_id else []
        # Spaces kept in a module file's name ("EVO OT L  ") don't show.
        row.target = ", ".join(" ".join(str(n).split()) for n in names)


def _order_slugs() -> list[str]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_ORDER) or "")
    return [p.strip() for p in raw.split(",") if p.strip()]


def _set_order(slugs: list[str]) -> None:
    _ensure_display_options()
    _write_status(_CFG_ORDER, ",".join(slugs))


def _merged_order(saved: list[str], showing: list[str]) -> list[str]:
    """The card order to save: the showing cards in their given order, and
    each saved card that isn't showing (a stick unplugged) kept in its saved
    place, so it comes back there. Showing cards new to the order go last."""
    here = set(showing)
    queue = iter(showing)
    out: list[str] = []
    for slug in dict.fromkeys(saved):
        if slug not in here:
            out.append(slug)
            continue
        out.append(next(queue))
    out.extend(queue)
    return out


def _renamed_cards(order: list[str], rows: list, hidden: set[str]) -> dict[str, str]:
    """Each renamed stick's old card key -> its new one. A card is named
    after its device; a renamed stick's folder (found by its id, 03 S130)
    still records the name it was saved under, which is its old card's.
    Only the folder holding this stick's id counts, and only an old card
    that isn't showing or hidden and a new one the order doesn't hold yet."""
    showing = {row.slug for row in rows}
    out: dict[str, str] = {}
    for row in rows:
        if row.direction != "source" or row.tab != "physical" or row.slug in order:
            continue
        if not row.guid:
            continue
        try:
            found = store.dir_of_id(row.guid)
            if found is None:
                continue
            doc = read_doc(store.module_file_in(found)) or {}
            saved_as = str(doc.get("boundName") or doc.get("device") or "")
            old = store.card_key(saved_as) if saved_as.strip() else ""
        except Exception:
            continue
        if not old or old == row.slug or old not in order:
            continue
        if old in showing or old in hidden or old in out:
            continue
        out[old] = row.slug
    return out


def _renamed_into_order(order: list[str], renamed: dict[str, str]) -> list[str]:
    """The card order with each renamed stick in its old card's place.
    Without this the old card's place stayed in the order for good and the
    stick went last."""
    return [renamed.get(slug, slug) for slug in order]


def _carry_renamed_layout(renamed: dict[str, str]) -> None:
    """A renamed stick keeps its old card's size and stack, as it keeps its
    place (_renamed_into_order). Written only when something moved."""
    if not renamed:
        return
    sizes = _sizes()
    moved = {renamed.get(slug, slug): dim for slug, dim in sizes.items()}
    for old, new in renamed.items():
        if old in sizes and new in sizes:
            moved[new] = sizes[new]
    if moved != sizes:
        _set_sizes(moved)
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_STACKS) or "")
    parts = (part.split("+") for part in raw.split("|"))
    groups = [g for g in ([s.strip() for s in p if s.strip()] for p in parts) if g]
    carried = [[renamed.get(s, s) for s in g] for g in groups]
    if carried != groups:
        _write_status(_CFG_STACKS, "|".join("+".join(g) for g in carried))


def _sizes() -> dict[str, tuple[int, int]]:
    _ensure_display_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SIZES) or "")
    out: dict[str, tuple[int, int]] = {}
    for part in raw.split(","):
        part = part.strip()
        if "=" not in part or "x" not in part:
            continue
        slug, dim = part.split("=", 1)
        try:
            w_s, h_s = dim.lower().split("x", 1)
            w, h = int(w_s), int(h_s)
        except ValueError:
            continue
        if slug.strip() and w > 0 and h > 0:
            out[slug.strip()] = (w, h)
    return out


def _set_sizes(sizes: dict[str, tuple[int, int]]) -> None:
    packed = ",".join(f"{slug}={w}x{h}" for slug, (w, h) in sizes.items())
    _write_status(_CFG_SIZES, packed)


# Pictures Import Image takes as they are; anything else is saved as .jpg.
_PHOTO_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp")


def _local_file(source: str) -> Path | None:
    """A picked file (a file: URL or a plain path) as a local path."""
    text = str(source or "").strip()
    if not text:
        return None
    url = QtCore.QUrl(text)
    path = Path(url.toLocalFile()) if url.isLocalFile() else Path(text)
    return path if path.is_file() else None


# Module Setup's edit (HardwareProfile.beginEditFor(name, "setup")).
_SETUP_EDIT = "setup"


def import_photo(device_name: str, guid: str, source: str) -> str:
    """The Logical Device card's Add/Change Image (03 S88), outside any
    edit: copies the picture into the device's own folder as
    pictures/photo.<ext> (any other photo.* there goes) and returns its
    reference for the device's photo (store.set_device_photo), or "" when nothing was
    copied. A damaged module file is refused before any picture is
    touched (03 S64). (Module Setup's Import Image keeps its picture in
    the window's edit instead: HardwareProfile.keepPhoto.)"""
    name = " ".join(str(device_name or "").split())
    src = _local_file(source)
    if not name or src is None:
        return ""
    path = store.module_file(name, guid)
    reason = store.damage_of(path)
    if reason:
        trace("SAVE", "Configure Module", "importImage", path, "damaged")
        module_file.report_refused(module_file.ModuleFileDamaged(path, reason))
        return ""
    ext = src.suffix.lower()
    if ext not in _PHOTO_EXT:
        ext = ".jpg"
    as_name = f"photo{ext}"
    dest = store.pictures_dir(name, guid) / as_name
    try:
        if dest.is_file() and dest.resolve() == src.resolve():
            return store.picture_ref(as_name)
    except OSError:
        return ""
    try:
        ref = store.put_picture(name, guid, src, as_name)
    except OSError as exc:
        _plog("import image failed", name=name, error=exc)
        trace("SAVE", "Configure Module", "importImage", dest, "error")
        return ""
    pictures = store.pictures_dir(name, guid)
    others = [p for p in pictures.glob("photo.*") if p.is_file() and p.name != as_name]
    try:
        store.remove_picture_files(others)
    except OSError:
        pass
    trace("SAVE", "Configure Module", "importImage", dest, "ok")
    return ref


# Home's Undo / Redo (01 S143, D-FIXLIST-B1 10): about 50 steps of the card
# layout, kept until the program closes; another profile clears them.
_HOME_STEPS = 50
_HOME_LAYOUT_KEYS = (_CFG_ORDER, _CFG_STACKS, _CFG_SIZES, _CFG_COMPACT, _CFG_SPLIT)


def _logical_picture() -> dict:
    """The Logical Device card's picture as Undo keeps it: its photo files
    (name -> bytes, so Undo of Remove Image brings the file back) and the
    bottom background picture node with its place in the map."""
    from gremlin import logical_device_file

    files: dict[str, bytes] = {}
    for path in store.photo_files("Logical Device", LOGICAL_GUID):
        try:
            files[path.name] = path.read_bytes()
        except OSError:
            continue
    doc = store.read_path(logical_device_file.path())
    ref = store.device_photo_ref(doc)
    node, index = None, 0
    nodes = doc.get("nodes")
    if ref and isinstance(nodes, list):
        for at, item in enumerate(nodes):
            if (
                store.is_background(item)
                and store.normal_ref(str(item.get("src") or "")) == ref
            ):
                node, index = json.loads(json.dumps(item)), at
                break
    return {"files": files, "node": node, "index": index}


def _put_logical_picture(saved: dict) -> None:
    """Puts the Logical Device card's picture back as _logical_picture()
    kept it. Raises OSError."""
    from gremlin import logical_device_file

    keep: dict[str, bytes] = saved.get("files") or {}
    for name, data in keep.items():
        dest = store.pictures_dir("Logical Device", LOGICAL_GUID) / name
        try:
            if dest.is_file() and dest.read_bytes() == data:
                continue
        except OSError:
            pass
        store.put_picture("Logical Device", LOGICAL_GUID, data, name)
    path = logical_device_file.path()
    node = saved.get("node")

    def change(doc: dict) -> None:
        store.set_device_photo(doc, "", path.parent)
        if node is not None:
            nodes = doc.setdefault("nodes", [])
            at = max(0, min(int(saved.get("index") or 0), len(nodes)))
            nodes.insert(at, json.loads(json.dumps(node)))

    store.update_path(path, change, "Home")
    now = store.photo_files("Logical Device", LOGICAL_GUID)
    _remove_pictures_soon([p for p in now if p.name not in keep])


def _remove_pictures_soon(paths: list[Path]) -> None:
    """Deletes picture files, waiting up to a second for one still open: the
    card's picture is read on another thread just after an Undo shows it,
    and Windows refuses to delete a file being read. Raises OSError."""
    deadline = clock.monotonic() + 1.0
    while True:
        try:
            store.remove_picture_files(paths)
            return
        except PermissionError:
            if clock.monotonic() > deadline:
                raise
            clock.sleep(0.025)


def _takes_image(row: ModuleRow) -> bool:
    """Input module cards (stick, Keyboard, OSC) have Add / Change / Remove
    Image for the device image (03 S88, D-03-DEVICE-IMAGE). Output cards
    have none; the Logical Device card keeps its own picture items."""
    return row.direction == "source" and row.slug != "logical"


def _image_state(device_name: str, guid: str) -> dict:
    """A device's image as Home Undo keeps it: the module file's
    reference and the image file's bytes (so Undo of Remove Image brings
    the file back)."""
    path = store.module_file(device_name, guid)
    doc = (read_doc(path) or {}) if path.is_file() else {}
    ref = store.normal_ref(store.device_image_ref(doc))
    files: dict[str, bytes] = {}
    found = store.find_picture(path.parent, ref) if ref else None
    if found is not None:
        try:
            files[found.name] = found.read_bytes()
        except OSError:
            pass
    return {"name": device_name, "guid": guid, "ref": ref, "files": files}


def _put_image_state(saved: dict) -> None:
    """Puts a device's image back as _image_state() kept it: its file, the
    module file's key (one write through the store, so History has it),
    and drops the image file the state doesn't name. Raises OSError."""
    name, guid = str(saved.get("name") or ""), str(saved.get("guid") or "")
    ref = str(saved.get("ref") or "")
    pictures = store.pictures_dir(name, guid)
    for file_name, data in (saved.get("files") or {}).items():
        dest = pictures / file_name
        try:
            if dest.is_file() and dest.read_bytes() == data:
                continue
        except OSError:
            pass
        store.put_picture_at(dest, data)
    path = store.module_file(name, guid)
    old: list[str] = []

    def change(doc: dict) -> object:
        old.append(store.normal_ref(store.device_image_ref(doc)))
        if old[0] == ref:
            return False
        if ref:
            doc[store.DEVICE_IMAGE_KEY] = ref
        else:
            doc.pop(store.DEVICE_IMAGE_KEY, None)
        return None

    store.update_path(path, change, "Home")
    if old and old[0] and old[0] != ref:
        gone = store.find_picture(path.parent, old[0])
        doc = read_doc(path) or {}
        named = {store.normal_ref(r) for r in store.named_refs(doc)}
        if gone is not None and old[0] not in named:
            _remove_pictures_soon([gone])


def _plog(action: str, **parts: object) -> None:
    detail = " ".join(f"{key}={value!r}" for key, value in parts.items())
    persist_log(f"Persist {action} {detail}")


def _clamp_size(w: int, h: int) -> tuple[int, int]:
    return (
        max(220, min(1080, int(w))),
        max(140, min(780, int(h))),
    )


def _show_stubs() -> bool:
    _ensure_display_options()
    return bool(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SHOW_STUBS))


def _osc_address(guid: str, kind: str, hid: int) -> str:
    """An OSC input's address ("/fire"), its name when the user gave none;
    "" for any other device."""
    if guid_key(guid) != guid_key(ids.OSC):
        return ""
    try:
        from gremlin.modules.claim import type_of
        from gremlin.osc_persist import osc_address

        return osc_address(type_of(kind), hid)
    except Exception:  # noqa: BLE001 - no OSC rows: the plain name
        return ""


def _load_module_doc(device_name: str, guid: str = "") -> dict:
    """The device's module file, from the store ({} when missing or
    damaged). Pass the device's id: twins share a name (decision F4)."""
    path = store.module_file(device_name, guid)
    if not path.is_file():
        _plog("load miss", name=device_name, guid=guid, path=str(path))
        return {}
    # One reader for every module file: a damaged one (not UTF-8 too) reads
    # as {} here; it used to stop Home, the Run lists and the card polling.
    data = read_doc(path)
    if data is None:
        _plog("load bad", name=device_name, guid=guid, path=str(path))
        return {}
    claim = data.get("claim") if isinstance(data.get("claim"), dict) else {}
    _plog(
        "load",
        name=device_name,
        guid=guid,
        path=str(path),
        buttons=len(claim.get("buttons") or []),
        axes=len(claim.get("axes") or []),
        hats=len(claim.get("hats") or []),
        nodes=len(data.get("nodes") or []) if isinstance(data.get("nodes"), list) else 0,
        view="view" in data,
    )
    return data


_DEFAULT_VIEW = {
    "layout": "pads_meters_grid",
    "padAX": 1,
    "padAY": 2,
    "padBX": 4,
    "padBY": 5,
    "showPads": True,
    "showHats": True,
    "showMeters": True,
    "meterStyle": "vertical",
    "meterWidth": 22,
    "meters": [],
    "buttonStyle": "tile",
    "buttonSize": "medium",
    "buttonColumns": 12,
    "buttonWidth": 64,
    # Colors: "" follows Dark mode; a value is the user's own choice.
    "colorLive": "",
    "colorMeter": "",
    "colorPress": "",
    "colorScreen": "#00000000",
    "screenImage": "",
}


def _module_damage(device_name: str, guid: str = "") -> str:
    """Why the device's module file can't be read ("" when it is fine)."""
    return store.damage(device_name, guid)


def _device_connected(guid: str, name: str = "") -> bool:
    """Whether the device is plugged in now: one rule for the whole program
    (hardware.plugged_in, 03 S90a), by its id, never by its name; the name
    only marks a vJoy or Xbox output, which is always there."""
    return hardware.plugged_in(guid, name)


def _unplugged_reason(device_name: str) -> str:
    """Why Module Setup's Save is refused while the device is unplugged,
    whether it was unplugged before or after the setup opened (03 S46)."""
    return (
        f"Plug in {device_name or 'the device'} to change its setup. "
        "Nothing was saved."
    )


def _typing_in_a_text_box() -> bool:
    """True while a text box of this program has the keyboard focus (a
    friendly name being typed): those keys are text, not presses for
    Keyboard Module Setup (03 Q16). The keyboard hook sees every key."""
    if not isinstance(QtCore.QCoreApplication.instance(), QtGui.QGuiApplication):
        return False
    focus = QtGui.QGuiApplication.focusObject()
    if focus is None:
        return False
    return bool(focus.inherits("QQuickTextInput") or focus.inherits("QQuickTextEdit"))


def module_exists(device_name: str, guid: str = "") -> bool:
    """The device has a module file (pass its id: twins share a name)."""
    return store.exists(device_name, guid)


class ModuleRow:
    __slots__ = (
        "slug",
        "name",
        "raw_name",
        "guid",
        "direction",
        "status",
        "bus",
        "buttons",
        "axes",
        "hats",
        "photo",
        "is_stub",
        "is_module",
        "tab",
        "target",
        "vid",
        "pid",
        "last_friendly",
        "last_hardware",
        "damaged",
        "name_key",
        "vjoy_id",
        "cant_send_count",
        "cant_send_tip",
        "has_image",
    )

    def __init__(self) -> None:
        self.slug = ""
        # The shown name: the user's name for the device, else raw_name
        # (10 S7, D-01-OWNER-NOTICES 2a). raw_name names its module file.
        self.name = ""
        self.raw_name = ""
        # The key its user-given name is kept under (device id, or
        # "keyboard", "osc", "xbox", "logical").
        self.name_key = ""
        self.guid = ""
        self.direction = "source"
        self.status = "Stub"
        # Why the device's module file can't be read ("" when it is fine).
        self.damaged = ""
        self.bus = "DirectInput"
        self.buttons = 0
        self.axes = 0
        self.hats = 0
        self.photo = ""
        self.is_stub = True
        self.is_module = False
        self.tab = "physical"
        self.target = ""
        self.vid = ""
        self.pid = ""
        self.last_friendly = ""
        self.last_hardware = ""
        # The vJoy number of a vJoy card (0: any other card).
        self.vjoy_id = 0
        # Its Map to vJoy bindings that can't be sent (D-05-CANT-SEND).
        self.cant_send_count = 0
        self.cant_send_tip = ""
        # An input card's device has a device image (D-03-DEVICE-IMAGE).
        self.has_image = False


_DAMAGED_STATUS = "Module file damaged – inputs blocked"

# A card's can't-be-sent tip lists this many bindings, then "… and n more".
_CANT_SEND_TIP_LIMIT = 10


def cant_send_line(count: int) -> str:
    """The card's red line (glossary): "" when every binding can be sent."""
    if count <= 0:
        return ""
    return f"⚠ {count} binding{'' if count == 1 else 's'} can't be sent"


def cant_send_tip(items: list[dict]) -> str:
    """The first ten as "<input> (<mode>) → <text>", then "… and n more"."""
    lines = [
        f"{item.get('input_label', '')} ({item.get('mode', '')})"
        f" → {item.get('text', '')}"
        for item in items[:_CANT_SEND_TIP_LIMIT]
    ]
    if len(items) > _CANT_SEND_TIP_LIMIT:
        lines.append(f"… and {len(items) - _CANT_SEND_TIP_LIMIT} more")
    return "\n".join(lines)


def apply_cant_send(rows: list) -> list[int]:
    """Sets each card's can't-be-sent count and tip from the profile's Map
    to vJoy bindings, by the binding's source device id (D-05-CANT-SEND).
    Returns the indexes of the cards that changed."""
    from gremlin.modules.output import cant_send_bindings

    groups: dict[str, list[dict]] = {}
    for item in cant_send_bindings():
        groups.setdefault(guid_key(item.get("device_guid")), []).append(item)
    changed: list[int] = []
    for idx, row in enumerate(rows):
        items = groups.get(guid_key(row.guid), []) if row.direction == "source" else []
        count, tip = len(items), cant_send_tip(items)
        if (count, tip) != (row.cant_send_count, row.cant_send_tip):
            row.cant_send_count, row.cant_send_tip = count, tip
            changed.append(idx)
    return changed


def _card_status(row: ModuleRow) -> str:
    """A card's status, one rule for a full reload and a refresh in place:
    damaged, a vJoy another program holds (03 S34), or what the card is."""
    if row.damaged:
        return _DAMAGED_STATUS
    if row.direction == "dest":
        if row.vjoy_id:
            from gremlin.modules.output import vjoy_in_use_elsewhere

            if vjoy_in_use_elsewhere(row.vjoy_id):
                return "In use by another program"
        return "Virtual"
    return "Connected" if row.is_module else "Stub"


def _set_claimed_counts(row: ModuleRow, doc: dict | None) -> None:
    """A card with a module file shows its claimed counts, 0 for a kind
    with nothing claimed (03 S78, Q8)."""
    claim = read_claim(doc or {})
    row.buttons = len(claim["buttons"])
    row.axes = len(claim["axes"])
    row.hats = len(claim["hats"])


def reset_all_card_sizes() -> None:
    """Back to the default size for every card. Home cards follow on configChanged."""
    _set_sizes({})
    signal.configChanged.emit()


@ta.QmlElement
class CardSizes(QtCore.QObject):
    """Card size reset for pages that do not show the cards (Options)."""

    @QtCore.Slot()
    def resetAll(self) -> None:
        reset_all_card_sizes()


# The keys the Device Mapping Editor writes as its map (its "ui" block is saved on its
# own and is not part of an edit).
# The device's photo is the bottom background layer in "nodes" (07 S127).
_MAP_KEYS = ("nodes",)


def map_parts(device_name: str, guid: str = "") -> str:
    """The map parts of the device's module file (map and photo) as one
    string: it changes when another window changes them (07 Q6). "" when
    the file is missing or damaged."""
    if not device_name:
        return ""
    doc = store.read(device_name, guid)
    if not doc:
        return ""
    return json.dumps({key: doc.get(key) for key in _MAP_KEYS}, sort_keys=True)


@ta.QmlElement
class ModuleFileWatch(QtCore.QObject):
    """Lets the Device Mapping Editor see that its module file was changed elsewhere
    (History Restore, Device Pack, Module Setup): outside Edit it reloads,
    in Edit its Save asks Keep mine / Take theirs (07 Q6, GL-071).
    changed follows the store's notice (D-01-OWNER-NOTICES 6b); files edited
    outside the program are not followed (7a)."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        # path -> ((mtime_ns, size), parts): read only when the file changed.
        self._seen: dict[str, tuple[tuple[int, int], str]] = {}
        signal.moduleFilesChanged.connect(self._files_changed)

    @QtCore.Slot()
    def _files_changed(self) -> None:
        self.changed.emit()

    @QtCore.Slot(str, str, result=str)
    def mapParts(self, device_name: str, guid: str) -> str:
        if not device_name:
            return ""
        path = store.module_file(device_name, guid)
        try:
            stat = path.stat()
        except OSError:
            self._seen.pop(str(path), None)
            return ""
        stamp = (stat.st_mtime_ns, stat.st_size)
        cached = self._seen.get(str(path))
        if cached is not None and cached[0] == stamp:
            return cached[1]
        parts = map_parts(device_name, guid)
        self._seen[str(path)] = (stamp, parts)
        return parts

    @QtCore.Slot(str, str, result=str)
    def deviceIdFor(self, device_name: str, guid: str) -> str:
        """The device's id key, as its History entries hold it (08 S43)."""
        if not device_name:
            return ""
        return store.id_key(device_name, guid)


@ta.QmlElement
class ModuleListModel(QtCore.QAbstractListModel):
    """Status cards: detected hardware stubs plus saved modules."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"slug"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"name"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"rawName"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"guid"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"direction"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"status"),
        QtCore.Qt.ItemDataRole.UserRole + 7: QtCore.QByteArray(b"bus"),
        QtCore.Qt.ItemDataRole.UserRole + 8: QtCore.QByteArray(b"buttons"),
        QtCore.Qt.ItemDataRole.UserRole + 9: QtCore.QByteArray(b"axes"),
        QtCore.Qt.ItemDataRole.UserRole + 10: QtCore.QByteArray(b"hats"),
        QtCore.Qt.ItemDataRole.UserRole + 11: QtCore.QByteArray(b"photo"),
        QtCore.Qt.ItemDataRole.UserRole + 12: QtCore.QByteArray(b"isStub"),
        QtCore.Qt.ItemDataRole.UserRole + 13: QtCore.QByteArray(b"isModule"),
        QtCore.Qt.ItemDataRole.UserRole + 14: QtCore.QByteArray(b"tab"),
        QtCore.Qt.ItemDataRole.UserRole + 15: QtCore.QByteArray(b"target"),
        QtCore.Qt.ItemDataRole.UserRole + 16: QtCore.QByteArray(b"vid"),
        QtCore.Qt.ItemDataRole.UserRole + 17: QtCore.QByteArray(b"pid"),
        QtCore.Qt.ItemDataRole.UserRole + 18: QtCore.QByteArray(b"lastLine"),
        QtCore.Qt.ItemDataRole.UserRole + 19: QtCore.QByteArray(b"lastHardware"),
        QtCore.Qt.ItemDataRole.UserRole + 20: QtCore.QByteArray(b"focused"),
        QtCore.Qt.ItemDataRole.UserRole + 21: QtCore.QByteArray(b"damaged"),
        QtCore.Qt.ItemDataRole.UserRole + 22: QtCore.QByteArray(b"cantSendCount"),
        QtCore.Qt.ItemDataRole.UserRole + 23: QtCore.QByteArray(b"cantSendTip"),
        QtCore.Qt.ItemDataRole.UserRole + 24: QtCore.QByteArray(b"hasImage"),
    }

    lastChanged = QtCore.Signal()
    focusChanged = QtCore.Signal()
    panesChanged = QtCore.Signal()
    claimsChanged = QtCore.Signal()
    # A card's "Driven by" changed (an action added, removed or retargeted).
    targetsChanged = QtCore.Signal()
    # A card's count of bindings that can't be sent changed (D-05-CANT-SEND).
    cantSendChanged = QtCore.Signal()
    # A card's shown name (the user's name for the device) may have changed.
    namesChanged = QtCore.Signal()
    # Home's Undo / Redo steps changed (D-FIXLIST-B1 10).
    stepsChanged = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._rows: list[ModuleRow] = []
        # Home's Undo / Redo: (label, before, after); before and after hold
        # only the parts of the layout one user action changed.
        self._undo_steps: list[tuple[str, dict, dict]] = []
        self._redo_steps: list[tuple[str, dict, dict]] = []
        self._step_depth = 0
        self._divider_before: dict | None = None
        self._steps_profile = id(shared_state.current_profile)
        self._hidden_names: dict[str, str] = {}
        self._focus = ""
        self._last: dict[str, tuple[str, str]] = {}
        self._last_saved_path = ""
        self._hw = HardwareProfile(self)
        _ensure_display_options()
        self._reload_timer = QtCore.QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.setInterval(200)
        self._reload_timer.timeout.connect(self._reload)
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(50)
        self._refresh_timer.timeout.connect(self._refresh_inplace)
        self._dest_snap: dict[str, dict] = {}
        # vJoy id and claim per output card, read once per reload.
        self._dest_targets: dict[str, tuple[int, dict]] = {}
        # Claim per input card: (checked at, file stamp, claim). Input events
        # come hundreds of times a second while sticks move; re-reading and
        # parsing the module file for each one churned memory and CPU.
        self._source_claims: dict[str, tuple[float, tuple[int, int] | None, dict]] = {}
        self._reload()
        event_handler.EventListener().device_change_event.connect(self._schedule_reload)
        from gremlin.modules.runtime import InputModuleRuntime

        InputModuleRuntime().event.connect(self._on_joy)
        self._dest_timer = QtCore.QTimer(self)
        self._dest_timer.setInterval(50)
        self._dest_timer.timeout.connect(self._poll_dest_last)
        self._dest_timer.start()
        signal.profileChanged.connect(self._schedule_reload)
        signal.profileChanged.connect(self._forget_steps_on_switch)
        signal.configChanged.connect(self._schedule_refresh)
        # "Driven by" follows the bindings' owner, input_pairing: one notice
        # per burst of edits, undo and Delete Mode included
        # (D-01-OWNER-NOTICES 1a).
        signal.bindingsChanged.connect(self._follow_bindings)
        # The user's names for devices (10 S7; D-01-OWNER-NOTICES 2a, 3a).
        signal.deviceNamesChanged.connect(self._follow_names)
        # A module file saved, deleted or moved aside: output cards drop
        # their claim copy (D-01-OWNER-NOTICES 6b).
        signal.moduleFilesChanged.connect(self._follow_module_files)
        # A restored Logical Device file (History, Library) may bring its
        # picture back or take it away: the card shows it at once.
        signal.logicalDeviceReloaded.connect(self._logical_reloaded)
        # What can be sent changed (claims, vJoy driver, Xbox, OSC, Logical
        # Device): the output layer's one notice (D-05-CANT-SEND-LIVE).
        signal.cantSendChanged.connect(self._follow_cant_send)
        # Options > Reset all card sizes changes the saved sizes elsewhere;
        # re-read them here so Home cards follow at once.
        self._sizes_snap = _sizes()
        signal.configChanged.connect(self._follow_card_sizes)

    @QtCore.Slot()
    def _follow_card_sizes(self) -> None:
        sizes = _sizes()
        if sizes == self._sizes_snap:
            return
        self._sizes_snap = sizes
        self.panesChanged.emit()

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if role not in self.roles or not index.isValid():
            return None
        row = self._rows[index.row()]
        last_f, last_h = self._last.get(row.slug, (row.last_friendly, row.last_hardware))
        match bytes(self.roles[role]).decode():
            case "slug":
                return row.slug
            case "name":
                return row.name
            case "rawName":
                return row.raw_name
            case "guid":
                return row.guid
            case "direction":
                return row.direction
            case "status":
                return row.status
            case "bus":
                return row.bus
            case "buttons":
                return row.buttons
            case "axes":
                return row.axes
            case "hats":
                return row.hats
            case "photo":
                return row.photo
            case "isStub":
                return row.is_stub
            case "isModule":
                return row.is_module
            case "tab":
                return row.tab
            case "target":
                return row.target
            case "vid":
                return row.vid
            case "pid":
                return row.pid
            case "lastLine":
                return last_f
            case "lastHardware":
                return last_h
            case "focused":
                return row.slug == self._focus
            case "damaged":
                return row.damaged
            case "cantSendCount":
                return row.cant_send_count
            case "cantSendTip":
                return row.cant_send_tip
            case "hasImage":
                return row.has_image
            case _:
                return None

    @QtCore.Slot()
    def reload(self) -> None:
        self._reload()

    @QtCore.Slot(str)
    def setFocus(self, slug: str) -> None:
        if slug == self._focus:
            return
        self._focus = slug
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, 0),
                [QtCore.Qt.ItemDataRole.UserRole + 20],
            )
        self.focusChanged.emit()

    @QtCore.Property(str, notify=focusChanged)
    def focusedSlug(self) -> str:
        return self._focus

    viewChanged = QtCore.Signal()

    @QtCore.Slot(str, str, result=str)
    def viewConfigJson(self, device_name: str, guid: str) -> str:
        doc: dict = {}
        if device_name:
            path = store.module_file(device_name, guid)
            if path.is_file():
                loaded = read_doc(path)
                doc = loaded or {}
                result = "ok" if loaded is not None else "error"
                trace("READ", "Output Configuration", "viewConfigJson", path, result)
            else:
                trace("READ", "Output Configuration", "viewConfigJson", path, "missing")
        view = dict(_DEFAULT_VIEW)
        view["meters"] = list(_DEFAULT_VIEW["meters"])
        raw = doc.get("view")
        if isinstance(raw, dict):
            view.update(raw)
        return json.dumps(view)

    @QtCore.Slot(str, str, str, result=bool)
    def saveViewConfig(self, device_name: str, guid: str, json_text: str) -> bool:
        name = str(device_name or "").strip()
        if not name:
            return False
        try:
            incoming = json.loads(json_text or "{}")
        except json.JSONDecodeError:
            return False
        if not isinstance(incoming, dict):
            return False
        try:
            path = store.module_file_in(store.ensure_device_dir(name, guid))
        except OSError as exc:
            _plog("save view failed", name=name, error=exc)
            return False

        def change(doc: dict) -> None:
            view = dict(_DEFAULT_VIEW)
            view["meters"] = list(_DEFAULT_VIEW["meters"])
            raw = doc.get("view")
            if isinstance(raw, dict):
                view.update(raw)
            view.update(incoming)
            doc["view"] = view
            doc.setdefault("kind", "control.hardware")
            doc.setdefault("device", name)

        _plog("save view", name=name, path=str(path))
        try:
            if not store.update_path(path, change, "Output Configuration"):
                return False
            written = json.loads(path.read_text(encoding="utf-8"))
            trace("SAVE", "Output Configuration", "saveViewConfig", path, "ok")
        except (OSError, json.JSONDecodeError) as exc:
            _plog("save view failed", path=str(path), error=exc)
            trace("SAVE", "Output Configuration", "saveViewConfig", path, "error")
            return False
        if not isinstance(written.get("view"), dict):
            _plog("save view mismatch", path=str(path))
            return False
        self.viewChanged.emit()
        _plog("save view ok", path=str(path))
        self._last_saved_path = str(path)
        return True

    @QtCore.Slot(result=str)
    def lastSavedPath(self) -> str:
        return self._last_saved_path

    @QtCore.Slot(str, result=str)
    def otherDestViews(self, current_name: str) -> str:
        current = str(current_name or "").strip()
        rows = []
        seen = set()
        for row in self._rows:
            if getattr(row, "direction", "") != "dest":
                continue
            name = _raw(row).strip()
            if not name or name.casefold() == current.casefold() or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            # name opens its view; label is what the user calls it (10 S7).
            rows.append({
                "name": name,
                "label": str(getattr(row, "name", "") or name).strip(),
                "guid": str(getattr(row, "guid", "") or ""),
            })
        rows.sort(key=lambda item: item["name"].lower())
        return json.dumps(rows)

    @QtCore.Slot(str)
    def ignoreSlug(self, slug: str) -> None:
        hidden = _hidden_slugs()
        hidden.add(slug)
        _set_hidden(hidden)
        if self._focus == slug:
            self._focus = ""
        self._reload()

    @QtCore.Slot(str)
    def hideSelected(self, slugs_csv: str) -> None:
        """Hide Selected Cards (D-03-HOME-BAND): the listed cards, one step."""
        slugs = {s.strip() for s in (slugs_csv or "").split(",") if s.strip()}
        hidden = _hidden_slugs()
        added = sorted(slugs - hidden)
        if not added:
            return
        _set_hidden(hidden | slugs)
        # Its Undo shows only these cards again; cards hidden another way
        # stay hidden (Hide Card is not a step).
        self._add_step("Hide Selected Cards", {"show": added}, {"hide": added})
        if self._focus in slugs:
            self._focus = ""
        self._reload()
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def unignoreSlug(self, slug: str) -> None:
        hidden = _hidden_slugs()
        hidden.discard(slug)
        _set_hidden(hidden)
        self._reload()

    @QtCore.Slot()
    def unignoreAll(self) -> None:
        hidden = _hidden_slugs()
        if not hidden:
            return
        _set_hidden(set())
        self._reload()

    @QtCore.Slot(result=list)
    def hiddenList(self) -> list[str]:
        return sorted(_hidden_slugs())

    @QtCore.Slot(result=list)
    def hiddenCards(self) -> list[dict[str, str]]:
        """Each hidden card as {slug, name}, by name (Home menu → Hidden
        Cards). A card whose device is not here now shows its stored id."""
        names = self._hidden_names
        cards = [{"slug": s, "name": names.get(s, s)} for s in _hidden_slugs()]
        return sorted(cards, key=lambda c: c["name"].lower())

    @QtCore.Slot(str, str)
    def dropSlugBefore(self, slug: str, before_slug: str) -> None:
        """A card dragged to a new place: out of its stack and moved, as one
        step."""
        with self._home_step("Move Card"):
            self.unstackSlug(slug)
            self._move_slug_before(slug, before_slug)

    def _move_slug_before(self, slug: str, before_slug: str) -> None:
        groups = {g[0]: g for g in self._stacks()}
        stacked = {s for g in groups.values() for s in g}
        leaders: list[str] = []
        for row in self._rows:
            if row.slug in stacked and row.slug not in groups:
                continue
            leaders.append(row.slug)
        if slug not in leaders:
            leaders.append(slug)
        leaders = [s for s in leaders if s != slug]
        if before_slug and before_slug in leaders:
            leaders.insert(leaders.index(before_slug), slug)
        else:
            leaders.append(slug)
        expanded: list[str] = []
        for lead in leaders:
            expanded.extend(groups.get(lead, [lead]))
        # Hidden cards keep their places (they used to be dropped here, while
        # a reload kept them): _merged_order keeps every card not showing.
        _set_order(_merged_order(_order_slugs(), expanded))
        self._reload()
        self.panesChanged.emit()

    @QtCore.Slot(result=int)
    def visibleCount(self) -> int:
        return len(self._rows)

    def _saved_stacks(self) -> list[list[str]]:
        """Every saved stack, with the cards that aren't showing (hidden or
        unplugged): stack edits keep them, as card order does (03 Q10)."""
        _ensure_display_options()
        raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_STACKS) or "")
        groups: list[list[str]] = []
        for part in raw.split("|"):
            group = [s.strip() for s in part.split("+") if s.strip()]
            if len(group) > 1:
                groups.append(group)
        return groups

    def _stacks(self) -> list[list[str]]:
        """The stacks as Home shows them: only cards that are showing."""
        visible = {row.slug for row in self._rows}
        groups: list[list[str]] = []
        for saved in self._saved_stacks():
            group = [s for s in saved if s in visible]
            if len(group) > 1:
                groups.append(group)
        return groups

    def _set_stacks(self, groups: list[list[str]]) -> None:
        _ensure_display_options()
        packed = "|".join("+".join(g) for g in groups if len(g) > 1)
        _write_status(_CFG_STACKS, packed)

    # +---------------------------------------------------------------------
    # | Home's Undo / Redo (01 S143, D-FIXLIST-B1 10). One user action is one
    # | step; Delete Device is not one (History). The keys, the page bar's
    # | Undo / Redo pair and the card menu's header all use these.

    def _home_state(
        self, picture: bool = False, image: tuple[str, str, str] | None = None
    ) -> dict:
        """picture: the Logical Device card's picture; image: (slug, device
        name, guid) of an input card whose device image the step changes."""
        _ensure_display_options()
        cfg = config.Configuration()
        state: dict = {
            key: cfg.value(_CFG_SECTION, _CFG_GROUP, key) for key in _HOME_LAYOUT_KEYS
        }
        state["ratio"] = self._ratio_now()
        if picture:
            state["picture"] = _logical_picture()
        if image is not None:
            slug, name, guid = image
            state["image"] = {"slug": slug, **_image_state(name, guid)}
        return state

    def _ratio_now(self) -> float:
        """The divider's place, as a step keeps it."""
        return round(float(self.splitRatio), 4)  # pyright: ignore[reportArgumentType]

    @contextlib.contextmanager
    def _home_step(
        self,
        label: str,
        picture: bool = False,
        image: tuple[str, str, str] | None = None,
    ) -> Iterator[None]:
        """Records what the block changes as one step (the outermost block
        only: Reset Card Layout's unstack is part of its own step)."""
        if self._step_depth:
            yield
            return
        before = self._home_state(picture, image)
        self._step_depth += 1
        try:
            yield
        finally:
            self._step_depth -= 1
        self._push_step(label, before, self._home_state(picture, image))

    def _push_step(self, label: str, before: dict, after: dict) -> None:
        changed = [key for key in after if before.get(key) != after[key]]
        if not changed:
            return
        self._add_step(
            label, {k: before.get(k) for k in changed}, {k: after[k] for k in changed}
        )

    def _add_step(self, label: str, undo_state: dict, redo_state: dict) -> None:
        """undo_state / redo_state: what _apply_state puts back or redoes."""
        self._undo_steps.append((label, undo_state, redo_state))
        del self._undo_steps[:-_HOME_STEPS]
        self._redo_steps.clear()
        self.stepsChanged.emit()

    def _apply_state(self, state: dict) -> None:
        for key in _HOME_LAYOUT_KEYS:
            if key in state:
                _write_status(key, state[key])
        if "show" in state or "hide" in state:
            hidden = _hidden_slugs() - set(state.get("show") or [])
            _set_hidden(hidden | set(state.get("hide") or []))
        if "ratio" in state:
            from gremlin.ui import window_placement

            try:
                window_placement.save_split("home", float(state["ratio"]))
            except Exception:
                pass
        if "picture" in state:
            try:
                _put_logical_picture(state["picture"])
            except OSError as exc:
                _plog("home undo picture failed", error=exc)
            self._set_card_photo("logical")
        if "image" in state:
            try:
                _put_image_state(state["image"])
            except OSError as exc:
                _plog("home undo image failed", error=exc)
            self._set_card_photo(str(state["image"].get("slug") or ""))
        self._reload()
        signal.configChanged.emit()
        self.panesChanged.emit()

    @QtCore.Slot()
    def undo(self) -> None:
        if not self._undo_steps:
            return
        step = self._undo_steps.pop()
        self._apply_state(step[1])
        self._redo_steps.append(step)
        self.stepsChanged.emit()

    @QtCore.Slot()
    def redo(self) -> None:
        if not self._redo_steps:
            return
        step = self._redo_steps.pop()
        self._apply_state(step[2])
        self._undo_steps.append(step)
        self.stepsChanged.emit()

    @QtCore.Slot()
    def _forget_steps_on_switch(self) -> None:
        """Another profile opened: its Home steps start empty."""
        now = id(shared_state.current_profile)
        if now == self._steps_profile:
            return
        self._steps_profile = now
        self.forgetSteps()

    @QtCore.Slot()
    def forgetSteps(self) -> None:
        if not self._undo_steps and not self._redo_steps:
            return
        self._undo_steps.clear()
        self._redo_steps.clear()
        self.stepsChanged.emit()

    @QtCore.Property(bool, notify=stepsChanged)
    def canUndo(self) -> bool:
        return bool(self._undo_steps)

    @QtCore.Property(bool, notify=stepsChanged)
    def canRedo(self) -> bool:
        return bool(self._redo_steps)

    @QtCore.Slot()
    def beginDivider(self) -> None:
        """The Input / Output divider is picked up: its step starts here."""
        self._divider_before = {"ratio": self._ratio_now()}

    @QtCore.Slot(float)
    def endDivider(self, ratio: float) -> None:
        """The divider is let go: one step from where it was picked up."""
        before = self._divider_before
        self._divider_before = None
        self.setSplitRatio(ratio)
        if before is not None:
            self._push_step(
                "Move Divider", before, {"ratio": self._ratio_now()}
            )

    @QtCore.Property(bool, notify=panesChanged)
    def compactView(self) -> bool:
        try:
            _ensure_display_options()
            return bool(
                config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_COMPACT)
            )
        except Exception:
            return False

    @QtCore.Slot(bool)
    def setCompactView(self, compact: bool) -> None:
        flag = bool(compact)
        if flag == self.compactView:
            return
        with self._home_step("Compact View On" if flag else "Compact View Off"):
            try:
                _ensure_display_options()
                _write_status(_CFG_COMPACT, flag)
            except Exception:
                return
        self.panesChanged.emit()

    @QtCore.Property(str, notify=panesChanged)
    def splitMode(self) -> str:
        try:
            _ensure_display_options()
            raw = str(
                config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SPLIT) or "none"
            ).lower()
        except Exception:
            return "none"
        return raw if raw in ("none", "vertical", "horizontal") else "none"

    @QtCore.Slot(str)
    def setSplitMode(self, mode: str) -> None:
        name = (mode or "none").lower()
        if name not in ("none", "vertical", "horizontal"):
            name = "none"
        if name == self.splitMode:
            return
        shown = {
            "none": "Single list", "vertical": "Side by side", "horizontal": "Stacked"
        }
        with self._home_step(f"Layout: {shown[name]}"):
            try:
                _ensure_display_options()
                _write_status(_CFG_SPLIT, name)
            except Exception:
                return
        self.panesChanged.emit()

    @QtCore.Property(float, notify=panesChanged)
    def splitRatio(self) -> float:
        """The Home page's divider. Kept with the other window layout
        (window_placement); a value saved the old way here is the starting
        point."""
        from gremlin.ui import window_placement

        old = 0.5
        try:
            _ensure_display_options()
            old = float(
                config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SPLIT_RATIO) or 0.5
            )
        except Exception:
            pass
        return min(0.8, max(0.2, window_placement.split_ratio("home", old)))

    @QtCore.Slot(float)
    def setSplitRatio(self, ratio: float) -> None:
        from gremlin.ui import window_placement

        value = min(0.8, max(0.2, float(ratio)))
        if abs(value - self.splitRatio) < 0.001:
            return
        try:
            window_placement.save_split("home", value)
        except Exception:
            return
        self.panesChanged.emit()

    @QtCore.Slot(str, result=list)
    def pileLeaders(self, direction: str) -> list:
        groups = {g[0]: g for g in self._stacks()}
        stacked = {s for g in groups.values() for s in g}
        leaders: list[str] = []
        for row in self._rows:
            if direction and row.direction != direction:
                continue
            if row.slug in stacked and row.slug not in groups:
                continue
            leaders.append(row.slug)
        return leaders

    @QtCore.Slot(str, result=list)
    def pileMembers(self, leader: str) -> list:
        for group in self._stacks():
            if leader in group:
                return group
        return [leader] if leader else []

    @QtCore.Slot(str, result=int)
    def cardWidth(self, slug: str) -> int:
        return int(_sizes().get(slug, (0, 0))[0])

    @QtCore.Slot(str, result=int)
    def cardHeight(self, slug: str) -> int:
        return int(_sizes().get(slug, (0, 0))[1])

    @QtCore.Slot(str, int, int)
    def setPileSize(self, slug: str, width: int, height: int) -> None:
        """A card's size, once its corner is let go (one step)."""
        w, h = _clamp_size(width, height)
        with self._home_step("Resize Card"):
            sizes = _sizes()
            for member in self.pileMembers(slug):
                sizes[member] = (w, h)
            _set_sizes(sizes)
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def resetCardSize(self, slug: str) -> None:
        with self._home_step("Reset Size"):
            sizes = _sizes()
            for member in self.pileMembers(slug):
                sizes.pop(member, None)
            _set_sizes(sizes)
        signal.configChanged.emit()
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def resetSelectedSizes(self, slugs_csv: str) -> None:
        """Reset Size of Selected Cards (D-03-HOME-BAND): each listed card
        and its stack, one step."""
        slugs = [s.strip() for s in (slugs_csv or "").split(",") if s.strip()]
        if not slugs:
            return
        with self._home_step("Reset Size of Selected Cards"):
            sizes = _sizes()
            for slug in slugs:
                for member in self.pileMembers(slug):
                    sizes.pop(member, None)
            _set_sizes(sizes)
        signal.configChanged.emit()
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def clearCardSettings(self, slug: str) -> None:
        with self._home_step("Reset Card Layout"):
            self._clear_card_settings(slug)

    def _clear_card_settings(self, slug: str) -> None:
        """The card's size and stack go (Reset Card Layout, Delete Device:
        only the first is a Home step)."""
        sizes = _sizes()
        sizes.pop(slug, None)
        _set_sizes(sizes)
        self._unstack_slug(slug)
        signal.configChanged.emit()
        self.panesChanged.emit()

    @QtCore.Slot()
    def resetAllCardSizes(self) -> None:
        with self._home_step("Reset All Card Sizes"):
            reset_all_card_sizes()
        self.panesChanged.emit()

    @QtCore.Slot(str, str)
    def stackSelected(self, leader: str, slugs_csv: str) -> None:
        """Stack the listed slugs onto leader. Leader keeps the pile slot."""
        with self._home_step("Stack Selected Cards"):
            self._stack_selected(leader, slugs_csv)

    def _stack_selected(self, leader: str, slugs_csv: str) -> None:
        if not leader:
            return
        names: list[str] = []
        seen: set[str] = set()
        for raw in [leader] + [p.strip() for p in (slugs_csv or "").split(",")]:
            if raw and raw not in seen:
                names.append(raw)
                seen.add(raw)
        dirs = {row.slug: row.direction for row in self._rows}
        lead_dir = dirs.get(leader)
        names = [
            s for s in names
            if s in dirs and (not lead_dir or dirs.get(s) == lead_dir)
        ]
        if leader not in names or len(names) < 2:
            return
        selected = set(names)
        groups = []
        for group in self._saved_stacks():
            rest = [s for s in group if s not in selected]
            if len(rest) > 1:
                groups.append(rest)
        merged = [leader] + [s for s in names if s != leader]
        groups.append(merged)
        self._set_stacks(groups)
        sizes = _sizes()
        shared = sizes.get(leader)
        if not shared:
            for slug in names:
                if slug in sizes:
                    shared = sizes[slug]
                    break
        if shared:
            for member in merged:
                sizes[member] = shared
            _set_sizes(sizes)
        self._reload()
        self.panesChanged.emit()

    @QtCore.Slot(str)
    def unstackSlug(self, slug: str) -> None:
        with self._home_step("Unstack"):
            self._unstack_slug(slug)

    def _unstack_slug(self, slug: str) -> None:
        groups = []
        changed = False
        for group in self._saved_stacks():
            if slug in group:
                rest = [s for s in group if s != slug]
                if len(rest) > 1:
                    groups.append(rest)
                changed = True
            else:
                groups.append(group)
        if changed:
            self._set_stacks(groups)
            self._reload()
            self.panesChanged.emit()

    @QtCore.Slot(str)
    def unstackAll(self, slug: str) -> None:
        with self._home_step("Unstack All"):
            self._unstack_all(slug)

    def _unstack_all(self, slug: str) -> None:
        groups = []
        changed = False
        for group in self._saved_stacks():
            if slug in group:
                changed = True
                continue
            groups.append(group)
        if changed:
            self._set_stacks(groups)
            self._reload()
            self.panesChanged.emit()

    @QtCore.Slot(str)
    def raiseSlug(self, slug: str) -> None:
        groups = []
        changed = False
        for group in self._saved_stacks():
            if slug in group and group[-1] != slug:
                group = [s for s in group if s != slug] + [slug]
                changed = True
            groups.append(group)
        if changed:
            self._set_stacks(groups)
            self._reload()
            self.panesChanged.emit()

    def _row_map(self, row: ModuleRow) -> dict:
        last_f, last_h = self._last.get(row.slug, (row.last_friendly, row.last_hardware))
        return {
            "slug": row.slug,
            "name": row.name,
            "rawName": row.raw_name,
            "guid": row.guid,
            "direction": row.direction,
            "status": row.status,
            "bus": row.bus,
            "buttons": row.buttons,
            "axes": row.axes,
            "hats": row.hats,
            "photo": row.photo,
            "isStub": row.is_stub,
            "isModule": row.is_module,
            "tab": row.tab,
            "target": row.target,
            "vid": row.vid,
            "pid": row.pid,
            "lastLine": last_f,
            "lastHardware": last_h,
            "focused": row.slug == self._focus,
            "damaged": row.damaged,
            "cantSendCount": row.cant_send_count,
            "cantSendTip": row.cant_send_tip,
            "hasPhoto": bool(row.photo),
            "hasImage": row.has_image,
        }

    @QtCore.Slot(str, result="QVariantMap")
    def cardMap(self, slug: str) -> dict:
        for row in self._rows:
            if row.slug == slug:
                return self._row_map(row)
        return {}

    @QtCore.Slot()
    def _logical_reloaded(self) -> None:
        self._set_card_photo("logical")

    def _set_card_photo(self, slug: str) -> None:
        """Reads the card's photo and whether it has a device image again
        (after Add/Change/Remove Image)."""
        for idx, row in enumerate(self._rows):
            if row.slug != slug:
                continue
            row.photo = self._photo(row.raw_name or row.name, row.guid)
            row.has_image = self._has_image(row)
            ix = self.index(idx, 0)
            user = QtCore.Qt.ItemDataRole.UserRole
            self.dataChanged.emit(ix, ix, [user + 11, user + 24])

    @staticmethod
    def _has_image(row: ModuleRow) -> bool:
        """An input card's device has a device image and its file is there."""
        if not _takes_image(row):
            return False
        path = store.module_file(row.raw_name or row.name, row.guid)
        if not path.is_file():
            return False
        ref = store.device_image_ref(read_doc(path) or {})
        return bool(ref) and store.find_picture(path.parent, ref) is not None

    def _image_row(self, slug: str) -> ModuleRow | None:
        """The input card slug names (None: no such card, or not an input
        module card)."""
        row = next((r for r in self._rows if r.slug == slug), None)
        return row if row is not None and _takes_image(row) else None

    @QtCore.Slot(str, str, result=bool)
    def setCardImage(self, slug: str, fileUrl: str) -> bool:
        """Add/Change Image on a card (03 S88). An input module card (stick,
        Keyboard, OSC): the picture becomes the device image, its own file
        named by the module file (store.set_device_image; D-03-DEVICE-IMAGE).
        The Logical Device card: the picture becomes its photo, the bottom
        background picture of its map (07 S127). Both go through the store
        (History, Library, Export and Restore carry it) and are one Home
        Undo step. Output cards and a damaged file: False."""
        if slug != "logical":
            return self._set_input_image(slug, fileUrl)
        from gremlin import logical_device_file

        path = logical_device_file.path()
        reason = store.damage_of(path)
        if reason:
            module_file.report_refused(module_file.ModuleFileDamaged(path, reason))
            return False
        had = store.photo_files("Logical Device", LOGICAL_GUID)
        label = "Change Image" if had else "Add Image"
        with self._home_step(label, picture=True):
            rel = import_photo("Logical Device", LOGICAL_GUID, fileUrl)
            if not rel:
                return False

            def change(doc: dict) -> None:
                store.set_device_photo(doc, rel, path.parent)

            try:
                if not store.update_path(path, change, "Home"):
                    return False
            except OSError:
                return False
        self._set_card_photo(slug)
        return True

    @QtCore.Slot(str, result=bool)
    def removeCardImage(self, slug: str) -> bool:
        """Remove Image. An input module card: its device image goes (the
        key and the file; History and Home Undo keep both). The Logical
        Device card: its photo files go and its bottom background picture
        goes (History keeps both)."""
        if slug != "logical":
            return self._remove_input_image(slug)
        from gremlin import logical_device_file

        path = logical_device_file.path()
        reason = store.damage_of(path)
        if reason:
            module_file.report_refused(module_file.ModuleFileDamaged(path, reason))
            return False
        found = store.photo_files("Logical Device", LOGICAL_GUID)
        # Undo keeps the picture file, so it comes back (D-FIXLIST-B1 10).
        with self._home_step("Remove Image", picture=True):
            try:
                store.remove_picture_files(found)

                def change(doc: dict) -> object:
                    if not store.device_photo_ref(doc):
                        return False
                    store.set_device_photo(doc, "", path.parent)
                    return None

                store.update_path(path, change, "Home")
            except OSError:
                return False
        self._set_card_photo(slug)
        return True

    def _set_input_image(self, slug: str, file_url: str) -> bool:
        """setCardImage for an input module card (D-03-DEVICE-IMAGE)."""
        row = self._image_row(slug)
        src = _local_file(file_url)
        if row is None or src is None:
            return False
        name = row.raw_name or row.name
        label = "Change Image" if self._has_image(row) else "Add Image"
        with self._home_step(label, image=(slug, name, row.guid)):
            try:
                ref = store.set_device_image(name, row.guid, src, "Home")
            except OSError as exc:
                _plog("card image failed", name=name, error=exc)
                ref = ""
        self._set_card_photo(slug)
        return bool(ref)

    def _remove_input_image(self, slug: str) -> bool:
        """removeCardImage for an input module card (D-03-DEVICE-IMAGE)."""
        row = self._image_row(slug)
        if row is None:
            return False
        name = row.raw_name or row.name
        with self._home_step("Remove Image", image=(slug, name, row.guid)):
            try:
                done = store.remove_device_image(name, row.guid, "Home")
            except OSError as exc:
                _plog("card image remove failed", name=name, error=exc)
                done = False
        self._set_card_photo(slug)
        return bool(done)

    @QtCore.Slot()
    def _follow_bindings(self) -> None:
        self._refresh_targets()

    @QtCore.Slot()
    def _follow_names(self) -> None:
        """Cards show the user's name for their device at once (10 S7)."""
        role = QtCore.Qt.ItemDataRole.UserRole + 2
        changed = False
        for idx, row in enumerate(self._rows):
            shown = _shown(row.name_key, row.raw_name)
            if shown != row.name:
                row.name = shown
                changed = True
                at = self.index(idx, 0)
                self.dataChanged.emit(at, at, [role])
        if changed:
            # Driven by lists the other cards by name.
            self._refresh_targets()
        self.namesChanged.emit()

    @QtCore.Slot()
    def _follow_module_files(self) -> None:
        self._refresh_inplace()

    @QtCore.Slot(str, str, result=str)
    def shownName(self, guid: str, raw_name: str) -> str:
        """The name a card shows for its device (the Device Bindings page
        title): the user's name, else raw_name."""
        want = guid_key(guid)
        for row in self._rows:
            if want and guid_key(row.guid) == want and row.raw_name == raw_name:
                return row.name or raw_name
        for row in self._rows:
            if raw_name and row.raw_name == raw_name:
                return row.name or raw_name
        return raw_name

    @QtCore.Slot()
    def _refresh_targets(self) -> None:
        """Works out every card's "Driven by" again from the profile's actions
        and updates the cards whose list changed."""
        before = [row.target for row in self._rows]
        apply_bound_targets(self._rows)
        role = QtCore.Qt.ItemDataRole.UserRole + 15
        changed = False
        for idx, row in enumerate(self._rows):
            if row.target != before[idx]:
                changed = True
                at = self.index(idx, 0)
                self.dataChanged.emit(at, at, [role])
        if changed:
            self.targetsChanged.emit()
        self._refresh_cant_send()

    @QtCore.Slot()
    def _follow_cant_send(self) -> None:
        self._refresh_cant_send()

    def _refresh_cant_send(self) -> None:
        """The can't-be-sent line follows action edits (D-05-CANT-SEND) and
        the output layer's notice (D-05-CANT-SEND-LIVE)."""
        changed = apply_cant_send(self._rows)
        roles = [
            QtCore.Qt.ItemDataRole.UserRole + 22,
            QtCore.Qt.ItemDataRole.UserRole + 23,
        ]
        for idx in changed:
            at = self.index(idx, 0)
            self.dataChanged.emit(at, at, roles)
        if changed:
            self.cantSendChanged.emit()

    @QtCore.Slot(str, result=str)
    def boundLine(self, device_name: str) -> str:
        # Fresh, not as of the last check: the header asks when a page opens.
        self._refresh_targets()
        name = str(device_name or "")
        for row in self._rows:
            if _raw(row) == name:
                target = str(getattr(row, "target", "") or "")
                return "Driven by: [" + (target if target else "nothing") + "]"
        return "Driven by: [nothing]"

    @QtCore.Slot(str, result="QVariantMap")
    def firstCardMap(self, direction: str) -> dict:
        """The first card of that direction ("source" or "dest"), not the
        Xbox output or the Logical Device (they have no Module Setup, 03
        S39, Q7); {} when there is none."""
        for row in self._rows:
            found = self._row_map(row)
            if found.get("direction") != direction:
                continue
            if found.get("bus") == "XInput" or found.get("tab") in ("xbox", "logical"):
                continue
            return found
        return {}

    @QtCore.Slot(result="QVariantMap")
    def focusedCardMap(self) -> dict:
        if self._focus:
            found = self.cardMap(self._focus)
            if found:
                return found
        if self._rows:
            return self._row_map(self._rows[0])
        return {}

    def _schedule_reload(self) -> None:
        self._reload_timer.start()

    @QtCore.Slot()
    def _schedule_refresh(self) -> None:
        self._refresh_timer.start()

    def _refresh_inplace(self) -> None:
        self._dest_targets = {}
        self._source_claims = {}
        if not self._rows:
            self._reload()
            return
        roles = [
            QtCore.Qt.ItemDataRole.UserRole + 2,
            QtCore.Qt.ItemDataRole.UserRole + 6,
            QtCore.Qt.ItemDataRole.UserRole + 8,
            QtCore.Qt.ItemDataRole.UserRole + 9,
            QtCore.Qt.ItemDataRole.UserRole + 10,
            QtCore.Qt.ItemDataRole.UserRole + 11,
            QtCore.Qt.ItemDataRole.UserRole + 12,
            QtCore.Qt.ItemDataRole.UserRole + 13,
        ]
        apply_bound_targets(self._rows)
        roles = roles + [
            QtCore.Qt.ItemDataRole.UserRole + 15,
            QtCore.Qt.ItemDataRole.UserRole + 21,
            QtCore.Qt.ItemDataRole.UserRole + 24,
        ]
        for idx, row in enumerate(self._rows):
            name = row.raw_name or row.name
            row.photo = self._photo(name, row.guid)
            row.has_image = self._has_image(row)
            # By the card's device id: twins share a name (decision F4).
            saved = module_exists(name, row.guid)
            row.is_module = saved
            row.is_stub = not saved
            # Checked again: a file fixed elsewhere (History Restore) is no
            # longer damaged (03 S65). vJoy cards are not checked, as at a
            # full reload.
            row.damaged = (
                _module_damage(name, row.guid) if saved and not row.vjoy_id else ""
            )
            if saved:
                _set_claimed_counts(row, _load_module_doc(name, row.guid))
            row.status = _card_status(row)
            ix = self.index(idx, 0)
            self.dataChanged.emit(ix, ix, roles)
        self.claimsChanged.emit()

    @QtCore.Slot()
    def notifyClaims(self) -> None:
        self._refresh_inplace()

    @QtCore.Slot(str, str, result="QVariantList")
    def moduleFileNames(self, guid: str, device_name: str) -> list:
        """Module Setup's "Import from": the other devices' folders (its
        own isn't listed)."""
        return store.import_choices(device_name, guid) if device_name else []

    @QtCore.Slot(str, str, result=str)
    def moduleFileFor(self, guid: str, device_name: str) -> str:
        """The device's folder name (03 S54), found by its id first: twin
        sticks share a name but not a folder, a renamed stick's folder
        follows it (S3, S131)."""
        if not device_name:
            return ""
        return store.device_dir(device_name, guid).name

    @QtCore.Slot(str, str, result=str)
    def deviceIdFor(self, guid: str, device_name: str) -> str:
        """The device's id key, as its History entries hold it (08 S43)."""
        if not device_name:
            return ""
        return store.id_key(device_name, guid)

    @QtCore.Slot(result=str)
    def mapsFolderUrl(self) -> str:
        """The modules folder (every device's folder is in it)."""
        return store.folder().as_uri()

    @QtCore.Slot(str, str, result=str)
    def importedFolderUrl(self, guid: str, device_name: str) -> str:
        """Where Browse for File opens: the device's imported/ (the files
        imports kept, 03 S58), else its folder, else the modules folder.
        Nothing is created for a device not saved yet."""
        if device_name:
            base = store.device_dir(device_name, guid)
            if base.is_dir():
                imported = store.imported_dir(device_name, guid)
                return (imported if imported.is_dir() else base).as_uri()
        return store.folder().as_uri()

    @QtCore.Slot(str, str, result=bool)
    def moduleFileExists(self, guid: str, device_name: str) -> bool:
        """True when the device's folder holds its module file; False is
        Module Setup's "(not saved yet)" (03 S54)."""
        if not device_name:
            return False
        return store.module_file(device_name, guid).is_file()

    @QtCore.Slot(str, str, str, str, result=str)
    def importModuleFile(self, guid: str, device_name: str, file_name: str, direction: str) -> str:
        # Into the device's own module file; the previous one is kept in its
        # imported/ (03 S58). "Import from" names another device's folder,
        # Browse for File a path. Its Undo is tied to this device and Module
        # Setup (store, 03 S59).
        source = store.resolve_import_source(file_name)
        if source is not None:
            file_name = str(source)
        message = store.import_file(device_name, guid, file_name, direction, _IMPORT_WINDOW)
        if str(message).startswith("Imported "):
            signal.configChanged.emit()
            self._refresh_inplace()
        return message

    @QtCore.Slot(result=bool)
    @QtCore.Slot(str, str, result=bool)
    def importCanUndo(self, guid: str = "", device_name: str = "") -> bool:
        """The last import can be undone here: it was made for this device
        in Module Setup (with no device named: any)."""
        return store.can_undo_file_import(device_name, guid, _IMPORT_WINDOW)

    @QtCore.Slot()
    @QtCore.Slot(str, str)
    def dropImportUndo(self, guid: str = "", device_name: str = "") -> None:
        store.drop_file_import_undo(device_name, guid, _IMPORT_WINDOW)

    @QtCore.Slot(result=str)
    @QtCore.Slot(str, str, result=str)
    def undoLastImport(self, guid: str = "", device_name: str = "") -> str:
        message = store.undo_file_import(device_name, guid, _IMPORT_WINDOW)
        if str(message).startswith("Undone"):
            signal.configChanged.emit()
            self._refresh_inplace()
        return message

    @QtCore.Slot(str, str, result=str)
    def deletePreview(self, device_name: str, guid: str) -> str:
        return delete_preview(device_name, guid)

    @QtCore.Slot(str, str, result=str)
    def deleteDevice(self, device_name: str, guid: str) -> str:
        """Delete Device: always keeps a "stick deleted" autosave in the
        Device Library first (no "Save a copy" question, 10 S21). One
        History entry, "Deleted X" (03 S94a); inside a group already open
        (the Library's Remove) it joins that one."""
        from gremlin import device_aliases, history

        shown = device_aliases.display_name(guid, " ".join(device_name.split()))
        token = history.begin_group(f"Deleted {shown}")
        try:
            raw = delete_device(device_name, guid)
        finally:
            history.end_group(token)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        if data.get("ok"):
            slug = store.card_key(device_name)
            if data.get("stub"):
                _remember_stub(slug)
            # Not a Home step: Delete Device is undone through History.
            self._clear_card_settings(slug)
            if self._focus == slug:
                self._focus = ""
            self._reload()
            # Its card is gone: so is its place in the card order (a stick
            # still plugged in keeps its card and its place).
            if slug not in {row.slug for row in self._rows}:
                order = _order_slugs()
                if slug in order:
                    _set_order([s for s in order if s != slug])
        return raw

    @QtCore.Slot(str, str, result=str)
    def startFresh(self, device_name: str, guid: str) -> str:
        """Moves a damaged module file aside (kept as .bad-<date>) so the
        device can be set up again. Returns where the copy is, or ""."""
        try:
            # The file the device uses (stale id filtered); recorded in
            # History (decision F3).
            copy = store.move_aside(device_name, guid)
        except OSError as e:
            _plog("start fresh failed", name=device_name, error=e)
            return ""
        if copy is None:
            return ""
        signal.configChanged.emit()
        self._reload()
        return str(copy)

    @QtCore.Slot(str, str, result=str)
    def deleteModuleFile(self, guid: str, device_name: str) -> str:
        message = delete_module_file(device_name, guid)
        if not message:
            signal.configChanged.emit()
            self._refresh_inplace()
        return message

    def _on_joy(self, event: event_handler.Event) -> None:
        if event is None:
            return
        from gremlin.modules.gate import status_last_from_hid

        guid = guid_key(event.device_guid)
        row = next((r for r in self._rows if guid_key(r.guid) == guid), None)
        if row is None:
            return
        if not status_last_from_hid(row.direction):
            return
        kind = kind_of(getattr(event, "event_type", None)) or "button"
        try:
            hid = int(getattr(event, "identifier", 0) or 0)
        except (TypeError, ValueError):
            return
        # The input module already passed it (InputModuleRuntime.event, S74);
        # the claim here only gives the friendly name.
        self._set_last(row, kind, hid, self._source_claim(row))

    # How often an input card looks at its module file for a newer save.
    _CLAIM_CHECK_S = 0.5

    def _source_claim(self, row: ModuleRow) -> dict:
        """An input card's claim, re-read only when its module file changed
        (looked at no more than twice a second)."""
        now = clock.monotonic()
        cached = self._source_claims.get(row.slug)
        if cached is not None and now - cached[0] < self._CLAIM_CHECK_S:
            return cached[2]
        name = row.raw_name or row.name
        path = store.module_file(name, row.guid)
        try:
            stat = path.stat()
            stamp: tuple[int, int] | None = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            stamp = None
        if cached is not None and cached[1] == stamp:
            claim = cached[2]
        else:
            doc = _load_module_doc(name, row.guid) if stamp else {}
            claim = read_claim(doc) if doc else {}
        self._source_claims[row.slug] = (now, stamp, claim)
        return claim

    def _set_last(self, row: ModuleRow, kind: str, hid: int, claim: dict | None) -> None:
        hardware = f"{kind} {hid}"
        friendly = (
            claim_friendly(claim, kind, hid)
            or _osc_address(row.guid, kind, hid)
            or hardware.replace("button", "Button")
            .replace("axis", "Axis")
            .replace("hat", "Hat")
        )
        # The same input again (an axis moving): the card already shows it.
        if self._last.get(row.slug) == (friendly, hardware):
            return
        self._last[row.slug] = (friendly, hardware)
        idx = self._rows.index(row)
        self.dataChanged.emit(
            self.index(idx, 0),
            self.index(idx, 0),
            [QtCore.Qt.ItemDataRole.UserRole + 18, QtCore.Qt.ItemDataRole.UserRole + 19],
        )
        self.lastChanged.emit()

    def _dest_target(self, row: ModuleRow) -> tuple[int, dict]:
        """vJoy id and claim of an output card's output module."""
        cached = self._dest_targets.get(row.slug)
        if cached is not None:
            return cached
        from gremlin.modules.registry import resolve_vjoy_id

        name = row.raw_name or row.name
        vid = int(resolve_vjoy_id(name, row.guid) or 0)
        doc = _load_module_doc(name, row.guid) if vid else None
        target = (vid, read_claim(doc) if doc else {})
        self._dest_targets[row.slug] = target
        return target

    def _poll_dest_last(self) -> None:
        # Outputs only change while a profile runs.
        if not runtime_active():
            self._dest_snap = {}
            return
        from gremlin.modules.gate import dest_last_change
        from gremlin.modules.output import vjoy_state

        for row in self._rows:
            if row.direction != "dest":
                continue
            vid, claim = self._dest_target(row)
            if not vid:
                continue
            snap = vjoy_state(vid, claim)
            prev = self._dest_snap.get(row.slug)
            self._dest_snap[row.slug] = snap
            changed = dest_last_change(prev or {}, snap)
            if changed is None:
                continue
            kind, hid = changed
            self._set_last(row, kind, hid, claim)

    def _photo(self, device_name: str, guid: str) -> str:
        """A card's photo, from the file of that device (by its id: twins
        share a name, decision F4)."""
        self._hw.setDeviceGuid(guid)
        return self._hw.profilePhotoUrl(device_name)

    def _reload(self) -> None:
        self._dest_targets = {}
        self._source_claims = {}
        hidden = _hidden_slugs()
        # The names of the hidden cards (Home menu → Hidden Cards).
        hidden_names: dict[str, str] = {}
        self._hidden_names = hidden_names
        show_stubs = _show_stubs()
        kept = _kept_stubs()
        # Settings to change, written once the cards are built (GL-250).
        released: set[str] = set()
        rows: list[ModuleRow] = []

        for dev in device_initialization.physical_devices():
            name = dev.name
            slug = store.card_key(name)
            if slug in hidden:
                hidden_names[slug] = name
                continue
            saved = module_exists(name, str(dev.device_guid))
            if not _show_unconfigured(slug, saved, show_stubs, kept, released):
                continue
            row = ModuleRow()
            row.slug = slug
            row.raw_name = name
            row.name_key = str(dev.device_guid)
            row.name = _shown(row.name_key, name)
            row.guid = str(dev.device_guid)
            row.direction = "source"
            row.tab = "physical"
            row.bus = "DirectInput"
            row.vid = f"{dev.vendor_id:04X}"
            row.pid = f"{dev.product_id:04X}"
            row.photo = self._photo(name, str(dev.device_guid))
            if saved:
                row.is_stub = False
                row.is_module = True
                row.damaged = _module_damage(name, str(dev.device_guid))
                _set_claimed_counts(row, _load_module_doc(name, str(dev.device_guid)))
                row.status = _card_status(row)
            else:
                row.is_stub = True
                row.is_module = False
                row.status = "Stub"
                row.buttons = int(getattr(dev, "button_count", 0) or 0)
                row.axes = int(getattr(dev, "axis_count", 0) or 0)
                row.hats = int(getattr(dev, "hat_count", 0) or 0)
            rows.append(row)

        def extra(slug: str, name: str, guid: str, tab: str, bus: str, direction: str) -> None:
            if slug in hidden:
                hidden_names[slug] = name
                return
            saved = module_exists(name, guid)
            # Keyboard, OSC and the Logical Device always have a card, with
            # or without a module file (D-03-S71-ALWAYS); this only releases
            # a kept card.
            _show_unconfigured(slug, saved, show_stubs, kept, released)
            row = ModuleRow()
            row.slug = slug
            row.raw_name = name
            row.name_key = slug
            row.name = _shown(slug, name)
            row.guid = guid
            row.direction = direction
            row.tab = tab
            row.bus = bus
            row.is_module = saved
            row.is_stub = not saved
            row.photo = self._photo(name, guid)
            if saved:
                row.damaged = _module_damage(name, guid)
                _set_claimed_counts(row, _load_module_doc(name, guid))
            row.status = _card_status(row)
            rows.append(row)

        extra("keyboard", "Keyboard", KEYBOARD_GUID, "keyboard", "HID", "source")
        extra("osc", "OSC", OSC_GUID, "osc", "OSC", "source")

        for vdev in device_initialization.vjoy_devices():
            name = f"vJoy {vdev.vjoy_id}"
            slug = store.card_key(name)
            if slug in hidden:
                hidden_names[slug] = name
                continue
            row = ModuleRow()
            row.slug = slug
            row.raw_name = name
            row.name_key = str(vdev.device_guid)
            row.name = _shown(row.name_key, name)
            row.guid = str(vdev.device_guid)
            row.direction = "dest"
            row.tab = "physical"
            row.bus = "DirectInput"
            row.vjoy_id = int(vdev.vjoy_id)
            row.is_stub = not module_exists(name, str(vdev.device_guid))
            row.is_module = not row.is_stub
            row.status = _card_status(row)
            row.photo = self._photo(name, str(vdev.device_guid))
            if not row.photo:
                row.photo = self._photo("vJoy", "")
            if row.is_module:
                _set_claimed_counts(row, _load_module_doc(name, str(vdev.device_guid)))
            else:
                row.buttons = vdev.button_count
                row.axes = vdev.axis_count
                row.hats = vdev.hat_count
            rows.append(row)

        extra("xbox", "Xbox 360 Controller", XBOX_GUID, "xbox", "XInput", "dest")

        # Always a card, as Keyboard and OSC (03 S71, D-04-LD-FILE).
        extra("logical", "Logical Device", LOGICAL_GUID, "logical", "Logical", "source")

        for row in rows:
            row.has_image = self._has_image(row)

        if not self._focus and rows:
            src = next((r for r in rows if r.direction == "source" and r.status != "Stub"), None)
            if src is None:
                src = next((r for r in rows if r.direction == "source"), rows[0])
            self._focus = src.slug

        saved_order = _order_slugs()
        renamed = _renamed_cards(saved_order, rows, hidden)
        order = _renamed_into_order(saved_order, renamed)
        if order:
            rank = {slug: index for index, slug in enumerate(order)}
            rows.sort(key=lambda row: rank.get(row.slug, 1000 + len(rank)))
        visible = [row.slug for row in rows]
        merged = _merged_order(order, visible)

        apply_bound_targets(rows)
        apply_cant_send(rows)

        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        # Writes after the read, and only for values that changed.
        if released:
            _set_kept_stubs(kept - released)
        if visible and merged != saved_order:
            _set_order(merged)
        _carry_renamed_layout(renamed)
        self.focusChanged.emit()
        self.panesChanged.emit()
        # Pages that ask the list (the Output View header, the
        # Device Bindings page title) read afresh after a full reload.
        self.targetsChanged.emit()
        self.namesChanged.emit()


@ta.QmlElement
class DriverInputModel(QtCore.QAbstractListModel):
    """Full hardware list for Configure module (press-to-check)."""

    roles = {
        QtCore.Qt.ItemDataRole.UserRole + 1: QtCore.QByteArray(b"kind"),
        QtCore.Qt.ItemDataRole.UserRole + 2: QtCore.QByteArray(b"hwId"),
        QtCore.Qt.ItemDataRole.UserRole + 3: QtCore.QByteArray(b"label"),
        QtCore.Qt.ItemDataRole.UserRole + 4: QtCore.QByteArray(b"claimed"),
        QtCore.Qt.ItemDataRole.UserRole + 5: QtCore.QByteArray(b"friendly"),
        QtCore.Qt.ItemDataRole.UserRole + 6: QtCore.QByteArray(b"lit"),
    }

    changed = QtCore.Signal()
    rowActivated = QtCore.Signal(int)
    userEdited = QtCore.Signal()
    undoChanged = QtCore.Signal()

    # Undo steps kept (each a check, a press that checks, or a name).
    UNDO_STEPS = 100

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._undo: list[dict[tuple, tuple[bool, str]]] = []
        self._redo: list[dict[tuple, tuple[bool, str]]] = []
        self._guid = ""
        # Why Save is refused for the loaded device ("" when it isn't).
        self._not_connected = ""
        self._device_name = ""
        self._rows: list[dict] = []
        # The names as read at load (by friendly key), to tell which ones the
        # user changed in this window.
        self._names_loaded: dict[str, str] = {}
        # The device's controls were read (it was plugged in at load).
        self._read_from_device = False
        self._lit_index = -1
        self._last_saved_path = ""
        try:
            listener = event_handler.EventListener()
            listener.joystick_event.connect(
                self._on_joy, QtCore.Qt.ConnectionType.QueuedConnection
            )
            listener.device_change_event.connect(self._device_list_changed)
            listener.keyboard_event.connect(
                self._on_key, QtCore.Qt.ConnectionType.QueuedConnection
            )
        except Exception:
            pass

    def rowCount(self, parent: ta.ModelIndex = QtCore.QModelIndex()) -> int:
        return len(self._rows)

    def roleNames(self) -> dict[int, QtCore.QByteArray]:
        return self.roles

    def data(self, index: ta.ModelIndex, role: int = QtCore.Qt.ItemDataRole.DisplayRole):
        if role not in self.roles or not index.isValid():
            return None
        row = self._rows[index.row()]
        return row.get(bytes(self.roles[role]).decode())

    def _device_list_changed(self) -> None:
        """The stick came or went while its setup is open: Save is refused
        while it is unplugged (and allowed again, with the work on screen,
        when it is back); opened while unplugged, its controls load now."""
        if not self._guid or self._is_keyboard() or self._is_osc():
            return
        if guid_key(self._guid) == guid_key(XBOX_GUID):
            return
        if _device_connected(self._guid):
            if not self._not_connected:
                return
            if self._read_from_device:
                self._not_connected = ""
            else:
                self.loadDevice(self._guid, self._device_name)
        elif not self._not_connected:
            self._not_connected = _unplugged_reason(self._device_name)

    @QtCore.Slot(str, str)
    def loadDevice(self, guid: str, device_name: str) -> None:
        self._guid = guid or ""
        self._device_name = device_name or ""
        self._not_connected = ""
        self._read_from_device = False
        rows: list[dict] = []
        claim = read_claim(_load_module_doc(device_name, guid)) if device_name else {
            "buttons": [],
            "axes": [],
            "hats": [],
            "friendly": {},
        }
        _plog(
            "open module",
            name=device_name,
            guid=guid,
            buttons=claim.get("buttons"),
            axes=claim.get("axes"),
            hats=claim.get("hats"),
            friendly=list((claim.get("friendly") or {})),
        )
        info = None
        if guid:
            try:
                info = hardware.device_info(guid)
            except Exception:
                info = None
        if self._is_keyboard():
            self._load_keyboard(claim)
            return
        if self._is_osc():
            self._load_osc(claim)
            return
        # The Xbox output has no claims (S32, S39): nothing to tick. A real
        # Xbox pad that is unplugged has its own id and is refused below.
        if info is None and guid_key(guid) == guid_key(XBOX_GUID):
            self.beginResetModel()
            self._rows = []
            self._loaded_now()
            self.endResetModel()
            self.changed.emit()
            return
        # A device that isn't plugged in shows no controls: saving would
        # erase its claims and names, so Save is refused until it is back.
        # A stick with no id is not plugged in (03 S90a).
        if (guid or device_name) and not _device_connected(guid, device_name):
            self._not_connected = _unplugged_reason(device_name)
        if info is not None:
            self._read_from_device = True
            for i in range(info.axis_count):
                hid = info.axis_map[i].axis_index
                rows.append(
                    {
                        "kind": "axis",
                        "hwId": hid,
                        "label": f"Axis {hid}",
                        "claimed": hid in claim["axes"],
                        "friendly": claim["friendly"].get(f"axis:{hid}", ""),
                        "lit": False,
                    }
                )
            for hid in range(1, info.button_count + 1):
                rows.append(
                    {
                        "kind": "button",
                        "hwId": hid,
                        "label": f"Button {hid}",
                        "claimed": hid in claim["buttons"],
                        "friendly": claim["friendly"].get(f"button:{hid}", ""),
                        "lit": False,
                    }
                )
            for hid in range(1, info.hat_count + 1):
                rows.append(
                    {
                        "kind": "hat",
                        "hwId": hid,
                        "label": f"Hat {hid}",
                        "claimed": hid in claim["hats"],
                        "friendly": claim["friendly"].get(f"hat:{hid}", ""),
                        "lit": False,
                    }
                )
        self.beginResetModel()
        self._rows = rows
        self._loaded_now()
        self.endResetModel()
        self.changed.emit()

    # By the built-in id only: a stick named "Keyboard" or "OSC" is a stick
    # (03 7.12, S23).
    def _is_keyboard(self) -> bool:
        return guid_key(self._guid) == guid_key(KEYBOARD_GUID)

    def _is_osc(self) -> bool:
        return guid_key(self._guid) == guid_key(OSC_GUID)

    def _load_osc(self, claim: dict) -> None:
        """OSC's inputs from the one shared list (OSC's own file,
        D-09-OSC-FILE); friendly names are kept by the input's uid."""
        from gremlin.osc import OscDevice
        from gremlin.types import InputType

        claimed_btn = {int(x) for x in (claim.get("buttons") or [])}
        claimed_axis = {int(x) for x in (claim.get("axes") or [])}
        friendly = claim.get("friendly") or {}
        rows: list[dict] = []
        for item in OscDevice().rows.rows():
            if item.input_type == InputType.JoystickAxis:
                kind, claimed = "axis", item.input_id in claimed_axis
            else:
                kind, claimed = "button", item.input_id in claimed_btn
            rows.append(
                {
                    "kind": kind,
                    "hwId": int(item.input_id),
                    "uid": item.uid,
                    "label": item.label,
                    "claimed": claimed if (claimed_btn or claimed_axis) else True,
                    "friendly": str(friendly.get(osc_friendly_key(item.uid)) or ""),
                    "lit": False,
                }
            )
        self.beginResetModel()
        self._rows = rows
        self._loaded_now()
        self.endResetModel()
        self.changed.emit()

    @QtCore.Property(bool, notify=changed)
    def isOsc(self) -> bool:
        """The loaded device is OSC (its Module Setup shows the Server
        section)."""
        return self._is_osc()

    def _load_keyboard(self, claim: dict) -> None:
        saved = {int(k) for k in (claim.get("keys") or [])}
        # Never saved: every key ticked (they all pass). Saved with none: none.
        chosen = bool(saved) or bool(claim.get("keysChosen"))
        friendly = claim.get("friendly") or {}
        skip = {"noname", "eraseeof", "zoom"}
        seen: set[int] = set()
        rows = []

        def add_key(key) -> None:
            hid = key_id(key.scan_code, key.is_extended)
            if hid in seen:
                return
            seen.add(hid)
            rows.append(
                {
                    "kind": "key",
                    "hwId": hid,
                    "label": key.name,
                    "claimed": hid in saved if chosen else True,
                    "friendly": friendly.get(f"key:{hid}", ""),
                    "lit": False,
                }
            )

        for name, key in gremlin_keyboard.g_name_to_key.items():
            if name in skip:
                continue
            add_key(key)
        for ch in list("abcdefghijklmnopqrstuvwxyz0123456789`-=[]\\;'\",./"):
            try:
                add_key(gremlin_keyboard.key_from_name(ch))
            except Exception:
                pass
        for hid in saved:
            if hid in seen:
                continue
            scan = hid & 0xFFFF
            ext = bool(hid >> 16)
            try:
                add_key(gremlin_keyboard.key_from_code(scan, ext))
            except Exception:
                rows.append(
                    {
                        "kind": "key",
                        "hwId": hid,
                        "label": f"Key {scan}",
                        "claimed": True,
                        "friendly": friendly.get(f"key:{hid}", ""),
                        "lit": False,
                    }
                )
        self.beginResetModel()
        self._rows = rows
        self._loaded_now()
        self.endResetModel()
        self.changed.emit()

    def _on_key(self, event: event_handler.Event) -> None:
        if event is None or not self._is_keyboard():
            return
        # Hardware only: a key the program sent (macro) is no press (GL-244).
        if getattr(event, "synthetic", False):
            return
        if event.is_pressed is False:
            return
        if _typing_in_a_text_box():
            return
        ident = event.identifier
        try:
            scan, ext = ident[0], ident[1]
        except Exception:
            return
        hid = key_id(int(scan), bool(ext))
        try:
            label = gremlin_keyboard.key_from_code(int(scan), bool(ext)).name
        except Exception:
            label = f"Key {scan}"
        found = None
        for i, row in enumerate(self._rows):
            if row["kind"] == "key" and int(row["hwId"]) == hid:
                found = i
                break
        if found is None:
            # A key that wasn't listed: added ticked, an Undo step like a press.
            self._step()
            self.beginInsertRows(QtCore.QModelIndex(), len(self._rows), len(self._rows))
            self._rows.append(
                {
                    "kind": "key",
                    "hwId": hid,
                    "label": label,
                    "claimed": True,
                    "friendly": "",
                    "lit": False,
                }
            )
            self.endInsertRows()
            found = len(self._rows) - 1
            self.changed.emit()
        self.markPressed("key", hid)

    def _same_device(self, event: event_handler.Event) -> bool:
        if event is None:
            return False
        if guid_key(event.device_guid) == guid_key(self._guid):
            return True
        if not self._device_name:
            return False
        try:
            devices = list(device_initialization.joystick_devices())
        except Exception:
            devices = []
        want = store.card_key(self._device_name)
        ev = guid_key(event.device_guid)
        for dev in devices:
            if guid_key(dev.device_guid) != ev:
                continue
            if store.card_key(dev.name) == want or dev.name == self._device_name:
                self._guid = str(dev.device_guid)
                return True
        return False

    def _on_joy(self, event: event_handler.Event) -> None:
        try:
            if event is None or not self._rows:
                return
            # Hardware only: program-made events tick nothing (GL-244).
            if getattr(event, "synthetic", False):
                return
            if not self._same_device(event):
                return
            et = getattr(event, "event_type", None)
            kind = "button"
            if et == InputType.JoystickAxis:
                kind = "axis"
                try:
                    if abs(float(event.value)) < 0.35:
                        return
                except Exception:
                    return
            elif et == InputType.JoystickHat:
                kind = "hat"
                if getattr(event, "value", None) in (0, (0, 0), "center", None):
                    return
            elif et == InputType.JoystickButton:
                if event.is_pressed is False:
                    return
            try:
                hid = int(event.identifier)
            except Exception:
                return
            self.markPressed(kind, hid)
        except Exception:
            return

    # --- Undo / Redo: the checks and names, as they were before each edit ---

    def _marks(self) -> dict[tuple, tuple[bool, str]]:
        # By control: a pressed key that wasn't listed adds a row.
        return {
            (r["kind"], int(r["hwId"])): (
                bool(r["claimed"]), str(r.get("friendly") or "")
            )
            for r in self._rows
        }

    def _step(self) -> None:
        """Before an edit: keep how it was, for Undo."""
        self._undo.append(self._marks())
        del self._undo[: -self.UNDO_STEPS]
        self._redo.clear()
        self.undoChanged.emit()

    @staticmethod
    def _name_key(row: dict) -> str:
        # OSC's inputs by their uid: the number is only a name.
        if row.get("uid"):
            return osc_friendly_key(row["uid"])
        return f"{row['kind']}:{int(row['hwId'])}"

    def _row_names(self) -> dict[str, str]:
        return {self._name_key(r): str(r.get("friendly") or "") for r in self._rows}

    def _loaded_now(self) -> None:
        """A device was loaded: no Undo steps, and its names as read, so Save
        writes only the names changed here (AD3, like OSC's names_loaded)."""
        self._names_loaded = self._row_names()
        self._forget_steps()

    def _forget_steps(self) -> None:
        if self._undo or self._redo:
            self._undo.clear()
            self._redo.clear()
            self.undoChanged.emit()

    def _put_marks(self, marks: dict[tuple, tuple[bool, str]]) -> None:
        for row in self._rows:
            # A row added since (a key pressed): it wasn't claimed then.
            claimed, friendly = marks.get((row["kind"], int(row["hwId"])), (False, ""))
            row["claimed"] = claimed
            row["friendly"] = friendly
        if self._rows:
            self.dataChanged.emit(
                self.index(0, 0),
                self.index(len(self._rows) - 1, 0),
                [
                    QtCore.Qt.ItemDataRole.UserRole + 4,
                    QtCore.Qt.ItemDataRole.UserRole + 5,
                ],
            )
        self.userEdited.emit()
        self.undoChanged.emit()

    @QtCore.Slot()
    def undo(self) -> None:
        if self._undo:
            self._redo.append(self._marks())
            self._put_marks(self._undo.pop())

    @QtCore.Slot()
    def redo(self) -> None:
        if self._redo:
            self._undo.append(self._marks())
            self._put_marks(self._redo.pop())

    def _can_undo(self) -> bool:
        return bool(self._undo)

    def _can_redo(self) -> bool:
        return bool(self._redo)

    canUndo = QtCore.Property(bool, fget=_can_undo, notify=undoChanged)
    canRedo = QtCore.Property(bool, fget=_can_redo, notify=undoChanged)

    @QtCore.Slot(int, bool)
    def setClaimed(self, index: int, claimed: bool) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if bool(self._rows[index]["claimed"]) == bool(claimed):
            return
        self._step()
        self._rows[index]["claimed"] = bool(claimed)
        ix = self.index(index, 0)
        self.dataChanged.emit(ix, ix, [QtCore.Qt.ItemDataRole.UserRole + 4])
        self.userEdited.emit()

    @QtCore.Slot(int, str)
    def setFriendly(self, index: int, name: str) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if str(self._rows[index].get("friendly") or "") == str(name or ""):
            return
        self._step()
        self._rows[index]["friendly"] = name
        ix = self.index(index, 0)
        self.dataChanged.emit(ix, ix, [QtCore.Qt.ItemDataRole.UserRole + 5])
        self.userEdited.emit()

    def _set_lit(self, index: int, lit: bool) -> None:
        if not (0 <= index < len(self._rows)):
            return
        if bool(self._rows[index].get("lit")) == bool(lit):
            return
        self._rows[index]["lit"] = bool(lit)
        ix = self.index(index, 0)
        self.dataChanged.emit(ix, ix, [QtCore.Qt.ItemDataRole.UserRole + 6])

    @QtCore.Slot(str, int)
    def markPressed(self, kind: str, hw_id: int) -> None:
        for i, row in enumerate(self._rows):
            if row["kind"] == kind and int(row["hwId"]) == int(hw_id):
                if not row["claimed"]:
                    self.setClaimed(i, True)
                if self._lit_index == i:
                    return
                if self._lit_index >= 0:
                    self._set_lit(self._lit_index, False)
                self._lit_index = i
                self._set_lit(i, True)
                self.rowActivated.emit(i)
                return

    @QtCore.Slot(result=str)
    def saveBlockedReason(self) -> str:
        """Why Save is refused for the loaded device ("" when it isn't)."""
        return self._not_connected

    @QtCore.Slot(str, str, result=bool)
    @QtCore.Slot(str, str, str, result=bool)
    @QtCore.Slot(str, str, str, bool, result=bool)
    def saveClaim(
        self,
        device_name: str,
        direction: str,
        image: str = "",
        removeImage: bool = False,
    ) -> bool:
        """Module Setup's Save. image: the reference of the picture Add /
        Change Image kept in the window's edit ("setup"); removeImage: Remove
        Image was chosen. With the edit open the write goes through
        store.commit_edit, so the picture is copied into the device's folder
        and named in the same write as the claims (one History entry, 03
        S52, 07 S107). An input device: the picture is the device image
        (the module file's deviceImage, D-03-DEVICE-IMAGE); the old image
        file goes with the edit's clean-up. An output device: the picture
        is the bottom background picture of its map, as before (outputs
        unchanged)."""
        if self.saveBlockedReason():
            _plog("save claim refused", name=device_name, reason=self._not_connected)
            return False
        name = device_name or self._device_name
        # The device's own folder, found by its id (03 S1, S130): a device
        # whose name changed kept its folder. Made now with its device.json.
        try:
            path = store.module_file_in(store.ensure_device_dir(name, self._guid))
        except OSError as exc:
            _plog("save claim failed", name=name, error=exc)
            return False
        photo = str(image or "").strip()
        output = is_output_name(name)
        buttons = [int(r["hwId"]) for r in self._rows if r["kind"] == "button" and r["claimed"]]
        axes = [int(r["hwId"]) for r in self._rows if r["kind"] == "axis" and r["claimed"]]
        hats = [int(r["hwId"]) for r in self._rows if r["kind"] == "hat" and r["claimed"]]
        keys = [int(r["hwId"]) for r in self._rows if r["kind"] == "key" and r["claimed"]]
        # The window is non-modal: only the names changed here are written;
        # a name saved elsewhere since it opened stays (AD3, AUD-FILES-01).
        edited = {
            key: name
            for key, name in self._row_names().items()
            if name != self._names_loaded.get(key, "")
        }
        # A name is kept only for a claimed control (03 S42).
        claimed_keys = {self._name_key(r) for r in self._rows if r["claimed"]}
        friendly: dict[str, str] = {}

        def change(doc: dict) -> None:
            old = doc.get("claim")
            names = old.get("friendly") if isinstance(old, dict) else None
            if not isinstance(names, dict):
                names = {}
            merged = {str(k): str(v) for k, v in names.items() if v}
            for key, text in edited.items():
                if text:
                    merged[key] = text
                else:
                    merged.pop(key, None)
            friendly.clear()
            friendly.update({k: v for k, v in merged.items() if k in claimed_keys})
            doc["kind"] = "control.hardware"
            doc["device"] = name
            if is_output_name(name):
                doc["direction"] = "dest"
            elif self._guid and _device_connected(self._guid, name):
                # A physical stick is an input (a file the old Output menu
                # marked "dest" blocked every input; saving here repairs it).
                doc["direction"] = "source"
            elif doc.get("direction") not in ("source", "dest"):
                doc["direction"] = direction or "source"
            if self._guid:
                doc["boundName"] = name
                # GUID stays local-only; stored for this machine bind, not exported.
                doc["boundGuidLocal"] = self._guid
            doc["claim"] = {
                "buttons": buttons,
                "axes": axes,
                "hats": hats,
                "keys": keys,
                "friendly": friendly,
            }
            if self._is_keyboard() and not keys:
                doc["claim"]["keysChosen"] = True
            doc.setdefault("space", "world")
            # The one page size (the Device Mapping Editor's, GL-270).
            for key in ("pageW", "pageH", "photoWell"):
                doc.setdefault(key, PAGE_SIZE[key])
            doc.setdefault("nodes", [])
            if output:
                if photo:
                    # An output's photo: the bottom background picture (07 S127).
                    store.set_device_photo(doc, photo, path.parent)
            elif photo:
                # An input's device image: its own file, not a map layer.
                doc[store.DEVICE_IMAGE_KEY] = store.normal_ref(photo)
            elif removeImage:
                doc.pop(store.DEVICE_IMAGE_KEY, None)

        _plog(
            "save claim",
            name=name,
            guid=self._guid,
            direction=direction,
            path=str(path),
            buttons=buttons,
            axes=axes,
            hats=hats,
            names_edited=list(edited),
        )
        editing = (
            store.edit_temp_dir(name, self._guid, _SETUP_EDIT) / store.STATE_FILE
        ).is_file()
        try:
            if editing:
                error = store.commit_edit(
                    name, self._guid, change, _SETUP_EDIT, "Configure Module"
                )
                if error:
                    _plog("save claim failed", path=str(path), error=error)
                    return False
            elif not store.update_path(path, change, "Configure Module"):
                return False
            elif removeImage and not output:
                # No edit to clean up after: the dropped image file goes here.
                store.remove_unused_pictures(name, self._guid)
            written = json.loads(path.read_text(encoding="utf-8"))
            trace("SAVE", "Configure Module", "saveClaim", path, "ok")
        except (OSError, json.JSONDecodeError) as exc:
            _plog("save claim failed", path=str(path), error=exc)
            trace("SAVE", "Configure Module", "saveClaim", path, "error")
            return False
        got = written.get("claim") if isinstance(written.get("claim"), dict) else {}
        if [int(n) for n in (got.get("buttons") or [])] != buttons:
            _plog("save claim mismatch", path=str(path), field="buttons", wrote=buttons, read=got.get("buttons"))
            return False
        if [int(n) for n in (got.get("axes") or [])] != axes:
            _plog("save claim mismatch", path=str(path), field="axes", wrote=axes, read=got.get("axes"))
            return False
        if [int(n) for n in (got.get("hats") or [])] != hats:
            _plog("save claim mismatch", path=str(path), field="hats", wrote=hats, read=got.get("hats"))
            return False
        signal.configChanged.emit()
        _plog("save claim ok", path=str(path), bytes=path.stat().st_size)
        self._last_saved_path = str(path)
        return True

    @QtCore.Slot(result=str)
    def lastSavedPath(self) -> str:
        return self._last_saved_path
