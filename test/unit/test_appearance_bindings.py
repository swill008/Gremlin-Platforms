# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""05 S125 (D-05-BINDINGS-BOXES): the Appearance panel's "Bindings" section.

- After "Shown", a "Bindings" section lists, in order: Show bindings,
  "Bindings" size and color, Number size, font and color, Brackets, Target
  size, font, text color, background and border color, Border width,
  Corners, Roundness, Space between boxes and Reset to defaults.
- Each value is saved in the page's Appearance under its property name and
  reaches the page's ControlTree property of the same name.
- Reset to defaults puts this section back only; Reset Appearance puts it
  back with the rest. Open All / Close All include it.
- Not on the Xbox Output View (pageKey "xbox-output"); the old "Show action
  summary" switch and its key are gone.

Off-screen, each QML part in its own process (this file run as a script).
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

sys.path.append(".")

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]

_LABELS = [
    "Show bindings",
    '"Bindings" size',
    '"Bindings" color',
    "Number size",
    "Number font",
    "Number color",
    "Brackets",
    "Target size",
    "Target font",
    "Target text color",
    "Target background",
    "Target border color",
    "Border width",
    "Corners",
    "Roundness",
    "Space between boxes",
    "Reset to defaults",
]

# Property (= saved key) and its default; colours are "" until chosen.
_DEFAULTS = {
    "showBindings": True,
    "bindingsWordSize": 12,
    "bindingsWordColor": "",
    "bindingsNumberSize": 12,
    "bindingsNumberMono": True,
    "bindingsNumberColor": "",
    "bindingsBrackets": True,
    "bindingTargetSize": 12,
    "bindingTargetMono": True,
    "bindingTargetTextColor": "",
    "bindingTargetBgColor": "",
    "bindingTargetBorderColor": "",
    "bindingTargetBorderWidth": 1,
    "bindingTargetRounded": True,
    "bindingTargetRadius": 5,
    "bindingTargetSpacing": 6,
}

# A changed value for each.
_CHANGED = {
    "showBindings": False,
    "bindingsWordSize": 15,
    "bindingsWordColor": "#112233",
    "bindingsNumberSize": 14,
    "bindingsNumberMono": False,
    "bindingsNumberColor": "#223344",
    "bindingsBrackets": False,
    "bindingTargetSize": 16,
    "bindingTargetMono": False,
    "bindingTargetTextColor": "#334455",
    "bindingTargetBgColor": "#445566",
    "bindingTargetBorderColor": "#556677",
    "bindingTargetBorderWidth": 0,
    "bindingTargetRounded": False,
    "bindingTargetRadius": 9,
    "bindingTargetSpacing": 10,
}


def _screens():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(
        "_audit3_screens", _HERE / "test_audit3_screens.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__)), part, str(tmp_path)],
        text=True,
        encoding="utf-8",
        timeout=180,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
        },
    )
    lines = result.stdout.splitlines()
    assert "done" in lines, result.stdout[-3000:] + result.stderr[-3000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert not errors, errors
    ours = [
        line
        for line in lines
        if line.startswith("WARN")
        and any(
            name in line
            for name in ("LogicalPage", "ListAppearancePanel", "PageAppearance")
        )
    ]
    assert not ours, ours
    return {
        line.split(" ", 2)[1]: line.split(" ", 2)[2]
        for line in lines
        if line.startswith("RESULT ")
    }


def test_bindings_section_lists_saves_and_resets(tmp_path: pathlib.Path) -> None:
    r = _run("panel", tmp_path)
    titles = r["titles"].split("|")
    assert titles[titles.index("Shown") + 1] == "Bindings"
    assert r["shown"] == "true"
    assert r["labels"].split("|") == _LABELS
    # Open All / Close All include it.
    assert r["openAll"] == "true false"
    saved = json.loads(r["saved"])
    for key, value in _CHANGED.items():
        assert saved[key] == value, key
    assert "showActionSummary" not in saved
    # Written-by size stays (the written-by line).
    assert saved["summaryFont"] == 11
    # A fresh panel shows the saved values.
    assert json.loads(r["loaded"]) == _CHANGED
    # Reset to defaults: this section only.
    assert json.loads(r["sectionReset"]) == _DEFAULTS
    assert r["othersKept"] == "60"
    # Reset Appearance puts everything back.
    assert json.loads(r["allReset"]) == _DEFAULTS
    assert r["allResetOther"] == "44"
    # A chosen colour is shown; Default goes back to the theme's.
    assert r["colour"] == "#334455 true"


def test_bindings_section_is_hidden_on_the_xbox_output_view(
    tmp_path: pathlib.Path,
) -> None:
    r = _run("xbox", tmp_path)
    assert "Bindings" in r["titles"].split("|")
    assert r["shown"] == "false"


def test_the_page_tree_takes_each_bindings_value(tmp_path: pathlib.Path) -> None:
    r = _run("page", tmp_path)
    assert json.loads(r["tree"]) == _CHANGED


def test_pages_pass_every_bindings_property() -> None:
    for page in (
        "DeviceBindingsPage.qml",
        "KeyboardPage.qml",
        "LogicalPage.qml",
        "OscPage.qml",
    ):
        text = (_ROOT / "qml" / page).read_text(encoding="utf-8")
        for key in _DEFAULTS:
            assert f"{key}: _appear.{key}" in text, (page, key)
        assert "showActionSummary" not in text, page
    panel = (_ROOT / "qml" / "ListAppearancePanel.qml").read_text(encoding="utf-8")
    assert "showActionSummary" not in panel
    assert "Show action summary" not in panel


_FIND = b"""
    function find(item, test) {
        if (test(item))
            return item
        var kids = item.children || []
        for (var i = 0; i < kids.length; i++) {
            var f = find(kids[i], test)
            if (f) return f
        }
        return null
    }
    function all(item, test, out) {
        if (test(item))
            out.push(item)
        var kids = item.children || []
        for (var i = 0; i < kids.length; i++)
            all(kids[i], test, out)
        return out
    }
    function sections(root) {
        return all(root, function(i) {
            return i.toggled !== undefined && i.body !== undefined
        }, [])
    }
    function section(root, name) {
        var s = sections(root)
        for (var i = 0; i < s.length; i++)
            if (s[i].title === name) return s[i]
        return null
    }
    function firstText(item) {
        if (typeof item.label === "string" && item.label.length) return item.label
        if (typeof item.text === "string" && item.text.length) return item.text
        var kids = item.children || []
        for (var i = 0; i < kids.length; i++) {
            var t = firstText(kids[i])
            if (t.length) return t
        }
        return ""
    }
    function labels(sec) {
        var out = []
        for (var i = 0; i < sec.body.length; i++)
            out.push(firstText(sec.body[i]))
        return out.join("|")
    }
"""

_KEYS_JS = json.dumps(list(_DEFAULTS))


def _values(js, who: str) -> str:  # noqa: ANN001
    return js(
        f"var o = {{}}; var keys = {_KEYS_JS}; "
        "for (var i = 0; i < keys.length; i++) { var k = keys[i]; "
        f"var v = {who}[k]; "
        "if (k.indexOf('Color') >= 0) v = "
        f"({who}[k + 'Set'] !== undefined ? {who}[k + 'Set'] : String(v)); "
        "o[k] = v } JSON.stringify(o)"
    )


def _panel(s, out: pathlib.Path, page_key: str) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    from gremlin.ui import window_placement

    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 500; height: 900; visible: true
    ListAppearancePanel { id: _p; anchors.fill: parent; pageKey: "%s" }
    ListAppearancePanel { id: _q; width: 10; height: 10; pageKey: "%s" }
%s
}
"""
        % (page_key.encode(), page_key.encode(), _FIND),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731
    js("_p.load(); 1")
    s._Out.result(
        "titles",
        js("sections(_p).map(function(x) { return x.title }).join('|')"),
    )
    s._Out.result(
        "shown",
        js("var b = section(_p, 'Bindings'); String(!!b && b.visible)"),
    )
    if page_key == "xbox-output":
        s._report(warnings)
        return
    s._Out.result("labels", js("labels(section(_p, 'Bindings'))"))
    js("_p.setAllSections(true); 1")
    opened = js("String(section(_p, 'Bindings').open)")
    js("_p.setAllSections(false); 1")
    closed = js("String(section(_p, 'Bindings').open)")
    s._Out.result("openAll", f"{opened} {closed}")
    for key, value in _CHANGED.items():
        target = f"{key}Set" if "Color" in key else key
        js(f"_p.{target} = {json.dumps(value)}; 1")
    js("_p.save(); 1")
    s._wait(50)
    s._Out.result(
        "saved", json.dumps(window_placement.list_appearance(page_key))
    )
    js("_q.load(); 1")
    s._Out.result("loaded", _values(js, "_q"))
    s._Out.result(
        "colour",
        js(
            "String(_q.bindingTargetTextColor) + ' ' + "
            "(function() { _q.bindingTargetTextColorSet = ''; "
            "return String(_q.bindingTargetTextColor) !== '#334455' })()"
        ),
    )
    js("_p.parentHeight = 60; _p.resetBindings(); 1")
    s._Out.result("sectionReset", _values(js, "_p"))
    s._Out.result("othersKept", js("String(_p.parentHeight)"))
    for key, value in _CHANGED.items():
        target = f"{key}Set" if "Color" in key else key
        js(f"_p.{target} = {json.dumps(value)}; 1")
    js("_p.reset(); 1")
    s._Out.result("allReset", _values(js, "_p"))
    s._Out.result("allResetOther", js("String(_p.parentHeight)"))
    s._report(warnings)


def _page(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    app, engine, warnings = s._engine(out)  # noqa: F841
    import gremlin.ui.logical_layout  # noqa: F401
    import gremlin.ui.profile  # noqa: F401
    from gremlin import plugin_manager, shared_state
    from gremlin.logical_device import LogicalDevice
    from gremlin.profile import Profile
    from gremlin.signal import signal
    from gremlin.ui.backend import UIState

    plugin_manager.PluginManager()
    shared_state.current_profile = Profile()
    LogicalDevice().reset()
    backend_cls, _ = s._fakes()
    engine.rootContext().setContextProperty("backend", backend_cls())
    engine.rootContext().setContextProperty("uiState", UIState())
    engine.rootContext().setContextProperty("signal", signal)
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 1200; height: 800; visible: true
    QtObject { id: bsi; property var icons: ({ remove: "x" }) }
    LogicalPage { id: _page; anchors.fill: parent }
%s
    function panel() {
        return find(_page, function(i) {
            return i.liveOptions !== undefined && i.save !== undefined
        })
    }
    function tree() {
        return find(_page, function(i) { return i.liveDecoration !== undefined })
    }
}
"""
        % _FIND,
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(400)
    js = lambda code: s._js(win, code)  # noqa: E731
    for key, value in _CHANGED.items():
        target = f"{key}Set" if "Color" in key else key
        js(f"panel().{target} = {json.dumps(value)}; 1")
    s._wait(50)
    tree = js(
        f"var o = {{}}; var keys = {_KEYS_JS}; var t = tree(); "
        "for (var i = 0; i < keys.length; i++) { var k = keys[i]; var v = t[k]; "
        "if (k.indexOf('Color') >= 0) v = String(v); o[k] = v } JSON.stringify(o)"
    )
    s._Out.result("tree", tree)
    s._report(warnings)


if __name__ == "__main__":
    _s = _screens()
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        parts = {
            "panel": lambda s, o: _panel(s, o, "keyboard"),
            "xbox": lambda s, o: _panel(s, o, "xbox-output"),
            "page": _page,
        }
        parts[_part](_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
