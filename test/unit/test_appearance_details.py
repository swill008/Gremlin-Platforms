# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Batch L: the Appearance panel's "Group details" and "Row details".

- After "Bindings", a "Group details" section then a "Row details" section,
  each listing its settings in the approved order with Reset to defaults.
- "Show bindings" left the Bindings section: it is Row details' first
  setting, "Bindings and targets", same key showBindings.
- Each value is saved per device under its property name and reaches the
  page's ControlTree property of the same name; Reset to defaults puts back
  that section only, Reset Appearance puts back everything. Open All /
  Close All include both. Neither shows on the Xbox Output View.
- The pages' Find box hint says "custom name", not "your name".

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

_GROUP_LABELS = [
    "Controls by type",
    "Bindings by type",
    "No bindings",
    "Binding output not found",
    "Output devices",
    "Action types",
    "Custom names",
    "Other modes",
    "Wrap details",
    "Hide empty",
    "Reset to defaults",
]
_GROUP_DEFAULTS = {
    "groupControlsByType": True,
    "groupBindingsByType": True,
    "groupNoBindings": False,
    "groupOutputNotFound": False,
    "groupOutputDevices": False,
    "groupActionTypes": False,
    "groupCustomNames": False,
    "groupOtherModes": False,
    "groupWrapDetails": False,
    "groupHideEmpty": False,
}
_ROW_LABELS = [
    "Bindings and targets",
    "Action types",
    "Binding output not found",
    "Other modes",
    "System name",
    "Has a condition",
    "No bindings",
    "Wrap details",
    "Reset to defaults",
]
_ROW_DEFAULTS = {
    "showBindings": True,
    "rowActionTypes": False,
    "rowOutputNotFound": False,
    "rowOtherModes": False,
    "rowSystemName": False,
    "rowHasCondition": False,
    "rowNoBindings": False,
    "rowWrapDetails": False,
}
_DEFAULTS = {**_GROUP_DEFAULTS, **_ROW_DEFAULTS}
_CHANGED = {key: not value for key, value in _DEFAULTS.items()}
_KEYS_JS = json.dumps(list(_DEFAULTS))

_PAGES = (
    "DeviceBindingsPage.qml",
    "KeyboardPage.qml",
    "LogicalPage.qml",
    "OscPage.qml",
)


def _bindings_module():  # noqa: ANN202
    spec = importlib.util.spec_from_file_location(
        "_appearance_bindings", _HERE / "test_appearance_bindings.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(part: str, tmp_path: pathlib.Path) -> dict[str, str]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
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
    assert "done" in lines, smoke_report.explain(result)
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


def test_details_sections_list_save_per_device_and_reset(
    tmp_path: pathlib.Path,
) -> None:
    r = _run("panel", tmp_path)
    titles = r["titles"].split("|")
    at = titles.index("Bindings")
    assert titles[at + 1 : at + 3] == ["Group details", "Row details"]
    assert r["shown"] == "true true"
    assert r["groupLabels"].split("|") == _GROUP_LABELS
    assert r["rowLabels"].split("|") == _ROW_LABELS
    # Show bindings is no longer in the Bindings section.
    assert "Show bindings" not in r["bindingsLabels"].split("|")
    assert "Bindings and targets" not in r["bindingsLabels"].split("|")
    assert r["openAll"] == "true true false false"
    # Saved for this device only, under the property names.
    saved = json.loads(r["saved"])
    for key, value in _CHANGED.items():
        assert saved[key] == value, key
    assert r["otherDevice"] == "{}"
    assert json.loads(r["loaded"]) == _CHANGED
    # Each section's Reset to defaults puts back that section only.
    assert json.loads(r["groupReset"]) == {**_CHANGED, **_GROUP_DEFAULTS}
    assert json.loads(r["rowReset"]) == _DEFAULTS
    assert r["othersKept"] == "60"
    # Reset Appearance puts everything back.
    assert json.loads(r["allReset"]) == _DEFAULTS


def test_details_sections_are_hidden_on_the_xbox_output_view(
    tmp_path: pathlib.Path,
) -> None:
    r = _run("xbox", tmp_path)
    assert "Group details" in r["titles"].split("|")
    assert r["shown"] == "false false"


def test_the_page_tree_takes_each_details_value(tmp_path: pathlib.Path) -> None:
    r = _run("page", tmp_path)
    assert json.loads(r["tree"]) == _CHANGED


def test_pages_pass_every_details_property() -> None:
    for page in _PAGES:
        text = (_ROOT / "qml" / page).read_text(encoding="utf-8")
        for key in _DEFAULTS:
            assert f"{key}: _appear.{key}" in text, (page, key)


def test_find_hints_say_custom_name() -> None:
    hints = {
        "DeviceBindingsPage.qml": "System name, custom name, or group",
        "KeyboardPage.qml": "Key name, custom name, or group",
        "LogicalPage.qml": "System name, custom name, or group",
        "OscPage.qml": "Address, custom name, or group",
    }
    for page, hint in hints.items():
        text = (_ROOT / "qml" / page).read_text(encoding="utf-8")
        assert f'placeholder: "{hint}"' in text, page
        assert "your name" not in text, page


def _panel(s, out: pathlib.Path, page_key: str) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    find_js = _bindings_module()._FIND
    app, engine, warnings = s._engine(out)  # noqa: F841
    from gremlin.ui import window_placement

    scope = b"dev-a" if page_key == "device-bindings" else b""
    engine.loadData(
        b"""
import QtQuick
import QtQuick.Window
Window {
    width: 500; height: 900; visible: true
    ListAppearancePanel {
        id: _p; anchors.fill: parent; pageKey: "%s"; scopeKey: "%s"
    }
    ListAppearancePanel {
        id: _q; width: 10; height: 10; pageKey: "%s"; scopeKey: "%s"
    }
    ListAppearancePanel {
        id: _r; width: 10; height: 10; pageKey: "%s"; scopeKey: "dev-b"
    }
%s
}
"""
        % (
            page_key.encode(),
            scope,
            page_key.encode(),
            scope,
            page_key.encode(),
            find_js,
        ),
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
    )
    if not engine.rootObjects():
        for warning in warnings:
            print("ERROR load: " + warning, flush=True)
        os._exit(1)
    win = engine.rootObjects()[0]
    s._wait(300)
    js = lambda code: s._js(win, code)  # noqa: E731

    def values(who: str) -> str:
        return js(
            f"var o = {{}}; var keys = {_KEYS_JS}; "
            f"for (var i = 0; i < keys.length; i++) o[keys[i]] = {who}[keys[i]]; "
            "JSON.stringify(o)"
        )

    def change(who: str) -> None:
        for key, value in _CHANGED.items():
            js(f"{who}.{key} = {json.dumps(value)}; 1")

    js("_p.load(); 1")
    s._Out.result(
        "titles",
        js("sections(_p).map(function(x) { return x.title }).join('|')"),
    )
    s._Out.result(
        "shown",
        js(
            "var g = section(_p, 'Group details'); "
            "var w = section(_p, 'Row details'); "
            "String(!!g && g.visible) + ' ' + String(!!w && w.visible)"
        ),
    )
    if page_key == "xbox-output":
        s._report(warnings)
        return
    s._Out.result("groupLabels", js("labels(section(_p, 'Group details'))"))
    s._Out.result("rowLabels", js("labels(section(_p, 'Row details'))"))
    s._Out.result("bindingsLabels", js("labels(section(_p, 'Bindings'))"))
    js("_p.setAllSections(true); 1")
    opened = js(
        "section(_p, 'Group details').open + ' ' + section(_p, 'Row details').open"
    )
    js("_p.setAllSections(false); 1")
    closed = js(
        "section(_p, 'Group details').open + ' ' + section(_p, 'Row details').open"
    )
    s._Out.result("openAll", f"{opened} {closed}")
    change("_p")
    js("_p.save(); 1")
    s._wait(50)
    s._Out.result(
        "saved",
        json.dumps(window_placement.list_appearance_for(page_key, scope.decode())),
    )
    s._Out.result(
        "otherDevice",
        json.dumps(window_placement.list_appearance_for(page_key, "dev-b")),
    )
    js("_q.load(); 1")
    s._Out.result("loaded", values("_q"))
    js("_p.parentHeight = 60; _p.resetGroupDetails(); 1")
    s._Out.result("groupReset", values("_p"))
    js("_p.resetRowDetails(); 1")
    s._Out.result("rowReset", values("_p"))
    s._Out.result("othersKept", js("String(_p.parentHeight)"))
    change("_p")
    js("_p.reset(); 1")
    s._Out.result("allReset", values("_p"))
    s._report(warnings)


def _page(s, out: pathlib.Path) -> None:  # noqa: ANN001
    from PySide6 import QtCore

    find_js = _bindings_module()._FIND
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
        % find_js,
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
        js(f"panel().{key} = {json.dumps(value)}; 1")
    s._wait(50)
    s._Out.result(
        "tree",
        js(
            f"var o = {{}}; var keys = {_KEYS_JS}; var t = tree(); "
            "for (var i = 0; i < keys.length; i++) o[keys[i]] = t[keys[i]]; "
            "JSON.stringify(o)"
        ),
    )
    s._report(warnings)


if __name__ == "__main__":
    _s = _bindings_module()._screens()
    _s._boot()
    sys.stdout.reconfigure(encoding="utf-8")
    _part, _out_dir = sys.argv[1], pathlib.Path(sys.argv[2])
    _out_dir.mkdir(parents=True, exist_ok=True)
    try:
        parts = {
            "panel": lambda s, o: _panel(s, o, "device-bindings"),
            "xbox": lambda s, o: _panel(s, o, "xbox-output"),
            "page": _page,
        }
        parts[_part](_s, _out_dir)
    except Exception as failed:  # noqa: BLE001
        import traceback

        traceback.print_exc()
        print(f"ERROR {_part}: {failed!r}", flush=True)
        os._exit(1)
