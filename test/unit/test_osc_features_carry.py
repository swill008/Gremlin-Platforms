# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The OSC features batch's new parts of OSC's module file travel like the
rest of it (D-09-OSC-OUTPUT/FEEDBACK/ENCODER: "all new settings live in OSC's
file"): the "targets" list, the "feedback" rows, the new "server" keys and
the encoder settings of each input come back through Save to Device Library
and Restore, Export (current and saved), a Device Pack import with "OSC
addresses and server" ticked (one write, Undo Import reverts) and History
restore. Each put-back is one write of osc.json and one History entry, after
which the server settings, the Feedback section's model and the feedback
runtime read the file again. The real store, Library, Device Pack and
History in an empty modules folder; no network (discovery is stubbed)."""

from __future__ import annotations

import io
import json
import zipfile
from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6 import QtCore

from gremlin import device_library as library
from gremlin import history, library_copy, osc_device_file, shared_state
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

# Every new server key away from its default (A) and back (B).
NEW_A = {
    "output_enabled": False,
    "reply_to_sender": False,
    "announce": True,
    "find_devices": True,
    "feedback_enabled": False,
    "resend_run": False,
    "resend_mode": False,
    "resend_profile": False,
    "sync_enabled": False,
    "sync_address": "/sim/sync",
    "feedback_rate": 7,
}
NEW_B = {
    "output_enabled": True,
    "reply_to_sender": True,
    "announce": False,
    "find_devices": False,
    "feedback_enabled": True,
    "resend_run": True,
    "resend_mode": True,
    "resend_profile": True,
    "sync_enabled": True,
    "sync_address": "/gremlin/sync",
    "feedback_rate": 50,
}
SERVER_A = {"host": "", "port": 9001, "autorelease_delay_ms": 400, **NEW_A}
SERVER_B = {"host": "", "port": 9100, "autorelease_delay_ms": 120, **NEW_B}
SIM = "5" * 32
DESK = "d" * 32
TARGETS_A = [
    {"id": SIM, "name": "Sim", "host": "10.0.0.5", "port": 9500},
    {"id": DESK, "name": "Desk", "host": "10.0.0.6", "port": 9600},
]
TARGETS_B = [{"id": "b" * 32, "name": "Other", "host": "10.0.0.9", "port": 9900}]
FB_A = [
    {
        "id": "f1" * 16,
        "enabled": False,
        "source": {"kind": "vjoy_button", "device": 1, "input": 3},
        "target": SIM,
        "address": "/fb/b3",
        "min": 0.0,
        "max": 1.0,
        "type": "int",
    },
    {
        "id": "f2" * 16,
        "enabled": True,
        "source": {"kind": "mode", "device": None, "input": None},
        "target": "reply",
        "address": "/fb/mode",
        "min": -2.0,
        "max": 2.0,
        "type": "text",
    },
]
FB_B = [
    {
        "id": "fb" * 16,
        "enabled": True,
        "source": {"kind": "vjoy_axis", "device": 2, "input": 1},
        "target": "b" * 32,
        "address": "/other",
        "min": 0.0,
        "max": 1.0,
        "type": "float",
    }
]
ENC_A = {
    "/knob": {"enc_format": "signed", "enc_step": 0.2, "enc_output": "axis"},
    "/detent": {"enc_format": "direction", "enc_step": 0.1, "enc_output": "pulse_cw"},
}
_SIGNALS = ("oscDeviceReloaded", "oscServerSettingsChanged", "oscFeedbackChanged")

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
    # "announce"/"find_devices" on must never reach the network.
    from gremlin import osc_discovery

    monkeypatch.setattr(osc_discovery, "set_announce", lambda *a, **k: None)
    monkeypatch.setattr(osc_discovery, "set_find", lambda *a, **k: None)
    return request.getfixturevalue(folder.__name__)


@pytest.fixture
def rows(modules: Path) -> Iterator[object]:
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
    """OSC's file as saved: two encoders (axis and pulse), new server keys,
    two targets and two feedback rows, all away from their defaults."""
    knob = rows.create(_A, "/knob", mode="encoder", **ENC_A["/knob"])  # type: ignore[attr-defined]
    detent = rows.create(_B, "/detent", mode="encoder", **ENC_A["/detent"])  # type: ignore[attr-defined]
    assert osc_device_file.save()
    assert osc_device_file.write_server(SERVER_A)
    assert osc_device_file.write_targets(TARGETS_A)
    assert osc_device_file.write_feedback(FB_A)
    return {"/knob": knob.uid, "/detent": detent.uid}


def _doc() -> dict:
    return json.loads(osc_device_file.path().read_text(encoding="utf-8-sig"))


def _change_to_b(rows: object) -> None:
    """After saving: the encoders' settings changed, every new key back to
    its default, other targets and feedback rows."""
    data = rows.to_dict()  # type: ignore[attr-defined]
    for row in data["inputs"]:
        row["enc_format"] = "auto"
        row["enc_step"] = 0.05
        if row["label"] == "/detent":
            row["enc_output"] = "pulse_ccw"
    rows.load_dict(data)  # type: ignore[attr-defined]
    assert osc_device_file.save()
    assert osc_device_file.write_server(SERVER_B)
    assert osc_device_file.write_targets(TARGETS_B)
    assert osc_device_file.write_feedback(FB_B)
    _assert_carries(_doc(), None, want_a=False)


def _assert_carries(doc: dict, state: dict | None, want_a: bool = True) -> None:
    """A document (the file or one inside a zip) holds A's new parts."""
    server = doc.get("server") or {}
    picked = {k: server.get(k) for k in NEW_A}
    targets = osc_device_file.clean_targets(doc.get("targets"))
    feedback = osc_device_file.clean_feedback(doc.get("feedback"))
    inputs = {r.get("label"): r for r in doc.get("inputs") or []}
    enc = {
        label: {k: inputs[label].get(k) for k in ENC_A[label]}
        for label in ENC_A
        if label in inputs
    }
    if not want_a:
        assert picked == NEW_B, picked
        assert targets == TARGETS_B and feedback == FB_B
        assert enc != ENC_A
        return
    assert picked == NEW_A, picked
    assert server.get("port") == 9001
    assert targets == TARGETS_A, doc.get("targets")
    assert feedback == FB_A, doc.get("feedback")
    assert enc == ENC_A, enc
    if state is not None:
        assert {label: inputs[label]["uid"] for label in ENC_A} == state


def _assert_state_a(state: dict) -> None:
    """The file, the read API, OSC's shared rows and the server are A's."""
    _assert_carries(_doc(), state)
    assert osc_device_file.read_targets() == TARGETS_A
    assert osc_device_file.read_feedback() == FB_A
    assert {k: osc_device_file.read_server()[k] for k in NEW_A} == NEW_A
    shared = OscDevice().rows
    for label, settings in ENC_A.items():
        row = shared.by_uid(state[label])
        assert row is not None and row.mode == "encoder"
        assert {k: getattr(row, k) for k in settings} == settings
    assert not shared.dirty
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
        self._slots = []
        for name in _SIGNALS:
            slot = lambda n=name: self.signals.append(n)  # noqa: E731
            getattr(signal, name).connect(slot)
            self._slots.append((name, slot))

    def close(self) -> None:
        for name, slot in self._slots:
            try:
                getattr(signal, name).disconnect(slot)
            except (TypeError, RuntimeError):
                pass

    def entries(self) -> list[dict]:
        settle_history()
        return [
            e
            for e in history.entries()
            if str(e.get("id")) not in self.before
            and (e.get("subject") or {}).get("fileName") == "osc.json"
        ]


@pytest.fixture
def watch_maker(monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    made: list[_Watch] = []

    def make() -> _Watch:
        made.append(_Watch(monkeypatch))
        return made[-1]

    yield make
    for w in made:
        w.close()


class _Stub(QtCore.QObject):
    mode_changed = QtCore.Signal(str)
    joystick_event = QtCore.Signal(object)


@pytest.fixture
def listeners(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple]:
    """The Feedback section's model and a feedback runtime listening to the
    real signals (mode/input sources stubbed: no keyboard hook, no
    hardware thread)."""
    from gremlin import event_handler, mode_manager, osc_feedback
    from gremlin.ui.osc_feedback_model import OscFeedbackModel

    stub = _Stub()
    monkeypatch.setattr(mode_manager, "ModeManager", lambda: stub)
    monkeypatch.setattr(event_handler, "EventListener", lambda: stub)
    runtime = osc_feedback.OscFeedback()
    runtime._connect(True)
    runtime.reload()
    model = OscFeedbackModel()
    try:
        yield model, runtime
    finally:
        runtime._connect(False)
        osc_feedback._reload_settings()
        for name in _SIGNALS:
            try:
                getattr(signal, name).disconnect(model.reload)
            except (TypeError, RuntimeError):
                pass
        model.deleteLater()
        runtime.deleteLater()


def _assert_listeners_a(model: object, runtime: object) -> None:
    for _ in range(20):
        QtCore.QCoreApplication.processEvents()
    assert model._rows == FB_A  # type: ignore[attr-defined]
    assert model._targets == TARGETS_A  # type: ignore[attr-defined]
    assert model._server["feedback_enabled"] is False  # type: ignore[attr-defined]
    assert runtime._rows == FB_A  # type: ignore[attr-defined]
    assert runtime._settings["sync_address"] == "/sim/sync"  # type: ignore[attr-defined]
    assert runtime._settings["feedback_rate"] == 7  # type: ignore[attr-defined]


def _save() -> dict:
    out = library.save_setup("OSC", OSC_GUID, [])
    assert out["ok"], out
    setups = out.get("setups") or [out.get("setup")]
    return setups[0]


def _osc_doc_in(data: bytes | Path) -> dict:
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
def test_restore_brings_new_parts_back_in_one_write(
    how: str,
    state_a: dict,
    rows: object,
    listeners: tuple,
    watch_maker: object,
) -> None:
    setup = _save()
    _change_to_b(rows)
    watch = watch_maker()  # type: ignore[operator]
    out = getattr(library_copy, how)(setup["key"])
    assert out["ok"], out
    _assert_state_a(state_a)
    _assert_listeners_a(*listeners)
    assert len(watch.writes) == 1, watch.writes
    assert len(watch.entries()) == 1, watch.entries()
    assert "oscDeviceReloaded" in watch.signals
    assert "oscServerSettingsChanged" in watch.signals


def test_restore_says_feedback_changed(
    state_a: dict, rows: object, watch_maker: object
) -> None:
    """Whatever listens only to oscFeedbackChanged hears a Restore too."""
    setup = _save()
    _change_to_b(rows)
    watch = watch_maker()  # type: ignore[operator]
    assert library_copy.restore_to_stick(setup["key"])["ok"]
    assert "oscFeedbackChanged" in watch.signals, watch.signals


# --- (2) Export current / Export saved setup ---------------------------------


def test_export_current_includes_new_parts(state_a: dict, tmp_path: Path) -> None:
    row = next(r for r in library.devices() if r["name"] == "OSC")
    dest = tmp_path / "out" / "now.zip"
    out = library.export_current(row["key"], dest)
    assert out["ok"], out
    _assert_carries(_osc_doc_in(dest), state_a)


def test_export_saved_setup_includes_new_parts(
    state_a: dict, rows: object, tmp_path: Path
) -> None:
    setup = _save()
    _change_to_b(rows)  # the saved setup keeps A
    dest = tmp_path / "out" / "saved.zip"
    out = library.export_setup(setup["key"], dest)
    assert out["ok"], out
    _assert_carries(_osc_doc_in(dest), state_a)


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


def test_device_pack_carries_new_parts_and_undo_reverts(
    state_a: dict,
    rows: object,
    profile: Profile,
    listeners: tuple,
    tmp_path: Path,
    watch_maker: object,
) -> None:
    from gremlin.ui import device_pack

    built = device_pack.assemble(
        "OSC", lambda stored: None, None, {}, profile, str(OSC_DEVICE_UUID)
    )
    assert not isinstance(built, str), built
    path = tmp_path / "osc.zip"
    path.write_bytes(built[0])
    _assert_carries(_osc_doc_in(path), state_a)
    assert "in.osc" in device_pack.pack_item_ids(path)["input"]
    _change_to_b(rows)
    b_doc = _doc()
    watch = watch_maker()  # type: ignore[operator]
    result = device_pack.apply_zip(
        path, "OSC", {"items": ["in.osc"]}, target_guid=str(OSC_DEVICE_UUID)
    )
    assert result["ok"], result
    _assert_state_a(state_a)
    _assert_listeners_a(*listeners)
    assert len(watch.writes) == 1, watch.writes
    assert len(watch.entries()) == 1, watch.entries()
    assert "oscDeviceReloaded" in watch.signals
    # Undo Import puts B back.
    assert device_pack.undo_import()["ok"]
    now = _doc()
    for key in ("inputs", "server", "targets", "feedback"):
        assert now.get(key) == b_doc.get(key), key
    assert osc_device_file.read_feedback() == FB_B
    assert osc_device_file.read_targets() == TARGETS_B
    for _ in range(20):
        QtCore.QCoreApplication.processEvents()
    model, runtime = listeners
    assert model._rows == FB_B and runtime._rows == FB_B


# --- (4) History restore -----------------------------------------------------


@pytest.mark.parametrize("key", ["targets", "feedback"])
def test_history_restore_of_targets_or_feedback(
    key: str,
    state_a: dict,
    listeners: tuple,
    watch_maker: object,
) -> None:
    watch = watch_maker()  # type: ignore[operator]
    if key == "targets":
        assert osc_device_file.write_targets(TARGETS_B, "OSC page")
    else:
        assert osc_device_file.write_feedback(FB_B, "OSC Module Setup")
    model, runtime = listeners
    for _ in range(20):
        QtCore.QCoreApplication.processEvents()
    assert (model._targets if key == "targets" else runtime._rows) != (
        TARGETS_A if key == "targets" else FB_A
    )
    entries = watch.entries()
    assert len(entries) == 1, entries
    before = json.loads((entries[0].get("before") or {}).get("text") or "{}")
    assert before.get(key) == (TARGETS_A if key == "targets" else FB_A)
    out = history_model.restore(str(entries[0]["id"]), "before")
    assert out["ok"], out
    _assert_state_a(state_a)
    _assert_listeners_a(model, runtime)
    assert "oscDeviceReloaded" in watch.signals
