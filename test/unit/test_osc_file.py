# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC's own module file (gremlin.osc_device_file, decision D-09-OSC-FILE):
rows and server settings through the module store (History records it,
other keys kept, a damaged file never written over), the old-profile merge,
the profile backup, the one-time settings copy from the configuration and
the reload after the file is replaced."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import history_modules
from gremlin import osc_device_file as odf
from gremlin.modules import store

OSC_GUID = "A7C3E91B-4D2F-4E18-9B06-2F8C1D5A6E70"


class FakeRows:
    """Stands in for gremlin.osc_rows.OscRows' dict API (contract)."""

    def __init__(self, inputs: list | None = None) -> None:
        self.inputs = inputs or []
        self.dirty = False
        self.saved = 0

    def to_dict(self) -> dict:
        return json.loads(json.dumps({"inputs": self.inputs}))

    def load_dict(self, d: dict) -> None:
        self.inputs = json.loads(json.dumps(d.get("inputs", [])))

    def mark_saved(self) -> None:
        self.dirty = False
        self.saved += 1


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    return folder


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, str]]:
    seen: list[tuple[Path, str]] = []
    monkeypatch.setattr(
        history_modules,
        "note_write",
        lambda path, text, old: seen.append((Path(path), text)),
    )
    return seen


@pytest.fixture
def emitted(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Signals said, by name, whether or not gremlin.signal has them yet."""
    import gremlin.signal

    seen: list[str] = []

    class Sig:
        def __init__(self, name: str) -> None:
            self.name = name

        def emit(self) -> None:
            seen.append(self.name)

    names = (
        "oscDeviceReloaded",
        "oscDeviceModified",
        "oscServerSettingsChanged",
        "logicalDeviceReloaded",
        "logicalDeviceModified",
    )
    fake = SimpleNamespace(**{n: Sig(n) for n in names})
    monkeypatch.setattr(gremlin.signal, "signal", fake)
    return seen


def _row(uid: str, kind: str, number: int, address: str, **extra: object) -> dict:
    row = {"uid": uid, "type": kind, "id": number, "label": address}
    row.update(extra)
    return row


def _doc(modules: Path) -> dict:
    return json.loads((modules / "osc.json").read_text(encoding="utf-8"))


def test_the_file_is_the_osc_module_file(modules: Path) -> None:
    assert odf.path() == modules / "osc.json"


def test_save_writes_rows_keeps_other_keys_and_history_records_it(
    modules: Path, writes: list
) -> None:
    (modules / "osc.json").write_text(
        json.dumps({"notes": "kept", "server": {"port": 9001}}), encoding="utf-8"
    )
    rows = FakeRows([_row("a" * 32, "button", 1, "/a", mode="button")])
    rows.dirty = True
    assert odf.save(rows) is True
    doc = _doc(modules)
    assert doc["notes"] == "kept" and doc["server"] == {"port": 9001}
    assert doc["inputs"][0]["uid"] == "a" * 32
    assert doc["kind"] == "control.hardware" and doc["direction"] == "source"
    assert doc["device"] == "OSC" and doc["boundGuidLocal"] == OSC_GUID
    assert rows.dirty is False
    assert [p.name for p, _ in writes] == ["osc.json"]


def test_save_if_dirty_saves_only_a_change(
    modules: Path, writes: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = FakeRows([_row("a" * 32, "button", 1, "/a")])
    monkeypatch.setattr(odf, "_rows", lambda r: rows if r is None else r)
    assert odf.save_if_dirty() is False
    assert not (modules / "osc.json").exists()
    rows.dirty = True
    assert odf.save_if_dirty() is True
    assert _doc(modules)["inputs"][0]["label"] == "/a"


def test_load_of_a_missing_file_is_empty_with_default_settings(
    modules: Path,
) -> None:
    rows = FakeRows([_row("b" * 32, "axis", 1, "/x")])
    server = odf.load(rows)
    assert rows.inputs == [] and rows.saved == 1
    assert server == odf.SERVER_DEFAULTS
    assert server["host"] == "" and server["port"] == 8001
    assert server["output_port"] == 8000 and server["autorelease_delay_ms"] == 250
    assert not (modules / "osc.json").exists()


def test_load_reads_back_rows_and_server(modules: Path, writes: list) -> None:
    inputs = [_row("c" * 32, "axis", 2, "/fader", mode="axis", range_min=-1.0)]
    odf.save(FakeRows(inputs))
    assert odf.write_server({"port": "9001", "host": "10.0.0.5"}) is True
    rows = FakeRows()
    server = odf.load(rows)
    assert rows.inputs == inputs
    assert server["port"] == 9001 and server["host"] == "10.0.0.5"
    assert server["enabled"] is True
    assert odf.read_server() == server


def test_write_server_keeps_rows_says_the_change_and_skips_no_change(
    modules: Path, writes: list, emitted: list
) -> None:
    odf.save(FakeRows([_row("d" * 32, "button", 1, "/b")]))
    assert odf.write_server({"enabled": False}) is True
    assert emitted == ["oscServerSettingsChanged"]
    doc = _doc(modules)
    assert doc["inputs"][0]["uid"] == "d" * 32
    assert doc["server"]["enabled"] is False and doc["server"]["port"] == 8001
    assert odf.write_server({"enabled": False}) is False
    assert len(writes) == 2


def test_a_damaged_file_is_never_written_over(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import module_file

    monkeypatch.setattr(module_file, "report_refused", lambda damaged: None)
    damaged = modules / "osc.json"
    damaged.write_text("{ not json", encoding="utf-8")
    rows = FakeRows([_row("e" * 32, "button", 1, "/a")])
    rows.dirty = True
    assert odf.save(rows) is False
    assert odf.write_server({"port": 9000}) is False
    assert odf.migrate_settings_from_config() is False
    assert damaged.read_text(encoding="utf-8") == "{ not json"
    assert rows.dirty is True


def test_merge_matches_type_number_and_address_else_adds_with_a_new_number(
    modules: Path, writes: list
) -> None:
    rows = FakeRows(
        [_row("f" * 32, "button", 1, "/a"), _row("1" * 32, "axis", 1, "/x")]
    )
    old = {
        "inputs": [
            {"type": "button", "id": 1, "label": "/A"},  # same (address casefold)
            {"type": "button", "id": 2, "label": "/b"},  # new, number free
            {"type": "axis", "id": 1, "label": "/y"},  # new, number taken
        ]
    }
    dry = odf.merge_profile_rows(old, dry_run=True, rows=rows)
    assert len(rows.inputs) == 2 and writes == []
    result = odf.merge_profile_rows(old, rows=rows)
    assert result.uid_map == dry.uid_map  # dry run and real merge agree
    assert result.uid_map[("button", 1)] == "f" * 32
    assert result.added == ["/b", "/y"]
    by_label = {r["label"]: r for r in rows.inputs}
    assert by_label["/b"]["id"] == 2
    assert by_label["/y"]["id"] == 2 and by_label["/y"]["type"] == "axis"
    assert result.uid_map[("axis", 1)] == by_label["/y"]["uid"]
    assert [r["uid"] for r in _doc(modules)["inputs"]] == [
        r["uid"] for r in rows.inputs
    ]
    # A second merge of the same profile adds nothing and writes nothing.
    again = odf.merge_profile_rows(old, rows=rows)
    assert again.added == [] and again.uid_map == result.uid_map
    assert len(writes) == 1


def test_a_row_carrying_a_uid_keeps_it(modules: Path, writes: list) -> None:
    rows = FakeRows()
    result = odf.merge_profile_rows(
        {"inputs": [_row("9" * 32, "button", 3, "/c", mode="change")]}, rows=rows
    )
    assert result.uid_map == {("button", 3): "9" * 32}
    assert rows.inputs[0]["uid"] == "9" * 32 and rows.inputs[0]["mode"] == "change"


def test_a_matching_row_only_in_memory_still_reaches_the_file(
    modules: Path, writes: list
) -> None:
    rows = FakeRows([_row("2" * 32, "button", 1, "/a")])
    result = odf.merge_profile_rows(
        {"inputs": [{"type": "button", "id": 1, "label": "/a"}]}, rows=rows
    )
    assert result.added == []
    assert _doc(modules)["inputs"][0]["uid"] == "2" * 32


def test_backup_old_is_made_once(modules: Path, tmp_path: Path) -> None:
    profile = tmp_path / "game.xml"
    profile.write_text("<profile version='15'/>", encoding="utf-8")
    made = odf.backup_old(profile, 15)
    assert made == tmp_path / "game.xml.v15.bak"
    assert made.read_text(encoding="utf-8") == "<profile version='15'/>"
    profile.write_text("<profile version='16'/>", encoding="utf-8")
    assert odf.backup_old(profile, 15) is None
    assert made.read_text(encoding="utf-8") == "<profile version='15'/>"
    assert odf.backup_old(profile, 14) == tmp_path / "game.xml.v14.bak"


def test_migrate_copies_the_configuration_once_and_drops_this_pcs_address(
    modules: Path, writes: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "enabled": False,
        "host": "192.168.1.50",
        "port": "9100",
        "output_host": "10.0.0.9",
        "output_port": "9200",
        "autorelease_no_arg": False,
        "autorelease_delay_ms": "500",
        "pad_args": True,
    }
    monkeypatch.setattr(odf, "_config_values", lambda: dict(config))
    monkeypatch.setattr(odf, "_own_addresses", lambda: {"192.168.1.50"})
    (modules / "osc.json").write_text(
        json.dumps({"inputs": [_row("3" * 32, "button", 1, "/a")]}), encoding="utf-8"
    )
    assert odf.migrate_settings_from_config() is True
    server = _doc(modules)["server"]
    # The settings the configuration never had (output, feedback,
    # discovery) get their defaults.
    assert server == {
        **odf.SERVER_DEFAULTS,
        "enabled": False,
        "host": "",
        "port": 9100,
        "output_host": "10.0.0.9",
        "output_port": 9200,
        "autorelease_no_arg": False,
        "autorelease_delay_ms": 500,
        "pad_args": True,
    }
    assert _doc(modules)["inputs"][0]["uid"] == "3" * 32
    config["port"] = "7000"
    assert odf.migrate_settings_from_config() is False
    assert _doc(modules)["server"]["port"] == 9100


def test_migrate_keeps_another_host(
    modules: Path, writes: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(odf, "_config_values", lambda: {"host": "127.0.0.1"})
    monkeypatch.setattr(odf, "_own_addresses", lambda: {"192.168.1.50"})
    assert odf.migrate_settings_from_config() is True
    assert _doc(modules)["server"]["host"] == "127.0.0.1"
    assert _doc(modules)["server"]["port"] == 8001


def test_replacing_the_file_reloads_osc_and_says_so(
    modules: Path, writes: list, emitted: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = FakeRows()
    monkeypatch.setattr(odf, "_rows", lambda r: rows if r is None else r)
    doc = {"inputs": [_row("4" * 32, "button", 1, "/r")], "server": {"port": 9001}}
    store.replace(odf.path(), json.dumps(doc).encode("utf-8"), "Library")
    assert rows.inputs == doc["inputs"]
    assert emitted == [
        "oscDeviceReloaded",
        "oscDeviceModified",
        "oscServerSettingsChanged",
    ]
    emitted.clear()
    store.write_text(odf.path(), json.dumps({"inputs": []}), "History")
    assert rows.inputs == []
    assert "oscDeviceReloaded" in emitted


def test_replacing_another_file_does_not_reload_osc(
    modules: Path, writes: list, emitted: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = FakeRows([_row("5" * 32, "button", 1, "/k")])
    monkeypatch.setattr(odf, "_rows", lambda r: rows if r is None else r)
    store.replace(modules / "keyboard.json", b"{}", "Library")
    assert rows.inputs[0]["uid"] == "5" * 32
    assert not [n for n in emitted if n.startswith("osc")]


def test_an_old_row_with_a_known_address_under_another_number_is_that_row(
    modules: Path, writes: list
) -> None:
    rows = FakeRows([_row("6" * 32, "button", 1, "/a")])
    old = {
        "inputs": [
            {"type": "button", "id": 3, "label": "/a"},
            {"type": "button", "id": 4, "label": "/A"},  # same key again
            {"type": "button", "id": 5, "label": "/n"},
            {"type": "button", "id": 6, "label": "/n"},  # same key as the new one
        ]
    }
    result = odf.merge_profile_rows(old, rows=rows)
    assert result.uid_map[("button", 3)] == "6" * 32
    assert result.uid_map[("button", 4)] == "6" * 32
    assert result.added == ["/n"]
    assert result.uid_map[("button", 6)] == result.uid_map[("button", 5)]
    assert [r["label"] for r in rows.inputs] == ["/a", "/n"]


def _real_rows() -> tuple[object, str, str]:
    from gremlin.osc_rows import OscRows
    from gremlin.types import InputType

    rows = OscRows()
    a = rows.create(InputType.JoystickButton, "/a", input_id=3)
    x = rows.create(InputType.JoystickAxis, "/x", input_id=1, mode="axis")
    return rows, a.uid, x.uid


def test_claim_friendly_finds_an_osc_name_by_uid_else_the_old_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import gremlin.osc
    from gremlin.modules.claim import claim_friendly

    rows, a_uid, _ = _real_rows()
    monkeypatch.setattr(gremlin.osc, "OscDevice", lambda: SimpleNamespace(rows=rows))
    claim = {"friendly": {f"osc:{a_uid}": "Fire", "button:1": "Old"}}
    assert claim_friendly(claim, "button", 3) == "Fire"
    assert claim_friendly(claim, "button", 1) == "Old"  # not converted yet
    assert claim_friendly(claim, "axis", 1) == ""
    # Another device's claim is read as before.
    assert claim_friendly({"friendly": {"button:3": "Trigger"}}, "button", 3) == (
        "Trigger"
    )


def test_a_device_copy_keeps_osc_uid_names() -> None:
    names = {
        "osc:" + "a" * 32: "Fire",
        "osc:bad": "x",
        "button:2": "B",
        "button:9": "C",
    }
    kept = store._filter_friendly(names, {2}, set(), set(), set())
    assert kept == {"osc:" + "a" * 32: "Fire", "button:2": "B"}


def test_loading_the_file_converts_old_friendly_keys_to_uids(
    modules: Path, writes: list
) -> None:
    rows, a_uid, x_uid = _real_rows()
    doc = rows.to_dict()
    doc["claim"] = {
        "buttons": [3],
        "axes": [1],
        "friendly": {"button:3": "Fire", "axis:1": "Throttle", "button:7": "Gone"},
    }
    (modules / "osc.json").write_text(json.dumps(doc), encoding="utf-8")
    from gremlin.osc_rows import OscRows

    fresh = OscRows()
    odf.load(fresh)
    assert _doc(modules)["claim"]["friendly"] == {
        f"osc:{a_uid}": "Fire",
        f"osc:{x_uid}": "Throttle",
        "button:7": "Gone",
    }
    assert len(writes) == 1
    odf.load(fresh)
    assert len(writes) == 1  # nothing left to convert


def test_migrate_with_only_default_settings_makes_no_file(
    modules: Path, writes: list, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = {
        "enabled": True,
        "host": "192.168.1.50",  # this PC's address: the default ""
        "port": "8001",
        "output_host": "127.0.0.1",
        "output_port": "8000",
        "autorelease_no_arg": True,
        "autorelease_delay_ms": "250",
        "pad_args": False,
    }
    monkeypatch.setattr(odf, "_config_values", lambda: dict(config))
    monkeypatch.setattr(odf, "_own_addresses", lambda: {"192.168.1.50"})
    assert odf.migrate_settings_from_config() is False
    assert not (modules / "osc.json").exists() and writes == []
    assert odf.read_server() == odf.SERVER_DEFAULTS
    odf.load(FakeRows())
    assert not (modules / "osc.json").exists()
