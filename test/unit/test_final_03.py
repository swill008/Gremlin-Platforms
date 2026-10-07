# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final test plan, page 03 (input and output modules).

One test per section 8 statement that had no automatic check (see
claude/final-test-plan/03-modules.md). Each drives the owner module on the
real path with the fake stick (pJoy Pro) and vJoy 1, in an emptied modules
folder that is put back afterwards (test_stage1_modules.folder).
"""

from __future__ import annotations

import json
import types
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import config, event_handler, history, shared_state
from gremlin.modules import auto_map, calibration, ids, output, store
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import hardware_profile, module_model
from test.unit.test_stage1_modules import (  # noqa: F401  # pyright: ignore[reportMissingImports]
    folder,
    map_button,
    mapped,
    open_profile,
    settle_history,
    setup_cards,
    stick_doc,
    stick_guid,
    stick_uid,
    vjoy_doc,
    vjoy_guid,
    write_module,
)

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


@pytest.fixture
def modules(request: pytest.FixtureRequest) -> Path:
    """The emptied modules folder (test_stage1_modules.folder)."""
    return request.getfixturevalue(folder.__name__)


@pytest.fixture
def gate(modules: Path) -> Iterator[InputModuleRuntime]:
    """The input module runtime, its claims put back as they were."""
    runtime = InputModuleRuntime()
    kept = (runtime._claims, runtime._dest_guids, runtime._passthrough)
    yield runtime
    runtime._claims, runtime._dest_guids, runtime._passthrough = kept


def _set_show_stubs(on: bool) -> None:
    module_model._ensure_display_options()
    config.Configuration().set(
        module_model._CFG_SECTION,
        module_model._CFG_GROUP,
        module_model._CFG_SHOW_STUBS,
        on,
    )


def _history_count(file_name: str) -> int:
    settle_history()
    return sum(
        1
        for e in history.entries("modules")
        if (e.get("subject") or {}).get("fileName") == file_name
    )


# --- B. Claims and the input gate --------------------------------------------


def test_s14_a_connected_stick_with_no_module_file_passes_nothing(
    gate: InputModuleRuntime,
) -> None:
    gate.reload()
    for kind, ident in (
        (InputType.JoystickButton, 1),
        (InputType.JoystickAxis, 1),
        (InputType.JoystickHat, 1),
    ):
        assert not gate.allows(stick_guid(), kind, ident)


def test_s16_a_vjoy_read_back_as_an_input_passes_unfiltered(
    modules: Path, gate: InputModuleRuntime, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(modules, "vjoy_1", vjoy_doc(boundGuidLocal=vjoy_guid()))
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    gate.reload()
    # Its own events never enter the wire, claimed or not.
    assert not gate.allows(vjoy_guid(), InputType.JoystickButton, 1)
    profile.settings.vjoy_as_input = {1: True}
    gate.reload()
    # Read back as an input (Profile Settings): every control passes.
    assert gate.allows(vjoy_guid(), InputType.JoystickButton, 1)
    assert gate.allows(vjoy_guid(), InputType.JoystickButton, 7)
    assert gate.allows(vjoy_guid(), InputType.JoystickAxis, 3)


def test_s22_a_damaged_module_file_blocks_its_devices_inputs(
    modules: Path, gate: InputModuleRuntime
) -> None:
    path = modules / "pjoy_pro.json"
    path.write_text('{"kind": "control.hardware", "dev', encoding="utf-8")
    gate.reload()
    assert not gate.allows(stick_guid(), InputType.JoystickButton, 1)
    # Fixed (restored, or set up again after Start Fresh): it passes again.
    write_module(modules, "pjoy_pro", stick_doc())
    gate.reload()
    assert gate.allows(stick_guid(), InputType.JoystickButton, 1)
    assert not gate.allows(stick_guid(), InputType.JoystickButton, 3)


# --- D. Output modules ---------------------------------------------------------


def test_s35_stop_releases_every_vjoy_and_unplugs_every_xbox_pad(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    released: list[str] = []
    vjoy = types.SimpleNamespace(reset=lambda: released.append("vjoy"))
    monkeypatch.setattr(output, "_vjoy_proxy", lambda: vjoy)

    class _Pads:
        def reset(self) -> None:
            released.append("xbox")

    monkeypatch.setattr("vigem.xbox.XboxProxy", _Pads)
    monkeypatch.setattr(output, "_blocked", {("vjoy", 1, "button", 9)})
    output.reset_drivers()
    assert released == ["vjoy", "xbox"]
    # The next Run tells about a blocked output again.
    assert output._blocked == set()


# --- E. Module Setup -----------------------------------------------------------


def _setup_for_stick() -> module_model.DriverInputModel:
    model = module_model.DriverInputModel()
    model.loadDevice(stick_guid(), "pJoy Pro")
    return model


def _row_of(model: module_model.DriverInputModel, kind: str, hw_id: int) -> int:
    return next(
        i
        for i, row in enumerate(model._rows)
        if row["kind"] == kind and int(row["hwId"]) == hw_id
    )


def test_s42_a_friendly_name_is_saved_only_for_a_claimed_control(
    modules: Path,
) -> None:
    write_module(modules, "pjoy_pro", stick_doc())
    model = _setup_for_stick()
    model.setFriendly(_row_of(model, "button", 1), "Fire")
    model.setFriendly(_row_of(model, "button", 3), "Unticked")
    assert model.saveClaim("pJoy Pro", "source")
    doc = json.loads((modules / "pjoy_pro.json").read_text(encoding="utf-8"))
    assert doc["claim"]["friendly"] == {"button:1": "Fire"}
    model.deleteLater()


def test_s48_a_save_that_does_not_read_back_counts_as_not_saved(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(modules, "pjoy_pro", stick_doc())
    real = store.update_path

    def written_wrong(path: Path, change, who: str, **kw: bool) -> bool:  # noqa: ANN001
        done = real(path, change, who, **kw)
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        doc["claim"]["buttons"] = [9]
        Path(path).write_text(json.dumps(doc), encoding="utf-8")
        return done

    monkeypatch.setattr(store, "update_path", written_wrong)
    model = _setup_for_stick()
    model.setClaimed(_row_of(model, "button", 3), True)
    assert model.saveClaim("pJoy Pro", "source") is False
    assert model.lastSavedPath() == ""
    model.deleteLater()


# --- F. Import -------------------------------------------------------------------


def test_s55_s56_s58_import_copies_what_the_device_has_and_keeps_the_rest(
    modules: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = write_module(modules, "pjoy_pro", stick_doc(image="pjoy_pro/photo.jpg"))
    previous = current.read_bytes()
    profile = open_profile(monkeypatch)
    wires = mapped(profile, stick_uid())
    chosen = tmp_path / "other_stick.json"
    chosen.write_text(
        json.dumps(
            {
                "kind": "control.hardware",
                "device": "Other Stick",
                "direction": "source",
                "image": "other_stick/photo.png",
                "claim": {
                    # pJoy Pro has 64 buttons, axes 1-3 and 6-8, 2 hats.
                    "buttons": [1, 3, 200],
                    "axes": [1, 4],
                    "hats": [1, 3],
                    "keys": [],
                    "friendly": {"button:3": "Fire"},
                },
            }
        ),
        encoding="utf-8",
    )
    chosen_bytes = chosen.read_bytes()

    message = module_model.ModuleListModel().importModuleFile(
        stick_guid(), "pJoy Pro", str(chosen), "source"
    )
    assert message.startswith("Imported into pjoy_pro.json."), message
    # S55: copied into this device's file; the chosen file stays as it was.
    assert chosen.read_bytes() == chosen_bytes
    doc = json.loads(current.read_text(encoding="utf-8"))
    claim = doc["claim"]
    # S56: only the controls this device has, the ones left out named.
    assert (claim["buttons"], claim["axes"], claim["hats"]) == ([1, 3], [1], [1])
    assert claim["friendly"] == {"button:3": "Fire"}
    assert "not copied" in message
    # S56: this device's picture kept; profile wires unchanged.
    assert doc["image"] == "pjoy_pro/photo.jpg"
    assert "The picture already on this device was kept." in message
    assert mapped(profile, stick_uid()) == wires
    assert "Profile wires were not changed." in message
    # S58: the previous file is kept in the imported folder.
    kept = list(store.imported_dir().glob("pjoy_pro.*.json"))
    assert [k.read_bytes() for k in kept] == [previous]


# --- G. History ------------------------------------------------------------------


def test_s69_each_module_file_write_and_delete_is_one_history_entry(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(store.module_file, "report_refused", lambda error: None)
    path = store.path_for("pJoy Pro", stick_guid())
    store.write_json(path, stick_doc(), "test")
    assert _history_count("pjoy_pro.json") == 1
    assert store.update_path(path, lambda doc: doc.update(note=1), "test")
    assert _history_count("pjoy_pro.json") == 2
    # A refused write (damaged file) is no entry.
    good = path.read_bytes()
    path.write_text('{"kind": "control.hard', encoding="utf-8")
    refused = store.update_path(
        path, lambda doc: doc.update(note=2), "test", report=False
    )
    assert not refused
    assert _history_count("pjoy_pro.json") == 2
    path.write_bytes(good)
    assert hardware_profile.delete_module_file("pJoy Pro", stick_guid()) == ""
    assert not path.exists()
    assert _history_count("pjoy_pro.json") == 3


# --- H. Home cards ---------------------------------------------------------------


def test_s70_s71_home_shows_each_device_and_the_logical_device_only_with_a_file(
    modules: Path,
) -> None:
    setup_cards(modules)
    _set_show_stubs(False)
    model = module_model.ModuleListModel()
    cards = {model.cardMap(slug).get("name"): model.cardMap(slug) for slug in (
        "pjoy_pro", "keyboard", "osc", "vjoy_1", "xbox", "logical"
    )}
    assert cards["pJoy Pro"]["direction"] == "source"
    assert cards["vJoy 1"]["direction"] == "dest"
    assert cards["Xbox 360 Controller"]["direction"] == "dest"
    assert cards["Keyboard"]["direction"] == "source"
    assert cards["OSC"]["direction"] == "source"
    assert None in cards  # no Logical Device card without its file
    store.write_json(
        store.path_for("Logical Device", str(ids.LOGICAL_DEVICE)),
        {"kind": "control.hardware", "device": "Logical Device", "direction": "source"},
        "test",
    )
    assert module_model.ModuleListModel().cardMap("logical")["name"] == "Logical Device"


def test_s72_a_device_without_a_module_shows_no_module_only_with_show_stubs(
    modules: Path,
) -> None:
    _set_show_stubs(True)
    card = module_model.ModuleListModel().cardMap("pjoy_pro")
    # "Stub" reads "No module" on the card (StatusCard.qml).
    assert card["status"] == "Stub" and card["isStub"] and not card["isModule"]
    # D-03-Q8-NOFILE: a card with no module file shows the device's own counts.
    assert (card["buttons"], card["axes"], card["hats"]) == (64, 6, 2)
    _set_show_stubs(False)
    assert module_model.ModuleListModel().cardMap("pjoy_pro") == {}


def test_s73_an_output_card_is_driven_by_the_devices_wired_to_it(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The "Driven by" line itself shows on output cards only (StatusCard.qml
    # visible: direction === "dest"; checked hands-on).
    setup_cards(modules)
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    map_button(profile, stick_uid(), 1, 1)
    model = module_model.ModuleListModel()
    assert model.cardMap("vjoy_1")["target"] == "pJoy Pro"
    assert model.cardMap("xbox")["target"] == ""
    # Claimed counts, as numbers the card turns into words ("1 button").
    card = model.cardMap("vjoy_1")
    assert (card["buttons"], card["axes"], card["hats"]) == (1, 0, 0)


# --- I. Home layout --------------------------------------------------------------


def test_s83_card_sizes_are_kept_in_their_limits_and_persist(modules: Path) -> None:
    setup_cards(modules)
    model = module_model.ModuleListModel()
    model.setPileSize("pjoy_pro", 10, 9999)
    assert (model.cardWidth("pjoy_pro"), model.cardHeight("pjoy_pro")) == (220, 520)
    model.setPileSize("pjoy_pro", 9999, 10)
    assert (model.cardWidth("pjoy_pro"), model.cardHeight("pjoy_pro")) == (720, 140)
    model.setPileSize("pjoy_pro", 400, 300)
    again = module_model.ModuleListModel()
    assert (again.cardWidth("pjoy_pro"), again.cardHeight("pjoy_pro")) == (400, 300)


def test_s85_reset_size_reset_all_and_reset_card_layout(modules: Path) -> None:
    setup_cards(modules)
    model = module_model.ModuleListModel()
    model.setPileSize("pjoy_pro", 400, 300)
    model.setPileSize("vjoy_1", 500, 300)
    model.resetCardSize("pjoy_pro")
    assert model.cardWidth("pjoy_pro") == 0
    assert model.cardWidth("vjoy_1") == 500
    model.resetAllCardSizes()
    assert model.cardWidth("vjoy_1") == 0
    # Reset Card Layout: size and stacking.
    model.stackSelected("pjoy_pro", "keyboard")
    model.setPileSize("keyboard", 300, 200)
    model.clearCardSettings("keyboard")
    assert model.cardWidth("keyboard") == 0
    assert model.pileMembers("pjoy_pro") == ["pjoy_pro"]


# --- L. Calibration --------------------------------------------------------------


def _calibration_window(monkeypatch: pytest.MonkeyPatch):  # noqa: ANN202
    from gremlin.ui import device as ui_device

    model = ui_device.AxisCalibration()
    model.moduleSlug = "pjoy_pro"
    assert model.rowCount() == 6
    return model


def test_s100_calibration_lists_only_connected_sticks_with_an_input_module(
    modules: Path,
) -> None:
    from gremlin.ui.module_calibration import CalibrationModuleModel

    setup_cards(modules)  # pJoy Pro, Keyboard, OSC and vJoy 1 have files
    model = CalibrationModuleModel()
    assert model.moduleCount == 1
    assert model.data(model.index(0, 0), QtCore.Qt.ItemDataRole.UserRole + 2) == (
        "pjoy_pro"
    )
    (modules / "pjoy_pro.json").unlink()
    model.reload()
    # None: the window says "No connected input module."
    assert model.moduleCount == 0
    model.deleteLater()


def test_s102_only_one_capture_runs_at_a_time(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(modules, "pjoy_pro", stick_doc())
    model = _calibration_window(monkeypatch)
    model.calibrateCenter(0, True)
    model.calibrateExtrema(0, True)
    assert model._active_calibrations[0]["extrema"] is True
    assert model._active_calibrations[0]["center"] is False
    model.calibrateCenter(0, True)
    assert model._active_calibrations[0]["extrema"] is False
    model.deleteLater()


def test_s99_s108_a_saved_axis_is_used_at_once_before_any_action_sees_it(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(modules, "pjoy_pro", stick_doc())
    listener = event_handler.EventListener()
    monkeypatch.setattr(listener, "_calibrations", dict(listener._calibrations))
    model = _calibration_window(monkeypatch)
    roles = {bytes(v.data()).decode(): k for k, v in model.roles.items()}
    index = model.index(0, 0)
    model.setData(index, -1000, roles["low"])
    model.setData(index, 1000, roles["high"])
    assert model.save(0)
    device = model._device
    assert device is not None
    raw = types.SimpleNamespace(
        device_guid=device.device_guid,
        input_index=device.axis_map[0].axis_index,
        value=1000,
    )
    # The listener (which gives every action its axis value) uses it now.
    assert listener._apply_calibration(raw) == pytest.approx(1.0)
    model.deleteLater()


def test_s111_old_program_calibration_is_used_until_the_module_file_has_one(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_module(modules, "pjoy_pro", stick_doc())
    old = (-2000, -10, 10, 2000, True)
    monkeypatch.setattr(
        config.Configuration, "get_calibration", lambda self, device, axis: old
    )
    assert calibration.values_for_device(stick_uid(), 1) == old
    new = (-1000, 0, 0, 1000, True)
    assert calibration.write_axes("pjoy_pro", {1: new})
    assert calibration.values_for_device(stick_uid(), 1) == new
    # Other axes still use the old settings.
    assert calibration.values_for_device(stick_uid(), 2) == old


# --- M. Output View --------------------------------------------------------------


def test_s117_output_view_appearance_is_saved_in_the_module_file(modules: Path) -> None:
    path = write_module(modules, "vjoy_1", vjoy_doc())
    model = module_model.ModuleListModel()
    assert model.saveViewConfig("vJoy 1", vjoy_guid(), json.dumps({"columns": 3}))
    doc = json.loads(path.read_text(encoding="utf-8"))
    assert doc["view"]["columns"] == 3
    assert doc["claim"] == vjoy_doc()["claim"]
    assert json.loads(model.viewConfigJson("vJoy 1", vjoy_guid()))["columns"] == 3
    # Copy from another output: the other output cards are offered.
    others = [row["name"] for row in json.loads(model.otherDestViews("vJoy 1"))]
    assert others == ["Xbox 360 Controller"]


# --- N. Auto Mapper ----------------------------------------------------------------


def test_s119_auto_mapper_lists_claiming_inputs_once_and_one_output_per_vjoy(
    modules: Path,
) -> None:
    setup_cards(modules)  # pJoy Pro claims buttons; Keyboard and OSC keys only
    old = write_module(modules, "pjoy_old", stick_doc(boundGuidLocal=""))
    write_module(
        modules,
        "empty_stick",
        {
            "kind": "control.hardware",
            "device": "Empty Stick",
            "direction": "source",
            "claim": {"buttons": [], "axes": [], "hats": [], "keys": []},
        },
    )
    inputs = auto_map.input_modules()
    assert [(row["name"], row["slug"]) for row in inputs] == [("pJoy Pro", "pjoy_pro")]
    assert old.is_file()  # the other file for the device is not deleted
    output.refresh()
    outputs = auto_map.output_modules()
    assert [(row["vjoyId"], row["slug"]) for row in outputs] == [(1, "vjoy_1")]


# --- O. Other readers of claims ------------------------------------------------------


def test_s121_configuration_list_shows_claimed_controls_the_device_has(
    modules: Path,
) -> None:
    from gremlin.ui.module_inputs import ModuleClaimedInputModel

    write_module(
        modules,
        "pjoy_pro",
        stick_doc(
            claim={
                "buttons": [1, 2, 200],
                "axes": [4, 1],
                "hats": [],
                "keys": [],
                "friendly": {"button:1": "Fire", "button:3": "Unclaimed"},
            }
        ),
    )
    model = ModuleClaimedInputModel()
    model.deviceName = "pJoy Pro"
    model.guid = stick_guid()
    rows = [(model.kindAt(i), model.hwIdAt(i)) for i in range(model.rowCount())]
    assert rows == [("axis", 1), ("button", 1), ("button", 2)]
    assert model.nameAt(1) == "Fire"
    model.deleteLater()


def test_s122_vjoy_viewer_lists_wired_devices_and_marks_unclaimed_outputs(
    modules: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui.module_pairing import ModulePairButtonModel, ModulePairDeviceModel

    setup_cards(modules)  # vJoy 1 claims button 1 only
    profile = Profile()
    monkeypatch.setattr(shared_state, "current_profile", profile)
    map_button(profile, stick_uid(), 1, 1)
    map_button(profile, stick_uid(), 2, 5)
    devices = ModulePairDeviceModel()
    names = [devices._rows[i]["deviceName"] for i in range(devices.rowCount())]
    assert names == ["pJoy Pro"]
    buttons = ModulePairButtonModel()
    buttons.deviceName = "pJoy Pro"
    buttons.guid = stick_guid()
    rows = {row["identifier"]: row for row in buttons._rows}
    assert rows[1]["destClaimed"] is True
    assert rows[2]["destClaimed"] is False
    assert "(not claimed)" in rows[2]["vjoyLabel"]
    devices.deleteLater()
    buttons.deleteLater()




@pytest.mark.parametrize("case", ["no output module file", "file without its id"])
def test_s16_a_vjoy_read_back_passes_whatever_its_output_module_file(
    modules: Path, gate: InputModuleRuntime, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    if case == "file without its id":
        write_module(modules, "vjoy_1", vjoy_doc())
    profile = Profile()
    profile.settings.vjoy_as_input = {1: True}
    monkeypatch.setattr(shared_state, "current_profile", profile)
    gate.reload()
    assert gate.allows(vjoy_guid(), InputType.JoystickButton, 1)
