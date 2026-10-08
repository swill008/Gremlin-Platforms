# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A stand-in for the Device Library's owners (library, library_profiles,
library_copy, library_swap) with the contract's shapes, for the window and
model tests (test_device_library_LU_*.py). It records every call."""

from __future__ import annotations

import copy as _copy
import threading
import types
from pathlib import Path


def _setup(
    key: str,
    device: str,
    name: str,
    created: str,
    origin: str = "user",
    own: bool = True,
    reason: str = "",
    holds: list | None = None,
    description: str = "",
    profiles: list | None = None,
    vjoys: dict | None = None,
    history: list | None = None,
) -> dict:
    return {
        "key": key,
        "device": device,
        "name": name,
        "description": description,
        "created": created,
        "origin": origin,
        "own": own,
        "reason": reason,
        "holds": holds
        if holds is not None
        else ["setup", "button_map", "appearance", "calibration", "bindings"],
        "profiles": profiles or [],
        "vjoys": vjoys or {},
        "pack": f"{key}.zip",
        "history": history or [],
    }


def sample_devices() -> list[dict]:
    return [
        {
            "key": "dev-00000001",
            "name": "Left throttle",
            "description": "VKB Gladiator, the one with the sticky slider",
            "state": "connected",
            "guid": "{AAAA-0001}",
            "module": "left-throttle",
            "setups": [
                _setup(
                    "set-00000001",
                    "dev-00000001",
                    "DCS F-16, Viper layout",
                    "2026-10-02T14:20:00",
                    description=(
                        "My main F-16 layout. Throttle slider = range knob,"
                        " pinky switch = mode."
                    ),
                    profiles=[
                        {
                            "name": "DCS.xml",
                            "path": "C:/p/DCS.xml",
                            "modes": ["Default", "Landing", "AAR"],
                            "actions": 212,
                        }
                    ],
                    vjoys={"1": 38, "2": 4},
                    history=[
                        {
                            "at": "2026-10-08T10:00:00",
                            "text": "Copied to Right stick (Setup, Bindings)",
                        },
                        {"at": "2026-10-04T10:00:00", "text": "Description edited"},
                        {"at": "2026-10-02T14:20:00", "text": "Saved from DCS.xml"},
                    ],
                ),
                _setup(
                    "set-00000002",
                    "dev-00000001",
                    "Star Citizen 4.0",
                    "2026-09-21T09:00:00",
                    origin="autosave",
                    own=True,
                    reason="Autosave: before Swap with Right stick",
                ),
                _setup(
                    "set-00000003",
                    "dev-00000001",
                    "Autosave: before Copy from Old Warthog",
                    "2026-10-08T08:00:00",
                    origin="autosave",
                    own=False,
                    reason="Autosave: before Copy from Old Warthog",
                ),
            ],
        },
        {
            "key": "dev-00000002",
            "name": "Right stick",
            "description": "VKB Gunfighter Mk IV",
            "state": "connected",
            "guid": "{BBBB-0002}",
            "module": "right-stick",
            "setups": [
                _setup(
                    "set-00000004",
                    "dev-00000002",
                    "Elite night setup",
                    "2026-09-01T20:00:00",
                    profiles=[
                        {
                            "name": "Elite.xml",
                            "path": "C:/p/Elite.xml",
                            "modes": ["Default"],
                            "actions": 40,
                        }
                    ],
                ),
            ],
        },
        {
            "key": "dev-00000003",
            "name": "Rudder pedals",
            "description": "MFG Crosswind",
            "state": "not_connected",
            "guid": "{CCCC-0003}",
            "module": "rudder-pedals",
            "seen": "2026-10-05T18:30:00",
            "setups": [],
        },
        {
            "key": "dev-00000004",
            "name": "Old Warthog stick",
            "description": "Replaced Oct 2026, gimbal worn",
            "state": "deleted",
            "guid": "{DDDD-0004}",
            "module": "",
            "setups": [
                _setup(
                    "set-00000005",
                    "dev-00000004",
                    "Autosave: stick deleted",
                    "2026-10-01T12:00:00",
                    origin="autosave",
                    own=False,
                    reason="Autosave: stick deleted",
                ),
            ],
        },
        {
            "key": "dev-00000005",
            "name": "Friend's MFD pair",
            "description": "From Sam's pack",
            "state": "not_connected",
            "guid": "",
            "module": "",
            "setups": [
                _setup(
                    "set-00000006",
                    "dev-00000005",
                    "Sam's MFDs",
                    "2026-09-30T18:00:00",
                    origin="pack",
                    own=True,
                    reason="From Sam's pack",
                ),
            ],
        },
    ]


class FakeLibrary:
    """Every owner function the model calls, with recorded calls."""

    def __init__(self) -> None:
        self.devs = sample_devices()
        self.calls: list[tuple] = []
        self.conf = {
            "keep": 10,
            "default_parts": ["setup", "button_map", "appearance", "bindings"],
            "folder": "C:/Users/you/Gremlin Platforms/device library",
        }
        self.last: dict | None = None
        # A test can hold a change running until it sets this.
        self.gate: threading.Event | None = None
        self.fail: dict[str, str] = {}
        # A picture file the window shows as set-00000001's photo (S11).
        self.photo_file = ""
        # The vJoy devices that exist (S30).
        self.vjoys = [1, 2, 3]
        # The thread each profile read ran on (Gap 9).
        self.threads: dict[str, str] = {}
        self.plan_threads: list[str] = []

    def _rec(self, name: str, *args: object) -> None:
        self.calls.append((name, *args))

    def _all_setups(self) -> list[dict]:
        return [s for d in self.devs for s in d["setups"]]

    def _find(self, key: str) -> dict | None:
        for d in self.devs:
            if d["key"] == key:
                return d
            for s in d["setups"]:
                if s["key"] == key:
                    return s
        return None

    def _wait(self) -> None:
        if self.gate is not None:
            self.gate.wait(10)

    def _res(self, name: str, **extra: object) -> dict:
        if name in self.fail:
            return {"ok": False, "error": self.fail[name], "warnings": [], "notes": []}
        return {"ok": True, "error": "", "warnings": [], "notes": [], **extra}

    # library
    def folder(self) -> Path:
        return Path(self.conf["folder"])

    def settings(self) -> dict:
        return dict(self.conf)

    def set_settings(self, values: dict) -> None:
        self._rec("set_settings", dict(values))
        self.conf.update(values)

    def devices(self) -> list[dict]:
        return _copy.deepcopy(self.devs)

    def device(self, key: str) -> dict | None:
        return next((d for d in self.devs if d["key"] == key), None)

    def find_device(self, name: str, guid: str = "") -> dict | None:
        return next((d for d in self.devs if d["name"] == name), None)

    def save_setup(
        self,
        device_name: str,
        guid: str,
        profiles: list[Path],
        *,
        own: bool = True,
        reason: str = "",
        parts: list[str] | None = None,
    ) -> dict:
        self._rec("save_setup", device_name, guid, [str(p) for p in profiles])
        dev = next(d for d in self.devs if d["name"] == device_name)
        new = _setup(
            f"set-{len(self._all_setups()) + 100:08x}",
            dev["key"],
            "DCS.xml",
            "2026-10-08T15:00:00",
        )
        dev["setups"].insert(0, new)
        return self._res("save_setup", setups=[new])

    def autosave(self, *a: object, **k: object) -> dict:
        return self._res("autosave")

    def set_last_change(self, op: str, keys: list[str], label: str) -> None:
        self.last = {
            "op": op,
            "autosaves": keys,
            "label": label,
            "at": "2026-10-08T15:00:00",
        }

    def last_change(self) -> dict | None:
        return self.last

    def rename(self, key: str, name: str) -> dict:
        self._rec("rename", key, name)
        item = self._find(key)
        if item is not None:
            item["name"] = name
            if item.get("origin") == "autosave":
                item["own"] = True
        return self._res("rename")

    def describe(self, key: str, text: str) -> dict:
        self._rec("describe", key, text)
        item = self._find(key)
        if item is not None:
            item["description"] = text
            if item.get("origin") == "autosave":
                item["own"] = True
        return self._res("describe")

    def delete(self, key: str) -> dict:
        self._rec("delete", key)
        for d in self.devs:
            d["setups"] = [s for s in d["setups"] if s["key"] != key]
        self.devs = [d for d in self.devs if d["key"] != key]
        return self._res("delete")

    def import_pack(self, path: Path) -> dict:
        self._rec("import_pack", str(path))
        new = _setup(
            "set-000000aa",
            "dev-00000002",
            path.stem,
            "2026-10-08T16:00:00",
            origin="pack",
            reason="From Sam's pack",
        )
        self.devs[1]["setups"].insert(0, new)
        return self._res("import_pack", setup=new)

    def export_setup(self, key: str, dest: Path) -> dict:
        self._rec("export_setup", key, str(dest))
        return self._res("export_setup")

    def tidy_preview(self, months: int) -> list[dict]:
        self._rec("tidy_preview", months)
        return [
            {
                "key": "set-00000005",
                "label": "Old Warthog stick › Autosave: stick deleted (2026-10-01)",
                "bytes": 20480,
            },
            {
                "key": "set-00000003",
                "label": "Left throttle › Autosave: before Copy from Old Warthog",
                "bytes": 10240,
            },
        ][: 2 if months <= 1 else 1]

    def tidy(self, keys: list[str]) -> dict:
        self._rec("tidy", list(keys))
        for k in keys:
            self.delete(k)
        return self._res("tidy")

    def size_bytes(self) -> int:
        return 48 * 1024 * 1024

    def search(self, text: str) -> list[str]:
        t = text.lower()
        out = []
        for d in self.devs:
            if t in d["name"].lower() or t in d["description"].lower():
                out.append(d["key"])
            for s in d["setups"]:
                hay = " ".join(
                    [s["name"], s["description"], s["reason"]]
                    + [p["name"] + " " + " ".join(p["modes"]) for p in s["profiles"]]
                    + [f"vjoy {v}" for v in s["vjoys"]]
                ).lower()
                if t in hay:
                    out.append(s["key"])
        return out

    def add_history(self, key: str, text: str) -> None:
        pass

    def inputs(self, key: str) -> dict:
        self._rec("inputs", key)
        if key == "dev-00000003":
            return {"buttons": 0, "axes": 3, "hats": 0, "from": "module file"}
        return {"buttons": 32, "axes": 6, "hats": 1, "from": "device"}

    def photo(self, key: str) -> str:
        self._rec("photo", key)
        return self.photo_file if key == "set-00000001" else ""

    def note_seen(self, guids: list[str]) -> None:
        self._rec("note_seen", sorted(guids))

    def pack_path(self, key: str) -> Path:
        return Path(f"{key}.zip")

    # library_profiles
    def profiles_using(self, guids: list[str], always_open: bool = False) -> list[dict]:
        self._rec("profiles_using", list(guids))
        row = self.open_profile_row(guids, always_open)
        return ([row] if row else []) + self.saved_profiles_using(
            guids, row["path"] if row else ""
        )

    def is_open_path(self, path: Path | str) -> bool:
        return str(path) in ("", ".") or str(path) == str(Path("C:/p/DCS.xml"))

    def open_profile_row(
        self, guids: list[str], always_open: bool = False
    ) -> dict | None:
        self._rec("open_profile_row", list(guids), always_open)
        self.threads["open"] = threading.current_thread().name
        if "{CCCC-0003}" in guids:
            # The open profile, never saved (path "").
            return {"path": "", "name": "Untitled", "open": True, "actions": 5}
        count = 212 if {"{AAAA-0001}", "{BBBB-0002}"} & set(guids) else 0
        if not count and not always_open:
            return None
        return {
            "path": "C:/p/DCS.xml",
            "name": "DCS.xml",
            "open": True,
            "actions": count,
        }

    def saved_profiles_using(self, guids: list[str], open_path: str = "") -> list[dict]:
        self._rec("saved_profiles_using", list(guids), open_path)
        self.threads["saved"] = threading.current_thread().name
        if "{CCCC-0003}" in guids or not {"{AAAA-0001}", "{BBBB-0002}"} & set(guids):
            return []
        return [
            {
                "path": "C:/p/StarCitizen.xml",
                "name": "StarCitizen.xml",
                "open": False,
                "actions": 90,
            },
            {
                "path": "C:/p/Elite.xml",
                "name": "Elite.xml",
                "open": False,
                "actions": 40,
            },
        ]

    # library_copy
    def plan_copy(
        self,
        setup_key: str,
        target_name: str,
        target_guid: str,
        parts: list[str],
        profiles: list[Path],
        modes: list[str],
    ) -> dict:
        self._rec(
            "plan_copy",
            setup_key,
            target_name,
            list(parts),
            [str(p) for p in profiles],
            list(modes),
            target_guid,
        )
        self.plan_threads.append(threading.current_thread().name)
        current = (
            {
                "holds": ["setup", "button_map", "bindings"],
                "sourceModes": ["Default", "Combat"],
            }
            if setup_key.startswith("dev-")
            else {}
        )
        return self._res(
            "plan_copy",
            **current,
            warnings=[
                f"{target_name} has 24 buttons: 6 bindings on Buttons 25–30 stay"
                " behind.",
                f"{target_name} has no Hat 2: 4 bindings stay behind.",
                f"{target_name} has no Slider 1: its curve stays behind.",
            ],
        )

    def copy(
        self,
        setup_key: str,
        target_name: str,
        target_guid: str,
        parts: list[str],
        profiles: list[Path],
        modes: list[str],
    ) -> dict:
        self._rec(
            "copy",
            setup_key,
            target_name,
            list(parts),
            [str(p) for p in profiles],
            list(modes),
            target_guid,
        )
        self._wait()
        res = self._res("copy")
        if res["ok"]:
            self.set_last_change("copy", ["set-x"], f"Copy to {target_name}")
        return res

    def plan_output(
        self,
        device_name: str,
        guid: str,
        moves: dict[int, int],
        swap_other: bool,
        profiles: list[Path],
    ) -> dict:
        self._rec(
            "plan_output",
            device_name,
            dict(moves),
            swap_other,
            [str(p) for p in profiles],
            guid,
        )
        to1 = moves.get(1, 1)
        return self._res(
            "plan_output",
            rows=[
                {"vjoy": 1, "inputs": 38, "to": to1, "changes": to1 != 1},
                {
                    "vjoy": 2,
                    "inputs": 4,
                    "to": moves.get(2, 2),
                    "changes": moves.get(2, 2) != 2,
                },
            ],
            others=[
                {
                    "guid": "{BBBB-0002}",
                    "name": "Right stick",
                    "vjoy": 2,
                    "to": 1,
                    "inputs": 12,
                }
            ]
            if to1 == 2
            else [],
            warnings=[
                "vJoy 2's output module doesn't claim Button 31–32: 2 bindings would"
                " send nothing.",
                'Macro "Gear up" (Button 7) names vJoy 1 inside it: not changed,'
                " check it yourself.",
            ],
        )

    def change_output(
        self,
        device_name: str,
        guid: str,
        moves: dict[int, int],
        swap_other: bool,
        profiles: list[Path],
    ) -> dict:
        self._rec(
            "change_output",
            device_name,
            dict(moves),
            swap_other,
            [str(p) for p in profiles],
            guid,
        )
        self.set_last_change(
            "output", ["set-y"], f"Change vJoy Output of {device_name}"
        )
        return self._res("change_output")

    def restore(self, setup_key: str) -> dict:
        return self._res("restore")

    def undo_last(self) -> dict:
        self._rec("undo_last")
        self.last = None
        return self._res("undo_last", notes=["Put back."])

    # library_swap
    def plan_swap(
        self,
        first: tuple[str, str],
        second: tuple[str, str],
        parts: list[str],
        profiles: list[Path],
    ) -> dict:
        self._rec(
            "plan_swap",
            tuple(first),
            tuple(second),
            list(parts),
            [str(p) for p in profiles],
        )
        return self._res(
            "plan_swap",
            warnings=[
                f"{first[0]} → {second[0]}: Buttons 25–30 (6 bindings), Hat 2 (4)"
                f" stay on {first[0]}.",
                f"{second[0]} → {first[0]}: Rotary 1 (2 bindings) stays on"
                f" {second[0]}.",
            ],
        )

    def swap(
        self,
        first: tuple[str, str],
        second: tuple[str, str],
        parts: list[str],
        profiles: list[Path],
    ) -> dict:
        self._rec(
            "swap", tuple(first), tuple(second), list(parts), [str(p) for p in profiles]
        )
        self.set_last_change("swap", ["a", "b"], f"Swap {first[0]} with {second[0]}")
        return self._res("swap")

    def api(self) -> types.SimpleNamespace:
        """The namespace the model takes (library, profiles, copy, swap)."""
        return types.SimpleNamespace(
            library=self,
            profiles=self,
            copy=self,
            swap=self,
            vjoy_ids=lambda: list(self.vjoys),
        )
