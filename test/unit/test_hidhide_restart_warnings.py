# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-INPUT-TESTER addendum 2026-10-10, items 3 (Gremlin side), 4 and 5:
Gremlin notes its last HidHide change (time and what) on a page edit, the
apply at start and what the watch sees, and writes it to expected.json
(hidhide_changed_at, hidhide_change); the HidHide page warns about listed
programs (games, the Input Tester) running since before that change, with
Restart Input Tester (a fresh tester through the injected starter; nothing
is ever closed); none while no change is known; a HIDHIDE trace warning
once per process; Save Diagnostics takes the tester's files.

The page part runs this file as a script: the real program off-screen,
fake HidHide driver, fake process list with start times, real mouse clicks.
No real process is started or stopped; the real HidHide driver is never
opened."""

from __future__ import annotations

import datetime
import json
import os
import pathlib
import subprocess
import sys
import zipfile
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

if __name__ != "__main__":
    from gremlin import diagnostics, hidhide_watch, process_paths
    from gremlin import input_tester_link as link
    from test.unit.test_diagnostics_zip import home  # noqa: F401 - fixture
    from test.unit.test_input_tester_link import setup  # noqa: F401 - fixture
    from test.unit.test_trace_hidhide import (  # noqa: F401 - fixture
        _HidHide,
        hidhide,
    )

_HERE = pathlib.Path(__file__).parent
LIVE = r"D:\StarCitizen\LIVE\Bin64\StarCitizen.exe"
LATE = r"D:\Games\Late\Late.exe"
TESTER_NAME = "Gremlin Input Tester.exe"


# --- process_paths -------------------------------------------------------------


def test_only_listed_programs_started_before_the_change_are_named() -> None:
    change = datetime.datetime(2026, 10, 10, 4, 5, 12)
    tester = r"C:\Prog\Gremlin Input Tester.exe"
    programs = [
        (LIVE, datetime.datetime(2026, 10, 10, 3, 58)),
        (LIVE.lower(), datetime.datetime(2026, 10, 10, 3, 59)),  # same path again
        (tester, datetime.datetime(2026, 10, 10, 4, 2)),
        (LATE, datetime.datetime(2026, 10, 10, 4, 6)),  # after the change
        (r"C:\Windows\explorer.exe", datetime.datetime(2026, 10, 10, 1, 0)),
        (r"D:\NoTime\Game.exe", None),
    ]
    got = process_paths.started_before(
        programs, [LIVE, LATE, tester, r"D:\NoTime\Game.exe"], change
    )
    assert got == [
        (LIVE, datetime.datetime(2026, 10, 10, 3, 58)),
        (tester, datetime.datetime(2026, 10, 10, 4, 2)),
    ]
    assert process_paths.started_before(programs, [LIVE], None) == []
    assert process_paths.stale_text(LIVE, got[0][1], change) == (
        "StarCitizen.exe was started (03:58) before the last HidHide change "
        "(04:05): restart it so the change applies. HidHide only checks devices "
        "when a program opens them."
    )
    text = process_paths.stale_text(tester, got[1][1], change)
    assert text.startswith(
        "Gremlin Input Tester was started (04:02) before the last HidHide change "
        "(04:05): restart it"
    )
    assert "close the old window" in text


@pytest.mark.skipif(sys.platform != "win32", reason="Windows process list")
def test_running_programs_gives_this_python_a_start_time() -> None:
    mine = os.path.normcase(os.path.realpath(sys.executable))
    found = process_paths.running_programs([mine])
    # Only processes with that exe name are opened.
    assert found and all(
        os.path.basename(p).casefold() == os.path.basename(mine).casefold()
        for p, _s in found
    )
    assert process_paths.running_programs([]) == []
    starts = [start for path, start in found if os.path.normcase(path) == mine]
    assert starts and all(
        s is not None and s <= datetime.datetime.now() for s in starts
    )


# --- the last change and expected.json -------------------------------------------


def _expected(data: pathlib.Path) -> dict:
    return json.loads((data / "tester" / "expected.json").read_text("utf-8"))


def test_no_change_known_writes_no_change_fields(setup: SimpleNamespace) -> None:  # noqa: F811
    assert link.last_hidhide_change() is None
    assert link.write_expected() is True
    got = _expected(setup.data)
    assert "hidhide_changed_at" not in got and "hidhide_change" not in got


def test_a_change_is_noted_and_written_to_expected_json(
    setup: SimpleNamespace,  # noqa: F811
) -> None:
    link.write_expected()  # a tester has run: the file is there
    before = datetime.datetime.now().replace(microsecond=0)
    link.hidhide_changed("program list")
    when, what = link.last_hidhide_change()
    assert what == "program list" and when >= before
    got = _expected(setup.data)
    assert got["hidhide_change"] == "program list"
    assert got["hidhide_changed_at"] == when.isoformat(timespec="seconds")
    link.hidhide_changed("something else")
    assert link.last_hidhide_change()[1] == "settings"


def test_apply_saved_list_notes_a_change(
    hidhide: _HidHide, monkeypatch: pytest.MonkeyPatch  # noqa: F811
) -> None:
    from gremlin.ui import hidhide as hh

    link._reset_for_tests()
    monkeypatch.setattr(hh, "_hidhide_managed", lambda: True)
    monkeypatch.setattr(hh, "driver_present", lambda: True)
    monkeypatch.setattr(hh, "_load_games", lambda: [])
    monkeypatch.setattr(hh, "_gremlin_exe", lambda: "")
    monkeypatch.setattr(hh, "_full_image_name", lambda path: path)
    hh.apply_saved_list()
    change = link.last_hidhide_change()
    link._reset_for_tests()
    assert change is not None and change[1] == "settings"


def test_the_watch_notes_what_it_saw(hidhide: _HidHide) -> None:  # noqa: F811
    link._reset_for_tests()
    hidhide_watch.check()
    hidhide.apps = []  # the HidHide window changed the program list
    hidhide_watch.check()
    change = link.last_hidhide_change()
    link._reset_for_tests()
    assert change is not None and change[1] == "program list"


def _hidhide_warnings() -> list[str]:
    from gremlin import trace

    return [
        line[3] for line in trace.lines()
        if line[2] == trace.HIDHIDE and line[4]
    ]


def test_trace_warns_once_per_process_started_before_the_change(
    hidhide: _HidHide, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path  # noqa: F811
) -> None:
    from gremlin.ui import hidhide as hh

    tester = tmp_path / TESTER_NAME
    change = datetime.datetime(2026, 10, 10, 4, 5, 12)
    monkeypatch.setattr(hh, "_load_games", lambda: [
        {"name": "SC", "path": LIVE}, {"name": "Tester", "path": str(tester)},
    ])
    monkeypatch.setattr(process_paths, "running_images", lambda: [])
    monkeypatch.setattr(process_paths, "running_programs", lambda *_a: [
        (LIVE, datetime.datetime(2026, 10, 10, 3, 58)),
        (str(tester), datetime.datetime(2026, 10, 10, 4, 2)),
        (LATE, datetime.datetime(2026, 10, 10, 3, 0)),  # not listed
    ])
    monkeypatch.setattr(link, "last_hidhide_change", lambda: None)
    hidhide_watch.check()
    assert not [w for w in _hidhide_warnings() if "was started" in w]
    monkeypatch.setattr(link, "last_hidhide_change", lambda: (change, "cloak"))
    hidhide_watch.check()
    hidhide_watch.check()
    stale = [w for w in _hidhide_warnings() if "was started" in w]
    assert len(stale) == 2
    assert stale[0].startswith("StarCitizen.exe was started (03:58)")
    assert stale[1].startswith("Gremlin Input Tester was started (04:02)")


# --- Save Diagnostics ----------------------------------------------------------------


def test_save_diagnostics_takes_the_tester_files(
    home: pathlib.Path, tmp_path: pathlib.Path,  # noqa: F811
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    folder = home / "Gremlin Platforms" / "tester"
    monkeypatch.setattr(link, "tester_dir", lambda: folder)
    folder.mkdir(parents=True, exist_ok=True)
    for name in ("tester.log", "tester.log.1", "expected.json", "result.json"):
        (folder / name).write_text(f"{name} text\n", encoding="utf-8")
    (folder / "expected.json.tmp").write_text("half", encoding="utf-8")
    dest = tmp_path / "out.zip"
    ok, _message = diagnostics.save(diagnostics.collect(False), dest)
    assert ok
    with zipfile.ZipFile(dest) as zf:
        names = set(zf.namelist())
        assert zf.read("tester/tester.log").decode().strip() == "tester.log text"
    assert {
        "tester/tester.log", "tester/tester.log.1",
        "tester/expected.json", "tester/result.json",
    } <= names
    assert "tester/expected.json.tmp" not in names


# --- the page, in the real program -----------------------------------------------


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict]:
    home_dir = tmp_path_factory.mktemp("hh_restart_home")
    (home_dir / "Gremlin Platforms").mkdir()
    work = tmp_path_factory.mktemp("hh_restart_work")
    proc = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), str(work)],
        capture_output=True, text=True, encoding="utf-8", timeout=150,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ, "USERPROFILE": str(home_dir),
            "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1",
        },
    )
    results: dict = {"work": str(work), "home": str(home_dir)}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
    tail = proc.stdout[-3000:] + proc.stderr[-3000:]
    assert "done" in proc.stdout, tail
    assert results.get("open") is True, tail
    yield results


def test_no_warning_while_no_change_is_known(run: dict) -> None:
    assert run["open-state"] == {"change": None, "games": [], "tester": []}


def test_a_page_edit_shows_the_warnings_for_programs_started_before(
    run: dict,
) -> None:
    res = run["after-edit"]
    assert res["clicked"] is True and res["change"] == "cloak"
    assert len(res["games"]) == 1
    assert res["games"][0].startswith("\u26a0 StarCitizen.exe was started (")
    assert "before the last HidHide change (" in res["games"][0]
    assert "Late.exe" not in json.dumps(res)
    assert len(res["tester"]) == 1
    assert res["tester"][0].startswith("\u26a0 Gremlin Input Tester was started (")
    assert "close the old window" in res["tester"][0]
    assert res["restartShown"] is True


def test_restart_input_tester_starts_a_fresh_one_and_closes_nothing(
    run: dict,
) -> None:
    res = run["restart"]
    assert res["clicked"] is True
    assert len(res["starts"]) == 1
    exe, args = res["starts"][0]
    assert exe.endswith(TESTER_NAME)
    assert args[0] == "--gremlin-dir"
    # The old tester is still running: its warning stays until it is closed.
    assert len(res["tester"]) == 1


def test_expected_json_carries_the_change(run: dict) -> None:
    got = run["expected"]
    assert got["hidhide_change"] == "cloak"
    when = datetime.datetime.fromisoformat(got["hidhide_changed_at"])
    assert when.strftime("%H:%M") in run["after-edit"]["games"][0]


# --- the script (run by the fixture above) ----------------------------------------


def _main() -> None:  # noqa: C901, PLR0915 - one scripted run
    import importlib.util
    import time

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", root / "test" / "fake_hardware.py"
    )
    assert spec and spec.loader
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake_hardware.install()

    import gremlin.ui.update_model as um

    um.UpdateModel.startup = lambda self, *a, **k: None

    import shiboken6
    from PySide6 import QtCore, QtQuick, QtTest

    from gremlin import hidhide_driver, process_paths
    from gremlin import input_tester_link as link
    from gremlin.ui import hidhide as hh

    work = pathlib.Path(sys.argv[1])
    tester = str(work / "new" / TESTER_NAME)
    left = QtCore.Qt.MouseButton.LeftButton
    nomod = QtCore.Qt.KeyboardModifier.NoModifier

    class Driver:  # a fake HidHide driver: never the real one
        active = False
        inverse = True
        blacklist: list[str] = []
        whitelist: list[str] = []

    drv = Driver()

    def _set(name: str, value: object) -> bool:
        setattr(drv, name, value)
        return True

    fakes = {
        "driver_present": lambda: True,
        "driver_version": lambda: "1.5",
        "get_active": lambda: drv.active,
        "set_active": lambda on: _set("active", on),
        "get_inverse": lambda: drv.inverse,
        "set_inverse": lambda on: _set("inverse", on),
        "get_blacklist": lambda: list(drv.blacklist),
        "set_blacklist": lambda ids: _set("blacklist", list(ids)),
        "get_whitelist": lambda: list(drv.whitelist),
        "set_whitelist": lambda paths: _set("whitelist", list(paths)),
        "list_hid_devices": lambda gaming_only=False: [],
        "read_state": lambda: None,
        "_full_image_name": lambda path: path,
        "_gremlin_exe": lambda: r"C:\Gremlin\joystick_gremlin.exe",
    }
    for name, fake in fakes.items():
        for mod in (hidhide_driver, hh):
            if hasattr(mod, name):
                setattr(mod, name, fake)

    # Running: the game since 20 min ago, the tester since 10 min ago, a
    # listed game started in an hour (after any change), and explorer.
    now = datetime.datetime.now().replace(microsecond=0)
    programs = [
        (LIVE, now - datetime.timedelta(minutes=20)),
        (tester, now - datetime.timedelta(minutes=10)),
        (LATE, now + datetime.timedelta(hours=1)),
        (r"C:\Windows\explorer.exe", now - datetime.timedelta(hours=2)),
    ]
    process_paths.running_programs = lambda *_a: list(programs)
    process_paths.running_images = lambda: [p for p, _s in programs]

    starts: list[list] = []

    class Proc:
        def poll(self) -> None:
            return None

    def starter(exe: str, args: list[str]) -> Proc:
        starts.append([exe, list(args)])
        return Proc()

    link.tester_path = lambda: pathlib.Path(tester)  # type: ignore[assignment]
    link.set_starter(starter)

    hh._ensure_options()
    hh._save_games([
        {"name": "Star Citizen", "path": LIVE},
        {"name": "Late", "path": LATE},
        {"name": "Gremlin Input Tester", "path": tester},
    ])
    hh._mark_managed()
    hh._save_list_mode(True)

    import joystick_gremlin

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    def wait_until(check, timeout: float = 10.0):  # noqa: ANN001, ANN202
        deadline = time.monotonic() + timeout
        while True:
            value = check()
            if value or time.monotonic() > deadline:
                return value
            QtTest.QTest.qWait(20)

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for c in item.childItems():
            found += items(c)
        return found

    def named(win: QtQuick.QQuickWindow, name: str) -> list:
        return [i for i in items(win.contentItem()) if i.objectName() == name]

    def shown(win: QtQuick.QQuickWindow, name: str) -> list[str]:
        return [str(i.property("text")) for i in named(win, name) if i.isVisible()]

    def click(win: QtQuick.QQuickWindow, name: str) -> bool:
        found = [i for i in named(win, name) if i.isVisible() and i.isEnabled()]
        if not found:
            return False
        it = found[0]
        QtTest.QTest.qWait(150)
        p = it.mapToScene(QtCore.QPointF(it.width() / 2, it.height() / 2)).toPoint()
        QtTest.QTest.mouseClick(win, left, nomod, p)
        QtTest.QTest.qWait(50)
        return True

    def change() -> str | None:
        last = link.last_hidhide_change()
        return None if last is None else last[1]

    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root_obj = wait_until(lambda: app.engine.rootObjects())[0]
    item = next(
        (o for o in root_obj.findChildren(QtCore.QObject)
         if "ThemedMenuItem" in o.metaObject().className()
         and o.property("command") == "tools.hidhide"),
        None,
    )
    win = None
    if item is not None:
        QtCore.QMetaObject.invokeMethod(item, "triggered")
        win = wait_until(lambda: next(
            (w for w in app.topLevelWindows()
             if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
             and w.title() == "HidHide"),
            None,
        ))
    result("open", win is not None)
    if win is None:
        print("done", flush=True)
        os._exit(0)
    win = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
    win.resize(900, 900)
    QtTest.QTest.qWait(300)

    result("open-state", {
        "change": change(),
        "games": shown(win, "hidHideStaleGame"),
        "tester": shown(win, "hidHideStaleTester"),
    })

    # A page edit: HidHide Enabled clicked on. The page's 5 s check shows it.
    clicked = click(win, "hidHideCloakSwitch")
    wait_until(lambda: shown(win, "hidHideStaleTester"), 8)
    result("after-edit", {
        "clicked": clicked,
        "change": change(),
        "games": shown(win, "hidHideStaleGame"),
        "tester": shown(win, "hidHideStaleTester"),
        "restartShown": bool(shown(win, "hidHideRestartTester")),
    })

    clicked = click(win, "hidHideRestartTester")
    wait_until(lambda: starts, 3)
    QtTest.QTest.qWait(200)
    result("restart", {
        "clicked": clicked,
        "starts": starts,
        "tester": shown(win, "hidHideStaleTester"),
    })
    expected = link.expected_file()
    result("expected", json.loads(expected.read_text(encoding="utf-8"))
           if expected.is_file() else {})
    print("done", flush=True)
    os._exit(0)


if __name__ == "__main__":
    _main()
