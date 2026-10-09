# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Options search from the models (ConfigSectionModel.matchingSections)
finds the same sections the built pages do: for every section of both
Options windows, words from each group title, setting name and description
(and words that match nothing) give what ConfigGroup.qml's own matching
shows. The pages run off-screen in their own process (this file, run as a
script: python test/unit/test_options_search_model.py <out_dir>)."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest.mock

_HERE = pathlib.Path(__file__).parent
_ROOT = _HERE.parents[1]
sys.path.append(".")

# Edge cases on top of the words from the settings themselves.
_EXTRA = [
    "", "   ", "\t", "zzqxj-nothing", "other", "OTHER", "  Tempo  ", "TEMPO",
    "e", " ", "a b", "folder", "Ö",
]


def test_python_search_equals_qml_search(tmp_path: pathlib.Path) -> None:
    result = subprocess.run(
        [sys.executable, str(pathlib.Path(__file__)), str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        cwd=str(_ROOT),
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GREMLIN_OFFLINE": "1",
            "USERPROFILE": str(tmp_path),
            "PYTHONIOENCODING": "utf-8",
        },
    )
    out = result.stdout + result.stderr
    lines = result.stdout.splitlines()
    assert "done" in lines, out[-3000:]
    errors = [line for line in lines if line.startswith("ERROR")]
    assert errors == [], errors[:20]
    checked = [line for line in lines if line.startswith("CHECKED ")]
    # Both windows, many words each.
    assert len(checked) == 2 and all(int(c.split()[2]) > 50 for c in checked), checked
    warned = [line for line in lines if "ConfigGroup.qml" in line]
    assert warned == [], warned


def test_blank_text_matches_nothing() -> None:
    from gremlin.ui import option

    model = option.ConfigSectionModel()
    for text in ("", "  ", "\t\n"):
        assert model.matchingSections(text) == []
    assert model.matchingSections("zzqxj-nothing") == []
    # The "Other" heading itself never counts.
    rows = model.matchingSections("folder")
    assert rows and all(0 <= r < model.rowCount() for r in rows)


# --- the off-screen pages ------------------------------------------------------


def _words(model: object) -> list[str]:
    """Group titles, first and last words of names, description words."""
    from PySide6 import QtCore

    words = list(_EXTRA)
    role = QtCore.Qt.ItemDataRole.UserRole
    for row in range(model.rowCount()):
        groups = model.data(model.index(row), role + 2)
        for g in range(groups.rowCount()):
            gi = groups.index(g)
            title = groups.data(gi, role + 1)
            words += [title, title.lower()[:4]]
            entries = groups.data(gi, role + 2)
            for e in range(entries.rowCount()):
                ei = entries.index(e)
                name = str(entries.data(ei, role + 5) or "")
                text = str(entries.data(ei, role + 3) or "")
                parts = name.split()
                if parts:
                    words += [parts[0], parts[-1].upper(), name]
                desc = text.split()
                if desc:
                    words += [desc[len(desc) // 2], " ".join(desc[:2])]
    seen: list[str] = []
    for word in words:
        if word not in seen:
            seen.append(word)
    return seen


def _main(out: pathlib.Path) -> None:
    from PySide6 import QtCore, QtGui, QtQml, QtTest

    app = QtGui.QGuiApplication(sys.argv[:1])  # noqa: F841
    QtQml.qmlRegisterSingletonType(
        QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Style.qml")),
        "Gremlin.Style", 1, 0, "Style",
    )
    import gremlin.ui.backend  # noqa: F401
    import gremlin.ui.button_map_options  # noqa: F401
    import joystick_gremlin
    from gremlin.ui import option

    joystick_gremlin.register_config_options()
    engine = QtQml.QQmlApplicationEngine()
    engine.addImportPath(str(_ROOT / "theme"))
    engine.warnings.connect(
        lambda ws: [print("WARN " + w.toString(), flush=True) for w in ws]
    )
    for scope in ("", "button-map"):
        model = option.ConfigSectionModel()
        model.scope = scope
        engine.rootContext().setContextProperty("sectionModel", model)
        # Every section's groups built as the Options page builds them.
        engine.loadData(
            b"""
import QtQuick
import QtQuick.Layouts
import QtQuick.Window
import Gremlin.Config
Window {
    width: 700; height: 500; visible: true
    property string filterText: ""
    property alias sections: _sections
    function shown() {
        var rows = []
        for (var s = 0; s < _sections.count; s++) {
            var groups = _sections.itemAt(s).groups
            var any = false
            for (var g = 0; g < groups.count; g++) {
                if (groups.itemAt(g).firstMatch >= 0)
                    any = true
            }
            if (any)
                rows.push(s)
        }
        return JSON.stringify(rows)
    }
    ColumnLayout {
        Repeater {
            id: _sections
            model: sectionModel
            delegate: ColumnLayout {
                required property ConfigGroupModel groupModel
                property alias groups: _groups
                Repeater {
                    id: _groups
                    model: groupModel
                    delegate: ConfigGroup {
                        filterText: _win.filterText
                    }
                }
            }
        }
    }
    id: _win
}
""",
            QtCore.QUrl.fromLocalFile(str(_ROOT / "qml" / "Root.qml")),
        )
        win = engine.rootObjects()[-1]
        QtTest.QTest.qWait(200)
        count = QtQml.QQmlExpression(QtQml.qmlContext(win), win, "sections.count")
        if count.evaluate()[0] != model.rowCount():
            print(f"ERROR {scope!r}: sections not built", flush=True)
        words = _words(model)
        for word in words:
            win.setProperty("filterText", word)
            expr = QtQml.QQmlExpression(QtQml.qmlContext(win), win, "shown()")
            qml = json.loads(expr.evaluate()[0])
            ours = model.matchingSections(word)
            if not word.strip():
                # A blank search shows every page; the model answers none.
                if ours != [] or qml != list(range(model.rowCount())):
                    print(f"ERROR {scope!r} blank {word!r}: {qml} {ours}", flush=True)
            elif qml != ours:
                print(f"ERROR {scope!r} {word!r}: qml {qml} python {ours}", flush=True)
        print(f"CHECKED {scope or 'main'} {len(words)}", flush=True)
        win.setProperty("visible", False)
    print("done", flush=True)


if __name__ == "__main__":
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    sys.path.insert(0, str(_ROOT))
    sys.stdout.reconfigure(encoding="utf-8")
    import gremlin.util

    # Settings in a folder of their own, never the user's.
    gremlin.util.userprofile_path = unittest.mock.Mock(return_value=tempfile.mkdtemp())
    _out = pathlib.Path(sys.argv[1])
    _out.mkdir(parents=True, exist_ok=True)
    try:
        _main(_out)
    except Exception as failed:  # noqa: BLE001 (said, then the process ends)
        import traceback

        traceback.print_exc()
        print(f"ERROR main: {failed!r}", flush=True)
        os._exit(1)
    os._exit(0)
