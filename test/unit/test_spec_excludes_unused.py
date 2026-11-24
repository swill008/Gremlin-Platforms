# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The QML folders the build leaves out must stay unused by the program."""

from __future__ import annotations

import ast
import os
import pathlib
import re
from collections.abc import Callable

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_SPEC = _ROOT / "joystick_gremlin.spec"
_QML_PREFIX = "pyside6\\qml\\"

# Python code shipped in the build.
_PY_DIRS = ("gremlin", "action_plugins", "gremlin_ctl", "dill", "vigem", "vjoy")
_PY_FILES = ("joystick_gremlin.py", "input_tester.py")

_QML_IMPORT = re.compile(r"^\s*import\s+([A-Za-z_][\w.]*)", re.MULTILINE)


def _spec_tree() -> ast.Module:
    return ast.parse(_SPEC.read_text(encoding="utf-8"))


def _assigned(name: str) -> list[str]:
    for node in _spec_tree().body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == name for t in node.targets
        ):
            return list(ast.literal_eval(node.value))
    raise AssertionError(f"joystick_gremlin.spec has no {name} list")


def _excluded_qml_modules() -> list[str]:
    """Excluded PySide6\\qml folders as QML module names, e.g. QtQuick.Pdf."""
    return [
        d[len(_QML_PREFIX):].replace("\\", ".")
        for d in _assigned("directory_excludes")
        if d.lower().startswith(_QML_PREFIX)
    ]


def _trim() -> Callable[[object], None]:
    """The spec's trim() with the spec's own lists."""
    namespace: dict = {
        "os": os,
        "directory_excludes": _assigned("directory_excludes"),
        "to_exclude": _assigned("to_exclude"),
    }
    funcs = [
        n for n in _spec_tree().body
        if isinstance(n, ast.FunctionDef) and n.name == "trim"
    ]
    assert funcs, "joystick_gremlin.spec has no trim()"
    code = compile(ast.Module(body=funcs, type_ignores=[]), str(_SPEC), "exec")
    exec(code, namespace)
    return namespace["trim"]


def _covers(module: str, excluded: str) -> bool:
    return module == excluded or module.startswith(excluded + ".")


def test_spec_excludes_qml_folders() -> None:
    assert len(_excluded_qml_modules()) >= 24


@pytest.mark.parametrize(
    "kept",
    [
        "QtQuick",
        "QtQuick.Dialogs",
        "QtQuick.NativeStyle",
        "QtQuick.Controls",
        "QtQuick.Controls.Basic",
        "QtQuick.Controls.Universal",
        "QtQuick.Controls.impl",
        "QtQuick.Templates",
        "QtQuick.Layouts",
        "QtQuick.Window",
        "QtQuick.Shapes",
        "QtCharts",
        "QtTextToSpeech",
        "QtQml",
        "QtQml.StateMachine",
        "QtCore",
        "Qt.labs.qmlmodels",
    ],
)
def test_used_modules_are_not_excluded(kept: str) -> None:
    hits = [e for e in _excluded_qml_modules() if _covers(kept, e)]
    assert not hits, f"{kept} is used but excluded by {hits}"


def test_no_qml_file_imports_an_excluded_module() -> None:
    excluded = _excluded_qml_modules()
    bad = []
    for folder in ("qml", "theme"):
        for path in (_ROOT / folder).rglob("*"):
            if path.suffix not in (".qml", ".js") and path.name != "qmldir":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            for module in _QML_IMPORT.findall(text):
                bad += [
                    f"{path.relative_to(_ROOT)}: {module}"
                    for e in excluded if _covers(module, e)
                ]
    assert not bad, f"Imports of modules left out of the build: {bad}"


def _python_files() -> list[pathlib.Path]:
    files = [_ROOT / f for f in _PY_FILES]
    for folder in _PY_DIRS:
        files += (_ROOT / folder).rglob("*.py")
    return [f for f in files if f.is_file()]


def test_no_python_file_imports_an_excluded_module() -> None:
    # Top-level folders match PySide6 modules: Qt3D -> Qt3DCore,
    # QtWebEngine -> QtWebEngineCore and so on.
    tops = [e for e in _excluded_qml_modules() if "." not in e]
    bad = []
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names += [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
                if node.module == "PySide6":
                    names += [f"PySide6.{a.name}" for a in node.names]
        for name in names:
            parts = name.split(".")
            if parts[0] != "PySide6" or len(parts) < 2:
                continue
            if any(parts[1].startswith(t) for t in tops):
                bad.append(f"{path.relative_to(_ROOT)}: {name}")
    assert not bad, f"Imports of Qt modules left out of the build: {bad}"


def test_no_excluded_controls_style_is_selected() -> None:
    styles = {
        e.rsplit(".", 1)[1]
        for e in _excluded_qml_modules()
        if e.startswith("QtQuick.Controls.")
    }
    bad = []
    for path in _python_files():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "QT_QUICK_CONTROLS_STYLE" in line or "setStyle(" in line:
                bad += [f"{path.relative_to(_ROOT)}: {line.strip()}"
                        for s in styles if re.search(rf"['\"]{s}['\"]", line)]
    assert not bad, f"Excluded Controls style selected: {bad}"


def test_trim_compare_ignores_case() -> None:
    class Analysis:
        binaries = [
            ("pyside6\\QML\\qt3d\\core\\plugin.dll", "src", "BINARY"),
            ("PySide6\\qml\\QtQuick\\Dialogs\\plugin.dll", "src", "BINARY"),
        ]
        datas = [
            ("PYSIDE6\\qml\\QtQuick\\Controls\\fusion\\Button.qml", "src", "DATA"),
            ("PySide6\\qml\\QtQuick\\Controls\\Universal\\Button.qml", "src", "DATA"),
        ]

    analysis = Analysis()
    _trim()(analysis)
    assert [d for d, _, _ in analysis.binaries] == [
        "PySide6\\qml\\QtQuick\\Dialogs\\plugin.dll"
    ]
    assert [d for d, _, _ in analysis.datas] == [
        "PySide6\\qml\\QtQuick\\Controls\\Universal\\Button.qml"
    ]
