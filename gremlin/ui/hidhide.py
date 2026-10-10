# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The HidHide window (Tools > Device Setup > HidHide) and its settings.

The driver client and the device list are in gremlin.hidhide_driver."""

from __future__ import annotations

import datetime
import json
import logging
import os
from collections.abc import Callable
from pathlib import Path

from PySide6 import QtCore, QtGui

import gremlin.ui.type_aliases as ta
from gremlin import config, event_handler, hidhide_driver, process_paths
from gremlin.hidhide_driver import (
    _display_name,
    _full_image_name,
    _gremlin_exe,
    _hh_log,
    _vid_pid,
    driver_present,
    driver_version,
    get_active,
    get_blacklist,
    get_inverse,
    list_hid_devices,
    set_active,
    set_blacklist,
    set_inverse,
    set_whitelist,
)
from gremlin.types import PropertyType
from gremlin.ui import device_reset_model  # noqa: F401 - registers ResetDevicesModel

QML_IMPORT_NAME = "Gremlin.Device"
QML_IMPORT_MAJOR_VERSION = 1

_CFG_SECTION = "display"
_CFG_GROUP = "hidhide"
_CFG_GAMES = "games"
_CFG_PHOTOS = "photos"
_CFG_LINKS = "module-links"
_CFG_LIST_MODE = "list-mode"
_CFG_HIDDEN = "hidden-devices"
_CFG_CLOAK = "cloak"
_CFG_MANAGED = "managed"
_CFG_GAMING = "gaming-only"
_CFG_WINDOW_W = "window-width"
_CFG_WINDOW_H = "window-height"
_CFG_SPLIT = "split-ratio"
_DOWNLOAD = "https://github.com/nefarius/HidHide/releases"



def _ensure_options() -> None:
    cfg = config.Configuration()
    try:
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_GAMES,
            PropertyType.String,
            "[]",
            "Hardware Hide game whitelist (name + exe path).",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_PHOTOS,
            PropertyType.String,
            "{}",
            "Hardware Hide device photos keyed by instance id.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_LINKS,
            PropertyType.String,
            "{}",
            "Hardware Hide device to input or output module.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_LIST_MODE,
            PropertyType.String,
            "",
            "Hardware Hide program list mode: allow or block.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_HIDDEN,
            PropertyType.String,
            "",
            "Hardware Hide device instance ids that stay hidden.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_CLOAK,
            PropertyType.String,
            "",
            "Hardware Hide enforcement: on or off.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_MANAGED,
            PropertyType.String,
            "",
            "Set after the user saves HidHide Enabled. Empty means leave the driver alone.",
            {},
            False,
        )
        cfg.register(
            "global",
            "general",
            "hidhide-on-start",
            PropertyType.Bool,
            False,
            "Turn HidHide on when the program starts.",
            {},
            True,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_GAMING,
            PropertyType.String,
            "",
            "Limit the HidHide device list to game controllers.",
            {},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_WINDOW_W,
            PropertyType.Int,
            720,
            "Hardware Hide window width.",
            {"min": 480, "max": 8000},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_WINDOW_H,
            PropertyType.Int,
            640,
            "Hardware Hide window height.",
            {"min": 360, "max": 8000},
            False,
        )
        cfg.register(
            _CFG_SECTION,
            _CFG_GROUP,
            _CFG_SPLIT,
            PropertyType.Int,
            600,
            "Hardware Hide device list share of the splitter, in thousandths.",
            {"min": 150, "max": 850},
            False,
        )
    except Exception:
        logging.getLogger("system").exception("HidHide settings not registered")


def _load_games() -> list[dict]:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_GAMES) or "[]")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return []
    out = []
    if isinstance(data, list):
        for row in data:
            if not isinstance(row, dict):
                continue
            path = str(row.get("path") or "").strip()
            if not path:
                continue
            name = str(row.get("name") or Path(path).stem)
            out.append({"name": name, "path": path})
    out.sort(key=lambda r: r["name"].lower())
    return out


# The last HidHide setting that could not be written ("" when all were).
_settings_error = ""


def _settings_write_failed(exc: Exception) -> None:
    global _settings_error
    _settings_error = f"Could not save the HidHide settings: {exc}"
    _hh_log(_settings_error, logging.WARNING)


def _save_games(rows: list[dict]) -> None:
    _ensure_options()
    packed = json.dumps(
        [{"name": r["name"], "path": r["path"]} for r in rows],
        ensure_ascii=True,
    )
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_GAMES, packed)
        _hh_log(f"saved games count={len(rows)}")
    except Exception as exc:
        _settings_write_failed(exc)



def _card_photo(stored: str) -> str | None:
    """The picture for a device card: the picked file (a URL); "" when one
    was picked but is no longer there (no picture until another is picked);
    None when none was picked (the module's photo is shown)."""
    if not stored:
        return None
    text = str(stored)
    path = Path(QtCore.QUrl(text).toLocalFile() if text.startswith("file:") else text)
    return _file_url(path) if path.is_file() else ""


def _load_photos() -> dict[str, str]:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_PHOTOS) or "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


def _save_photos(rows: dict[str, str]) -> None:
    _ensure_options()
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_PHOTOS, json.dumps(rows, ensure_ascii=True)
        )
    except Exception as exc:
        _settings_write_failed(exc)


def _load_links() -> dict[str, str]:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_LINKS) or "{}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    if not isinstance(data, dict):
        return {}
    return {str(k): str(v) for k, v in data.items() if k and v}


def _save_links(rows: dict[str, str]) -> None:
    _ensure_options()
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_LINKS, json.dumps(rows, ensure_ascii=True)
        )
    except Exception as exc:
        _settings_write_failed(exc)


def _drop_instances(rows: dict[str, str], instances: set[str]) -> bool:
    gone = [key for key in rows if key.upper() in instances]
    for key in gone:
        rows.pop(key)
    return bool(gone)


def forget_devices(label_gone: Callable[[str], bool]) -> None:
    """At a device scan: forgets the photo and link of every HidHide entry
    whose linked device label_gone(name) says is forgotten (no module file,
    not plugged in: D-02-GL243-FORGET). Only the program's own settings;
    the HidHide driver is not touched."""
    links = _load_links()
    instances = {key.upper() for key, label in links.items() if label_gone(label)}
    if not instances:
        return
    _hh_log(f"forgot photo and link of {sorted(instances)}")
    photos = _load_photos()
    _drop_instances(links, instances)
    _save_links(links)
    if _drop_instances(photos, instances):
        _save_photos(photos)


def _forget_unlisted_photos(rows: list[dict]) -> None:
    """A photo of a device that isn't in the full HID list and has no link
    to a device (so no module file) is forgotten (D-02-GL243-FORGET)."""
    present = {
        str(i).upper()
        for row in rows
        for i in (row.get("instanceIds") or [row.get("instanceId")])
        if i
    }
    linked = {key.upper() for key in _load_links()}
    photos = _load_photos()
    gone = {key.upper() for key in photos} - present - linked
    if gone and _drop_instances(photos, gone):
        _hh_log(f"forgot photo of {sorted(gone)}")
        _save_photos(photos)


def _saved_block_list() -> bool | None:
    """True is Block list, False is Allow list, None if the user has not chosen."""
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_LIST_MODE) or "").strip().lower()
    if raw == "block":
        return True
    if raw == "allow":
        return False
    return None


def _save_list_mode(block: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_LIST_MODE, "block" if block else "allow"
        )
    except Exception as exc:
        _settings_write_failed(exc)


def _apply_saved_list_mode() -> bool:
    """Write Allow list until the user picks Block list."""
    choice = _saved_block_list()
    if choice is None:
        choice = False
        _save_list_mode(False)
    if bool(get_inverse()) != choice:
        if not set_inverse(choice):
            return bool(get_inverse())
    return choice


def _saved_hidden() -> list[str] | None:
    """None means this install has not stored a device list yet."""
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_HIDDEN) or "")
    if not raw.strip():
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, list):
        return None
    return [str(item) for item in loaded if str(item).strip()]


def _save_hidden(ids: list[str]) -> None:
    _ensure_options()
    kept: list[str] = []
    seen: set[str] = set()
    for item in ids:
        text = str(item).strip()
        key = text.upper()
        if not text or key in seen:
            continue
        seen.add(key)
        kept.append(text)
    try:
        config.Configuration().set(
            _CFG_SECTION, _CFG_GROUP, _CFG_HIDDEN, json.dumps(kept, ensure_ascii=True)
        )
    except Exception as exc:
        _settings_write_failed(exc)


def _apply_saved_hidden() -> None:
    """Write the saved device list. A new install hides nothing."""
    saved = _saved_hidden()
    if saved is None:
        saved = []
        _save_hidden(saved)
    set_blacklist(saved)


def _saved_cloak() -> bool | None:
    _ensure_options()
    raw = str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_CLOAK) or "").strip().lower()
    if raw == "on":
        return True
    if raw == "off":
        return False
    return None


def _save_cloak(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_CLOAK, "on" if on else "off")
    except Exception as exc:
        _settings_write_failed(exc)


def _start_enabled() -> bool:
    _ensure_options()
    return bool(config.Configuration().value("global", "general", "hidhide-on-start"))


def _save_start(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set("global", "general", "hidhide-on-start", bool(on))
    except Exception as exc:
        _settings_write_failed(exc)


def _saved_gaming_only() -> bool:
    _ensure_options()
    return str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_GAMING) or "").strip().lower() == "on"


def _save_gaming_only(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_GAMING, "on" if on else "off")
    except Exception as exc:
        _settings_write_failed(exc)


def _hidhide_managed() -> bool:
    _ensure_options()
    return str(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_MANAGED) or "").strip().lower() == "yes"


def _mark_managed() -> None:
    _set_managed(True)


def _clear_managed() -> None:
    _set_managed(False)


def _set_managed(on: bool) -> None:
    _ensure_options()
    try:
        config.Configuration().set(_CFG_SECTION, _CFG_GROUP, _CFG_MANAGED, "yes" if on else "")
    except Exception as exc:
        _settings_write_failed(exc)


def _apply_saved_cloak() -> bool:
    """Write HidHide Enabled. The unset value is off, and it is not taken from the driver."""
    choice = _saved_cloak()
    if choice is None:
        choice = False
        _save_cloak(False)
    if bool(get_active()) != choice:
        set_active(choice)
    return choice


def _module_label(dev) -> str:
    if getattr(dev, "is_virtual", False):
        return f"vJoy {int(getattr(dev, 'vjoy_id', 0) or 0)}"
    return str(getattr(dev, "name", "") or "")


def _collection_index(instance: str) -> int | None:
    import re
    text = (instance or "").upper()
    match = re.search(r"&([0-9A-F]{4})$", text)
    if match:
        return int(match.group(1), 16)
    match = re.search(r"COL(\d+)", text)
    if match:
        return max(0, int(match.group(1)) - 1)
    return None


def _module_photo(hw, name: str) -> str:
    if hw is None or not name:
        return ""
    try:
        url = hw.profilePhotoUrl(name) or ""
    except Exception:
        url = ""
    if url:
        return url
    if name.lower().startswith("vjoy"):
        try:
            return hw.profilePhotoUrl("vJoy") or ""
        except Exception:
            return ""
    return ""




def _dill_matches() -> list:
    try:
        from gremlin.device_initialization import joystick_devices
        return list(joystick_devices())
    except Exception:
        return []


def _file_url(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.resolve().as_uri()




def _enrich_devices(rows: list[dict]) -> list[dict]:
    photos = _load_photos()
    links = _load_links()
    dill_devs = _dill_matches()
    hw = None
    try:
        from gremlin.ui.hardware_profile import HardwareProfile
        hw = HardwareProfile()
    except Exception:
        hw = None
    physical = [dev for dev in dill_devs if not getattr(dev, "is_virtual", False)]
    virtual = [dev for dev in dill_devs if getattr(dev, "is_virtual", False)]
    by_vjoy = {}
    for dev in virtual:
        try:
            by_vjoy[int(dev.vjoy_id)] = dev
        except (TypeError, ValueError, AttributeError):
            continue
    known = {_module_label(dev) for dev in dill_devs if _module_label(dev)}
    present = {str(row.get("instanceId") or "").upper() for row in rows}
    used = {
        name for key, name in links.items()
        if str(key).upper() in present and name in known
    }
    changed = False
    for row in rows:
        instance = row["instanceId"]
        vid, pid = _vid_pid(instance)
        match = None
        if vid is not None and pid is not None:
            hits = []
            for dev in physical:
                try:
                    if int(dev.vendor_id) == vid and int(dev.product_id) == pid:
                        hits.append(dev)
                except Exception:
                    continue
            if len(hits) == 1:
                match = hits[0]
        if match and match.name:
            row["name"] = _display_name("", "", row.get("name") or "", match.name)
        else:
            row["name"] = _display_name("", "", row.get("name") or "", "")
        module = links.get(instance) or links.get(instance.upper(), "")
        if module not in known:
            module = ""
            if match is not None:
                module = _module_label(match)
            elif _looks_vjoy(row):
                index = _collection_index(instance)
                dev = by_vjoy.get((index + 1) if index is not None else -1)
                if dev is not None and _module_label(dev) not in used:
                    module = _module_label(dev)
                else:
                    for candidate in sorted(by_vjoy):
                        label = _module_label(by_vjoy[candidate])
                        if label and label not in used:
                            module = label
                            break
            if module:
                links[instance] = module
                used.add(module)
                changed = True
                _hh_log(f"module link {instance} -> {module}")
        elif instance not in links:
            links[instance] = module
            changed = True
        shown = _card_photo(photos.get(instance) or photos.get(instance.upper(), ""))
        if shown is None:
            row["photo"] = _module_photo(hw, module)
            row["photoSource"] = "module" if row["photo"] else ""
        else:
            row["photo"] = shown
            row["photoSource"] = "override" if shown else "missing"
    if changed:
        _save_links(links)
    return rows


def _sorted_devices(rows: list[dict]) -> list[dict]:
    """By name like HidHide's device list.

    The instance id keeps equal names in a fixed order.
    """
    def key(row: dict) -> tuple[str, str]:
        name = str(row.get("name") or "").lower()
        return name, str(row.get("instanceId") or "").upper()

    return sorted(rows, key=key)


def _link():  # noqa: ANN202
    """gremlin.input_tester_link, or None when it isn't there."""
    try:
        from gremlin import input_tester_link
    except ImportError:
        return None
    return input_tester_link


def _tell_link_hidhide_changed(what: str = "settings") -> None:
    """Notes the change (what: program list, cloak, hidden devices, mode,
    settings); a running Input Tester gets a new expected.json."""
    link = _link()
    if link is None:
        return
    try:
        link.hidhide_changed(what)
    except Exception:
        logging.getLogger("system").exception("Input Tester expected list not updated")


def _tester_path() -> str:
    link = _link()
    if link is None:
        return ""
    try:
        path = link.tester_path()
    except Exception:
        logging.getLogger("system").exception("Input Tester path failed")
        return ""
    return str(path) if path else ""


def _result_line(result: dict | None) -> tuple[str, bool]:
    """'Last Input Tester result' text and whether it is a Fail."""
    if not result:
        return "never run", False
    verdict = str(result.get("verdict") or "")
    written = str(result.get("written") or "")
    clock_text = ""
    try:
        clock_text = datetime.datetime.fromisoformat(written).strftime("%H:%M")
    except ValueError:
        pass
    head = {"pass": "✓ Pass", "fail": "✗ Fail"}.get(
        verdict, "Nothing to compare"
    )
    if clock_text:
        head += f", {clock_text}"
    summary = str(result.get("summary") or "").strip()
    return (f"{head} · {summary}" if summary else head), verdict == "fail"


def _reset_available() -> bool:
    try:
        from gremlin import device_reset

        return any(d.plugged for d in device_reset.list_devices([]))
    except Exception:
        logging.getLogger("system").exception("Reset Devices: device list failed")
        return False


def _same_path(a: str, b: str) -> bool:
    return os.path.normcase(os.path.normpath(a)) == os.path.normcase(os.path.normpath(b))


def _looks_vjoy(row: dict) -> bool:
    name = str(row.get("name") or "").lower()
    instance = str(row.get("instanceId") or "").upper()
    return "vjoy" in name or "HIDCLASS" in instance

@ta.QmlElement
class HidHideModel(QtCore.QObject):
    """System-wide HidHide panel. Persistent cloak, devices, and game list."""

    changed = QtCore.Signal()

    def __init__(self, parent: ta.OQO = None) -> None:
        super().__init__(parent)
        self._present = False
        self._active = False
        self._driver_active = False
        self._devices: list[dict] = []
        self._games: list[dict] = []
        self._gaming_only = _saved_gaming_only()
        self._generation = 0
        self._last_error = ""
        # A new window starts clean; a failed setting write shows until then.
        global _settings_error
        _settings_error = ""
        self._inverse = False
        self._version = ""
        self._reset_available = False
        _ensure_options()
        self.reload()
        # A stick plugged in or out shows (or leaves) the list while open.
        event_handler.EventListener().device_change_event.connect(self.reload)
        # Input Tester (02 D-02-INPUT-TESTER): last result, path checks.
        self._tester_message = ""
        self._game_problems: list[str] = []
        self._tester_problem = ""
        # Listed programs started before the last HidHide change.
        self._stale_games: list[str] = []
        self._stale_tester = ""
        self._result_text, self._result_failed = _result_line(None)
        self._path_timer = QtCore.QTimer(self)
        self._path_timer.setInterval(5000)
        self._path_timer.timeout.connect(self._check_paths)
        self._read_result()
        link = _link()
        if link is not None:
            try:
                link.watcher().resultChanged.connect(self._read_result)
            except Exception:
                logging.getLogger("system").exception("Input Tester watcher not connected")

    def reload(self) -> None:
        self._present = driver_present()
        self._driver_active = get_active() if self._present else False
        saved_cloak = _saved_cloak()
        self._active = bool(saved_cloak) if saved_cloak is not None else False
        saved_block = _saved_block_list()
        self._inverse = bool(saved_block) if saved_block is not None else False
        self._version = driver_version() if self._present else ""
        saved_ids = {i.upper() for i in (_saved_hidden() or [])}
        driver_ids = {i.upper() for i in get_blacklist()} if self._present else set()
        self._devices = []
        try:
            rows = list_hid_devices(self._gaming_only)
        except Exception:
            logging.getLogger("system").exception("HidHide device list failed")
            rows = []
        # Only from the full list: Gaming only leaves plugged-in devices out.
        if rows and not self._gaming_only:
            _forget_unlisted_photos(rows)
        built = []
        for row in _enrich_devices(rows):
            item = dict(row)
            ids = [str(x).upper() for x in (item.get("instanceIds") or [item.get("instanceId")]) if x]
            item["session"] = any(i in saved_ids for i in ids)
            item["clientBlocked"] = any(i in driver_ids for i in ids)
            item["hidden"] = item["clientBlocked"]
            item["confirmed"] = bool(self._driver_active and item["clientBlocked"])
            built.append(item)
        self._devices = _sorted_devices(built)
        self._games = _load_games()
        self._reset_available = _reset_available()
        self._generation += 1
        _hh_log(
            f"reload present={self._present} version={self._version} cloak={self._active} "
            f"driver={self._driver_active} inverse={self._inverse} "
            f"client={len(driver_ids)} rows={len(self._devices)}"
        )
        self.changed.emit()

    @QtCore.Property(bool, notify=changed)
    def installed(self) -> bool:
        return self._present

    @QtCore.Property(str, notify=changed)
    def driverVersion(self) -> str:
        return self._version

    @QtCore.Property(int, constant=True)
    def windowWidth(self) -> int:
        _ensure_options()
        try:
            return max(480, int(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_W)))
        except (TypeError, ValueError):
            return 720

    @QtCore.Property(int, constant=True)
    def windowHeight(self) -> int:
        _ensure_options()
        try:
            return max(360, int(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_H)))
        except (TypeError, ValueError):
            return 640

    @QtCore.Slot(int, int)
    def saveWindowSize(self, width: int, height: int) -> None:
        _ensure_options()
        cfg = config.Configuration()
        cfg.set(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_W, max(480, min(8000, int(width))))
        cfg.set(_CFG_SECTION, _CFG_GROUP, _CFG_WINDOW_H, max(360, min(8000, int(height))))

    @QtCore.Property(int, constant=True)
    def splitRatio(self) -> int:
        """The device list's share of the divider, in thousandths. Kept with
        the other window layout (window_placement); a value saved the old way
        here is the starting point."""
        from gremlin.ui import window_placement

        old = 600
        _ensure_options()
        try:
            old = int(config.Configuration().value(_CFG_SECTION, _CFG_GROUP, _CFG_SPLIT))
        except (TypeError, ValueError):
            pass
        share = window_placement.split_ratio("hardwareHide", old / 1000)
        return max(150, min(850, int(round(share * 1000))))

    @QtCore.Slot(int)
    def saveSplitRatio(self, ratio: int) -> None:
        from gremlin.ui import window_placement

        window_placement.save_split("hardwareHide", max(150, min(850, int(ratio))) / 1000)

    @QtCore.Property(str, constant=True)
    def downloadUrl(self) -> str:
        return _DOWNLOAD

    @QtCore.Property(bool, notify=changed)
    def cloakOn(self) -> bool:
        return self._active

    @QtCore.Property(bool, notify=changed)
    def inverseOn(self) -> bool:
        return self._inverse

    @QtCore.Slot(bool, result=bool)
    def setInverse(self, on: bool) -> bool:
        if not self._present or not _hidhide_managed():
            return False
        if not set_inverse(bool(on)):
            self._last_error = hidhide_driver.last_error() or "HidHide driver call failed."
            self.reload()
            return False
        _save_list_mode(bool(on))
        self._inverse = bool(on)
        self._last_error = ""
        self._sync_whitelist()
        self.reload()
        _tell_link_hidhide_changed("mode")
        return True

    @QtCore.Property(bool, notify=changed)
    def gamingOnly(self) -> bool:
        return self._gaming_only

    @QtCore.Slot(bool)
    def setGamingOnly(self, on: bool) -> None:
        self._gaming_only = bool(on)
        _save_gaming_only(self._gaming_only)
        self.reload()

    @QtCore.Property(int, notify=changed)
    def generation(self) -> int:
        return self._generation

    @QtCore.Property(str, notify=changed)
    def lastError(self) -> str:
        return self._last_error or _settings_error

    @QtCore.Property(int, notify=changed)
    def deviceCount(self) -> int:
        return len(self._devices)

    
    @QtCore.Property(int, notify=changed)
    def gameCount(self) -> int:
        return len(self._games)

    @QtCore.Slot(int, result="QVariant")
    def deviceAt(self, index: int):
        if 0 <= index < len(self._devices):
            return self._devices[index]
        return {}

    @QtCore.Slot(int, result="QVariant")
    def gameAt(self, index: int):
        if 0 <= index < len(self._games):
            return self._games[index]
        return {}

    @QtCore.Property(bool, notify=changed)
    def gremlinControl(self) -> bool:
        return _hidhide_managed()

    @QtCore.Slot(bool, result=bool)
    def setGremlinControl(self, on: bool) -> bool:
        if not self._present:
            return False
        if on:
            _mark_managed()
            apply_saved_list()
        else:
            _clear_managed()
        self.reload()
        _tell_link_hidhide_changed("settings")
        return True

    @QtCore.Property(bool, notify=changed)
    def startOn(self) -> bool:
        return _start_enabled()

    @QtCore.Slot(bool, result=bool)
    def setStartOn(self, on: bool) -> bool:
        _save_start(bool(on))
        self.changed.emit()
        return True

    @QtCore.Slot(bool, result=bool)
    def setCloak(self, on: bool) -> bool:
        if not self._present or not _hidhide_managed():
            return False
        if not set_active(bool(on)):
            # Same as the per-device switches: say why and show the real state.
            self._last_error = hidhide_driver.last_error() or "HidHide driver call failed."
            _hh_log(f"set active failed: {self._last_error}", logging.WARNING)
            self.reload()
            return False
        self._last_error = ""
        _save_cloak(bool(on))
        self.reload()
        _tell_link_hidhide_changed("cloak")
        return True

    @QtCore.Slot(str, bool, result=bool)
    def setDeviceHidden(self, instance_id: str, hidden: bool) -> bool:
        if not self._present or not instance_id or not _hidhide_managed():
            return False
        group_ids = [instance_id]
        for row in self._devices:
            ids = row.get("instanceIds") or [row.get("instanceId")]
            if instance_id.upper() in {str(x).upper() for x in ids}:
                group_ids = [str(x) for x in ids if x]
                break
        drop = {x.upper() for x in group_ids}
        base = _saved_hidden()
        if base is None:
            base = []
        kept = [i for i in base if i.upper() not in drop]
        if hidden:
            have = {i.upper() for i in kept}
            for group_id in group_ids:
                if group_id.upper() not in have:
                    kept.append(group_id)
                    have.add(group_id.upper())
        _hh_log(f"set hidden={bool(hidden)} id={instance_id} group={group_ids} blacklist={kept}")
        # Saved only after the driver accepts it (02 Q14), as HidHide
        # Enabled: a refused tick left the saved list and the driver apart.
        if not set_blacklist(kept):
            self._last_error = hidhide_driver.last_error() or "HidHide driver call failed."
            _hh_log(f"set blacklist failed: {self._last_error}", logging.WARNING)
            self.reload()
            return False
        _save_hidden(kept)
        self._last_error = ""
        self.reload()
        _tell_link_hidhide_changed("hidden devices")
        return True

    @QtCore.Slot(str, str, result=bool)
    def addGame(self, name: str, path: str) -> bool:
        path = str(Path(path).resolve()) if path else ""
        if not path:
            return False
        label = (name or "").strip() or Path(path).stem
        rows = [r for r in self._games if Path(r["path"]).resolve().as_posix().lower() != Path(path).as_posix().lower()]
        rows.append({"name": label, "path": path})
        rows.sort(key=lambda r: r["name"].lower())
        _save_games(rows)
        self._games = rows
        self._sync_whitelist()
        self.changed.emit()
        _tell_link_hidhide_changed("program list")
        return True

    @QtCore.Slot(str, result=bool)
    def removeGame(self, path: str) -> bool:
        rows = [r for r in self._games if r["path"] != path]
        _save_games(rows)
        self._games = rows
        self._sync_whitelist()
        self.changed.emit()
        _tell_link_hidhide_changed("program list")
        return True

    @QtCore.Slot(str, str, result=bool)
    def setDevicePhoto(self, instance_id: str, path: str) -> bool:
        if not instance_id or not path:
            return False
        src = Path(path)
        if not src.is_file():
            # QML file url
            text = path
            if text.startswith("file:///"):
                text = text[8:]
            src = Path(text)
        if not src.is_file():
            return False
        # The picture is used where it is (the folder it was picked from):
        # nothing is copied or deleted. If it is moved or deleted later, the
        # card shows no picture until another is picked.
        photos = _load_photos()
        photos[instance_id] = str(src.resolve())
        _save_photos(photos)
        self.reload()
        return True

    @QtCore.Slot()
    def refresh(self) -> None:
        self.reload()

    @QtCore.Slot()
    def openDownload(self) -> None:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(_DOWNLOAD))

    @QtCore.Slot()
    def openGameControllers(self) -> None:
        if os.name != "nt":
            return
        import subprocess
        try:
            subprocess.Popen(
                ["rundll32.exe", "shell32.dll,Control_RunDLL", "joy.cpl"],
                close_fds=True,
            )
        except OSError as exc:
            _hh_log(f"joy.cpl failed: {exc}", logging.WARNING)

    def _sync_whitelist(self) -> None:
        if not self._present:
            return
        apply_saved_list()

    # Input Tester ---------------------------------------------------------

    def _read_result(self) -> None:
        link = _link()
        result = None
        if link is not None:
            try:
                result = link.last_result()
            except Exception:
                logging.getLogger("system").exception("Input Tester result not read")
        line = _result_line(result)
        if line != (self._result_text, self._result_failed):
            self._result_text, self._result_failed = line
            self.changed.emit()

    def _check_paths(self) -> None:
        """Wrong game copies running, old tester entry; and the result again
        in case its watch was missed."""
        try:
            images = process_paths.running_images()
        except Exception:
            logging.getLogger("system").exception("Process list failed")
            images = []
        games = process_paths.game_path_problems(self._games, images)
        tester = process_paths.tester_path_problem(
            [r["path"] for r in self._games], _tester_path()
        )
        stale_games, stale_tester = self._stale_programs()
        if (
            games != self._game_problems or tester != self._tester_problem
            or stale_games != self._stale_games or stale_tester != self._stale_tester
        ):
            for line in games:
                if line not in self._game_problems:
                    _hh_log(f"game path: {line}", logging.WARNING)
            for line in [*stale_games, stale_tester]:
                if line and line not in [*self._stale_games, self._stale_tester]:
                    _hh_log(f"started before change: {line}", logging.WARNING)
            self._game_problems = games
            self._tester_problem = tester
            self._stale_games = stale_games
            self._stale_tester = stale_tester
            self.changed.emit()
        self._read_result()

    def _stale_programs(self) -> tuple[list[str], str]:
        """Warnings for programs on the list (games, the Input Tester)
        running since before Gremlin's last HidHide change; none when no
        change is known."""
        link = _link()
        change = None
        if link is not None:
            try:
                change = link.last_hidhide_change()
            except Exception:
                logging.getLogger("system").exception("HidHide change not read")
        if change is None:
            return [], ""
        tester = _tester_path()
        listed = [str(r["path"]) for r in self._games if r.get("path")]
        if not listed:
            return [], ""
        try:
            programs = process_paths.running_programs(listed)
        except Exception:
            logging.getLogger("system").exception("Process list failed")
            programs = []
        games: list[str] = []
        tester_text = ""
        for path, start in process_paths.started_before(programs, listed, change[0]):
            text = process_paths.stale_text(path, start, change[0])
            if tester and _same_path(path, tester):
                tester_text = tester_text or text
            else:
                games.append(text)
        return games, tester_text

    @QtCore.Slot(bool)
    def setPageOpen(self, open_: bool) -> None:
        """The page checks paths when shown and every 5 s while shown."""
        if open_:
            self._check_paths()
            self._path_timer.start()
        else:
            self._path_timer.stop()

    @QtCore.Property(str, notify=changed)
    def lastTesterResult(self) -> str:
        return self._result_text

    @QtCore.Property(bool, notify=changed)
    def lastTesterFailed(self) -> bool:
        return self._result_failed

    @QtCore.Property(list, notify=changed)
    def gamePathProblems(self) -> list:
        return list(self._game_problems)

    @QtCore.Property(str, notify=changed)
    def testerPathProblem(self) -> str:
        return self._tester_problem

    @QtCore.Property(list, notify=changed)
    def staleGameWarnings(self) -> list:  # noqa: N802 - QML name
        return list(self._stale_games)

    @QtCore.Property(str, notify=changed)
    def staleTesterWarning(self) -> str:  # noqa: N802 - QML name
        return self._stale_tester

    # Reset Devices (D-02-RESET-DEVICES) -------------------------------------

    @QtCore.Property(bool, notify=changed)
    def resetAvailable(self) -> bool:  # noqa: N802 - QML name
        """A physical USB game controller is plugged in."""
        return self._reset_available

    @QtCore.Slot(result="QVariant")
    def resetContext(self) -> dict:  # noqa: N802 - QML name
        """What the Reset Devices window needs from HidHide: the hidden
        ids, the program list, Gremlin names and the hidden devices that
        aren't plugged in."""
        hidden = [str(i) for i in get_blacklist()] if self._present else []
        saved = _saved_hidden() or []
        links = _load_links()
        known = []
        seen: set[tuple[int, int]] = set()
        for instance in [*hidden, *saved]:
            vid, pid = _vid_pid(instance)
            if vid is None or pid is None or (vid, pid) in seen:
                continue
            seen.add((vid, pid))
            known.append({
                "usb_id": instance,
                "name": links.get(instance) or links.get(instance.upper())
                or "HID-compliant game controller",
                "vid": vid,
                "pid": pid,
            })
        return {
            # HidHide's hidden list; without the driver, the saved one.
            "hiddenIds": hidden if self._present else saved,
            "games": [g["path"] for g in self._games],
            "names": {k: v for k, v in links.items() if v},
            "known": known,
        }

    @QtCore.Slot(result=str)
    def restartInputTester(self) -> str:  # noqa: N802 - QML name
        """Starts a fresh Input Tester; the old one is never closed from
        here (its own banner and the warning say to close it)."""
        return self.openInputTester()

    @QtCore.Property(str, notify=changed)
    def testerPath(self) -> str:
        return _tester_path()

    @QtCore.Property(bool, notify=changed)
    def testerOnList(self) -> bool:
        current = _tester_path()
        return bool(current) and any(_same_path(r["path"], current) for r in self._games)

    @QtCore.Property(str, notify=changed)
    def testerMessage(self) -> str:
        return self._tester_message

    @QtCore.Slot(result=str)
    def openInputTester(self) -> str:
        link = _link()
        if link is None:
            message = (
                "The Input Tester isn't built. From the program folder run: "
                "python tools/build_input_tester.py"
            )
        else:
            try:
                message = link.launch() or ""
            except Exception as exc:
                logging.getLogger("system").exception("Input Tester launch failed")
                message = f"The Input Tester didn't start: {exc}"
        self._tester_message = message
        self.changed.emit()
        return message

    @QtCore.Slot(result=bool)
    def addInputTesterToList(self) -> bool:
        current = _tester_path()
        if not self._present or not _hidhide_managed() or not current:
            return False
        if not self.addGame("Gremlin Input Tester", current):
            return False
        self._check_paths()
        return True

    @QtCore.Slot(result=bool)
    def updateTesterPath(self) -> bool:
        current = _tester_path()
        if not self._present or not _hidhide_managed() or not current:
            return False
        old = process_paths.old_tester_entry([r["path"] for r in self._games], current)
        if not old:
            return False
        name = next((r["name"] for r in self._games if r["path"] == old), "")
        self._games = [r for r in self._games if r["path"] != old]
        if not self.addGame(name or "Gremlin Input Tester", current):
            return False
        _hh_log(f"tester path updated {old} -> {current}", logging.INFO)
        self._check_paths()
        return True


def apply_on_start() -> None:
    """If Automatically Start is on, turn on Gremlin control and HidHide Enabled."""
    _ensure_options()
    if not _start_enabled():
        _hh_log("start skipped, Automatically Start is off", logging.INFO)
        return
    if not driver_present():
        _hh_log("start skipped, driver not present", logging.WARNING)
        return
    _hh_log("Automatically Start", logging.INFO)
    _mark_managed()
    _save_cloak(True)
    apply_saved_list()
    _tell_link_hidhide_changed("settings")


def apply_saved_list() -> None:
    """Write Gremlin's saved HidHide settings after the user has saved HidHide Enabled."""
    if not driver_present():
        _hh_log("apply skipped, driver not present", logging.WARNING)
        return
    if not _hidhide_managed():
        _hh_log("apply skipped, Gremlin control is off", logging.INFO)
        return
    _hh_log("apply saved list", logging.INFO)
    inverse = _apply_saved_list_mode()
    _hh_log(f"list mode block={inverse}", logging.INFO)
    gremlin = _gremlin_exe()
    gremlin_image = _full_image_name(gremlin)
    drop = set()
    if inverse:
        if gremlin:
            drop.add(gremlin.lower())
        if gremlin_image:
            drop.add(gremlin_image.lower())
    wanted = []
    for row in _load_games():
        image = _full_image_name(row["path"])
        if image:
            wanted.append(image)
        else:
            _hh_log(f"game path not converted {row['path']}", logging.WARNING)
    if not inverse and gremlin_image:
        wanted.append(gremlin_image)
    elif not inverse and not gremlin_image:
        _hh_log(f"gremlin path not converted {gremlin}", logging.WARNING)
    merged = []
    seen = set()
    for item in wanted:
        key = item.lower()
        if key in seen or not item or key in drop:
            continue
        seen.add(key)
        merged.append(item)
    _hh_log(f"whitelist count={len(merged)} inverse={inverse}", logging.INFO)
    set_whitelist(merged)
    _apply_saved_hidden()
    cloak = _apply_saved_cloak()
    _hh_log(f"cloak={cloak}", logging.INFO)
    # Programs started before this need a restart (D-02 addendum item 4).
    link = _link()
    if link is not None:
        try:
            link.record_hidhide_change("settings")
        except Exception:
            logging.getLogger("system").exception("HidHide change not noted")
