# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 2, B7: History, Device Pack and Auto Mapper (spec page 08).

Device Pack: a wire import that fails partway changes nothing in the profile
(GL-099, decision A3); Undo Import asks before putting back a file saved
again since (GL-031) and keeps a created Logical Device input that has
actions now (GL-032); output modules stay within the vJoy's size (GL-191).
History: reading waits for the writer instead of running its work on the
UI thread (GL-187), reads only what was appended (GL-041), shows module
files in words (GL-192) and applies Diagnostic logs and UI scale at once
on Restore (GL-115). Auto Mapper: every input and nested action counts as
using a vJoy output (GL-189), no assert on an odd binding (GL-190), and a
vJoy read back as an input is skipped and said (GL-313).
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import auto_mapper, device_initialization, history, plugin_manager
from gremlin.modules import module_file, store
from gremlin.profile import Profile
from gremlin.types import InputType, VjoyInput
from gremlin.ui import device_pack, history_model
from test.unit.test_device_pack_import import (  # noqa: F401
    _import,
    _map,
    _own_path,
    _targets,
    pack,  # noqa: F401
)

# --- Device Pack ---------------------------------------------------------------


def test_a_wire_import_failing_partway_changes_nothing(
    pack: dict, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """GL-099 / A3: the inputs it removed come back, the modes and Logical
    Device inputs it made go, and the note says so."""
    from gremlin.logical_device import LogicalDevice

    profile, uid = pack["profile"], pack["uid"]
    before_actions = set(profile.library._actions)

    def fail(*_args: object, **_kwargs: object) -> list:
        raise RuntimeError("disk full")

    monkeypatch.setattr(Profile, "add_inputs", fail)
    result = _import(pack, ["wire:Default", "wire:Combat"], createLogical=True)
    note = result.get("report") or result.get("error") or ""
    assert "nothing in the profile was changed" in note
    assert _targets(profile, uid, "Default") == {3: (1, 3)}
    assert not profile.modes.mode_exists("Combat")
    ident = LogicalDevice.Input.Identifier(InputType.JoystickButton, 7)
    assert not LogicalDevice().exists(ident)
    assert set(profile.library._actions) == before_actions


def test_undo_import_asks_before_losing_a_later_save(pack: dict) -> None:  # noqa: F811
    """GL-031 (08 Q5): a file saved again since the import is asked about."""
    path = _own_path(pack["name"])
    before = path.read_bytes()
    assert _import(pack, ["in.catalog"])["ok"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["catalog"] = {"rowHeight": 55}
    module_file.write_json(path, doc)
    later = path.read_bytes()
    asked = device_pack.undo_import()
    assert asked.get("ask") is True and not asked["ok"]
    assert path.name in asked["changed"]
    assert path.read_bytes() == later
    assert device_pack.can_undo_import()
    done = device_pack.undo_import(force=True)
    assert done["ok"], done
    assert path.read_bytes() == before


def test_undo_import_without_later_saves_does_not_ask(pack: dict) -> None:  # noqa: F811
    path = _own_path(pack["name"])
    before = path.read_bytes()
    assert _import(pack, ["in.catalog"])["ok"]
    done = device_pack.undo_import()
    assert done["ok"], done
    assert path.read_bytes() == before


def test_undo_import_keeps_a_logical_input_that_has_actions(pack: dict) -> None:  # noqa: F811
    """GL-032 (08 Q21)."""
    from gremlin.logical_device import LogicalDevice

    profile = pack["profile"]
    ident = LogicalDevice.Input.Identifier(InputType.JoystickButton, 7)
    assert _import(pack, ["wire:Default"], createLogical=True)["ok"]
    assert LogicalDevice().exists(ident)
    _map(profile, LogicalDevice.device_guid, 7, "Default", 1, 9)
    done = device_pack.undo_import()
    assert done["ok"], done
    assert LogicalDevice().exists(ident)
    assert "Kept on the Logical Device" in done["report"]
    assert "Button 7" in done["report"]


def test_an_output_module_stays_within_the_vjoy(
    pack: dict, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    """GL-191 (08 Q18): the pack's vJoy 2 has buttons 1-3; this vJoy 1 has 2."""
    vjoy = SimpleNamespace(
        is_virtual=True,
        vjoy_id=1,
        device_guid="{AAAAAAAA-0000-0000-0000-000000000001}",
        button_count=2,
        axis_count=0,
        axis_map=[],
        hat_count=0,
        name="vJoy Device",
    )
    monkeypatch.setattr(store, "live_devices", lambda: [vjoy])
    result = _import(pack, ["out:vjoy_2.checks"])
    assert result["ok"], result
    written = [
        p for p, _ in device_pack._last_import["files"] if p.suffix == ".json"
    ]
    assert written, result
    claim = json.loads(written[-1].read_text(encoding="utf-8"))["claim"]
    assert claim["buttons"] == [1, 2]
    assert "Button 3" in result["report"]


def test_module_text_reads_like_the_pack_rows() -> None:
    """GL-192 (08 Q13): words, not raw JSON."""
    doc = {
        "claim": {"buttons": [1, 3], "friendly": {"button:3": "Fire"}},
        "calibration": {"1": [0, 10, 20, 30]},
    }
    text = device_pack.module_text(doc, ["claim", "calibration"])
    assert "Checked controls:" in text
    assert "Button 3 — Fire" in text
    assert "Axis 1: 0 to 30" in text
    assert "{" not in text and '"' not in text
    side = {"text": json.dumps(doc)}
    assert history_model._module_text(side, ["claim"]).startswith("Checked controls:")


# --- History -------------------------------------------------------------------


@pytest.fixture
def folder(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    path = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: path)
    monkeypatch.setattr(history, "_pruned", True)
    yield path
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    history.flush()


def test_reading_waits_for_the_writer_instead_of_doing_its_work(folder: Path) -> None:
    """GL-187: queued work runs on the History thread, never on the caller's
    thread beside the writer."""
    busy = threading.Event()
    go = threading.Event()
    ran_on: list[str] = []

    def hold() -> None:
        busy.set()
        go.wait(5)

    history.later(hold)
    assert busy.wait(5)
    history.later(lambda: ran_on.append(threading.current_thread().name))
    threading.Timer(0.3, go.set).start()
    history.entries()
    assert ran_on, "the queued work was not done before reading"
    assert ran_on[0] != threading.current_thread().name


def test_only_what_was_appended_is_read_again(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """GL-041: the window coming to the front doesn't reread every file."""
    folder.mkdir(parents=True)
    path = folder / "settings.jsonl"
    lines = [
        json.dumps({"id": f"e{n}", "at": float(n), "area": "settings"}) + "\n"
        for n in range(50)
    ]
    path.write_text("".join(lines), encoding="utf-8")
    parsed: list[int] = []
    real = history._parse

    def count(text: str) -> list[dict]:
        parsed.append(len(text))
        return real(text)

    monkeypatch.setattr(history, "_parse", count)
    assert len(history.entries("settings")) == 50
    parsed.clear()
    assert len(history.entries("settings")) == 50
    assert sum(parsed) == 0
    extra = json.dumps({"id": "new", "at": 99.0, "area": "settings"}) + "\n"
    with open(path, "a", encoding="utf-8", newline="") as out:
        out.write(extra)
    found = history.entries("settings")
    assert [e["id"] for e in found][:1] == ["new"] and len(found) == 51
    assert sum(parsed) == len(extra)


def test_a_file_rewritten_or_cut_is_read_right(folder: Path) -> None:
    folder.mkdir(parents=True)
    path = folder / "settings.jsonl"
    one = json.dumps({"id": "a", "at": 1.0, "area": "settings"}) + "\n"
    two = json.dumps({"id": "b", "at": 2.0, "area": "settings"}) + "\n"
    path.write_text(one + two, encoding="utf-8")
    assert [e["id"] for e in history.entries("settings")] == ["b", "a"]
    # The clean-up rewrites it shorter, with other text.
    module_file.write_text(path, two, newline="")
    assert [e["id"] for e in history.entries("settings")] == ["b"]
    # A line cut by a crash, then the next entry on a line of its own.
    with open(path, "a", encoding="utf-8", newline="") as out:
        out.write('{"id": "cut", "at"')
    assert [e["id"] for e in history.entries("settings")] == ["b"]
    three = json.dumps({"id": "c", "at": 3.0, "area": "settings"}) + "\n"
    with open(path, "a", encoding="utf-8", newline="") as out:
        out.write("\n" + three)
    assert [e["id"] for e in history.entries("settings")] == ["c", "b"]


def _register(
    cfg: object, key: tuple[str, str, str], kind: object, value: object, props: dict
) -> None:
    cfg.register(*key, kind, value, "", props, True)  # type: ignore[attr-defined]


def test_restore_applies_logs_and_ui_scale_at_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """GL-115 (01 Q7): as the Options control does."""
    from gremlin import config
    from gremlin.signal import signal
    from gremlin.types import PropertyType
    from gremlin.ui import log_option

    monkeypatch.setattr(config, "_config_file_path", str(tmp_path / "c.json"))
    cfg = config.Configuration()
    log_key = ("global", "general", "log-level")
    _register(cfg, log_key, PropertyType.String, "Warning", {})
    scale_key = ("ui", "general", "ui-scale")
    _register(cfg, scale_key, PropertyType.Int, 100, {"min": 70, "max": 200})
    system = logging.getLogger("system")
    old_level, old_disabled = system.level, system.disabled
    scaled: list[bool] = []
    signal.uiScaleChanged.connect(lambda: scaled.append(True))
    try:
        cfg.set("global", "general", "log-level", "Warning")
        log_option.apply_log_level("Warning")
        ok, _message = history_model._restore_settings(
            {"global/general/log-level": "Error", "ui/general/ui-scale": 150}
        )
        assert ok
        assert system.level == logging.ERROR
        assert cfg.value("global", "general", "log-level") == "Error"
        assert scaled
        assert cfg.value("ui", "general", "ui-scale") == 150
    finally:
        log_option.apply_log_level("Warning")
        system.setLevel(old_level)
        system.disabled = old_disabled


def test_an_input_restore_closes_the_action_panes_first() -> None:
    """GL-098: the window asks the main window to close the panes first."""
    entry = {"area": "profile", "kind": "input", "before": None, "after": None}
    assert history_model.describe(entry)["closesPanes"] is True
    entry = {"area": "settings", "kind": "save", "before": {}, "after": {}}
    assert history_model.describe(entry)["closesPanes"] is False


# --- Auto Mapper ---------------------------------------------------------------


def _vjoy_map(item: object, vjoy: int, out: int) -> object:
    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = vjoy
    action.vjoy_input_id = out
    action.vjoy_input_type = InputType.JoystickButton
    return action


def test_every_input_and_nested_action_counts_as_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GL-189 (08 Q7): a stick not plugged in, inside a Tempo too."""
    from gremlin import shared_state

    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    unplugged = uuid.uuid4()
    item = profile.get_input_item(
        unplugged, InputType.JoystickButton, 1, "Default", create_if_missing=True
    )
    tempo = plugin_manager.PluginManager().create_instance(
        "Tempo", InputType.JoystickButton
    )
    tempo.insert_action(_vjoy_map(item, 1, 4), "short")
    item.add_item_binding().root_action.insert_action(tempo, "children")
    top = profile.get_input_item(
        unplugged, InputType.JoystickButton, 2, "Default", create_if_missing=True
    )
    top.add_item_binding().root_action.insert_action(_vjoy_map(top, 1, 5), "children")
    used = auto_mapper.AutoMapper(profile)._get_used_vjoy_inputs("Default")
    assert VjoyInput(1, InputType.JoystickButton, 4) in used
    assert VjoyInput(1, InputType.JoystickButton, 5) in used


def test_a_binding_without_the_usual_root_is_no_assert() -> None:
    """GL-190: skipped, not an AssertionError (on a plugged-in stick: the
    old code looked only at those)."""
    sticks = device_initialization.physical_devices()
    if not sticks:
        pytest.skip("no fake stick")
    profile = Profile()
    item = profile.get_input_item(
        sticks[0].device_guid.uuid,
        InputType.JoystickButton,
        1,
        "Default",
        create_if_missing=True,
    )
    binding = item.add_item_binding()
    binding.root_action = None
    assert auto_mapper.AutoMapper(profile)._get_used_vjoy_inputs("Default") == []


def test_a_vjoy_read_back_as_an_input_is_skipped_and_said(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """GL-313: no actions to it, and the result line says why."""
    from gremlin.modules import auto_map

    vjoy = SimpleNamespace(vjoy_id=1, axis_map=[], button_count=8, hat_count=0)
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [vjoy])
    monkeypatch.setattr(device_initialization, "output_vjoy_devices", lambda: [])
    stick = uuid.uuid4()
    monkeypatch.setattr(
        auto_map,
        "input_modules",
        lambda: [
            {
                "slug": "stick",
                "name": "Stick",
                "guid": "{" + str(stick).upper() + "}",
                "claim": {"buttons": [1, 2], "axes": [], "hats": []},
            }
        ],
    )
    monkeypatch.setattr(
        auto_map,
        "output_modules",
        lambda: [
            {
                "slug": "vjoy_1",
                "name": "vJoy 1",
                "vjoyId": 1,
                "claim": {"buttons": [1, 2], "axes": [], "hats": []},
            }
        ],
    )
    profile = Profile()
    mapper = auto_mapper.AutoMapper(profile)
    assert mapper._vjoy_limits(1) is None
    text = mapper.generate_module_mappings(
        ["stick"], ["vjoy_1"], auto_mapper.AutoMapperOptions()
    )
    assert "vJoy 1 is used as an input" in text
    items = profile.inputs.get(stick, [])
    assert not any(item.action_sequences for item in items)


def test_a_profile_filter_matches_the_path_however_written(tmp_path: Path) -> None:
    """For GL-194 (B5a): the row's filter passes the open profile's path."""
    saved = tmp_path / "Sub" / "My Profile.xml"
    entry = {"area": "profile", "subject": {"profile": str(saved)}}
    other = str(tmp_path / "sub" / "." / "my profile.XML").replace("\\", "/")
    assert history_model._matches(entry, {"profile": other})
    assert not history_model._matches(entry, {"profile": str(tmp_path / "x.xml")})


def test_a_pack_mode_goes_into_the_look_alike_mode_here(pack: dict) -> None:  # noqa: F811
    """B4 / GL-154: the pack's "Combat" is this profile's "combat"; no new
    look-alike mode, no roll-back."""
    profile, uid = pack["profile"], pack["uid"]
    profile.modes.add_mode("combat")
    result = _import(pack, ["wire:Combat"])
    assert result["ok"], result
    assert "wires were not written" not in result["report"]
    assert "Combat" not in profile.modes.mode_names()
    assert set(_targets(profile, uid, "combat")) == {2}
