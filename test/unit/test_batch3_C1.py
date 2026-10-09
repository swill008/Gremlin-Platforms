# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Catch-up batch 3, C1: help, glossary, docs and the small shared dialogs
say what the program does now."""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from PySide6 import QtCore

from test.unit import help_book

_ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def _topic(*titles: str) -> str:
    """One Help topic's title and text, by its title (any of these)."""
    topic = help_book.find(*titles)
    return topic["title"] + "\n" + help_book.text(topic["body"])


# The whole book's text, loaded by the QML engine (needs the application).
_GUIDE = ""


@pytest.fixture(autouse=True)
def _book(qapp: QtCore.QCoreApplication) -> None:
    global _GUIDE
    _GUIDE = help_book.book_text()


# | GL-202: the Options topic follows the Options window's layout.

def test_options_help_names_every_section_and_group() -> None:
    from gremlin.ui import option

    text = _topic("Options")
    missing = []
    for section, groups in option._LAYOUT:
        if section not in text:
            missing.append(section)
        for group, _keys in groups:
            if group and group not in text:
                missing.append(f"{section} > {group}")
    assert missing == []


# | GL-205, GL-135: Device change behavior shows Stop; HidHide's start
# | switch is only pointed to.

def test_help_says_stop_for_device_change_behavior() -> None:
    assert "Reload, Ignore, or Disable" not in _GUIDE
    assert _GUIDE.count("Stop, Ignore, or Reload") == 2  # Run and status, Options
    assert "Turn HidHide on at start" not in _GUIDE
    assert re.search(
        "Automatically Start in Tools [→›] Device Setup [→›] HidHide",
        _topic("General options", "Options"),
    )


# | GL-206: Device ID, not Device GUID.

def test_device_information_says_device_id() -> None:
    dialog = _read("qml/DialogDeviceInformation.qml")
    assert 'text: "Device ID"' in dialog
    assert "Device GUID" not in dialog
    assert "Device ID" in _topic("Device Information")
    assert "GUID" not in _GUIDE


# | GL-204: mouse buttons are for macros and Listen only.

def test_help_says_mouse_buttons_cant_fire_actions() -> None:
    assert "never reads the mouse" in _topic("Map to Mouse")
    assert "never an input of its own" in _topic("Macro")


# | GL-163 note: a macro's Joystick step goes through the input module.

def test_macro_help_says_joystick_steps_follow_claims() -> None:
    claims = "only does something for controls the stick's input module claims"
    assert claims in _topic("Macro")


# | GL-197 note: Text to Speech on keyboard keys.

def test_text_to_speech_help_names_keyboard_keys() -> None:
    import action_plugins.text_to_speech as tts
    from gremlin.types import InputType

    assert InputType.Keyboard in tts.TextToSpeechData.input_types
    assert "keyboard key" in _topic("Text to Speech")


# | GL-212, GL-146/147: Home lists every kind of card; the card menu help
# | matches what each card leaves out.

def test_home_help_lists_every_card_and_what_each_leaves_out() -> None:
    # Home and its card menus (one subject each in the book).
    home = (
        _topic("Home and its cards", "Home") + _topic("Card menus")
        + _topic("Delete a device")
    )
    for card in ("Keyboard", "OSC", "Logical Device", "vJoy", "Xbox"):
        assert card in home, card
    assert (
        "vJoy cards have no Calibration, Copy Setup to Another Stick…, Swap with "
        "Another Stick…, Change vJoy Output… or Delete Device"
    ) in home
    assert (
        "The Logical Device card has no Module Setup, Auto Mapper, Calibration, "
        "Device Information, Copy Setup to Another Stick…, Swap with Another "
        "Stick… or Change vJoy Output…"
    ) in home
    assert "Swap Device…" not in home
    assert "unsaved changes" in home  # Delete Device leaves the profile unsaved
    card = _read("qml/StatusCard.qml")
    # The rules the help describes are the card's own.
    assert "(xbox || logical) ? null : MenuModel.action(\"Module Setup…\"" in card
    assert re.search(r'dest \? null\s+: MenuModel\.action\("Delete Device"', card)


# | GL-214: the toolbar Mode box switches the running mode.

def test_help_says_the_mode_box_switches_the_running_mode() -> None:
    # Written once, under Modes (01 S128); Run links to it.
    modes = "".join(t["body"] for t in help_book.chapter_topics("modes"))
    assert "switches the running profile to it" in modes
    assert "Undo Delete Mode" in modes


# | Batch 2: Run asks about an open edit; the Keyboard page has OK/Cancel/Undo.

def test_help_covers_run_asking_and_the_keyboard_draft() -> None:
    run = _topic("Run and stop the profile", "Run and status")
    assert "Run asks first" in run and "Stop never asks" in run
    adding = (_topic("Add an action to an input") + _topic("Set up keyboard keys"))
    for word in ("Add Key", "OK", "Cancel", "Undo", "Redo"):
        assert word in adding, word


# | GL-218: Prefer Center, as the editor shows it.

def test_merge_axis_help_says_prefer_center() -> None:
    plugin = _read("action_plugins/merge_axis/__init__.py")
    assert '"Prefer Center"' in plugin
    assert "Prefer Center" in _topic("Merge Axis")
    assert "Prefercenter" not in _GUIDE


# | GL-221, GL-222: Clear Photo removes the photo; what Save writes.

def test_button_map_help_on_clear_photo_and_save() -> None:
    assert "module's picture" not in _GUIDE
    assert "Clear Photo removes the photo" in _GUIDE
    assert "only written by Save" not in _GUIDE
    options = _topic("Button Map Options")
    assert "written to the module file only by Save" in options
    assert "kept with the device's map at once" in options
    assert "one undo puts the old layout back" in _topic(
        "Copy a Button Map from another device"
    ).casefold()


# | GL-226: Restore is not always a new History entry.

def test_history_help_says_when_a_restore_shows() -> None:
    history = _topic("See saved changes in History") + _topic(
        "Restore an earlier version"
    )
    assert "and is itself a new change in the History" not in history
    assert "shows in the History at that Save Profile" in history
    assert "not a change in the History" in history
    glossary = _read("claude/glossary.md")
    assert "It is itself a saved change (a new History entry)." not in glossary
    assert "next Save Profile" in glossary


# | GL-230, GL-231, GL-232: Device Pack adds checked controls; Undo Import
# | ends on another pack; backups are explained.

def test_device_pack_and_backup_help() -> None:
    pack = (_topic("Module files") + _topic("Share a setup with a Device Pack"))
    assert "adds the pack's checked controls" in pack
    assert "open another pack" in pack
    backups = _topic("Deleted devices and backups")
    # The copies are autosaves in the Device Library (D-10-NO-DELETED-FOLDER).
    assert "deleted devices folder" not in backups
    words = ("Device Library", "autosave", "imported", "Delete File", "Import")
    for word in words:
        assert word in backups, word


# | GL-203: Options text uses the glossary; pickers say what they do.

def test_options_text_and_pickers_use_the_glossary() -> None:
    shell = _read("gremlin/ui/shell_option.py")
    assert "stub card" not in shell.lower()  # the stored key show-stubs stays
    assert "last:" not in shell
    assert "device without a module" in shell
    group = _read("qml/ConfigGroup.qml")
    assert "Select a File" not in group and "Select a Folder" not in group
    assert group.count("title: _pickerTitle()") == 2


# | GL-233: the Windows scaling box says what its title says.

def test_windows_scaling_box_matches_its_title() -> None:
    from gremlin.ui import option

    box = _read("qml/OptionWindowsScale.qml")
    title = option.entry_title("disable-windows-scaling")
    assert title == "Ignore Windows display scaling"
    assert f'text: "{title}"' in box
    assert "Gremlin-Platforms starts" not in box  # "the program" in sentences


# | GL-207, GL-208: HidHide's lists are replaced; source runs let python.exe through.

def test_hidhide_window_and_developer_notes() -> None:
    assert "replaces HidHide's program list and device list" in _read(
        "qml/DialogHardwareHide.qml"
    )
    readme = _read("README.md")
    assert "HidHide" in readme and "python.exe" in readme


# | GL-211, GL-223: glossary names.

def test_glossary_names_module_setup_windows_and_button_map_options() -> None:
    glossary = _read("claude/glossary.md")
    assert "**Input Module Setup**" in glossary
    assert "**Output Module Setup**" in glossary
    assert "its own window, not in the main Options" not in glossary
    assert "tool rows" in glossary


# | GL-219, GL-220, GL-225: the test plan uses today's words and features.

def test_test_plan_rows_are_current() -> None:
    plan = _read("claude/test-plan.md")
    open_rows = [line for line in plan.splitlines() if line.startswith("- [ ]")]
    stale = [
        line for line in open_rows
        if re.search(r"Toggle starts|Activate/Deactivate|Close to tray /|"
                     r"no confirm, see S-14|Clear image|Map pack Export|"
                     r"Executing mode", line)
    ]
    assert stale == []


# | GL-210, GL-280: RunningNote's two texts; TextInputDialog and
# | DismissibleDialog rules, driven directly off-screen.

_HARNESS = r"""
import os, sys
from PySide6 import QtCore, QtGui, QtQml

class FakeBackend(QtCore.QObject):
    changed = QtCore.Signal()
    uiScale = QtCore.Property(int, fget=lambda self: 100, notify=changed)
    gremlinActive = QtCore.Property(bool, fget=lambda self: True, notify=changed)

root = sys.argv[1]
app = QtGui.QGuiApplication([])
QtQml.qmlRegisterSingletonType(
    QtCore.QUrl.fromLocalFile(root + "/qml/Style.qml"), "Gremlin.Style", 1, 0, "Style")
engine = QtQml.QQmlApplicationEngine()
engine.addImportPath(root + "/theme")
fake = FakeBackend()
engine.rootContext().setContextProperty("backend", fake)
engine.loadData(b'''
import QtQuick
import QtQuick.Controls
ApplicationWindow {
    width: 500; height: 400; visible: true
    property var got: []
    RunningNote { id: plain }
    RunningNote { id: atOnce; appliesAtOnce: true }
    TextInputDialog { id: free; onAccepted: (v) => got.push("free:" + v) }
    TextInputDialog {
        id: strict
        allowBlank: false
        validator: function(v) { return v.indexOf("/") < 0 }
        onAccepted: (v) => got.push("strict:" + v)
    }
    DismissibleDialog { id: dd }
    function notes() { return plain.text + "|" + atOnce.text + "|" + plain.visible }
    function typeInto(dlg, seed, typed) {
        dlg.text = seed
        dlg.open()
        if (typed !== null)
            dlg.contentItem.children[1].children[0].text = typed
        var button = dlg.contentItem.children[1].children[1].enabled
        dlg._accept()
        dlg.close()
        return String(button)
    }
    function textInput() {
        var out = []
        out.push(typeInto(free, "", null))          // blank allowed
        out.push(typeInto(strict, "", null))        // blank refused
        out.push(typeInto(strict, "a/b", null))     // validator refuses the seed
        out.push(typeInto(strict, "x", "a/b"))      // and what is typed
        out.push(typeInto(strict, "x", "good"))
        // No seed: the last accepted value comes back.
        strict.text = ""
        strict.open()
        var seed = strict.contentItem.children[1].children[0].text
        strict.close()
        return out.join(",") + "|" + got.join(",") + "|" + seed
    }
    property var calls: []
    function dismissible() {
        dd.confirmThen("T", "M", "Go",
            function() { calls.push("yes") }, function() { calls.push("no") })
        dd.confirmed()
        dd.confirmThen("T", "M", "Go",
            function() { calls.push("yes2") }, function() { calls.push("no2") })
        dd.cancelled()
        dd.choose("Title", "Msg", "Restart", "Later")
        var labels = dd.confirmText + "/" + dd.discardText + "/" + dd.cancelText
        dd.close()  // closing without a choice is Cancel
        dd.announce(false, "bad")
        var failed = dd.titleText + "/" + dd.holdOpen
        dd.close()
        return calls.join(",") + "|" + labels + "|" + failed
    }
}
''', QtCore.QUrl.fromLocalFile(root + "/qml/Harness.qml"))
win = engine.rootObjects()[0]
ctx = QtQml.qmlContext(win)
for name in ("notes", "textInput", "dismissible"):
    out = QtQml.QQmlExpression(ctx, win, name + "()").evaluate()
    print("RESULT", name, out[0] if isinstance(out, tuple) else out, flush=True)
os._exit(0)
"""


def _run_harness() -> dict[str, str]:
    result = subprocess.run(
        [sys.executable, "-c", _HARNESS, str(_ROOT)],
        capture_output=True,
        text=True,
        timeout=60,
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "QT_QUICK_CONTROLS_STYLE": "GremlinStyle",
        },
    )
    out = {}
    for line in result.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            out[name] = value
    assert len(out) == 3, result.stderr[-3000:]
    return out


_RESULTS: dict[str, str] = {}


def _results() -> dict[str, str]:
    if not _RESULTS:
        _RESULTS.update(_run_harness())
    return _RESULTS


def test_running_note_says_module_setup_changes_work_at_once() -> None:
    plain, at_once, visible = _results()["notes"].split("|")
    assert plain == (
        "The profile is running. Changes here take effect the next time it starts."
    )
    assert at_once == "The profile is running. Saved changes work at once."
    assert visible == "true"


def test_text_input_dialog_rules() -> None:
    buttons, accepted, seed = _results()["textInput"].split("|")
    # OK is offered only for a usable value: blank where allowed, never a
    # value the validator refuses (seeded or typed).
    assert buttons == "true,false,false,false,true"
    assert accepted == "free:,strict:good"
    assert seed == "good"


def test_dismissible_dialog_runs_the_right_follow_up() -> None:
    calls, labels, failed = _results()["dismissible"].split("|")
    assert calls.startswith("yes,no2")
    assert labels == "Restart/Later/Cancel"
    assert failed == "Save Failed/true"
