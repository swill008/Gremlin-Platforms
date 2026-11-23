# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 S96-S98, 01 S58 / S65, D-04-PROFILE-WINDOW: Profile Settings is one
window of its own, opened at its section by the toolbar's Profile Settings
and Scripts buttons (after Options) and by Tools › Profile Settings… and
Scripts…; View lists neither. Its changes mark the profile unsaved and are
saved with it; Initial Values show one card per vJoy, two decimals, and the
Macro Default Delay its unit.

The real program off-screen (stand-in hardware, vJoy 1), in its own process.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_ROOT = pathlib.Path(__file__).resolve().parents[2]

_CODE = r"""
import importlib.util, json, os, sys, time
ROOT = sys.argv[1]
SAVE = sys.argv[2]
sys.path.insert(0, ROOT)
spec = importlib.util.spec_from_file_location(
    "fake_hardware", os.path.join(ROOT, "test", "fake_hardware.py"))
fake_hardware = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fake_hardware)
fake_hardware.install()
import gremlin.ui.update_model as um
um.UpdateModel.startup = lambda self, *a, **k: None
import joystick_gremlin
from PySide6 import QtCore, QtGui, QtQml, QtQuick, QtTest
from gremlin import shared_state
from gremlin.profile import Profile

app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
QtTest.QTest.qWait(500)
win = app.main_window

def pump(check, limit=10.0):
    end = time.monotonic() + limit
    while time.monotonic() < end:
        QtCore.QCoreApplication.processEvents(
            QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 50)
        if check():
            return True
    return bool(check())

def ev(obj, code):
    expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
    value = expr.evaluate()
    assert not expr.hasError(), code + ': ' + expr.error().toString()
    value = value[0] if isinstance(value, tuple) else value
    if isinstance(value, QtQml.QJSValue):
        value = value.toVariant()
    return value

def walk(item):
    yield item
    for child in item.childItems():
        yield from walk(child)

def named(root, name):
    return next((it for it in walk(root) if it.objectName() == name), None)

def windows():
    return [w for w in QtGui.QGuiApplication.allWindows()
            if w.title() == "Profile Settings" and w.isVisible()]

def x_of(item):
    return item.mapToScene(QtCore.QPointF(0, 0)).x()

out = {}
content = win.contentItem()

# 01 S58: Profile Settings and Scripts come right after Options.
options = ev(win, "_optionsButton")
settings_button = named(content, "profileSettingsToolbarButton")
scripts_button = named(content, "scriptsToolbarButton")
out["buttons"] = [settings_button is not None, scripts_button is not None]
if settings_button is not None and scripts_button is not None:
    pump(lambda: x_of(settings_button) > x_of(options), 3.0)
    out["after_options"] = (x_of(options) < x_of(settings_button)
                            < x_of(scripts_button))
    out["captions"] = [settings_button.property("caption"),
                       scripts_button.property("caption")]
    # The buttons further right than Options: only these two, Options' twins.
    toolbar = [it for it in walk(content)
               if it.property("caption") not in (None, "")
               and it.parentItem() is options.parentItem()]
    out["right_of_options"] = [
        it.property("caption") for it in sorted(toolbar, key=x_of)
        if x_of(it) > x_of(options)]

    # The Profile Settings button opens the one window at General.
    ev(settings_button, "clicked()")
    pump(lambda: len(windows()) == 1, 5.0)
    out["open_general"] = [len(windows()),
                           windows()[0].property("section") if windows() else None]
    # Moved to vJoy by its left list, a second press raises the same window
    # at General again.
    first = windows()[0] if windows() else None
    if first is not None:
        ev(named(first.contentItem(), "profileSettingsSection:vjoy"), "clicked()")
        out["moved"] = first.property("section")
    ev(settings_button, "clicked()")
    pump(lambda: bool(windows()) and windows()[0].property("section") == "general", 5.0)
    out["open_again"] = [len(windows()),
                         windows()[0] is first if windows() else False,
                         windows()[0].property("section") if windows() else None]

    # 04 S96: the Scripts button opens the Scripts window, Tools › Scripts…
    # raises the same one, and Profile Settings stays open beside it.
    def scripts_windows():
        return [w for w in QtGui.QGuiApplication.allWindows()
                if w.objectName() == "scriptsWindow" and w.isVisible()]
    ev(scripts_button, "clicked()")
    pump(lambda: len(scripts_windows()) == 1, 5.0)
    sw = scripts_windows()[0] if scripts_windows() else None
    out["scripts_button"] = [len(scripts_windows()),
                             sw.title() if sw else None, len(windows())]
    ev(win, 'Commands.trigger("tools.scripts")')
    pump(lambda: False, 0.5)
    out["scripts_menu"] = [len(scripts_windows()),
                           bool(scripts_windows()) and scripts_windows()[0] is sw,
                           len(windows())]
    if sw is not None:
        sw.close()
        pump(lambda: not scripts_windows(), 3.0)
    ev(win, 'Commands.trigger("tools.scripts")')
    pump(lambda: len(scripts_windows()) == 1, 5.0)
    out["scripts_menu_opens"] = len(scripts_windows())

# 01 S65: the menus.
out["menus"] = ev(win, '(function() { var bar = _root.menuBar; var r = {}; '
    'for (var i = 0; i < bar.count; i++) { var m = bar.menuAt(i); '
    'm.compactNow(); var rows = []; '
    'for (var j = 0; j < m.count; j++) { var it = m.itemAt(j); '
    'if (!it || it.text === undefined || !(it.height > 0)) continue; '
    'rows.push(it.text) } r[m.title] = rows } return r })()')
out["commands"] = [[r.get("id"), r.get("window")] for r in app.backend.command_list()
                   if r.get("id") in ("tools.profileSettings", "tools.scripts",
                                      "view.settings", "view.scripts")]

# S96: the window, its heading and left list.
pw = windows()[0] if windows() else None
if pw is not None:
    pc = pw.contentItem()
    out["title"] = pw.title()
    out["object"] = pw.objectName()
    out["sections"] = [
        [it.objectName(), it.property("text")] for it in walk(pc)
        if it.objectName().startswith("profileSettingsSection:")]
    note = named(pc, "profileSettingsSavedNote")
    out["note"] = note.property("text") if note else None

    # S62, S96: a change on General marks the profile unsaved and is saved
    # with the profile.
    ev(named(pc, "profileSettingsSection:general"), "clicked()")
    pump(lambda: named(pw.contentItem(), "startupModeBox") is not None, 5.0)
    profile = shared_state.current_profile
    profile.has_unsaved_changes()
    ev(win, "_root.refreshProfileDirty()")
    out["dirty_before"] = [profile.has_unsaved_changes(), ev(win, "_root.profileDirty")]
    box = named(pw.contentItem(), "startupModeBox")
    labels = json.loads(ev(
        box, "JSON.stringify([...Array(count).keys()].map(i => textAt(i)))"))
    pick = labels.index("Default")
    ev(box, f"currentIndex = {pick}; activated({pick})")
    out["startup"] = profile.settings.startup_mode
    ev(win, "_root.refreshProfileDirty()")
    pump(lambda: bool(ev(win, "_root.profileDirty")), 5.0)
    out["dirty_after"] = [profile.has_unsaved_changes(), ev(win, "_root.profileDirty")]
    url = QtCore.QUrl.fromLocalFile(SAVE).toString()
    out["saved"] = app.backend.saveProfile(url)
    back = Profile()
    back.from_xml(SAVE)
    out["saved_startup"] = back.settings.startup_mode
    out["clean_after_save"] = not shared_state.current_profile.has_unsaved_changes()

    # S98: the delay shows three decimals and its unit.
    delay = named(pw.contentItem(), "macroDefaultDelayBox")
    row = delay.parentItem()
    out["delay"] = [
        str(it.property("text")) for it in walk(row)
        if it.isVisible() and it.property("text") not in (None, "")
        and it is not delay]
    from gremlin.ui import control_windows
    rows = control_windows.call_read({"window": "Profile Settings"})["items"]
    out["delay_field"] = next(
        (r["text"] for r in rows if r.get("name") == "macroDefaultDelayBox"), None)

    # S97, S98: one card per vJoy, values with two decimals.
    ev(named(pw.contentItem(), "profileSettingsSection:vjoy"), "clicked()")
    pump(lambda: named(pw.contentItem(), "vjoyInitialValue:1:X Axis") is not None, 5.0)
    rows = control_windows.call_read({"window": "Profile Settings"})["items"]
    out["boxes"] = {r["name"]: r["text"] for r in rows
                    if r["kind"] == "field"
                    and r["name"].startswith("vjoyInitialValue:")}
    # A card per vJoy: the Initial Values delegates (vjoyId + its axes).
    out["cards"] = sorted(
        it.property("vjoyId") for it in walk(pw.contentItem())
        if it.property("initialValuesModel") is not None
        and it.property("vjoyId") is not None)
    from gremlin.modules import output
    out["vjoys"] = sorted(output.vjoy_axes())
# One script list (Backend.scriptListModel is cached): two reads are
# the same model, and a script added through it shows in the window.
m1, m2 = app.backend.scriptListModel, app.backend.scriptListModel
out["same_model"] = m1 is m2
from gremlin import util
folder = util.scripts_dir()
os.makedirs(folder, exist_ok=True)
demo = os.path.join(folder, "demo_one.py")
with open(demo, "w", encoding="utf-8") as f:
    f.write("import gremlin" + chr(10))
m1.addScript(QtCore.QUrl.fromLocalFile(demo).toString())
def script_rows():
    sws = scripts_windows()
    return [str(it.property("path")) for it in walk(sws[0].contentItem())
            if it.objectName().startswith("scriptRow:")] if sws else []
pump(lambda: any("demo_one" in n for n in script_rows()), 10.0)
out["script_rows"] = script_rows()

print("RESULT " + json.dumps(out, default=str), flush=True)
os._exit(0)
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("profile_settings_window")
    home = tmp / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", HTTPS_PROXY="http://127.0.0.1:9",
    )
    done = proc_tree.run(
        [sys.executable, "-c", _CODE, str(_ROOT), str(tmp / "saved.xml")],
        cwd=_ROOT, env=env, text=True, timeout=180,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(done)
    return json.loads(lines[-1][len("RESULT "):])


def test_s58_both_toolbar_buttons_come_after_options(run: dict) -> None:
    assert run["buttons"] == [True, True]
    assert run["after_options"] is True
    assert run["captions"] == ["Profile Settings", "Scripts"]
    assert run["right_of_options"] == ["Profile Settings", "Scripts"]


def test_s96_the_button_opens_one_window_at_general(run: dict) -> None:
    assert run["open_general"] == [1, "general"]
    # A second press raises the same window and sets its section.
    assert run["moved"] == "vjoy"
    assert run["open_again"] == [1, True, "general"]


def test_s96_scripts_is_its_own_window_beside_profile_settings(run: dict) -> None:
    # The toolbar button opens it; Profile Settings stays open too.
    assert run["scripts_button"] == [1, "Scripts", 1]
    # Tools › Scripts… raises the same window, and opens it when closed.
    assert run["scripts_menu"] == [1, True, 1]
    assert run["scripts_menu_opens"] == 1


def test_one_script_list_shows_a_script_added_through_it(run: dict) -> None:
    assert run["same_model"] is True
    assert any("demo_one" in n for n in run["script_rows"]), run["script_rows"]


def test_s65_tools_lists_both_after_options_and_view_neither(run: dict) -> None:
    tools = run["menus"]["Tools"]
    at = tools.index("Options")
    assert tools[at:at + 3] == ["Options", "Profile Settings…", "Scripts…"]
    assert "Profile Settings" not in run["menus"]["View"]
    assert "Scripts" not in run["menus"]["View"]
    # No old ids kept; both open a window (control API window.open, 13 S29).
    assert sorted(run["commands"]) == [
        ["tools.profileSettings", True], ["tools.scripts", True]]


def test_s96_the_window_title_heading_and_left_list(run: dict) -> None:
    assert run["title"] == "Profile Settings"
    assert run["object"] == "profileSettingsWindow"
    # General and vJoy only: Scripts is a window of its own (S96).
    assert run["sections"] == [
        ["profileSettingsSection:general", "General"],
        ["profileSettingsSection:vjoy", "vJoy"],
    ]
    assert run["note"] == "Saved with the profile (Save Profile)"


def test_s62_s96_a_general_change_is_unsaved_then_saved_with_the_profile(
    run: dict,
) -> None:
    assert run["dirty_before"] == [False, False]
    assert run["startup"] == "Default"
    assert run["dirty_after"] == [True, True]
    assert run["saved"] is True
    assert run["saved_startup"] == "Default"
    assert run["clean_after_save"] is True


def test_s98_the_delay_shows_its_unit(run: dict) -> None:
    assert run["delay_field"] == "0.050"
    assert "s" in run["delay"]


def test_s97_s98_initial_values_one_card_per_vjoy_two_decimals(run: dict) -> None:
    assert run["boxes"], "no initial value boxes"
    assert {name.split(":")[1] for name in run["boxes"]} == {
        str(v) for v in run["vjoys"]}
    assert run["cards"] == run["vjoys"]
    assert set(run["boxes"].values()) == {"0.00"}, run["boxes"]
