# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC's module file travels like the Logical Device's (D-09-OSC-FILE 1, 4):
its "inputs" (each with its uid and per-input settings, D-09-OSC-INPUT) and
its "server" settings come back through Save to Device Library and Restore,
Export (current and saved), a Device Pack import (one write, Undo Import
reverts) and History restore; each put-back is one write of osc.json and one
History entry, after which OSC's shared rows, the OSC page model and the
server settings are read again. Friendly names keyed "osc:<uid>" go with
them. The real store, Library, Device Pack and History in an empty modules
folder."""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_library as library
from gremlin import history, library_copy, osc_device_file, plugin_manager, shared_state
from gremlin.modules import claim as claim_mod
from gremlin.modules import ids, module_file
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime
from gremlin.profile import DeviceInfo, Profile
from gremlin.signal import signal
from gremlin.types import InputType
from gremlin.ui import history_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    settle_history,
)

pytestmark = pytest.mark.validate_off

OSC_GUID = "{" + str(ids.OSC).upper() + "}"
_B = InputType.JoystickButton
_A = InputType.JoystickAxis
SERVER_A = {"host": "", "port": 9001, "autorelease_delay_ms": 400}
SERVER_B = {"host": "", "port": 9100, "autorelease_delay_ms": 120}

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(
    request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> Path:
    monkeypatch.setattr(library, "_connected", lambda: [])
    return request.getfixturevalue(folder.__name__)


@pytest.fixture
def rows(modules: Path) -> Iterator[object]:
    """OSC's shared rows emptied, the runtime made (it applies server
    settings on oscServerSettingsChanged), all put back afterwards."""
    OscRuntime()
    shared = OscDevice().rows
    saved = shared.to_dict()
    shared.load_dict({"inputs": []})
    yield shared
    osc_device_file.current_uid_map = None
    shared.load_dict(saved)
    OscRuntime()._settings = osc_device_file.clean_server({})


@pytest.fixture
def state_a(rows: object) -> dict:
    """OSC's file as it is saved: a trigger button with a friendly name, an
    axis with its own range, and server settings A."""
    fire = rows.create(_B, "/fire", trigger=True, delay_ms=300)  # type: ignore[attr-defined]
    throttle = rows.create(  # type: ignore[attr-defined]
        _A, "/throttle", mode="axis", source=1, range_min=-1.0, range_max=1.0
    )
    assert osc_device_file.save()
    assert osc_device_file.write_server(SERVER_A)
    _set_friendly({f"osc:{fire.uid}": "Fire"})
    return {"fire": fire.uid, "throttle": throttle.uid, "fire_id": fire.input_id}


def _doc() -> dict:
    return json.loads(osc_device_file.path().read_text(encoding="utf-8-sig"))


def _set_friendly(names: dict) -> None:
    from gremlin.modules import store

    def change(doc: dict) -> None:
        doc.setdefault("claim", {})["friendly"] = dict(names)

    assert store.update_path(osc_device_file.path(), change, "Home")


def _change_to_b(rows: object) -> None:
    """The user changes things after saving: /throttle deleted, /other
    added, the server moved, the friendly name dropped."""
    data = rows.to_dict()  # type: ignore[attr-defined]
    data["inputs"] = [r for r in data["inputs"] if r["label"] != "/throttle"]
    rows.load_dict(data)  # type: ignore[attr-defined]
    rows.create(_B, "/other")  # type: ignore[attr-defined]
    assert osc_device_file.save()
    assert osc_device_file.write_server(SERVER_B)
    _set_friendly({})


def _assert_state_a(state: dict) -> None:
    """The file, OSC's shared rows and the runtime's settings are A's."""
    saved = {r["uid"]: r for r in osc_device_file.read_inputs()}
    assert set(saved) == {state["fire"], state["throttle"]}, saved
    assert saved[state["fire"]]["trigger"] is True
    assert saved[state["fire"]]["delay_ms"] == 300
    assert saved[state["throttle"]]["mode"] == "axis"
    assert saved[state["throttle"]]["range_min"] == -1.0
    assert saved[state["throttle"]]["source"] == 1
    server = osc_device_file.read_server()
    assert server["port"] == 9001 and server["autorelease_delay_ms"] == 400
    shared = OscDevice().rows
    assert {r.uid for r in shared.rows()} == {state["fire"], state["throttle"]}
    assert shared.by_uid(state["throttle"]).range_min == -1.0  # type: ignore[union-attr]
    assert not shared.dirty
    # The server took the settings at once (OscRuntime.sync_bind).
    assert OscRuntime()._settings["port"] == 9001


class _Watch:
    """Writes of osc.json, OSC's signals and its new History entries."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        settle_history()
        self.before = {str(e.get("id")) for e in history.entries()}
        self.writes: list[Path] = []
        self.signals: list[str] = []
        real = module_file.write_bytes

        def counting(path: Path, data: bytes) -> None:
            if Path(path).name == "osc.json":
                self.writes.append(Path(path))
            real(path, data)

        monkeypatch.setattr(module_file, "write_bytes", counting)
        for name in ("oscDeviceReloaded", "oscServerSettingsChanged"):
            getattr(signal, name).connect(lambda n=name: self.signals.append(n))

    def entries(self) -> list[dict]:
        settle_history()
        return [
            e
            for e in history.entries()
            if str(e.get("id")) not in self.before
            and (e.get("subject") or {}).get("fileName") == "osc.json"
        ]


def _save() -> dict:
    out = library.save_setup("OSC", OSC_GUID, [])
    assert out["ok"], out
    setups = out.get("setups") or [out.get("setup")]
    return setups[0]


def _osc_doc_in(data: bytes | Path) -> dict:
    """OSC's module file inside a pack/zip."""
    source = io.BytesIO(data) if isinstance(data, bytes) else Path(data)
    with zipfile.ZipFile(source) as zf:
        for name in zf.namelist():
            if not name.endswith(".json"):
                continue
            try:
                doc = json.loads(zf.read(name).decode("utf-8-sig"))
            except ValueError:
                continue
            if isinstance(doc, dict) and "inputs" in doc:
                return doc
    return {}


# --- (1) Save to Device Library, then Restore --------------------------------


@pytest.mark.parametrize("how", ["restore_to_stick", "restore"])
def test_restore_brings_inputs_and_server_back_in_one_write(
    how: str, state_a: dict, rows: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    setup = _save()
    _change_to_b(rows)
    assert OscRuntime()._settings["port"] == 9100
    watch = _Watch(monkeypatch)
    out = getattr(library_copy, how)(setup["key"])
    assert out["ok"], out
    _assert_state_a(state_a)
    assert len(watch.writes) == 1, watch.writes
    assert len(watch.entries()) == 1, watch.entries()
    assert "oscDeviceReloaded" in watch.signals
    assert "oscServerSettingsChanged" in watch.signals


# --- (5) friendly names by uid survive Save/Restore --------------------------


def test_friendly_names_by_uid_survive_save_and_restore(
    state_a: dict, rows: object
) -> None:
    setup = _save()
    _change_to_b(rows)
    assert not _doc().get("claim", {}).get("friendly")
    out = library_copy.restore_to_stick(setup["key"])
    assert out["ok"], out
    names = _doc()["claim"]["friendly"]
    assert names == {f"osc:{state_a['fire']}": "Fire"}, names
    # Shown by its current number through the uid.
    assert (
        claim_mod.claim_friendly(_doc()["claim"], "button", state_a["fire_id"])
        == "Fire"
    )


# --- (2) Export current / Export saved setup ---------------------------------


def _assert_carries_a(doc: dict, state: dict) -> None:
    assert {r["uid"] for r in doc.get("inputs") or []} == {
        state["fire"],
        state["throttle"],
    }, doc
    fire = next(r for r in doc["inputs"] if r["uid"] == state["fire"])
    assert fire["trigger"] is True and fire["delay_ms"] == 300
    assert (doc.get("server") or {}).get("port") == 9001
    assert doc["server"]["autorelease_delay_ms"] == 400


def test_export_current_includes_inputs_and_server(
    state_a: dict, tmp_path: Path
) -> None:
    row = next(r for r in library.devices() if r["name"] == "OSC")
    dest = tmp_path / "out" / "now.zip"
    out = library.export_current(row["key"], dest)
    assert out["ok"], out
    _assert_carries_a(_osc_doc_in(dest), state_a)


def test_export_saved_setup_includes_inputs_and_server(
    state_a: dict, rows: object, tmp_path: Path
) -> None:
    setup = _save()
    _change_to_b(rows)  # the saved setup keeps A
    dest = tmp_path / "out" / "saved.zip"
    out = library.export_setup(setup["key"], dest)
    assert out["ok"], out
    _assert_carries_a(_osc_doc_in(dest), state_a)


# --- (3) Device Pack ----------------------------------------------------------


@pytest.fixture
def profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    made = Profile()
    made.device_database.devices[OSC_DEVICE_UUID] = DeviceInfo(OSC_DEVICE_UUID, "OSC")
    shared_state.current_profile = made
    yield made
    from gremlin.ui import device_pack

    device_pack.drop_import_undo()
    shared_state.current_profile = old


def _map_vjoy(profile: Profile, number: int, out: int) -> None:
    action = plugin_manager.PluginManager().create_instance("Map to vJoy", _B)
    action.vjoy_device_id = 1
    action.vjoy_input_id = out
    action.vjoy_input_type = _B
    item = profile.get_input_item(
        OSC_DEVICE_UUID, _B, number, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _vjoy_targets(profile: Profile) -> dict[int, int]:
    out = {}
    for item in profile.inputs.get(OSC_DEVICE_UUID, []):
        for binding in item.action_sequences:
            for action in binding.root_action.get_actions()[0]:
                if getattr(action, "tag", "") == "map-to-vjoy":
                    out[int(item.input_id)] = action.vjoy_input_id
    return out


def _pack(profile: Profile, tmp_path: Path) -> Path:
    from gremlin.ui import device_pack

    built = device_pack.assemble(
        "OSC", lambda stored: None, None, {}, profile, str(OSC_DEVICE_UUID)
    )
    assert not isinstance(built, str), built
    path = tmp_path / "osc.zip"
    path.write_bytes(built[0])
    return path


def test_device_pack_carries_inputs_and_server_and_undo_reverts(
    state_a: dict,
    rows: object,
    profile: Profile,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import device_pack

    path = _pack(profile, tmp_path)
    assert "in.osc" in device_pack.pack_item_ids(path)["input"]
    _change_to_b(rows)
    b_doc = _doc()
    watch = _Watch(monkeypatch)
    result = device_pack.apply_zip(
        path, "OSC", {"items": ["in.osc"]}, target_guid=str(OSC_DEVICE_UUID)
    )
    assert result["ok"], result
    _assert_state_a(state_a)
    assert len(watch.writes) == 1, watch.writes
    assert len(watch.entries()) == 1, watch.entries()
    assert "oscDeviceReloaded" in watch.signals
    # Undo Import puts B back, rows and server read again.
    assert device_pack.undo_import()["ok"]
    assert _doc()["inputs"] == b_doc["inputs"]
    assert osc_device_file.read_server()["port"] == 9100
    labels = sorted(r.label for r in OscDevice().rows.rows())
    assert labels == ["/fire", "/other"]
    assert OscRuntime()._settings["port"] == 9100


def test_pack_wires_land_on_the_address_by_uid_when_numbers_differ(
    state_a: dict, rows: object, profile: Profile, tmp_path: Path
) -> None:
    from gremlin.ui import device_pack

    _map_vjoy(profile, state_a["fire_id"], 7)
    path = _pack(profile, tmp_path)
    # The other PC: same /fire (same uid) but on button 3, /a and /b first.
    data = rows.to_dict()  # type: ignore[attr-defined]
    fire = next(r for r in data["inputs"] if r["uid"] == state_a["fire"])
    rows.load_dict({"inputs": []})  # type: ignore[attr-defined]
    rows.create(_B, "/a")  # type: ignore[attr-defined]
    rows.create(_B, "/b")  # type: ignore[attr-defined]
    fire["id"] = 3
    rows.load_dict({"inputs": rows.to_dict()["inputs"] + [fire]})  # type: ignore[attr-defined]
    assert rows.by_uid(state_a["fire"]).input_id == 3  # type: ignore[attr-defined]
    assert osc_device_file.save()
    target = Profile()
    target.device_database.devices[OSC_DEVICE_UUID] = DeviceInfo(OSC_DEVICE_UUID, "OSC")
    shared_state.current_profile = target
    result = device_pack.apply_zip(
        path, "OSC", {"items": ["wire:Default"]}, target_guid=str(OSC_DEVICE_UUID)
    )
    assert result["ok"], result
    assert _vjoy_targets(target) == {3: 7}
    # Not re-targeted to whatever has the old number here.
    assert rows.by_uid(state_a["fire"]).input_id == 3  # type: ignore[attr-defined]


# --- (4) History restore -----------------------------------------------------


def test_history_restore_brings_rows_back_and_page_refreshes(
    state_a: dict, rows: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    model = OscDeviceManagementModel()
    try:
        assert model.rowCount() == 2
        watch = _Watch(monkeypatch)
        data = rows.to_dict()  # type: ignore[attr-defined]
        data["inputs"] = [r for r in data["inputs"] if r["label"] == "/fire"]
        rows.load_dict(data)  # type: ignore[attr-defined]
        assert osc_device_file.save()
        # The deletion's History entry: its "before" has both inputs.
        def before_inputs(e: dict) -> list:
            text = (e.get("before") or {}).get("text") or "{}"
            return json.loads(text).get("inputs") or []

        entry = next(e for e in watch.entries() if len(before_inputs(e)) == 2)
        resets: list[bool] = []
        model.modelReset.connect(lambda: resets.append(True))
        out = history_model.restore(str(entry["id"]), "before")
        assert out["ok"], out
        _assert_state_a(state_a)
        assert "oscDeviceReloaded" in watch.signals
        for _ in range(20):
            QtCore.QCoreApplication.processEvents()
        assert resets
        assert model.rowCount() == 2
    finally:
        model.deleteLater()
