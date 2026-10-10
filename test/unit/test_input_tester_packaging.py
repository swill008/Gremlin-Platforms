# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The build makes Gremlin Input Tester.exe next to the main exe (D-02-INPUT-TESTER).

The full PyInstaller build takes too long for a unit test, so these read the
spec, the installer scripts and the release workflow instead.
"""

from __future__ import annotations

import ast
import importlib.util
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_TESTER = "Gremlin Input Tester"


def _spec_tree() -> ast.Module:
    return ast.parse((_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8"))


def _assigned(tree: ast.Module) -> dict[str, ast.expr]:
    """Top-level name = value assignments of the spec."""
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = node.value
    return values


def _calls(tree: ast.Module, func: str) -> list[ast.Call]:
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == func
    ]


def _value(expr: ast.expr, values: dict[str, ast.expr]) -> object:
    if isinstance(expr, ast.Name):
        return ast.literal_eval(values[expr.id])
    return ast.literal_eval(expr)


def _kwarg(call: ast.Call, name: str) -> ast.expr:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    raise AssertionError(f"{ast.unparse(call)[:60]} has no {name}=")


def test_spec_builds_two_exes_with_no_console() -> None:
    tree = _spec_tree()
    values = _assigned(tree)
    exes = {
        _value(_kwarg(call, "name"), values): call
        for call in _calls(tree, "EXE")
    }
    assert set(exes) == {"gremlin_platforms", _TESTER}
    for call in exes.values():
        assert ast.literal_eval(_kwarg(call, "console")) is False
        assert ast.literal_eval(_kwarg(call, "icon")) == "gfx\\icon.ico"


def test_tester_is_analysed_from_input_tester_py() -> None:
    tree = _spec_tree()
    scripts = [ast.literal_eval(call.args[0]) for call in _calls(tree, "Analysis")]
    assert ["input_tester.py"] in scripts
    assert ["joystick_gremlin.py"] in scripts


def test_tester_takes_its_qml_and_dill() -> None:
    values = _assigned(_spec_tree())
    datas = ast.literal_eval(values["tester_datas"])
    # qml/tester/InputTester.qml and qml/Style.qml must be under a datas entry.
    for needed in ("qml/tester/InputTester.qml", "qml/Style.qml"):
        assert any(
            needed == source or needed.startswith(source.rstrip("/") + "/")
            for source, _ in datas
        ), needed
    binaries = ast.literal_eval(values["tester_binaries"])
    assert ("dill/dill.dll", ".") in binaries
    hidden = ast.literal_eval(values["tester_hidden_imports"])
    assert "gremlin.input_tester" in hidden


def test_both_exes_go_into_the_one_program_folder() -> None:
    tree = _spec_tree()
    collects = {
        _value(_kwarg(call, "name"), _assigned(tree)): call
        for call in _calls(tree, "COLLECT")
    }
    main = collects["gremlin_platforms"]
    names = [arg.id for arg in main.args if isinstance(arg, ast.Name)]
    assert "exe" in names and "tester_exe" in names
    # The source-only build (tools/build_input_tester.py) has its own folder.
    assert _TESTER in collects


def test_dev_build_tool_uses_the_spec_tester_switch() -> None:
    tool = (_ROOT / "tools" / "build_input_tester.py").read_text(encoding="utf-8")
    spec = (_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8")
    assert 'GREMLIN_TESTER_ONLY="1"' in tool
    assert 'os.environ.get("GREMLIN_TESTER_ONLY") == "1"' in spec
    assert "joystick_gremlin.spec" in tool


def test_installer_takes_the_whole_program_folder() -> None:
    # Inno Setup installs every file of dist\gremlin_platforms, so the tester
    # exe is installed next to gremlin_platforms.exe.
    iss = (_ROOT / "installer" / "gremlin_platforms.iss").read_text(encoding="utf-8")
    assert re.search(
        r'Source: "\{#DistDir\}\\\*"; DestDir: "\{app\}";[^\n]*recursesubdirs', iss
    )


def test_wix_generator_installs_the_tester_with_a_valid_id(
    tmp_path: pathlib.Path,
) -> None:
    spec = importlib.util.spec_from_file_location(
        "generate_wix", _ROOT / "generate_wix.py"
    )
    assert spec is not None and spec.loader is not None
    wix = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wix)
    (tmp_path / "gremlin_platforms.exe").write_bytes(b"")
    (tmp_path / f"{_TESTER}.exe").write_bytes(b"")
    files = wix.generate_file_list(str(tmp_path))
    assert f"{_TESTER}.exe" in files
    entry = wix.create_data_for_file(f"{_TESTER}.exe")
    assert entry["component_id"] == "component_Gremlin_Input_Tester.exe"
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.]*", entry["file_id"])


def test_release_workflow_checks_the_tester_was_built() -> None:
    workflow = (_ROOT / ".github" / "workflows" / "release-exe.yml").read_text(
        encoding="utf-8"
    )
    build = workflow.index("pyinstaller -y --clean joystick_gremlin.spec")
    check = workflow.index('"Gremlin Input Tester.exe"')
    assert build < check < workflow.index("Pack portable zip")
    assert "throw" in workflow[check:workflow.index("Pack portable zip")]
