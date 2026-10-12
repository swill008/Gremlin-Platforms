# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The new Device Bindings page, end to end on the real program (batch C).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver with the
fake "pJoy Pro" and a second stick, and a fake vJoy behind the output
module. The story opens the Device Bindings page from the stick's Home card
and drives the page's own model (HardwareLayoutModel), as the screen does:

1. Rows are the module's claimed inputs (05 S121). Open a row, add Map to
   vJoy in the shared pane, OK: the profile has it. Undo, Redo (S127).
2. Layout (S122, CS1): add a group, move inputs into it, reorder. The title
   shows "*", the module file is untouched; File > Save writes the layout
   into the module file (one History entry); open the profile again: the
   page shows it.
3. Rename (S129): writes the module's friendly name at Save, not before.
4. Discard drops an unsaved layout change (CS1).
5. Live decoration and jump to pressed input (S131): a fake stick button
   press lights its row and the page jumps to it.
6. Switching device clears Undo (S127).
7. The Keyboard page on the same layout (S128): add a key, give it an
   action, put it in a group.

Each part records its own values, so one failing part doesn't hide the
others. Parts that need code not in yet are xfail(strict) while the file
they need is missing, so they turn into ordinary tests once it lands.

Spec: 05 (actions/editors) section M S121-S131, CS1; 03 S121.
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
    Journey,
    JourneyIncomplete,
    run_journey,
)

STICK = "pJoy Pro"
SECOND = "Second Stick"
CLAIMED = [1, 2, 3, 4]
VJOY_BUTTON = 3
GROUP = "Weapons"
B1, B2, B3 = "parent:button:1", "parent:button:2", "parent:button:3"


def _qml_uses(word: str) -> bool:
    return any(
        word in p.read_text(encoding="utf-8", errors="replace")
        for p in (ROOT / "qml").glob("*.qml")
    )


_PAGE_MISSING = [
    what
    for what, there in (
        (
            "gremlin/ui/hardware_layout.py",
            (ROOT / "gremlin/ui/hardware_layout.py").exists(),
        ),
        ("qml/DeviceBindingsPage.qml", (ROOT / "qml/DeviceBindingsPage.qml").exists()),
        ("a QML page using HardwareLayoutModel", _qml_uses("HardwareLayoutModel")),
    )
    if not there
]
needs_page = pytest.mark.xfail(
    bool(_PAGE_MISSING),
    reason="needs the batch C Device Bindings page: missing "
    + ", ".join(_PAGE_MISSING),
    raises=(AssertionError, JourneyIncomplete),
    strict=True,
)

_LIVE_MISSING = list(_PAGE_MISSING)
if not _qml_uses("liveDecoration"):
    _LIVE_MISSING.append("ControlTree liveDecoration (CFG-APPEAR)")
needs_live = pytest.mark.xfail(
    bool(_LIVE_MISSING),
    reason="needs the live decoration: missing " + ", ".join(_LIVE_MISSING),
    raises=(AssertionError, JourneyIncomplete),
    strict=True,
)

_KEYS_MISSING = [
    what
    for what, there in (
        ("qml/KeyboardPage.qml", (ROOT / "qml/KeyboardPage.qml").exists()),
        (
            "gremlin/ui/keyboard_layout.py KeyboardLayoutModel",
            "class KeyboardLayoutModel"
            in (ROOT / "gremlin/ui/keyboard_layout.py").read_text(encoding="utf-8")
            if (ROOT / "gremlin/ui/keyboard_layout.py").exists()
            else False,
        ),
    )
    if not there
]
needs_keys = pytest.mark.xfail(
    bool(_KEYS_MISSING),
    reason="needs the Keyboard page on the shared layout: missing "
    + ", ".join(_KEYS_MISSING),
    raises=(AssertionError, JourneyIncomplete),
    strict=True,
)


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part of the story; an error is recorded under the part's
    name and the next part still runs."""

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


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
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


def _parents(model: Any) -> list[str]:  # noqa: ANN401
    return [
        r["key"] for r in _rows(model) if str(r.get("key", "")).startswith("parent:")
    ]


def _in_group(model: Any, group: str) -> list[str]:  # noqa: ANN401
    return [
        r["key"]
        for r in _rows(model)
        if str(r.get("key", "")).startswith("parent:")
        and (r.get("groupName") or "") == group
    ]


def _row(model: Any, key: str) -> dict:  # noqa: ANN401
    return next((r for r in _rows(model) if r.get("key") == key), {})


def _group_names(model: Any) -> list[str]:  # noqa: ANN401
    return [
        g["name"] if isinstance(g, dict) else str(g)
        for g in (model.property("groups") or [])
    ]


def _same_guid(a: object, b: object) -> bool:
    def clean(v: object) -> str:
        return str(v).strip("{}").lower()

    return clean(a) == clean(b)


def _open_page(j: Journey, slug: str, guid: object) -> Any:  # noqa: ANN401
    """Opens the Device Bindings page from the stick's Home card; returns
    the page's HardwareLayoutModel showing that stick."""
    import json

    from gremlin.ui.hardware_layout import HardwareLayoutModel

    j.ev(f"openDeviceBindingsForCard(_moduleModel.cardMap({json.dumps(slug)}))")

    def find() -> Any:  # noqa: ANN401
        for model in j.win.findChildren(HardwareLayoutModel):
            if _same_guid(model.property("guid"), guid) and model.property(
                "parentCount"
            ):
                return model
        return None

    return j.wait_until(find, f"the Device Bindings page of {slug}")


def _module_path(guid: object) -> pathlib.Path:
    from gremlin.modules import store

    return store.module_file(STICK, str(guid))


def _module_doc(guid: object) -> dict:
    import json

    return json.loads(_module_path(guid).read_text(encoding="utf-8-sig"))


def _history_count(j: Journey, guid: object) -> int:
    from gremlin import history

    j.wait_until(lambda: history._writer is None, "the History writer", 10)
    path = _module_path(guid)
    name = f"{path.parent.name}/{path.name}"
    return sum(
        1 for e in history.entries() if (e.get("subject") or {}).get("fileName") == name
    )


def _vjoy_targets(j: Journey, uid: Any, button: int) -> list[int]:  # noqa: ANN401
    from gremlin.types import InputType

    for item in j.profile.inputs.get(uid, []):
        if item.input_type == InputType.JoystickButton and item.input_id == button:
            return [
                getattr(action, "vjoy_input_id", -1)
                for seq in item.action_sequences
                for action in seq.root_action.get_actions()[0]
                if action.name == "Map to vJoy"
            ]
    return []


def _map_to_vjoy(button: int) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _part_rows_and_pane(j: Journey, page: Any, uid: Any) -> None:  # noqa: ANN401
    """1: rows are the claimed inputs; Map to vJoy in the pane; Undo/Redo."""
    out = j.out
    parents = _parents(page)
    out["1:button-parents"] = sorted(
        k for k in parents if k.startswith("parent:button:")
    )
    page.beginNewAction(B1)
    shadow = page._pane_shadow
    shadow.action_sequences[0].root_action.insert_action(
        _map_to_vjoy(VJOY_BUTTON), "children"
    )
    out["1:dirty"] = page.paneDirty()
    out["1:commit-index"] = page.commitPane()
    page.endPane()
    j.settle()
    out["1:after-ok"] = _vjoy_targets(j, uid, 1)
    out["1:child-rows"] = sum(
        1 for r in _rows(page) if r.get("parentKey") == B1 and r.get("key") != B1
    )
    out["1:can-undo"] = bool(page.property("canUndo"))
    page.undo()
    j.settle()
    out["1:after-undo"] = _vjoy_targets(j, uid, 1)
    out["1:can-redo"] = bool(page.property("canRedo"))
    page.redo()
    j.settle()
    out["1:after-redo"] = _vjoy_targets(j, uid, 1)


def _part_layout(j: Journey, page: Any, uid: Any) -> Any:  # noqa: ANN401
    """2: group, move, reorder; "*", file untouched; Save; reload."""
    from PySide6 import QtCore

    from gremlin import util
    from gremlin.modules import store

    out = j.out
    # A saved profile first, so File > Save has a file.
    path = util.profiles_dir() / "cfg_page_e2e.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(url)
    j.settle()
    out["2:star-before"] = bool(j.backend.property("profileContainsUnsavedChanges"))
    file_before = _module_path(uid).read_bytes()
    entries_before = _history_count(j, uid)

    page.addGroup(GROUP)
    page.setSelection([B1, B2])
    page.moveSelected(GROUP)
    j.settle()
    out["2:groups"] = _group_names(page)
    out["2:order-before"] = _in_group(page, GROUP)
    page.moveParent(B2, B1, "before")
    j.settle()
    out["2:order-after"] = _in_group(page, GROUP)
    out["2:star"] = bool(j.backend.property("profileContainsUnsavedChanges"))
    out["2:pending"] = store.has_pending()
    out["2:file-unchanged"] = _module_path(uid).read_bytes() == file_before
    out["2:can-undo-layout"] = bool(page.property("canUndo"))

    # File > Save.
    assert j.backend.saveProfile(url)
    j.settle()
    out["2:star-after-save"] = bool(j.backend.property("profileContainsUnsavedChanges"))
    doc = _module_doc(uid)
    layout = doc.get("layout") or {}
    out["2:file-groups"] = list(layout.get("groups") or [])
    out["2:file-group-of"] = dict(layout.get("group_of") or {})
    out["2:file-order"] = list(layout.get("order") or [])
    out["2:history-new"] = _history_count(j, uid) - entries_before
    out["2:profile-has-group"] = GROUP in path.read_text(encoding="utf-8-sig")

    # Open another profile, then this one again.
    j.reopen(url)
    j.settle()
    page = _open_page(j, "pjoy_pro", uid)
    out["2:groups-reloaded"] = _group_names(page)
    out["2:order-reloaded"] = _in_group(page, GROUP)
    out["2:binding-reloaded"] = _vjoy_targets(j, uid, 1)
    out["2:url"] = url
    return page


def _part_rename(j: Journey, page: Any, uid: Any) -> None:  # noqa: ANN401
    """3: Rename writes the module's friendly name, at Save."""
    out = j.out
    page.setUserName(B3, "Pinkie")
    j.settle()
    out["3:title"] = _row(page, B3).get("title")
    out["3:file-before-save"] = (
        (_module_doc(uid).get("claim") or {}).get("friendly") or {}
    ).get("button:3", "")
    assert j.backend.saveProfile(j.out["2:url"])
    j.settle()
    out["3:file-after-save"] = (
        (_module_doc(uid).get("claim") or {}).get("friendly") or {}
    ).get("button:3", "")


def _part_discard(j: Journey, page: Any, uid: Any) -> None:  # noqa: ANN401
    """4: Discard drops an unsaved layout change."""
    from gremlin.modules import store

    out = j.out
    file_before = _module_path(uid).read_bytes()
    page.addGroup("Temporary")
    j.settle()
    out["4:groups-edited"] = _group_names(page)
    out["4:pending-edited"] = store.has_pending()
    # What the save question's Discard calls.
    j.backend.discardDeviceBindingsLayouts()
    j.settle()
    out["4:groups-discarded"] = _group_names(page)
    out["4:pending-discarded"] = store.has_pending()
    out["4:file-unchanged"] = _module_path(uid).read_bytes() == file_before


def _live_tree(j: Journey) -> Any:  # noqa: ANN401
    for item in j.walk(j.win.contentItem()):
        if item.property("liveDecoration") is True and item.isVisible():
            return item
    return None


def _part_live(j: Journey, page: Any, uid: Any) -> None:  # noqa: ANN401
    """5: a stick press lights its row and the page jumps to it."""
    from gremlin.config import Configuration
    from gremlin.signal import signal
    from gremlin.ui.live_input import DeviceLiveState

    out = j.out
    Configuration().set("ui", "general", "input-highlighting", True)
    emitted: list[int] = []
    signal.setInputIndex.connect(emitted.append)
    tree = j.wait_until(lambda: _live_tree(j), "the tree with live decoration", 5)
    out["5:tree-highlight-before"] = str(tree.property("highlightKey") or "")
    index = int(_row(page, B3).get("deviceIndex", -1))
    out["5:device-index"] = index
    states = [
        s
        for s in j.win.findChildren(DeviceLiveState)
        if _same_guid(s.property("guid"), uid)
    ]
    out["5:live-states"] = len(states)
    stick = j.stick(STICK)
    j.press(stick, 3, True)

    def lit() -> bool:
        return any(float(s.valueAt(index)) > 0.5 for s in states)

    out["5:lit"] = bool(j.await_value(lit, True, 3))
    out["5:jump-signal"] = bool(j.await_value(lambda: bool(emitted), True, 3))
    out["5:tree-highlight"] = str(
        j.await_value(lambda: str(tree.property("highlightKey") or ""), B3, 3)
    )
    j.press(stick, 3, False)
    out["5:unlit"] = not bool(j.await_value(lit, False, 3))
    signal.setInputIndex.disconnect(emitted.append)


def _part_switch(j: Journey, page: Any, second: Any) -> None:  # noqa: ANN401
    """6: another device clears every Undo step."""
    out = j.out
    page.addGroup("Before switch")
    j.settle()
    out["6:can-undo-before"] = bool(page.property("canUndo"))
    page.setDevice(str(second), SECOND)
    j.settle()
    out["6:can-undo-after"] = bool(page.property("canUndo"))
    out["6:can-redo-after"] = bool(page.property("canRedo"))
    out["6:second-buttons"] = sorted(
        k for k in _parents(page) if k.startswith("parent:button:")
    )
    # Not saved: the held group goes with Discard.
    j.backend.discardDeviceBindingsLayouts()
    j.settle()


def _part_keyboard(j: Journey) -> None:
    """7: the Keyboard page: add a key, give it an action, group it."""
    import dill
    from gremlin.types import InputType
    from gremlin.ui.keyboard_layout import KeyboardLayoutModel

    out = j.out
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(
        lambda: j.backend.uiState.currentTab == "keyboard", "the Keyboard page"
    )
    page = j.wait_until(
        lambda: j.win.findChild(KeyboardLayoutModel), "the Keyboard page's model"
    )
    view = j.wait_until(
        lambda: next(
            (
                it
                for it in j.walk(j.win.contentItem())
                if it.property("layoutModel") is page and it.isVisible()
            ),
            None,
        ),
        "the KeyboardPage item",
    )
    # Add Key as the page's button does: it listens, then the A key
    # (scan code 0x1E) is pressed on the PC's keyboard.
    j.ev("addKey(); true", view)
    j.wait_until(lambda: j.ev("_listen.visible", view), "Add Key listening", 5)
    j.key(0x1E, True)
    j.key(0x1E, False)
    keys = j.await_value(lambda: _parents(page), ["x"], 3)
    out["7:added"] = bool(keys)
    out["7:parents"] = keys
    key = keys[0] if keys else ""
    out["7:key"] = key
    out["7:pane-opened-on-it"] = str(view.property("paneKey") or "")
    # The pane the Add Key opened, as the screen shows it.
    if view.property("actionOpen"):
        j.ev("actionPane.closeActionPane(); true", view)
        j.settle()
    page.beginNewAction(key)
    page._pane_shadow.action_sequences[0].root_action.insert_action(
        _map_to_vjoy(5), "children"
    )
    out["7:commit-index"] = page.commitPane()
    page.endPane()
    j.settle()
    targets = []
    for item in j.profile.inputs.get(dill.UUID_Keyboard, []):
        if item.input_type == InputType.Keyboard:
            targets += [
                getattr(a, "vjoy_input_id", -1)
                for seq in item.action_sequences
                for a in seq.root_action.get_actions()[0]
                if a.name == "Map to vJoy"
            ]
    out["7:targets"] = targets
    page.addGroup("Keys")
    page.setSelection([key])
    page.moveSelected("Keys")
    j.settle()
    out["7:in-group"] = _in_group(page, "Keys")


def story(j: Journey) -> None:
    uid = j.stick(STICK).device_guid.uuid
    second = j.stick(SECOND).device_guid.uuid
    j.out["uid"] = str(uid)
    page = None
    with _Part(j, "1"):
        page = _open_page(j, "pjoy_pro", uid)
        _part_rows_and_pane(j, page, uid)
    with _Part(j, "2"):
        if page is None:
            raise RuntimeError("part 1 did not open the page")
        page = _part_layout(j, page, uid)
    for name, part in (("3", _part_rename), ("4", _part_discard), ("5", _part_live)):
        with _Part(j, name):
            if page is None:
                raise RuntimeError("the page was not opened")
            page = _open_page(j, "pjoy_pro", uid)
            part(j, page, uid)
    with _Part(j, "6"):
        page = _open_page(j, "pjoy_pro", uid)
        _part_switch(j, page, second)


def keyboard_story(j: Journey) -> None:
    """The Keyboard page in a process of its own: a crash on the
    Device Bindings page doesn't hide it."""
    with _Part(j, "7"):
        _part_keyboard(j)


def main() -> None:
    def before(j: Journey) -> None:
        second = j.add_stick(SECOND, 7)
        j.input_module(buttons=CLAIMED)
        j.input_module(SECOND, buttons=[5, 6], guid=second)
        j.vjoy_module()

    which = sys.argv[1] if len(sys.argv) > 1 else "device-bindings"
    Journey(before).run(keyboard_story if which == "keyboard" else story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("cfg_page_e2e"))


@pytest.fixture(scope="module")
def run_keys(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(
        __file__, tmp_path_factory.mktemp("cfg_page_e2e_keys"), "keyboard"
    )


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {out.get(part + ':error', out.get('error', '(none)'))}\n"
        f"{out.get(part + ':traceback', out.get('traceback', ''))}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


@needs_page
def test_rows_are_the_claimed_inputs(run: dict) -> None:
    assert _step(run, "1:button-parents") == sorted(
        f"parent:button:{n}" for n in CLAIMED
    )


@needs_page
def test_map_to_vjoy_in_the_pane_with_undo_and_redo(run: dict) -> None:
    assert _step(run, "1:dirty") is True
    assert _step(run, "1:commit-index") == 0
    assert _step(run, "1:after-ok") == [VJOY_BUTTON]
    assert _step(run, "1:child-rows") >= 1
    assert _step(run, "1:can-undo") is True
    assert _step(run, "1:after-undo") == []
    assert _step(run, "1:can-redo") is True
    assert _step(run, "1:after-redo") == [VJOY_BUTTON]


@needs_page
def test_layout_is_held_until_save_then_in_the_module_file(run: dict) -> None:
    assert _step(run, "2:star-before") is False
    assert GROUP in _step(run, "2:groups")
    assert sorted(_step(run, "2:order-before")) == [B1, B2]
    assert _step(run, "2:order-after") == [B2, B1]
    # Held: "*" in the title, the module file not written yet (CS1).
    assert _step(run, "2:star") is True
    assert _step(run, "2:pending") is True
    assert _step(run, "2:file-unchanged") is True
    assert _step(run, "2:can-undo-layout") is True
    # File > Save: into the module file, one History entry, not the profile.
    assert _step(run, "2:star-after-save") is False
    assert _step(run, "2:file-groups") == [GROUP]
    assert _step(run, "2:file-group-of") == {"button:1": GROUP, "button:2": GROUP}
    order = _step(run, "2:file-order")
    assert order.index("button:2") < order.index("button:1")
    assert _step(run, "2:history-new") == 1
    assert _step(run, "2:profile-has-group") is False


@needs_page
def test_the_saved_layout_shows_after_a_reload(run: dict) -> None:
    assert GROUP in _step(run, "2:groups-reloaded")
    assert _step(run, "2:order-reloaded") == [B2, B1]
    assert _step(run, "2:binding-reloaded") == [VJOY_BUTTON]


@needs_page
def test_rename_writes_the_friendly_name_at_save(run: dict) -> None:
    assert _step(run, "3:title") == "Pinkie"
    assert _step(run, "3:file-before-save") == ""
    assert _step(run, "3:file-after-save") == "Pinkie"


@needs_page
def test_discard_drops_an_unsaved_layout_change(run: dict) -> None:
    assert "Temporary" in _step(run, "4:groups-edited")
    assert _step(run, "4:pending-edited") is True
    assert "Temporary" not in _step(run, "4:groups-discarded")
    assert GROUP in _step(run, "4:groups-discarded")
    assert _step(run, "4:pending-discarded") is False
    assert _step(run, "4:file-unchanged") is True


@needs_live
def test_a_stick_press_lights_its_row(run: dict) -> None:
    assert _step(run, "5:device-index") >= 0
    assert _step(run, "5:live-states") >= 1
    assert _step(run, "5:lit") is True
    assert _step(run, "5:unlit") is True


@needs_live
def test_a_stick_press_jumps_to_its_row(run: dict) -> None:
    assert _step(run, "5:jump-signal") is True
    assert _step(run, "5:tree-highlight") == B3


@needs_page
def test_switching_device_clears_undo(run: dict) -> None:
    assert _step(run, "6:can-undo-before") is True
    assert _step(run, "6:can-undo-after") is False
    assert _step(run, "6:can-redo-after") is False
    assert _step(run, "6:second-buttons") == ["parent:button:5", "parent:button:6"]


@needs_keys
def test_keyboard_page_add_key_action_and_group(run_keys: dict) -> None:
    run = run_keys
    assert _step(run, "7:added") is True
    assert len(_step(run, "7:parents")) == 1
    assert _step(run, "7:pane-opened-on-it") == _step(run, "7:key")
    assert _step(run, "7:commit-index") == 0
    assert _step(run, "7:targets") == [5]
    assert _step(run, "7:in-group") == [_step(run, "7:key")]


if __name__ == "__main__":
    main()
