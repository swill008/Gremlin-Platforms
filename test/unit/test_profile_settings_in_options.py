# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 S96-S98, 01 S58 / S65, D-04-OPTIONS-PROFILE: Profile Settings and
Scripts are pages of Options, in its "This profile" group: Startup and
macros, vJoy, Scripts, each with the strip naming the open profile. The old
windows, their toolbar buttons, Tools entries and commands are gone. Changes
mark the profile unsaved and are saved with it; Initial Values show one card
per vJoy, two decimals, and the Macro Default Delay its unit; Search options
finds the rows.

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
            if w.title() == "Options" and w.isVisible()]

def x_of(item):
    return item.mapToScene(QtCore.QPointF(0, 0)).x()

out = {}
content = win.contentItem()

def page_ready(name):
    # The shown item called name, once its page has loaded.
    def shown():
        it = named(pw.contentItem(), name)
        return it is not None and it.isVisible()
    pump(shown, 5.0)
    return named(pw.contentItem(), name) if shown() else None

# 01 S58: Options is the last toolbar button; the old two are gone.
options = ev(win, "_optionsButton")
out["buttons"] = [named(content, n) is not None for n in
                  ("profileSettingsToolbarButton", "scriptsToolbarButton")]
toolbar = [it for it in walk(content)
           if it.property("caption") not in (None, "")
           and it.parentItem() is options.parentItem()]
pump(lambda: x_of(options) > 0, 3.0)
out["captions"] = [it.property("caption") for it in sorted(toolbar, key=x_of)]

# One Options window: its button opens it, Tools > Options raises the same.
ev(options, "clicked()")
pump(lambda: len(windows()) == 1, 5.0)
pw = windows()[0]
ev(win, 'Commands.trigger("tools.options")')
pump(lambda: False, 0.5)
out["one_window"] = [len(windows()), windows()[0] is pw]
out["title"] = pw.title()

# S96: the "This profile" group is below Folders (the last program-wide
# section): heading, then its three pages.
def y_of(item):
    return item.mapToScene(QtCore.QPointF(0, 0)).y()
def program_buttons():
    return sorted(
        (it for it in walk(pw.contentItem())
         if it.metaObject().className().startswith("ConfigSectionButton")
         and not it.objectName().startswith("optionsSection:")), key=y_of)
pump(lambda: len(program_buttons()) > 2, 5.0)
heading = named(pw.contentItem(), "optionsProfileHeading")
profile_buttons = [it for it in walk(pw.contentItem())
                   if it.objectName().startswith("optionsSection:")]
out["heading"] = heading.property("text") if heading else None
out["sections"] = [[it.objectName(), it.property("text")] for it in profile_buttons]
pump(lambda: y_of(heading) > y_of(program_buttons()[-1]), 3.0)
out["order"] = (y_of(program_buttons()[-1]) < y_of(heading)
                < min(y_of(it) for it in profile_buttons))
out["last_program_section"] = program_buttons()[-1].property("text")
out["buttons_in_order"] = [y_of(it) for it in profile_buttons] == sorted(
    y_of(it) for it in profile_buttons)

def strip():
    # The strip's shown name and note, None when not shown.
    it = named(pw.contentItem(), "optionsProfileStrip")
    if it is None or not it.isVisible():
        return None
    return [named(it, "optionsProfileName").property("text"),
            named(it, "optionsProfileSavedNote").property("text")]

# No strip on the program-wide pages, and no profile page loaded.
out["strip_program"], out["title_program"] = [], []
for button in program_buttons():
    ev(button, "clicked()")
    pump(lambda: False, 0.2)
    out["strip_program"].append(strip())
    out["title_program"].append(
        [button.property("text"), ev(pw, "sectionTitle")])
out["loaded_early"] = [
    n for n in ("startupModeBox", "scriptManager", "vjoyInitialValue:1:X Axis")
    if named(pw.contentItem(), n) is not None]
# The strip and title on each of the three, by click.
out["strips"], out["titles"], out["page_shown"] = {}, {}, {}
MARK = {"startup-macros": "startupModeBox", "vjoy": "vjoyInitialValue:1:X Axis",
        "scripts": "scriptManager"}
for id, mark in MARK.items():
    ev(named(pw.contentItem(), "optionsSection:" + id), "clicked()")
    out["page_shown"][id] = page_ready(mark) is not None
    out["strips"][id] = strip()
    out["titles"][id] = ev(pw, "sectionTitle")
    # Only that page is loaded.
    out.setdefault("others", {})[id] = [
        m for m in MARK.values() if m != mark
        and named(pw.contentItem(), m) is not None]
out["window_title"] = app.backend.windowTitle

# showPage: shows the page and clears the search; false on an unknown id.
ev(pw, '_search.text = "keep"')
out["show_bad"] = [ev(pw, 'showPage("general")'), ev(pw, 'showPage("")')]
out["show_good"] = []
for id in MARK:
    ev(pw, '_search.text = "keep"')
    ok = ev(pw, f'showPage("{id}")')
    out["show_good"].append(
        [id, ok, ev(pw, "_search.text"), page_ready(MARK[id]) is not None])

# Search options finds the rows on these pages, and filters the others.
def search(text):
    ev(pw, f"_search.text = {json.dumps(text)}")
    pump(lambda: ev(pw, "_search.count") >= 0 if text else True, 3.0)
    pump(lambda: False, 0.5)
    return ev(pw, "_search.count")
def shown(name):
    it = named(pw.contentItem(), name)
    return it is not None and it.isVisible()
ev(program_buttons()[0], "clicked()")
out["search_none"] = [search("zzqqxx"), shown("startupModeBox")]
out["search_startup"] = [search("Startup Mode"), shown("startupModeBox"),
                         shown("macroDefaultDelayBox")]
out["search_delay"] = [search("Macro Default Delay"),
                       shown("macroDefaultDelayBox"), shown("startupModeBox")]
out["search_vjoy"] = [search("vJoy Initial Values"),
                      shown("vjoyInitialValue:1:X Axis")]
out["search_strip"] = strip()
ev(pw, '_search.text = ""')
pump(lambda: False, 0.3)

# 01 S65: the menus.
out["menus"] = ev(win, '(function() { var bar = _root.menuBar; var r = {}; '
    'for (var i = 0; i < bar.count; i++) { var m = bar.menuAt(i); '
    'm.compactNow(); var rows = []; '
    'for (var j = 0; j < m.count; j++) { var it = m.itemAt(j); '
    'if (!it || it.text === undefined || !(it.height > 0)) continue; '
    'rows.push(it.text) } r[m.title] = rows } return r })()')
out["commands"] = [[r.get("id"), r.get("window")] for r in app.backend.command_list()
                   if r.get("id") in ("tools.options", "tools.profileSettings",
                                      "tools.scripts", "view.settings", "view.scripts")]

# S62, S96: a change on Startup and macros marks the profile unsaved and is saved
# with the profile.
ev(named(pw.contentItem(), "optionsSection:startup-macros"), "clicked()")
page_ready("startupModeBox")
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
rows = control_windows.call_read({"window": "Options"})["items"]
out["delay_field"] = next(
    (r["text"] for r in rows if r.get("name") == "macroDefaultDelayBox"), None)

# S97, S98: one card per vJoy, values with two decimals.
ev(named(pw.contentItem(), "optionsSection:vjoy"), "clicked()")
page_ready("vjoyInitialValue:1:X Axis")
rows = control_windows.call_read({"window": "Options"})["items"]
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
# the same model, and a script added through it shows on the Scripts page.
ev(pw, 'showPage("scripts")')
page_ready("scriptManager")
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
    return [str(it.property("path")) for it in walk(pw.contentItem())
            if it.objectName().startswith("scriptRow:")]
pump(lambda: any("demo_one" in n for n in script_rows()), 10.0)
out["script_rows"] = script_rows()

# S96: the script is found by its name in Search options.
row = next(it for it in walk(pw.contentItem())
           if it.objectName().startswith("scriptRow:"))
out["search_script"] = [search(str(row.property("name"))),
                        any(it.objectName().startswith("scriptRow:")
                            and it.isVisible() for it in walk(pw.contentItem()))]

# S96: the strip and page follow the open profile when another is loaded.
ev(pw, 'showPage("startup-macros")')
page_ready("startupModeBox")
other = SAVE[:-len(".xml")] + "_other.xml"
blank = Profile()
blank.settings.startup_mode = "Last Active"
blank.to_xml(other)
before = [strip()[0], named(pw.contentItem(), "startupModeBox").property("displayText")]
app.backend.loadProfile(QtCore.QUrl.fromLocalFile(other).toString())
pump(lambda: strip() is not None and "_other" in str(strip()[0]), 10.0)
pump(lambda: (named(pw.contentItem(), "startupModeBox") is not None and
     named(pw.contentItem(), "startupModeBox").property("displayText")
     == "Last Active"), 5.0)
out["follows"] = [before, [
    strip()[0], named(pw.contentItem(), "startupModeBox").property("displayText")]]

print("RESULT " + json.dumps(out, default=str), flush=True)
os._exit(0)
"""


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp("profile_settings_in_options")
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


def test_s58_options_is_the_last_toolbar_button(run: dict) -> None:
    assert run["buttons"] == [False, False]
    assert run["captions"][-1] == "Options"
    assert "Profile Settings" not in run["captions"]
    assert "Scripts" not in run["captions"]


def test_s96_one_options_window(run: dict) -> None:
    assert run["one_window"] == [1, True]
    assert run["title"] == "Options"


def test_s96_the_old_windows_are_gone() -> None:
    for name in ("DialogProfileSettings.qml", "DialogScripts.qml"):
        assert not (_ROOT / "qml" / name).exists(), name


def test_s96_the_this_profile_group(run: dict) -> None:
    assert run["heading"] == "This profile"
    assert run["sections"] == [
        ["optionsSection:startup-macros", "Startup and macros"],
        ["optionsSection:vjoy", "vJoy"],
        ["optionsSection:scripts", "Scripts"],
    ]
    assert run["last_program_section"] == "Folders"
    assert run["order"] is True
    assert run["buttons_in_order"] is True


def test_s96_each_page_shows_with_its_title(run: dict) -> None:
    assert run["page_shown"] == {
        "startup-macros": True, "vjoy": True, "scripts": True}
    assert run["titles"] == {
        "startup-macros": "Startup and macros", "vjoy": "vJoy",
        "scripts": "Scripts"}
    assert all(shown == name for name, shown in run["title_program"])


def test_s96_the_strip_is_only_on_the_three_pages(run: dict) -> None:
    note = "Saved with the profile (Save Profile)"
    assert run["strips"] == {
        id: [run["window_title"], note]
        for id in ("startup-macros", "vjoy", "scripts")}
    assert len(run["strip_program"]) >= 3
    assert set(run["strip_program"]) == {None}


def test_a_profile_page_is_loaded_only_while_shown(run: dict) -> None:
    assert run["loaded_early"] == []
    assert run["others"] == {"startup-macros": [], "vjoy": [], "scripts": []}


def test_show_page_shows_the_page_and_clears_the_search(run: dict) -> None:
    assert run["show_bad"] == [False, False]
    assert run["show_good"] == [
        ["startup-macros", True, "", True],
        ["vjoy", True, "", True],
        ["scripts", True, "", True],
    ]


def test_s96_search_options_finds_the_rows(run: dict) -> None:
    assert run["search_none"] == [0, False]
    count, startup, delay = run["search_startup"]
    assert count >= 1 and startup is True and delay is False
    count, delay, startup = run["search_delay"]
    assert count >= 1 and delay is True and startup is False
    count, box = run["search_vjoy"]
    assert count >= 1 and box is True
    assert run["search_strip"] is None  # not over the search results
    count, row = run["search_script"]
    assert count >= 1 and row is True


def test_s96_the_pages_follow_the_open_profile(run: dict) -> None:
    before, after = run["follows"]
    assert "saved" in before[0] and before[1] == "Default"
    assert "_other" in after[0] and after[1] == "Last Active"


def test_one_script_list_shows_a_script_added_through_it(run: dict) -> None:
    assert run["same_model"] is True
    assert any("demo_one" in n for n in run["script_rows"]), run["script_rows"]


def test_s65_options_is_the_one_way_in(run: dict) -> None:
    tools = run["menus"]["Tools"]
    assert "Options" in tools
    for menu, rows in run["menus"].items():
        for text in ("Profile Settings", "Profile Settings…", "Scripts", "Scripts…"):
            assert text not in rows, (menu, text)
    # No old ids kept.
    assert run["commands"] == [["tools.options", True]]


def test_s62_s96_a_change_is_unsaved_then_saved_with_the_profile(
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
