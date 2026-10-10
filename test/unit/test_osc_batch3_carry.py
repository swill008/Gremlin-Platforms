# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC batch 3's new parts of OSC's module file travel like the rest of it
(09 S159-S164, S107): an axis input's Invert and deadzone, an encoder's
acceleration preset and the server's sender allow-list come back whole
through Save to Device Library and Restore, Export (current and saved),
History restore and a Device Pack import ("OSC addresses and server":
osc.json comes back key for key).

References follow the input's permanent id (S159, Q2): a Condition on an
OSC button and a macro's OSC step made while the input is number 1 still
name it, and read or play it, once a Library put-back or a Device Pack
import numbers it 6.

The real store, Library, Device Pack and History in an empty modules
folder; no network.

Spec: 09 (OSC) S107, S159, S160, S161, S164.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from PySide6 import QtCore

from gremlin import device_library as library
from gremlin import library_copy, osc_device_file, shared_state
from gremlin.osc import OSC_DEVICE_UUID, OscDevice
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import history_model
from test.unit import (  # pyright: ignore[reportMissingImports]
    test_osc_features_carry as _carry,
)

ROOT = Path(__file__).resolve().parents[2]

# The OSC features batch's fixtures: an empty modules folder, OSC's rows
# emptied and put back, the osc.json write / History watcher.
_app = _carry._app
folder = _carry.folder
modules = _carry.modules
rows = _carry.rows
watch_maker = _carry.watch_maker
_osc_doc_in = _carry._osc_doc_in
_save = _carry._save

pytestmark = pytest.mark.validate_off

_A = InputType.JoystickAxis
_B = InputType.JoystickButton
AXIS = "/ax"
ENC = "/enc"
GATE = "/gate"
OTHER = "/other"

SHAPE_A = {"invert": True, "deadzone": [-0.1, 0.2]}
ACCEL_A = "medium"
ALLOW_A = ["127.0.0.1", "10.0.0.0/8"]


def _has(path: str, *needles: str) -> bool:
    file = ROOT / path
    if not file.exists():
        return False
    text = file.read_text("utf-8", errors="replace")
    return all(n in text for n in needles)


_FIELDS = _has("gremlin/osc_rows.py", '"invert"', '"deadzone"', '"enc_accel"') and _has(
    "gremlin/osc_device_file.py", "allow_senders"
)
_COND = _has("action_plugins/condition/condition.py", "def setOscInput", "osc-uid")
_MACRO = _has("gremlin/macro.py", "class OscAction")


def _needs(present: bool, what: str) -> pytest.MarkDecorator:
    # Fails only because the named batch 3 code isn't in yet (strict: the
    # mark must come off once it lands).
    return pytest.mark.xfail(
        not present,
        reason=f"needs OSC batch 3: {what}",
        raises=Exception,
        strict=True,
    )


needs_fields = _needs(
    _FIELDS, "invert/deadzone/enc_accel on OscRow and server allow_senders"
)


def _doc() -> dict:
    return json.loads(osc_device_file.path().read_text(encoding="utf-8-sig"))


def _server_with(allow: list[str]) -> None:
    current = osc_device_file.read_server()
    osc_device_file.write_server({**current, "allow_senders": list(allow)})


@pytest.fixture
def state_a(rows: Any) -> dict:  # noqa: ANN401
    """OSC's file as saved: an inverted axis with a deadzone, an encoder on
    Medium and a two-entry allow-list."""
    axis = rows.create(_A, AXIS, range_min=0.0, range_max=1.0)
    rows.update(axis.uid, invert=True, deadzone=tuple(SHAPE_A["deadzone"]))
    enc = rows.create(_A, ENC, mode="encoder", enc_output="axis")
    rows.update(enc.uid, enc_accel=ACCEL_A)
    assert osc_device_file.save()
    _server_with(ALLOW_A)
    return {"uids": {AXIS: axis.uid, ENC: enc.uid}, "doc": _doc()}


def _change_to_b(rows: Any) -> None:  # noqa: ANN401
    """After saving: every new setting back to its default."""
    data = rows.to_dict()
    for row in data["inputs"]:
        row["invert"] = False
        row["deadzone"] = [0.0, 0.0]
        row["enc_accel"] = "off"
    rows.load_dict(data)
    assert osc_device_file.save()
    _server_with([])
    _assert_carries(_doc(), None, want_a=False)


def _assert_carries(doc: dict, state: dict | None, want_a: bool = True) -> None:
    """A document (the file or one in a zip) holds A's new settings."""
    inputs = {r.get("label"): r for r in doc.get("inputs") or []}
    server = osc_device_file.clean_server(doc.get("server"))
    shape = {k: inputs.get(AXIS, {}).get(k) for k in SHAPE_A}
    accel = inputs.get(ENC, {}).get("enc_accel")
    if not want_a:
        assert shape == {"invert": False, "deadzone": [0.0, 0.0]}, shape
        assert accel == "off"
        assert server["allow_senders"] == []
        return
    assert shape == SHAPE_A, shape
    assert accel == ACCEL_A
    assert server["allow_senders"] == ALLOW_A, doc.get("server")
    if state is not None:
        assert inputs[AXIS]["uid"] == state["uids"][AXIS]
        assert inputs[ENC]["uid"] == state["uids"][ENC]


def _assert_state_a(state: dict) -> None:
    """The file, OSC's shared rows and the server read A's settings."""
    from gremlin import osc

    _assert_carries(_doc(), state)
    shared = OscDevice().rows
    axis = shared.by_uid(state["uids"][AXIS])
    enc = shared.by_uid(state["uids"][ENC])
    assert axis is not None and enc is not None
    assert axis.invert is True
    assert tuple(axis.deadzone) == tuple(SHAPE_A["deadzone"])
    assert enc.enc_accel == ACCEL_A
    assert osc_device_file.read_server()["allow_senders"] == ALLOW_A
    # The allow-list answers from the restored file.
    assert osc.sender_allowed("10.1.2.3") is True
    assert osc.sender_allowed("192.168.1.9") is False


# --- (1) Save to Device Library, then Restore --------------------------------


@needs_fields
@pytest.mark.parametrize("how", ["restore_to_stick", "restore"])
def test_library_restore_brings_back_shaping_accel_and_allow_list(
    how: str,
    state_a: dict,
    rows: Any,  # noqa: ANN401
    watch_maker: Any,  # noqa: ANN401
) -> None:
    setup = _save()
    _change_to_b(rows)
    watch = watch_maker()
    out = getattr(library_copy, how)(setup["key"])
    assert out["ok"], out
    _assert_state_a(state_a)
    assert len(watch.writes) == 1, watch.writes


# --- (2) Export current / saved ------------------------------------------------


@needs_fields
def test_export_current_carries_shaping_accel_and_allow_list(
    state_a: dict, tmp_path: Path
) -> None:
    row = next(r for r in library.devices() if r["name"] == "OSC")
    dest = tmp_path / "out" / "now.zip"
    assert library.export_current(row["key"], dest)["ok"]
    _assert_carries(_osc_doc_in(dest), state_a)


@needs_fields
def test_export_saved_setup_carries_shaping_accel_and_allow_list(
    state_a: dict,
    rows: Any,  # noqa: ANN401
    tmp_path: Path,
) -> None:
    setup = _save()
    _change_to_b(rows)
    dest = tmp_path / "out" / "saved.zip"
    assert library.export_setup(setup["key"], dest)["ok"]
    _assert_carries(_osc_doc_in(dest), state_a)


# --- (3) History restore ------------------------------------------------------


@needs_fields
@pytest.mark.parametrize("part", ["inputs", "server"])
def test_history_restore_brings_back_shaping_accel_or_allow_list(
    part: str,
    state_a: dict,
    rows: Any,  # noqa: ANN401
    watch_maker: Any,  # noqa: ANN401
) -> None:
    watch = watch_maker()
    if part == "server":
        _server_with([])
    else:
        data = rows.to_dict()
        for row in data["inputs"]:
            row["invert"] = False
            row["deadzone"] = [0.0, 0.0]
            row["enc_accel"] = "off"
        rows.load_dict(data)
        assert osc_device_file.save()
    entries = watch.entries()
    assert len(entries) == 1, entries
    before = json.loads((entries[0].get("before") or {}).get("text") or "{}")
    _assert_carries(before, state_a)
    out = history_model.restore(str(entries[0]["id"]), "before")
    assert out["ok"], out
    _assert_state_a(state_a)


# --- (4) Device Pack: osc.json travels whole ----------------------------------


@pytest.fixture
def profile() -> Iterator[Profile]:
    old = shared_state.current_profile
    made = _osc_profile()
    shared_state.current_profile = made
    yield made
    from gremlin.ui import device_pack

    device_pack.drop_import_undo()
    shared_state.current_profile = old


def _osc_profile() -> Profile:
    made = Profile()
    made.device_database.devices[OSC_DEVICE_UUID] = DeviceInfo(OSC_DEVICE_UUID, "OSC")
    return made


def _pack(profile: Profile, tmp_path: Path, name: str = "osc.zip") -> Path:
    from gremlin.ui import device_pack

    built = device_pack.assemble(
        "OSC", lambda stored: None, None, {}, profile, str(OSC_DEVICE_UUID)
    )
    assert not isinstance(built, str), built
    path = tmp_path / name
    path.write_bytes(built[0])
    return path


def _import_pack(path: Path) -> dict:
    from gremlin.ui import device_pack

    return device_pack.apply_zip(
        path, "OSC", {"items": ["in.osc"]}, target_guid=str(OSC_DEVICE_UUID)
    )


@needs_fields
def test_device_pack_carries_osc_json_whole(
    state_a: dict,
    rows: Any,  # noqa: ANN401
    profile: Profile,
    tmp_path: Path,
) -> None:
    path = _pack(profile, tmp_path)
    _assert_carries(_osc_doc_in(path), state_a)
    _change_to_b(rows)
    result = _import_pack(path)
    assert result["ok"], result
    _assert_state_a(state_a)
    # Whole: every part of the file as saved comes back as it was (the
    # device's GUID comes back lower-case: same GUID).
    now = _doc()

    def same(key: str) -> bool:
        old, new = state_a["doc"][key], now.get(key)
        if key == "boundGuidLocal":
            return str(old).lower() == str(new).lower()
        return old == new

    differ = [k for k in state_a["doc"] if not same(k)]
    assert differ == [], {k: (state_a["doc"][k], now.get(k)) for k in differ}


def _state(cond: Any) -> Any:  # noqa: ANN401
    """The condition's one input (JoystickCondition.State)."""
    return cond._states[0]


# --- (5) A condition and a macro step follow the input's uid -------------------


@pytest.fixture
def renumbered(rows: Any, profile: Profile, tmp_path: Path) -> dict:  # noqa: ANN401
    """OSC's file as saved (Library setup and Device Pack): /other is
    button 1 and /gate button 6. Then the file as it is now: /gate alone,
    button 1 (same uid)."""
    rows.create(_B, OTHER, input_id=1)
    gate = rows.create(_B, GATE, input_id=6)
    assert gate.input_id == 6
    assert osc_device_file.save()
    setup = _save()
    pack = _pack(profile, tmp_path, "renumber.zip")
    data = rows.to_dict()
    data["inputs"] = [dict(r, id=1) for r in data["inputs"] if r["label"] == GATE]
    rows.load_dict(data)
    assert osc_device_file.save()
    assert rows.by_uid(gate.uid).input_id == 1
    return {"uid": gate.uid, "setup": setup, "pack": pack}


def _put_back(how: str, case: dict) -> None:
    if how == "library":
        out = library_copy.restore_to_stick(case["setup"]["key"])
    else:
        out = _import_pack(case["pack"])
    assert out["ok"], out
    gate = OscDevice().rows.by_uid(case["uid"])
    assert gate is not None and gate.input_id == 6, gate


@needs_fields
@_needs(_COND, "OSC conditions by uid (JoystickCondition.setOscInput, osc-uid)")
@pytest.mark.parametrize("how", ["library", "device_pack"])
def test_an_osc_condition_follows_its_input_through_a_renumber(
    how: str, renumbered: dict
) -> None:
    from action_plugins.condition import condition as cond_mod
    from gremlin.base_classes import Value
    from gremlin.input_cache import osc_state

    uid = renumbered["uid"]
    cond = cond_mod.JoystickCondition()
    cond.setOscInput(uid)
    assert _state(cond).input_id == 1
    saved = cond.to_xml()
    _put_back(how, renumbered)
    loaded = cond_mod.JoystickCondition()
    loaded.from_xml(saved)
    assert _state(loaded).osc_uid == uid
    assert _state(loaded).input_id == 6
    osc_state().clear()
    try:
        assert loaded(Value(True)) is False
        osc_state().set_button(uid, True)
        assert loaded(Value(True)) is True
        # The one made before the put-back reads the same input.
        assert cond(Value(True)) is True
        assert _state(cond).input_id == 6
        assert cond.states == [f"OSC - {GATE}"]
    finally:
        osc_state().clear()


@needs_fields
@_needs(_MACRO, "OSC macro steps by uid (gremlin.macro.OscAction)")
@pytest.mark.parametrize("how", ["library", "device_pack"])
def test_an_osc_macro_step_follows_its_input_through_a_renumber(
    how: str, renumbered: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import macro
    from gremlin.osc import OscRuntime

    uid = renumbered["uid"]
    step = macro.OscAction(uid, _B, True)
    saved = step.to_xml()
    _put_back(how, renumbered)
    loaded = macro.OscAction(None, _B, False)
    loaded.from_xml(saved)
    assert loaded.uid == uid
    assert not loaded.is_missing()
    row = loaded.row()
    assert row is not None and row.label == GATE and row.input_id == 6
    # Played, it presses that input through the runtime, by uid (whichever
    # of the runtime's entry points the step uses: play, or send_test).
    played: list[tuple] = []
    runtime = OscRuntime()
    for name in ("play", "send_test"):
        if hasattr(runtime, name):
            monkeypatch.setattr(
                runtime,
                name,
                lambda u, kind, value=None, *a, **k: played.append((u, kind, value)),
            )
    loaded()
    for _ in range(5):
        QtCore.QCoreApplication.processEvents()
    assert len(played) == 1, played
    who, kind, value = played[0]
    assert who == uid
    assert kind == "press" or (kind == "button" and value is True), played
