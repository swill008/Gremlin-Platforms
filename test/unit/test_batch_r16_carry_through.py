# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""R16 batch carry-through: what the batch keeps survives every path that
carries a profile's bindings.

Cases:
- raw: a macro step the program can't read (unknown type, unreadable data)
  is kept as its saved element, byte-equal after each path (05 S117);
- ld_missing: a macro Logical Device step whose control is missing is kept
  on Save (05 S117);
- merge: Merge Axis "maximum-deflection" keeps its operation (05 S114);
- vjoy_ids: Map to vJoy, a vJoy condition and a vJoy macro step saved on
  vJoy 3 button 5 keep those ids; creation defaults (05 S113, S115) never
  touch loaded data.

Paths: profile save + reload, History (input restore), Library copy
(Copy to Another Stick), Export (Export Current Setup, then import and
copy), Restore (Save to Device Library, then Restore) and Device Pack
(assemble + import). Plus: a profile with vJoy macro steps, conditions and
Map to vJoy opens with no vJoy and no modules (05 S104).

The real Profile, Device Pack, Device Library store (temp folder) and
History (temp folder); the fake pJoy Pro stick (conftest)."""

# The fixture lib comes from LC's tests.
# ruff: noqa: F811

from __future__ import annotations

import re
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import device_library as library
from gremlin import history, history_profile, library_copy, shared_state
from gremlin.base_classes import AbstractActionData
from gremlin.modules import output
from gremlin.profile import DeviceInfo, Profile, reachable
from gremlin.types import InputType
from gremlin.ui import device_pack, history_model
from test.unit.test_device_library_LC_copy import (  # noqa: F401 - the fixture
    _ALL,
    _REAL,
    lib,
)
from test.unit.test_stage1_modules import (  # pyright: ignore[reportMissingImports]
    settle_history,
)

pytestmark = pytest.mark.validate_off

_B = InputType.JoystickButton
_A = InputType.JoystickAxis

# Inputs of the pJoy Pro each case lives on.
RAW_BUTTON = 5
LD_BUTTON = 6
MAP_BUTTON = 7
COND_BUTTON = 8
MERGE_AXIS = 1
CASE_INPUTS: dict[str, list[tuple[InputType, int]]] = {
    "raw": [(_B, RAW_BUTTON)],
    "ld_missing": [(_B, LD_BUTTON)],
    "merge": [(_A, MERGE_AXIS)],
    "vjoy_ids": [(_B, RAW_BUTTON), (_B, MAP_BUTTON), (_B, COND_BUTTON)],
}

# A step of a type this program doesn't know, and a vJoy step whose data
# can't be read (05 S117): both kept exactly as saved.
UNKNOWN_STEP = (
    '<macro-action type="future-step" flavour="x">'
    '<property type="string"><name>what</name><value>kept</value></property>'
    "<extra a=\"1\">text<inner/></extra>"
    "</macro-action>"
)
UNREADABLE_STEP = (
    '<macro-action type="vjoy">'
    '<property type="int"><name>vjoy-id</name><value>not-a-number</value>'
    "</property>"
    "</macro-action>"
)
VJOY_STEP = (
    '<macro-action type="vjoy">'
    '<property type="int"><name>vjoy-id</name><value>3</value></property>'
    '<property type="input_type"><name>input-type</name><value>button</value>'
    "</property>"
    '<property type="int"><name>input-id</name><value>5</value></property>'
    '<property type="bool"><name>value</name><value>True</value></property>'
    "</macro-action>"
)
# A Logical Device step naming a control the Logical Device doesn't have.
MISSING_UID = "e" * 32
LD_STEP = (
    f'<macro-action type="logical-device" uid="{MISSING_UID}">'
    '<property type="input_type"><name>input-type</name><value>button</value>'
    "</property>"
    '<property type="int"><name>input-id</name><value>977</value></property>'
    '<property type="bool"><name>value</name><value>True</value></property>'
    "</macro-action>"
)

def _canon(element: ElementTree.Element) -> str:
    return ElementTree.canonicalize(
        ElementTree.tostring(element, encoding="unicode"), strip_text=True
    )


# --- Building the source profile ----------------------------------------


def _bind(
    profile: Profile,
    uid: uuid.UUID,
    kind: InputType,
    number: int,
    action: AbstractActionData,
) -> None:
    item = profile.get_input_item(uid, kind, number, "Default", create_if_missing=True)
    assert item is not None
    root = item.add_item_binding().root_action
    assert root is not None
    root.insert_action(action, "children")


def _build(path: Path, uid: uuid.UUID, name: str, raw: bool = True) -> Profile:
    """The source profile, saved to path and opened again from it (raw:
    with the unreadable steps, which stop it opening before MACROLOAD)."""
    from action_plugins.condition import condition as ca
    from action_plugins.merge_axis import MergeOperation

    profile = Profile()
    profile.device_database.devices[uid] = DeviceInfo(uid, name)
    raw_macro = profile.library.create("Macro", _B)
    ld_macro = profile.library.create("Macro", _B)
    assert raw_macro is not None and ld_macro is not None
    _bind(profile, uid, _B, RAW_BUTTON, raw_macro)
    _bind(profile, uid, _B, LD_BUTTON, ld_macro)

    merge = profile.library.create("Merge Axis", _A, reuse=False)
    assert merge is not None
    merge.axis_in1.input_type = _A  # type: ignore[attr-defined]
    merge.axis_in2.input_type = _A  # type: ignore[attr-defined]
    merge.axis_in1.device_guid = uid  # type: ignore[attr-defined]
    merge.axis_in1.input_id = 1  # type: ignore[attr-defined]
    merge.axis_in2.device_guid = uid  # type: ignore[attr-defined]
    merge.axis_in2.input_id = 2  # type: ignore[attr-defined]
    merge.operation = MergeOperation.MaximumDeflection  # type: ignore[attr-defined]
    _bind(profile, uid, _A, MERGE_AXIS, merge)

    vjoy_map = profile.library.create("Map to vJoy", _B)
    assert vjoy_map is not None
    vjoy_map.vjoy_device_id = 3  # type: ignore[attr-defined]
    vjoy_map.vjoy_input_type = _B  # type: ignore[attr-defined]
    vjoy_map.vjoy_input_id = 5  # type: ignore[attr-defined]
    _bind(profile, uid, _B, MAP_BUTTON, vjoy_map)

    cond = profile.library.create("Condition", _B)
    assert cond is not None
    vjc = ca.VJoyCondition()
    vjc.start_on(3, _B, 5)
    cond.conditions.append(vjc)  # type: ignore[attr-defined]
    _bind(profile, uid, _B, COND_BUTTON, cond)

    profile.to_xml(path)
    # The steps go into the saved file as another program version (or a
    # damaged edit) would have left them.
    tree = ElementTree.parse(path)
    for node in tree.getroot().iter("action"):
        if node.get("id") == str(raw_macro.id):
            kept = (UNKNOWN_STEP, UNREADABLE_STEP) if raw else ()
            for text in (*kept, VJOY_STEP):
                node.append(ElementTree.fromstring(text))
        elif node.get("id") == str(ld_macro.id):
            node.append(ElementTree.fromstring(LD_STEP))
    tree.write(path, encoding="utf-8", xml_declaration=True)
    loaded = Profile()
    loaded.from_xml(path)
    return loaded


# --- What each case looks at --------------------------------------------


def _actions_of(
    profile: Profile, uid: uuid.UUID, kind: InputType, number: int
) -> Iterator[AbstractActionData]:
    for item in profile.inputs.get(uid, []):
        if (item.mode, item.input_type, item.input_id) == ("Default", kind, number):
            yield from reachable(Profile.roots_of([item]))


def _xml_of(action: AbstractActionData) -> ElementTree.Element | None:
    return action.to_xml()


def _props(action: AbstractActionData) -> list[ElementTree.Element]:
    node = _xml_of(action)
    return [] if node is None else node.findall("property")


def _steps(profile: Profile, uid: uuid.UUID, number: int) -> list[str]:
    """The saved macro-action elements of the macro on that button."""
    out = []
    for action in _actions_of(profile, uid, _B, number):
        if getattr(action, "tag", "") != "macro":
            continue
        node = _xml_of(action)
        assert node is not None, "the macro isn't saved"
        out += [_canon(step) for step in node.iter("macro-action")]
    return out


def _vjoy_ids(profile: Profile, uid: uuid.UUID) -> dict[str, list[tuple[str, str]]]:
    """(vjoy-id, input-id) saved by Map to vJoy, the vJoy condition and the
    vJoy macro steps."""

    def props(node: ElementTree.Element, *names: str) -> tuple[str, ...]:
        found = {}
        for prop in node.findall("property"):
            key = prop.findtext("name")
            if key in names:
                found[key] = prop.findtext("value")
        return tuple(str(found.get(n)) for n in names)

    got: dict[str, list[tuple[str, str]]] = {"map": [], "condition": [], "step": []}
    for action in _actions_of(profile, uid, _B, MAP_BUTTON):
        if getattr(action, "tag", "") == "map-to-vjoy":
            got["map"].append(
                (str(action.vjoy_device_id), str(action.vjoy_input_id))  # type: ignore[attr-defined]
            )
    for action in _actions_of(profile, uid, _B, COND_BUTTON):
        if getattr(action, "tag", "") != "condition":
            continue
        node = _xml_of(action)
        assert node is not None, "the condition isn't saved"
        for cond in node.iter("condition"):
            if any(p.findtext("name") == "vjoy-id" for p in cond.iter("property")):
                got["condition"].append(props(cond, "vjoy-id", "input-id"))  # type: ignore[arg-type]
    for step in _steps(profile, uid, RAW_BUTTON):
        node = ElementTree.fromstring(step)
        if node.get("type") == "vjoy":
            ids = props(node, "vjoy-id", "input-id")
            if ids[0].isdigit():
                got["step"].append(ids)  # type: ignore[arg-type]
    return got


def _check(case: str, profile: Profile, uid: uuid.UUID) -> None:
    if case == "raw":
        steps = _steps(profile, uid, RAW_BUTTON)
        for text in (UNKNOWN_STEP, UNREADABLE_STEP):
            want = _canon(ElementTree.fromstring(text))
            assert want in steps, (want, steps)
    elif case == "ld_missing":
        steps = _steps(profile, uid, LD_BUTTON)
        want = _canon(ElementTree.fromstring(LD_STEP))
        assert want in steps, (want, steps)
    elif case == "merge":
        ops = [
            node.findtext("value")
            for action in _actions_of(profile, uid, _A, MERGE_AXIS)
            if getattr(action, "tag", "") == "merge-axis"
            for node in _props(action)
            if node.findtext("name") == "operation"
        ]
        assert ops == ["maximum-deflection"], ops
    elif case == "vjoy_ids":
        assert _vjoy_ids(profile, uid) == {
            "map": [("3", "5")],
            "condition": [("3", "5")],
            "step": [("3", "5")],
        }
    else:  # pragma: no cover
        raise AssertionError(case)


# --- The paths ------------------------------------------------------------


def _empty(path: Path, uid: uuid.UUID, name: str) -> Profile:
    """An open profile at path with the stick and nothing bound."""
    profile = Profile()
    profile.device_database.devices[uid] = DeviceInfo(uid, name)
    profile.to_xml(path)
    profile.fpath = path
    shared_state.current_profile = profile
    return profile


def _open(path: Path) -> Profile:
    profile = Profile()
    profile.from_xml(path)
    profile.fpath = path
    shared_state.current_profile = profile
    return profile


def _save_reload(env: dict) -> Profile:
    again = env["tmp"] / "again.xml"
    env["source"].to_xml(again)
    loaded = Profile()
    loaded.from_xml(again)
    return loaded


def _history(env: dict, monkeypatch: pytest.MonkeyPatch) -> Profile:
    settle_history()
    monkeypatch.setattr(history, "folder", lambda: env["tmp"] / "history")
    monkeypatch.setattr(history, "_pruned", True)
    path = env["path"]
    before = path.read_text(encoding="utf-8-sig")
    target = _empty(path, env["uid"], env["name"])
    after = path.read_text(encoding="utf-8-sig")
    history_profile.record_save(path, before, after)
    settle_history()
    entries = [
        e
        for e in history.entries()
        if e.get("area") == "profile" and e.get("kind") == "input"
    ]
    assert entries, history.entries()
    for entry in entries:
        out = history_model.restore(str(entry["id"]), "before")
        assert out["ok"], out
    return target


def _device_pack(env: dict) -> Profile:
    built = device_pack.assemble(
        env["name"],
        lambda stored: None,
        None,
        None,
        profile=env["source"],
        guid=str(env["uid"]),
    )
    assert not isinstance(built, str), built
    pack = env["tmp"] / "carry.zip"
    pack.write_bytes(built[0])
    fresh = Profile()
    fresh.device_database.devices[env["uid"]] = DeviceInfo(env["uid"], env["name"])
    result = device_pack.apply_zip(
        pack, env["name"], {"items": ["wire:Default"]}, fresh, record_undo=False
    )
    assert result["ok"], result
    return fresh


def _real(env: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    for name, real in _REAL.items():
        monkeypatch.setattr(library, name, real)
    monkeypatch.setattr(library, "folder", lambda: env["tmp"] / "device library")


def _library_copy(env: dict, monkeypatch: pytest.MonkeyPatch) -> Profile:
    _real(env, monkeypatch)
    _open(env["path"])
    saved = library.save_setup(env["name"], env["guid"], [env["path"]])
    assert saved["ok"], saved
    setup = (saved.get("setups") or [saved.get("setup")])[0]
    target_path = env["tmp"] / "target.xml"
    target = _empty(target_path, env["uid"], env["name"])
    result = library_copy.copy(
        setup["key"], env["name"], env["guid"], _ALL, [target_path], ["Default"]
    )
    assert result["ok"], result
    return target


def _export(env: dict, monkeypatch: pytest.MonkeyPatch) -> Profile:
    _real(env, monkeypatch)
    _open(env["path"])
    row = next(r for r in library.devices() if r.get("guid") == env["guid"])
    dest = env["tmp"] / "out" / "now.zip"
    out = library.export_current(row["key"], dest)
    assert out["ok"], out
    imported = library.import_pack(dest)
    assert imported["ok"], imported
    target_path = env["tmp"] / "target.xml"
    target = _empty(target_path, env["uid"], env["name"])
    result = library_copy.copy(
        imported["setup"]["key"],
        env["name"],
        env["guid"],
        _ALL,
        [target_path],
        ["Default"],
    )
    assert result["ok"], result
    return target


def _restore(env: dict, monkeypatch: pytest.MonkeyPatch) -> Profile:
    _real(env, monkeypatch)
    _open(env["path"])
    saved = library.save_setup(env["name"], env["guid"], [env["path"]])
    assert saved["ok"], saved
    setup = (saved.get("setups") or [saved.get("setup")])[0]
    _empty(env["path"], env["uid"], env["name"])
    result = library_copy.restore(setup["key"])
    assert result["ok"], result
    profile = shared_state.current_profile
    assert profile is not None
    return profile


PATHS: dict[str, Callable[..., Profile]] = {
    "save_reload": lambda env, mp: _save_reload(env),
    "history": _history,
    "library_copy": _library_copy,
    "export": _export,
    "restore": _restore,
    "device_pack": lambda env, mp: _device_pack(env),
}


@pytest.fixture
def env(
    lib: dict, monkeypatch: pytest.MonkeyPatch, request: pytest.FixtureRequest
) -> dict:
    # A creation default that differs from every saved id: loading must
    # never take it (05 S113, S115).
    monkeypatch.setattr(
        output, "first_claimed_output", lambda *a, **k: (1, _B, 1), raising=False
    )
    path = lib["tmp"] / "source.xml"
    params = getattr(request.node, "callspec", None)
    case = params.params.get("case", "raw") if params else "raw"
    source = _build(path, lib["uid"], lib["name"], raw=case == "raw")
    source.fpath = path
    shared_state.current_profile = source
    device_pack.drop_import_undo()
    return {**lib, "path": path, "source": source}


@pytest.mark.parametrize("path_name", list(PATHS))
@pytest.mark.parametrize("case", list(CASE_INPUTS))
def test_case_survives_path(
    case: str, path_name: str, request: pytest.FixtureRequest
) -> None:
    monkeypatch = request.getfixturevalue("monkeypatch")
    env = request.getfixturevalue("env")
    _check(case, env["source"], env["uid"])
    result = PATHS[path_name](env, monkeypatch)
    _check(case, result, env["uid"])


# --- 05 S104: opens with no vJoy and no modules --------------------------


def test_vjoy_bindings_open_with_no_vjoy_and_no_modules(
    request: pytest.FixtureRequest,
) -> None:
    """The profile opens; Map to vJoy, the vJoy condition and the vJoy macro
    step keep vJoy 3 button 5; nothing is dropped on Save."""
    from gremlin.modules import store
    from vjoy import vjoy

    monkeypatch = request.getfixturevalue("monkeypatch")
    env = request.getfixturevalue("env")
    monkeypatch.setattr(vjoy, "device_exists", lambda vjoy_id: False)
    monkeypatch.setattr(store, "bindings", lambda: {})
    monkeypatch.setattr(output, "vjoy_modules", lambda: [])
    monkeypatch.setattr(
        output, "first_claimed_output", lambda *a, **k: None, raising=False
    )
    loaded = Profile()
    loaded.from_xml(env["path"])
    _check("vjoy_ids", loaded, env["uid"])
    again = env["tmp"] / "no_vjoy.xml"
    loaded.to_xml(again)
    reread = Profile()
    reread.from_xml(again)
    _check("vjoy_ids", reread, env["uid"])
    assert re.search(r"future-step", again.read_text(encoding="utf-8-sig"))
