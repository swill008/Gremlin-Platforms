# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Facts shown in many places follow their owner's notice, end to end on the
real program (D-01-OWNER-NOTICES; audit 97, to-dos 100-103).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver (the
shared RIG: pJoy Pro, Saitek X52 and two Twin Sticks; vJoy 1 and 2) and
an output module for vJoy 1. Home is shown (off-screen). Each part edits
through the path the screens use and records what the user would read
afterwards, without opening anything again (a fresh page would read the
new value anyway):

1. Home on screen while another window edits: a Map to vJoy added (the
   editors' actionsChanged) shows on the vJoy 1 card's "Driven by".
2. Delete Mode: the X52 drives vJoy 1 only in "Combat"; Manage Modes'
   Delete takes "Saitek X52" off the card and the model.
3. OSC page Undo: OK adds OSC to vJoy 1's "Driven by"; the page's Undo
   takes it away.
4. Device Library Swap (pJoy Pro with Saitek X52, bindings, the open
   profile ticked): vJoy 1 is then driven by the X52, not the pJoy.
5. Device rename (the Device Library's rename, device_names.set_alias): the
   Device Library rows, the Input Viewer device list, the Device Bindings page title and
   the Home card show the new name.
6. Logical Device rename (the Logical Device page's setUserName): the
   Input Viewer's paired-input label and the Xbox page's "incoming" text
   show the new name.
7. A script's Logical Device variable makes a control: the Logical Device
   page lists it.
8. A module file saved from the Device Library (store.write_json): the
   Home output card's claim copy follows.
9. Profile reload while the Output View of vJoy 1 is open: its "Driven by"
   header follows the profile loaded (which has no Logical Device binding).

Each part records its own values (an error in one doesn't hide the
others).

A second journey (fake vJoy 1 and vJoy 2, an output module for each): the
pJoy Pro's button 1 sends to vJoy 1; the Device Library's Change vJoy
Output (the window's changeOutput) moves it to vJoy 2 in the open profile.
"Driven by" moves from the vJoy 1 card to the vJoy 2 card (model rows and
the Home cards), the Device Bindings page's wire label names vJoy 2, and the
open profile (saved and opened again) sends to vJoy 2.

Spec: D-01-OWNER-NOTICES (1a, 2a, 3a, 4a, 6b); 10 S7, S26, S58.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    RIG,
    Journey,
    run_journey,
    step,
)

NEW_NAME = "Left Stick Renamed"
LD_NAME = "Gear Lever"
OSC_ADDRESS = "/notice/1"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part; an error is recorded under the part's name and the
    next part still runs."""

    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()
        return True


def _model(j: Journey) -> Any:  # noqa: ANN401
    return j.ev("_moduleModel")


def _row(j: Journey, name: str, direction: str = "") -> Any:  # noqa: ANN401
    for row in _model(j)._rows:
        if row.name == name and (not direction or row.direction == direction):
            return row
    return None


def _row_target(j: Journey, name: str) -> str:
    row = _row(j, name)
    return str(getattr(row, "target", "") or "") if row is not None else "NO ROW"


def _cards(j: Journey) -> list[Any]:  # noqa: ANN401
    return [
        it
        for it in j.walk(j.win.contentItem())
        if it.metaObject().indexOfSignal("cardFocused()") >= 0
    ]


def _card_target(j: Journey, name: str) -> str:
    for card in _cards(j):
        if card.property("cardName") == name or card.property("rawName") == name:
            return str(card.property("target") or "")
    return "NO CARD"


def _card_names(j: Journey) -> list[str]:
    return [str(c.property("cardName") or "") for c in _cards(j)]


def _go_home(j: Journey) -> None:
    j.ev('uiState.setCurrentRoom("status")')
    j.wait_until(lambda: j.ev("uiState.currentRoom") == "status", "Home")
    j.settle()


def _actions_edited() -> None:
    """What an action editor sends after an edit (ActionModel)."""
    from gremlin.signal import signal

    signal.actionsChanged.emit()


def _map(action_name: str, **fields: Any) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        action_name, InputType.JoystickButton
    )
    for key, value in fields.items():
        setattr(action, key, value)
    return action


def _bind(j: Journey, uid: Any, button: int, mode: str, action: Any) -> None:  # noqa: ANN401
    from gremlin.types import InputType

    item = j.profile.get_input_item(uid, InputType.JoystickButton, button, mode, True)
    item.add_item_binding().root_action.insert_action(action, "children")


def _vjoy_button(button: int) -> Any:  # noqa: ANN401
    from gremlin.types import InputType

    return _map(
        "Map to vJoy",
        vjoy_device_id=1,
        vjoy_input_id=button,
        vjoy_input_type=InputType.JoystickButton,
    )


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    """Every row of a list model, as {role name: value}."""
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {}
        for role, name in names.items():
            value = model.data(index, role)
            plain = isinstance(value, (str, int, float, bool, type(None)))
            row[name] = value if plain else str(value)
        out.append(row)
    return out


def _part_home_on_screen(j: Journey) -> None:
    out = j.out
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    out["home:room"] = j.ev("uiState.currentRoom")
    out["home:card-before"] = _card_target(j, "vJoy 1")
    _bind(j, pjoy, 1, "Default", _vjoy_button(1))
    _actions_edited()
    out["home:row-after"] = j.await_value(
        lambda: "pJoy Pro" in _row_target(j, "vJoy 1"), True
    )
    out["home:card-after"] = j.await_value(
        lambda: _card_target(j, "vJoy 1"), "pJoy Pro"
    )


def _part_delete_mode(j: Journey) -> None:
    from gremlin.ui.profile import ModeHierarchyModel

    out = j.out
    x52 = j.stick("Saitek X52").device_guid.uuid
    modes = ModeHierarchyModel()
    modes.newMode("Combat")
    _bind(j, x52, 4, "Combat", _vjoy_button(9))
    _actions_edited()
    out["mode:row-before"] = j.await_value(
        lambda: "Saitek X52" in _row_target(j, "vJoy 1"), True
    )
    out["mode:card-before"] = j.await_value(
        lambda: "Saitek X52" in _card_target(j, "vJoy 1"), True
    )
    modes.deleteMode("Combat")
    out["mode:row-after"] = j.await_value(
        lambda: "Saitek X52" in _row_target(j, "vJoy 1"), False
    )
    out["mode:card-after"] = j.await_value(
        lambda: "Saitek X52" in _card_target(j, "vJoy 1"), False
    )


def _part_osc_undo(j: Journey) -> None:
    from gremlin.ui.osc_device_model import OscDeviceManagementModel
    from gremlin.ui.osc_layout import OscLayoutModel

    out = j.out
    state = j.backend.uiState
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: state.currentTab == "osc", "the OSC page")
    page = j.wait_until(lambda: j.win.findChild(OscLayoutModel), "the OSC page model")
    adder = j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()
    assert adder.createConfiguredInput({"address": OSC_ADDRESS, "mode": "button"})
    j.settle()
    key = next(
        r["key"]
        for r in _rows(page)
        if str(r.get("key", "")).startswith("parent:")
        and OSC_ADDRESS in str(r.get("title", "")) + str(r.get("subtitle", ""))
    )
    page.beginNewAction(key)
    page._pane_shadow.action_sequences[0].root_action.insert_action(
        _vjoy_button(3), "children"
    )
    page.commitPane()
    page.endPane()
    j.settle()
    osc_name = str(getattr(_row(j, "OSC"), "name", "OSC"))
    out["osc:row-after-ok"] = j.await_value(
        lambda: osc_name in _row_target(j, "vJoy 1"), True
    )
    page.undo()
    j.settle()
    out["osc:row-after-undo"] = j.await_value(
        lambda: osc_name in _row_target(j, "vJoy 1"), False
    )
    _go_home(j)
    out["osc:card-after-undo"] = j.await_value(
        lambda: osc_name in _card_target(j, "vJoy 1"), False
    )


def _part_library_swap(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import library_swap, util

    out = j.out
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    x52 = j.stick("Saitek X52").device_guid.uuid
    path = util.profiles_dir() / "notices.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(url), "the profile was not saved"
    j.settle()
    out["swap:row-before"] = _row_target(j, "vJoy 1")
    done = library_swap.swap(
        ("pJoy Pro", str(pjoy)), ("Saitek X52", str(x52)), ["bindings"], [path]
    )
    out["swap:ok"] = bool(done.get("ok"))
    out["swap:message"] = str(done.get("error") or "")
    out["swap:wires-pjoy"] = sorted(
        i.input_id for i in j.profile.inputs.get(pjoy, []) if i.action_sequences
    )
    out["swap:row-after"] = j.await_value(
        lambda: _row_target(j, "vJoy 1"), "Saitek X52"
    )
    out["swap:card-after"] = j.await_value(
        lambda: _card_target(j, "vJoy 1"), "Saitek X52"
    )


def _part_device_rename(j: Journey) -> None:
    from gremlin.ui import device_names
    from gremlin.ui.device_library_model import DeviceLibraryModel
    from gremlin.ui.viewer_devices import ViewerDeviceModel

    out = j.out
    x52 = j.stick("Saitek X52").device_guid.uuid
    viewer = ViewerDeviceModel()
    library = DeviceLibraryModel()
    library.refresh()
    j.settle()
    out["rename:viewer-before"] = [r["name"] for r in viewer._rows]
    j.ev(
        "openDeviceBindingsForCard(_moduleModel.cardMap("
        f'"{_row(j, "Saitek X52", "source").slug}"))'
    )
    j.wait_until(lambda: j.ev("uiState.currentRoom") == "configuration", "the X52 page")
    out["rename:title-before"] = j.ev("configTitleName")
    device_names.set_alias(str(x52), NEW_NAME)
    j.settle()
    out["rename:library"] = j.await_value(
        lambda: NEW_NAME in str(library.property("rows")), True
    )
    out["rename:viewer"] = j.await_value(
        lambda: NEW_NAME in [r["name"] for r in viewer._rows], True
    )
    out["rename:title"] = j.await_value(
        lambda: NEW_NAME in str(j.ev("_configTitle.text")), True
    )
    _go_home(j)
    out["rename:card"] = j.await_value(lambda: NEW_NAME in _card_names(j), True)
    out["rename:cards"] = _card_names(j)


def _part_ld_rename(j: Journey) -> None:
    from gremlin.logical_device import LogicalDevice
    from gremlin.ui.logical_layout import LogicalLayoutModel
    from gremlin.ui.module_pairing import ModulePairButtonModel
    from gremlin.ui.xbox_output_list import XboxOutputListModel

    out = j.out
    logical = LogicalDevice()
    page = LogicalLayoutModel()
    before = {i.identifier for i in logical.inputs_of_type()}
    page.addMany("button", 1, "", "")
    j.settle()
    made = next(i for i in logical.inputs_of_type() if i.identifier not in before)
    ld_uid = getattr(logical.device_guid, "uuid", logical.device_guid)
    _bind(j, ld_uid, made.id, "Default", _vjoy_button(7))
    _bind(j, ld_uid, made.id, "Default", _map("Map to Xbox", xbox_device_id=1))
    _actions_edited()
    j.settle()
    pairs = ModulePairButtonModel()
    pairs.setProperty("guid", str(ld_uid))
    pairs.setProperty("deviceName", "Logical Device")
    xbox = XboxOutputListModel()
    j.settle()
    out["ld:pairs-before"] = [r["label"] for r in _rows(pairs)]
    # The Xbox Output View lists each source as a line under its control.
    out["ld:incoming-before"] = [
        r["title"] for r in _rows(xbox) if r["rowKind"] == "child"
    ]
    # The Xbox list is redrawn only when the model says its rows changed.
    redrawn = [0]

    def count(*_: object) -> None:
        redrawn[0] += 1

    xbox.modelReset.connect(count)
    xbox.dataChanged.connect(count)
    page.setUserName(f"parent:button:{made.id}", LD_NAME)
    j.settle()
    out["ld:pairs-after"] = j.await_value(
        lambda: any(LD_NAME in str(r["label"]) for r in _rows(pairs)), True
    )
    out["ld:incoming-after"] = any(
        r["rowKind"] == "child" and LD_NAME in str(r["title"]) for r in _rows(xbox)
    )
    out["ld:xbox-redrawn"] = j.await_value(lambda: redrawn[0] > 0, True)
    out["ld:pairs-final"] = [r["label"] for r in _rows(pairs)]


def _part_script_variable(j: Journey) -> None:
    from gremlin import user_script
    from gremlin.types import InputType
    from gremlin.ui.logical_layout import LogicalLayoutModel

    out = j.out
    page = LogicalLayoutModel()
    j.settle()

    def parents() -> int:
        return sum(
            1 for r in _rows(page) if str(r.get("key", "")).startswith("parent:")
        )

    # A variable makes a control only when the Logical Device has none of
    # its type: the earlier parts made a button, none made a hat.
    from gremlin.logical_device import LogicalDevice

    out["script:hats-before"] = len(
        LogicalDevice().inputs_of_type([InputType.JoystickHat])
    )
    before = parents()
    out["script:before"] = before
    user_script.LogicalDeviceVariable("Notice test", "", False, [InputType.JoystickHat])
    out["script:after"] = j.await_value(parents, before + 1)


def _part_module_file_save(j: Journey) -> None:
    import json

    from gremlin.modules import store

    out = j.out
    model = _model(j)
    row = _row(j, "vJoy 1", "dest")
    out["claims:before"] = sorted(model._dest_target(row)[1].get("buttons", []))[:5]
    # vJoy 1's own device folder (03 S128).
    path = store.module_file("vJoy 1")
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["claim"]["buttons"] = [1, 2, 3]
    store.write_json(path, doc, "Device Library")
    j.settle()
    out["claims:after"] = j.await_value(
        lambda: sorted(
            model._dest_target(_row(j, "vJoy 1", "dest"))[1].get("buttons", [])
        ),
        [1, 2, 3],
    )


def _part_reload_header(j: Journey) -> None:
    """The Output View of vJoy 1 open; the saved profile (from the Swap
    part: no Logical Device binding) is loaded again over the open one,
    which has one."""
    from PySide6 import QtCore

    from gremlin import util

    out = j.out
    _go_home(j)
    slug = _row(j, "vJoy 1", "dest").slug
    j.ev(f'openDeviceBindingsForCard(_moduleModel.cardMap("{slug}"))')
    j.wait_until(lambda: j.ev("uiState.currentRoom") == "configuration", "Output View")
    header = j.item(j.win, "destBound")
    out["reload:header-before"] = str(header.property("text"))
    path = util.profiles_dir() / "notices.xml"
    j.backend.loadProfile(QtCore.QUrl.fromLocalFile(str(path)).toString())
    j.settle()
    out["reload:room"] = j.ev("uiState.currentRoom")
    out["reload:header-after"] = j.await_value(
        lambda: "Logical Device" in str(header.property("text")), False
    )
    out["reload:header-text"] = str(header.property("text"))


def story(j: Journey) -> None:
    import shiboken6
    from PySide6 import QtQuick

    root: Any = shiboken6.wrapInstance(
        shiboken6.getCppPointer(j.win)[0], QtQuick.QQuickWindow
    )
    j.win.setProperty("visible", True)
    root.setWidth(1400)
    root.setHeight(900)
    _go_home(j)
    j.wait_until(lambda: _card_target(j, "vJoy 1") != "NO CARD", "the vJoy 1 card")
    for name, part in (
        ("home", _part_home_on_screen),
        ("mode", _part_delete_mode),
        ("osc", _part_osc_undo),
        ("swap", _part_library_swap),
        ("rename", _part_device_rename),
        ("ld", _part_ld_rename),
        ("script", _part_script_variable),
        ("claims", _part_module_file_save),
        ("reload", _part_reload_header),
    ):
        with _Part(j, name):
            part(j)


def _button_1_dests(j: Journey, uid: Any) -> list[int]:  # noqa: ANN401
    """The vJoy each Map to vJoy on the stick's button 1 sends to."""
    return [
        int(action.vjoy_device_id)
        for item in j.profile.inputs.get(uid, [])
        if item.input_id == 1
        for binding in item.action_sequences
        for action in binding.root_action.get_actions()[0]
        if hasattr(action, "vjoy_device_id")
    ]


def _wire_labels(j: Journey, layout: Any) -> list[str]:  # noqa: ANN401
    """The Device Bindings page's wire labels on button 1 (its action rows)."""
    return [
        str(r.get("subtitle") or "")
        for r in j.catalog_rows(layout)
        if r.get("rowKind") == "child"
        and str(r.get("parentKey", "")) == "parent:button:1"
    ]


def output_story(j: Journey) -> None:
    from PySide6 import QtCore

    from gremlin import util
    from gremlin.ui.device_library_model import DeviceLibraryModel

    out = j.out
    _go_home(j)
    j.wait_until(lambda: _card_target(j, "vJoy 2") != "NO CARD", "the vJoy 2 card")
    pjoy = j.stick("pJoy Pro").device_guid.uuid
    j.map_button(pjoy, 1, "Default", 5, vjoy=1)
    _actions_edited()
    out["out:row1-before"] = j.await_value(
        lambda: "pJoy Pro" in _row_target(j, "vJoy 1"), True
    )
    path = util.profiles_dir() / "output.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(url), "the profile was not saved"
    saved_before = path.read_text(encoding="utf-8")
    layout = j.open_device_bindings(_row(j, "pJoy Pro", "source").slug)
    out["out:wire-before"] = _wire_labels(j, layout)

    library = DeviceLibraryModel()
    library.refresh()
    j.settle()
    key = next(
        str(d["key"])
        for d in library._devices
        if pjoy.hex in str(d.get("guid") or "").lower().replace("-", "")
    )
    results: list[dict] = []
    library.result.connect(lambda r: results.append(dict(r)))
    ticket = library.changeOutput(key, {"1": 2}, False, [url])
    out["out:started"] = bool(ticket)
    done = j.wait_until(
        lambda: next((r for r in results if r.get("ticket") == ticket), None),
        "Change vJoy Output's result",
        timeout=30,
    )
    out["out:ok"] = bool(done.get("ok"))
    out["out:message"] = str(done.get("error") or "")
    out["out:profile"] = _button_1_dests(j, pjoy)
    out["out:file-saved"] = path.read_text(encoding="utf-8") != saved_before
    out["out:wire-after"] = j.await_value(
        lambda: _wire_labels(j, layout), ["vJoy 2 · Button 5"]
    )
    out["out:row1-after"] = j.await_value(
        lambda: "pJoy Pro" in _row_target(j, "vJoy 1"), False
    )
    out["out:row2-after"] = j.await_value(
        lambda: "pJoy Pro" in _row_target(j, "vJoy 2"), True
    )
    _go_home(j)
    out["out:card1-after"] = j.await_value(
        lambda: "pJoy Pro" in _card_target(j, "vJoy 1"), False
    )
    out["out:card2-after"] = j.await_value(
        lambda: _card_target(j, "vJoy 2"), "pJoy Pro"
    )
    j.save_and_reopen("output")
    out["out:profile-reopened"] = _button_1_dests(j, pjoy)


def main() -> None:
    if "output" in sys.argv[1:]:

        def before_output(j: Journey) -> None:
            j.input_module()
            j.vjoy_module(1)
            j.vjoy_module(2)

        Journey(before_output, vjoy_ids=RIG["vjoy_ids"]).run(output_story)
        return

    def before(j: Journey) -> None:
        import dill

        x52 = next(
            dill.GUID(d.device_guid)
            for d in j.dill_fake.devices
            if d.name == b"Saitek X52"
        )
        j.input_module()
        j.input_module("Saitek X52", guid=x52)
        j.vjoy_module()

    Journey(before, **RIG).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("notices"))


def _no_error(run: dict, part: str) -> None:
    assert f"{part}:error" not in run, (
        run.get(f"{part}:error"),
        run.get(f"{part}:traceback"),
    )


def test_home_on_screen_follows_an_edit_in_another_window(run: dict) -> None:
    _no_error(run, "home")
    assert step(run, "home:room") == "status"
    assert step(run, "home:row-after") is True
    assert step(run, "home:card-after") == "pJoy Pro"


def test_delete_mode_updates_driven_by(run: dict) -> None:
    _no_error(run, "mode")
    assert step(run, "mode:row-before") is True
    assert step(run, "mode:card-before") is True
    assert step(run, "mode:row-after") is False
    assert step(run, "mode:card-after") is False


def test_osc_page_undo_updates_driven_by(run: dict) -> None:
    _no_error(run, "osc")
    assert step(run, "osc:row-after-ok") is True
    assert step(run, "osc:row-after-undo") is False
    assert step(run, "osc:card-after-undo") is False


def test_device_library_swap_updates_driven_by(run: dict) -> None:
    _no_error(run, "swap")
    assert step(run, "swap:ok") is True, step(run, "swap:message")
    assert step(run, "swap:row-after") == "Saitek X52"
    assert step(run, "swap:card-after") == "Saitek X52"


def test_device_rename_shows_everywhere(run: dict) -> None:
    _no_error(run, "rename")
    assert step(run, "rename:library") is True
    assert step(run, "rename:viewer") is True
    assert step(run, "rename:title") is True
    assert step(run, "rename:card") is True


def test_logical_device_rename_reaches_input_viewer_and_xbox_page(run: dict) -> None:
    _no_error(run, "ld")
    assert step(run, "ld:pairs-before"), "the Logical Device button is paired"
    assert step(run, "ld:incoming-before"), "the Xbox page lists it as incoming"
    assert step(run, "ld:pairs-after") is True
    assert step(run, "ld:incoming-after") is True
    assert step(run, "ld:xbox-redrawn") is True


def test_script_variable_control_shows_on_the_logical_device_page(run: dict) -> None:
    _no_error(run, "script")
    assert step(run, "script:hats-before") == 0
    assert step(run, "script:after") == step(run, "script:before") + 1


def test_module_file_save_updates_home_output_card_claims(run: dict) -> None:
    _no_error(run, "claims")
    assert step(run, "claims:after") == [1, 2, 3]


def test_output_view_header_follows_a_profile_reload(run: dict) -> None:
    _no_error(run, "reload")
    assert "Logical Device" in step(run, "reload:header-before")
    assert step(run, "reload:header-after") is False, step(run, "reload:header-text")


@pytest.fixture(scope="module")
def output_run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("output"), "output")


def test_change_vjoy_output_moves_driven_by_wire_label_and_profile(
    output_run: dict,
) -> None:
    run = output_run
    assert "error" not in run, (run.get("error"), run.get("traceback"))
    assert step(run, "out:row1-before") is True
    assert step(run, "out:wire-before") == ["vJoy 1 · Button 5"]
    assert step(run, "out:ok") is True, step(run, "out:message")
    assert step(run, "out:profile") == [2]
    assert step(run, "out:wire-after") == ["vJoy 2 · Button 5"]
    assert step(run, "out:row1-after") is False
    assert step(run, "out:row2-after") is True
    assert step(run, "out:card1-after") is False
    assert step(run, "out:card2-after") == "pJoy Pro"
    assert step(run, "out:profile-reopened") == [2]


if __name__ == "__main__":
    main()
