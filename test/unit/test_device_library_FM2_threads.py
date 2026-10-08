# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 Device Library, the last fix round (agent FM2), the model's threads
and its answers for the window:

- Item 3 (section 6): a change's saved profiles are read and written on a
  program thread while the main thread's event loop keeps going (a timer
  fires, the window shows busy); the open profile and the owners stay on
  the main thread.
- Item 7 (program thread rules): settings, delete, import, export, tidy and
  the plans run on the main thread (they reach the settings, the device
  lists and the open profile); a refresh or a rename waits for a change.
- Item 6 (S12): a saved setup's details say whether its device has
  anything to save now.
- Item 9 (S30): the "Also move" line names every other stick, each with its
  own vJoys.
"""

from __future__ import annotations

import importlib.util
import pathlib
import threading
import types
import uuid
from collections.abc import Callable, Iterator

import pytest
from PySide6 import QtCore
from pytestqt.qtbot import QtBot

from gremlin import history, library_profiles, shared_state, threads, util
from gremlin.modules import module_file
from gremlin.profile import DeviceInfo, Profile
from gremlin.types import InputType
from gremlin.ui import device_library_model
from gremlin.ui.device_library_model import DeviceLibraryModel

_HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke", _HERE / "device_library_LU_fake_smoke.py"
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)

_MAIN = threading.main_thread().name
_STICK = uuid.UUID("33333333-4444-5555-6666-777777777777")


@pytest.fixture
def folders(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> Iterator[pathlib.Path]:
    monkeypatch.setattr(history, "folder", lambda: tmp_path / "history")
    monkeypatch.setattr(history, "_pruned", True)
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    monkeypatch.setattr(util, "profiles_dir", lambda: profiles)
    monkeypatch.setattr(library_profiles, "_recent", lambda: [])
    monkeypatch.setattr(shared_state, "current_profile", None)
    yield profiles
    # The History entries are written by its own thread: let it finish.
    done = threading.Event()
    for _ in range(250):
        if history._writer is None:
            break
        done.wait(0.02)


def _map(profile: Profile, button: int) -> None:
    action = profile.library.create("Map to vJoy", InputType.JoystickButton)
    assert action is not None
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    item = profile.get_input_item(
        _STICK, InputType.JoystickButton, button, "Default", create_if_missing=True
    )
    item.add_item_binding().root_action.insert_action(action, "children")


def _saved(path: pathlib.Path) -> pathlib.Path:
    made = Profile(bind=False)
    made.device_database.devices[_STICK] = DeviceInfo(_STICK, "Test Stick")
    _map(made, 1)
    made.to_xml(path)
    return path


def _model(qtbot: QtBot, copy: object) -> tuple[DeviceLibraryModel, object]:
    lib = fake_mod.FakeLibrary()
    api = types.SimpleNamespace(
        library=lib, profiles=library_profiles, copy=copy, swap=copy, vjoy_ids=list
    )
    m = DeviceLibraryModel(api=api, watch_devices=False)
    m.refresh()
    qtbot.waitUntil(lambda: "Library:" in m.statusText, timeout=5000)
    return m, lib


# | Item 3: the window keeps going while saved profiles are written


def test_s6_a_slow_saved_profile_leaves_the_event_loop_running_and_busy(
    qtbot: QtBot, folders: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _saved(folders / "Saved.xml")
    seen: dict = {"read": [], "change": [], "write": []}

    # Change vJoy Output through the real Batch: the saved profile gets a
    # binding more.
    def change_output(name, guid, moves, swap_other, profiles):  # noqa: ANN001, ANN202
        def change(profile: Profile, is_open: bool) -> dict:
            seen["change"].append(threading.current_thread().name)
            _map(profile, 2)
            return {"ok": True, "notes": ["changed"]}

        return library_profiles.Batch(profiles, "Change vJoy Output").apply(change)

    m, _lib = _model(qtbot, types.SimpleNamespace(change_output=change_output))

    reader = library_profiles._read_here

    def read_here(p: pathlib.Path) -> object:
        seen["read"].append(threading.current_thread().name)
        return reader(p)

    monkeypatch.setattr(library_profiles, "_read_here", read_here)

    # The timer can only fire while the main thread's event loop runs.
    fired = threading.Event()
    timer_saw: dict = {}
    real_write = module_file.write_text

    def slow_write(target, text, encoding="utf-8", newline=None):  # noqa: ANN001, ANN202
        seen["write"].append(threading.current_thread().name)
        # A slow disk: the write waits for the main thread's timer (bounded).
        seen["timer_fired_during_write"] = fired.wait(3)
        return real_write(target, text, encoding=encoding, newline=newline)

    monkeypatch.setattr(module_file, "write_text", slow_write)

    def tick() -> None:
        if seen["write"] and not fired.is_set():
            timer_saw["busy"] = m.busy
            fired.set()

    timer = QtCore.QTimer()
    timer.setInterval(20)
    timer.timeout.connect(tick)
    timer.start()
    with qtbot.waitSignal(m.result, timeout=10000) as blocker:
        assert m.changeOutput("dev-00000001", {"1": 2}, False, [path.as_uri()])
    timer.stop()
    res = blocker.args[0]
    assert res["ok"], res
    assert res["changed"] == [str(path)]
    # The saved profile was read and written on a program thread, changed
    # here on the main thread; the timer fired while it was written, with
    # the window busy.
    assert seen["read"] and all(t != _MAIN for t in seen["read"])
    assert seen["write"] and all(t != _MAIN for t in seen["write"])
    assert seen["change"] == [_MAIN]
    assert seen["timer_fired_during_write"] is True
    assert timer_saw == {"busy": True}
    assert not m.busy
    # Written: the file on disk has both bindings.
    again = library_profiles._read_here(path)
    assert isinstance(again, Profile)
    assert len(again.inputs[_STICK]) == 2
    qtbot.waitUntil(
        lambda: not any("Device Library" in n for n in threads.running()), timeout=5000
    )


def test_outside_a_change_a_saved_profile_is_read_where_it_is_asked(
    folders: pathlib.Path, qtbot: QtBot
) -> None:
    path = _saved(folders / "Saved.xml")
    # Other callers (no responsive scope) read on their own thread, as before.
    assert isinstance(library_profiles.read_profile(path), Profile)
    names: list[str] = []
    with library_profiles.responsive():
        value = library_profiles.background(
            "test", lambda: names.append(threading.current_thread().name) or 7
        )
    assert value == 7 and names and names[0] != _MAIN
    names.clear()
    library_profiles.background(
        "test", lambda: names.append(threading.current_thread().name)
    )
    assert names == [_MAIN]


def test_a_background_step_raises_its_error_here(qtbot: QtBot) -> None:
    def fail() -> None:
        raise OSError("disk full")

    with library_profiles.responsive(), pytest.raises(OSError, match="disk full"):
        library_profiles.background("test", fail)


def test_a_background_step_that_never_ends_is_given_up(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(library_profiles, "BACKGROUND_LIMIT_S", 0.2)
    gate = threading.Event()
    try:
        with library_profiles.responsive(), pytest.raises(TimeoutError):
            library_profiles.background("test", lambda: gate.wait(5))
    finally:
        gate.set()
    qtbot.waitUntil(
        lambda: not any("Device Library" in n for n in threads.running()), timeout=5000
    )


def test_a_saved_profile_that_cant_be_written_is_left_and_named(
    qtbot: QtBot, folders: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _saved(folders / "Saved.xml")
    before = path.read_bytes()

    def broken(*_args: object, **_kw: object) -> None:
        raise OSError("the disk is read-only")

    monkeypatch.setattr(module_file, "write_text", broken)

    def change(profile: Profile, is_open: bool) -> dict:
        _map(profile, 2)
        return {"ok": True}

    with library_profiles.responsive():
        res = library_profiles.Batch([path], "Copy").apply(change)
    assert not res["ok"] and res["failed"] == [str(path)]
    assert "Saved.xml couldn't be saved (the disk is read-only)" in res["warnings"][0]
    assert path.read_bytes() == before


# | Item 7: what reaches shared state runs on the main thread


def _on(lib: object, name: str, record: dict) -> None:
    real = getattr(lib, name)

    def wrapped(*args: object, **kw: object) -> object:
        record[name] = threading.current_thread().name
        return real(*args, **kw)

    setattr(lib, name, wrapped)


def test_item7_library_changes_and_settings_run_on_the_main_thread(
    qtbot: QtBot, tmp_path: pathlib.Path
) -> None:
    lib = fake_mod.FakeLibrary()
    record: dict = {}
    for name in ("set_settings", "delete", "import_pack", "export_setup", "tidy"):
        _on(lib, name, record)
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()

    def run(start: Callable[[], int]) -> dict:
        with qtbot.waitSignal(m.result, timeout=5000) as blocker:
            assert start()
        return blocker.args[0]

    run(lambda: m.setSettings({"keep": 5}))
    run(lambda: m.deleteItem("set-00000006"))
    run(lambda: m.importPack((tmp_path / "pack.zip").as_uri()))
    run(lambda: m.exportSetup("set-00000001", (tmp_path / "out.zip").as_uri()))
    run(lambda: m.tidy(["set-00000003"]))
    assert record == {
        "set_settings": _MAIN,
        "delete": _MAIN,
        "import_pack": _MAIN,
        "export_setup": _MAIN,
        "tidy": _MAIN,
    }


def test_item7_a_refresh_and_a_rename_wait_for_a_change(qtbot: QtBot) -> None:
    lib = fake_mod.FakeLibrary()
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    results: list[dict] = []
    m.result.connect(results.append)
    assert m.copy("set-00000001", "dev-00000002", ["setup"], [], [])
    assert m.busy
    devices_before = lib.devices
    count = {"n": 0}

    def devices() -> list[dict]:
        count["n"] += 1
        return devices_before()

    lib.devices = devices  # type: ignore[method-assign]
    m.refresh()
    assert count["n"] == 0, "no refresh while the change runs"
    assert not m.rename("set-00000001", "New name")
    assert results[-1]["op"] == "rename" and "still running" in results[-1]["error"]
    qtbot.waitUntil(lambda: not m.busy, timeout=5000)
    # Refreshed once the change is done.
    assert count["n"] >= 1


def test_item7_a_plan_asked_for_during_a_change_runs_after_it(qtbot: QtBot) -> None:
    lib = fake_mod.FakeLibrary()
    api = lib.api()
    api.profiles = library_profiles
    m = DeviceLibraryModel(api=api, watch_devices=False)
    m.refresh()
    order: list[str] = []
    copy, plan = lib.copy, lib.plan_copy
    gate = threading.Event()

    def slow_copy(*args: object) -> dict:
        order.append("copy")
        # File work in the background: the event loop goes on meanwhile,
        # until the plan's settle timer has fired.
        library_profiles.background("test", gate.wait, 5)
        order.append("copy done")
        return copy(*args)

    def planned(*args: object) -> dict:
        order.append("plan")
        return plan(*args)

    lib.copy = slow_copy  # type: ignore[method-assign]
    lib.plan_copy = planned  # type: ignore[method-assign]
    results: list[dict] = []
    m.result.connect(results.append)
    m.planCopy("set-00000001", "dev-00000002", ["setup"], [], [])
    assert m.copy("set-00000001", "dev-00000002", ["setup"], [], [])
    look = QtCore.QTimer()
    look.setInterval(20)
    look.timeout.connect(
        lambda: order and not m._plan_timers["planCopy"].isActive() and gate.set()
    )
    look.start()
    try:
        qtbot.waitUntil(
            lambda: any(r["op"] == "planCopy" for r in results), timeout=5000
        )
    finally:
        look.stop()
        gate.set()
    assert order == ["copy", "copy done", "plan"]
    assert lib.plan_threads == [_MAIN]


# | Item 6 (S12) and item 9 (S30)


def test_s12_a_saved_setup_says_whether_its_device_has_anything_to_save(
    qtbot: QtBot,
) -> None:
    lib = fake_mod.FakeLibrary()
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    # A Deleted device's setup: nothing current to save.
    m.select("set-00000005")
    assert m.details["hasCurrent"] is False
    # A setup of a stick set up here.
    m.select("set-00000001")
    assert m.details["hasCurrent"] is True
    # A stick plugged in with no module file: its bindings can be saved.
    lib.devs.append(
        {
            "key": "dev-00000007",
            "name": "Throttle Quadrant",
            "description": "",
            "state": "connected",
            "guid": "{FFFF-0007}",
            "module": "",
            "setups": [],
        }
    )
    m.refresh()
    m.select("dev-00000007")
    assert m.details["hasCurrent"] is True


def test_s30_also_move_names_every_other_stick_with_its_own_vjoys(
    qtbot: QtBot,
) -> None:
    lib = fake_mod.FakeLibrary()
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    assert m.alsoMoveText([]) == ""
    assert (
        m.alsoMoveText(
            [{"guid": "b", "name": "Right stick", "vjoy": 2, "to": 1, "inputs": 12}]
        )
        == "Also move Right stick from vJoy 2 to vJoy 1 (swap them)"
    )
    assert device_library_model.also_move_text(
        [
            {"name": "Right stick", "vjoy": 2, "to": 1},
            {"name": "Rudder pedals", "vjoy": 3, "to": 1},
            {"name": "Left throttle", "vjoy": 2, "to": 1},
        ]
    ) == (
        "Also move Right stick and Left throttle from vJoy 2 to vJoy 1,"
        " and Rudder pedals from vJoy 3 to vJoy 1 (swap them)"
    )
