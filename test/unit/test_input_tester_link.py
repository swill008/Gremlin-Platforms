# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin's side of the Input Tester (D-02-INPUT-TESTER, contract 5, 9a,
9c, 9d, 9f): expected.json and its expect rules, written atomically and
again on a device change while a launched tester runs; launch through an
injected starter (no real tester is ever started); a new result is a trace
line; a game running from another folder is one trace warning; Tools has
Input Tester… in the real menu (whole program off-screen). HidHide is the
fake control device of test_trace_hidhide (the real driver is never
opened)."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import uuid
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import hidhide_watch, trace
from gremlin import input_tester_link as link
from test.unit.test_trace_hidhide import (  # noqa: F401 - the fixture
    _NEW,
    _HidHide,
    hidhide,
)

_ROOT = pathlib.Path(__file__).parents[2]
_STICK = uuid.UUID("11111111-2222-3333-4444-555555555555")


class _Guid:
    uuid = _STICK

    def __str__(self) -> str:
        return "{11111111-2222-3333-4444-555555555555}"


class _Proc:
    """A started tester: running until ended."""

    def __init__(self) -> None:
        self.ended = False

    def poll(self) -> int | None:
        return 0 if self.ended else None


@pytest.fixture
def setup(
    hidhide: _HidHide,  # noqa: F811
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[SimpleNamespace]:
    """One stick (EVO R, instance _NEW) mapped to vJoy 3; vJoy 3 present;
    Gremlin control on, so the fake driver is read."""
    from gremlin import device_initialization, input_monitor
    from gremlin.ui import hidhide as hh
    from gremlin.ui import trace_model

    data = tmp_path / "Gremlin Platforms"
    data.mkdir()
    exe = tmp_path / "prog" / "Gremlin Input Tester.exe"
    exe.parent.mkdir()
    exe.write_bytes(b"MZ")
    stick = SimpleNamespace(
        device_guid=_Guid(),
        name="VKBsim Gladiator EVO R",
        vendor_id=0x231D,
        product_id=0x0200,
        is_virtual=False,
    )
    vjoy = SimpleNamespace(
        device_guid="{AAAAAAAA-0000-0000-0000-000000000003}", vjoy_id=3,
        is_virtual=True,
    )
    monkeypatch.setattr(link, "gremlin_dir", lambda: data)
    monkeypatch.setattr(link, "tester_path", lambda: exe)
    monkeypatch.setattr(link, "_expected_tester_path", lambda: exe)
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: [stick])
    monkeypatch.setattr(device_initialization, "vjoy_devices", lambda: [vjoy])
    monkeypatch.setattr(input_monitor, "device_name", lambda uid: "Right stick")
    monkeypatch.setattr(
        trace_model, "targets", lambda uid: {("axis", 1): "→ vJoy 3 X"}
    )
    monkeypatch.setattr(hh, "_hidhide_managed", lambda: True)
    monkeypatch.setattr(hh, "_load_games", lambda: [])
    hidhide.devices = [_NEW]
    hidhide.cloak = True
    hidhide.inverse = True  # Block list
    hidhide.apps = [str(exe)]
    link._reset_for_tests()
    yield SimpleNamespace(data=data, exe=exe, hh=hidhide)
    link._reset_for_tests()


def _expected(data: pathlib.Path) -> dict:
    return json.loads((data / "tester" / "expected.json").read_text("utf-8"))


@pytest.mark.parametrize(
    ("on_list", "cloak", "block", "tester_on", "hidden"),
    [
        (True, True, True, True, True),  # Block list, tester on it
        (True, True, True, False, False),  # Block list, tester not on it
        (True, True, False, False, True),  # Allow list, tester not on it
        (True, True, False, True, False),  # Allow list, tester on it
        (True, False, True, True, False),  # cloak off
        (False, True, True, True, False),  # not on the hidden list
    ],
)
def test_expect_rules(
    on_list: bool, cloak: bool, block: bool, tester_on: bool, hidden: bool
) -> None:
    assert link.expect_hidden(on_list, cloak, block, tester_on) is hidden


def test_expected_json_has_the_contract_shape(setup: SimpleNamespace) -> None:
    assert link.write_expected() is True
    got = _expected(setup.data)
    assert got["version"] == 1 and got["written"]
    assert got["tester_path"] == str(setup.exe)
    assert got["hidhide"] == {
        "present": True, "cloak": True, "mode": "block", "tester_on_list": True,
        "apps": [str(setup.exe)],
    }
    (stick,) = got["sticks"]
    assert stick["name"] == "Right stick"
    assert stick["windows_name"] == "VKBsim Gladiator EVO R"
    assert (stick["vid"], stick["pid"]) == (0x231D, 0x0200)
    assert stick["guid"] == "{11111111-2222-3333-4444-555555555555}"
    assert stick["instance_ids"] == [_NEW]
    assert stick["feeds"] == ["vJoy 3"]
    assert stick["expect"] == "hidden"
    assert got["vjoy"] == [{
        "id": 3, "guid": "{AAAAAAAA-0000-0000-0000-000000000003}",
        "fed_by": ["Right stick"], "used": True, "expect": "visible",
    }]
    assert isinstance(got["xbox"], list)


def test_volume_path_entry_counts_as_the_tester_on_the_list(
    setup: SimpleNamespace,
) -> None:
    rest = os.path.splitdrive(str(setup.exe))[1]
    setup.hh.apps = [r"\Device\HarddiskVolume3" + rest]
    assert link.build_expected()["hidhide"]["tester_on_list"] is True


def test_tester_off_the_block_list_or_cloak_off_makes_sticks_visible(
    setup: SimpleNamespace,
) -> None:
    setup.hh.apps = []
    assert link.build_expected()["sticks"][0]["expect"] == "visible"
    setup.hh.inverse = False  # Allow list, tester not on it: hidden again
    assert link.build_expected()["sticks"][0]["expect"] == "hidden"
    setup.hh.cloak = False
    assert link.build_expected()["sticks"][0]["expect"] == "visible"


def test_write_is_atomic(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    swaps: list[tuple[str, str]] = []
    real = os.replace

    def spy(a: object, b: object) -> None:
        swaps.append((str(a), str(b)))
        real(a, b)

    monkeypatch.setattr(link.os, "replace", spy)
    link.write_expected()
    target = setup.data / "tester" / "expected.json"
    assert swaps == [(str(target) + ".tmp", str(target))]
    assert not (setup.data / "tester" / "expected.json.tmp").exists()
    _expected(setup.data)


def test_launch_starts_the_exe_with_the_gremlin_dir(setup: SimpleNamespace) -> None:
    started: list[tuple[str, list[str]]] = []
    link.set_starter(lambda exe, args: started.append((exe, args)) or _Proc())
    assert link.launch() == ""
    assert started == [(str(setup.exe), ["--gremlin-dir", str(setup.data)])]
    assert link.running() is True
    assert _expected(setup.data)["sticks"]


def test_launch_without_the_exe_is_the_not_built_message(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[object] = []
    link.set_starter(lambda exe, args: started.append(exe))
    monkeypatch.setattr(link, "tester_path", lambda: None)
    assert link.launch() == link.NOT_BUILT
    assert "python tools/build_input_tester.py" in link.NOT_BUILT
    assert started == [] and link.running() is False


def test_tester_path_frozen_is_next_to_the_program(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "Gremlin Input Tester.exe").write_bytes(b"MZ")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "joystick_gremlin.exe"))
    assert link.tester_path() == (tmp_path / "Gremlin Input Tester.exe").resolve()
    monkeypatch.setattr(sys, "frozen", False)
    found = link.tester_path()
    want = _ROOT / "dist" / "Gremlin Input Tester" / "Gremlin Input Tester.exe"
    assert found == (want.resolve() if want.is_file() else None)


def test_a_device_change_rewrites_expected_while_the_tester_runs(
    setup: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import device_initialization, event_handler

    proc = _Proc()
    link.set_starter(lambda exe, args: proc)
    link.launch()
    monkeypatch.setattr(device_initialization, "physical_devices", lambda: [])
    event_handler.EventListener().device_change_event.emit()
    assert _expected(setup.data)["sticks"] == []
    proc.ended = True  # closed: no more rewrites
    link.stop_watch()
    (setup.data / "tester" / "expected.json").unlink()
    event_handler.EventListener().device_change_event.emit()
    assert not (setup.data / "tester" / "expected.json").exists()


def test_a_hidhide_change_seen_by_the_watch_rewrites_expected(
    setup: SimpleNamespace,
) -> None:
    link.set_starter(lambda exe, args: _Proc())
    link.launch()
    hidhide_watch.check()
    setup.hh.cloak = False  # changed outside the program
    hidhide_watch.check()
    assert _expected(setup.data)["hidhide"]["cloak"] is False
    assert _expected(setup.data)["sticks"][0]["expect"] == "visible"


def _hidhide_lines() -> list[tuple[str, bool]]:
    return [(line[3], line[4]) for line in trace.lines() if line[2] == trace.HIDHIDE]


def test_a_new_result_is_a_signal_and_a_trace_line(setup: SimpleNamespace) -> None:
    seen: list[int] = []
    link.watcher().resultChanged.connect(lambda: seen.append(1))
    link.set_starter(lambda exe, args: _Proc())
    link.launch()
    assert seen == []
    result = setup.data / "tester" / "result.json"
    result.write_text(json.dumps({
        "version": 1, "verdict": "fail",
        "summary": "1 stick visible that should be hidden", "rows": [],
    }), "utf-8")
    link.poll_once()
    assert seen == [1]
    assert link.last_result()["verdict"] == "fail"
    assert (
        "Input Tester: Fail · 1 stick visible that should be hidden", True
    ) in _hidhide_lines()
    link.poll_once()  # unchanged: nothing more
    assert seen == [1]
    os.utime(result, (1, 2))
    result.write_text(json.dumps({"verdict": "pass", "summary": ""}), "utf-8")
    link.poll_once()
    assert ("Input Tester: Pass", False) in _hidhide_lines()


def test_the_watch_ends_when_the_tester_closes(setup: SimpleNamespace) -> None:
    proc = _Proc()
    link.set_starter(lambda exe, args: proc)
    link.launch()
    proc.ended = True
    link._tick(link._run)
    assert link.running() is False and link._timer is None


def test_a_game_running_from_another_folder_is_one_trace_warning(
    hidhide: _HidHide, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    from gremlin import process_paths
    from gremlin.ui import hidhide as hh

    monkeypatch.setattr(
        hh, "_load_games",
        lambda: [{"name": "SC", "path": r"D:\StarCitizen\LIVE\StarCitizen.exe"}],
    )
    monkeypatch.setattr(
        process_paths, "running_images",
        lambda: [r"D:\StarCitizen\PTU\StarCitizen.exe", r"C:\Windows\explorer.exe"],
    )
    hidhide_watch.check()
    hidhide_watch.check()
    warnings = [
        t for t, w in _hidhide_lines() if w and "StarCitizen.exe is running" in t
    ]
    assert warnings == [
        r"StarCitizen.exe is running from D:\StarCitizen\PTU\StarCitizen.exe, "
        "which isn't on the list"
    ]


# --- Tools › Input Tester… in the real menu (whole program off-screen) ----------

_CODE = r"""
import json, os, sys
sys.path.insert(0, '.')
import importlib.util
spec = importlib.util.spec_from_file_location('fake_hardware', 'test/fake_hardware.py')
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import pathlib
from gremlin import input_tester_link as link
import joystick_gremlin
from PySide6 import QtCore, QtQml
app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
win = app.main_window
out = {}

exe = pathlib.Path(os.environ["TESTER_EXE"])
started = []
link.set_starter(lambda e, a: started.append([e, a]) or None)

item = None
for obj in win.findChildren(QtCore.QObject):
    if obj.property("command") == "tools.inputTester":
        item = obj
        break
out["item"] = item is not None
if item is not None:
    QtCore.QMetaObject.invokeMethod(item, "refresh")
    out["text"] = str(item.property("text"))
    parent = item.parent()
    titles = []
    while parent is not None:
        if parent.property("title"):
            titles.append(str(parent.property("title")))
        parent = parent.parent()
    out["menus"] = titles
    link.tester_path = lambda: None
    item.triggered.emit()
    app.processEvents()
    dialog = None
    for obj in win.findChildren(QtCore.QObject):
        if obj.objectName() == "" and obj.property("title") == "Input Tester" \
                and obj.property("text") is not None:
            dialog = obj
    out["message"] = str(dialog.property("text")) if dialog is not None else ""
    link.tester_path = lambda: exe
    item.triggered.emit()
    app.processEvents()
    out["started"] = started
out["dir"] = str(link.gremlin_dir())
print('RESULT ' + json.dumps(out), flush=True)
os._exit(0)
"""


@pytest.fixture(scope="module")
def menu(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir()
    exe = home / "Gremlin Input Tester.exe"
    exe.write_bytes(b"MZ")
    script = home / "tester_menu.py"
    script.write_text(_CODE, encoding="utf-8")
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", TESTER_EXE=str(exe),
    )
    done = subprocess.run(
        [sys.executable, str(script)], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=150,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-2000:] + done.stderr[-3000:]
    found = json.loads(lines[-1][len("RESULT "):])
    found["exe"] = str(exe)
    return found


def test_tools_viewers_has_input_tester(menu: dict) -> None:
    assert menu["item"] is True, menu
    assert menu["text"] == "Input Tester…"
    assert "Viewers" in menu["menus"] and "Tools" in menu["menus"], menu


def test_the_menu_item_shows_the_not_built_message(menu: dict) -> None:
    assert menu["message"] == link.NOT_BUILT, menu


def test_the_menu_item_starts_the_tester(menu: dict) -> None:
    assert menu["started"] == [[menu["exe"], ["--gremlin-dir", menu["dir"]]]], menu
