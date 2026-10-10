# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The program ships the licence notices of the code it bundles (to-do 78).

dill.dll is WhiteMagic's dill (BSD-2-Clause) and links spdlog (MIT); both
notices must sit in licenses/ and go out with the PyInstaller build and the
installer. These read the files rather than running a build.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("name", "lines"),
    [
        (
            "dill.txt",
            ["BSD 2-Clause License", "Copyright (c) 2018, WhiteMagic"],
        ),
        (
            "spdlog.txt",
            [
                "The MIT License (MIT)",
                "Copyright (c) 2016 - present, Gabi Melman and spdlog contributors.",
            ],
        ),
        (
            # fmt v12 is compiled into dill.dll (symbols fmt::v12::format_error).
            "fmt.txt",
            ["Copyright (c) 2012 - present, Victor Zverovich and {fmt} contributors"],
        ),
    ],
)
def test_licence_file_has_its_copyright(name: str, lines: list[str]) -> None:
    path = _ROOT / "licenses" / name
    assert path.is_file(), f"licenses/{name} is missing"
    text = path.read_text(encoding="utf-8").splitlines()
    assert text[0].startswith("Source: https://raw.githubusercontent.com/")
    for line in lines:
        assert line in text, f"{name} lacks {line!r}"


def _spec_lists() -> dict[str, list]:
    tree = ast.parse((_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8"))
    values = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.List):
                    values[target.id] = ast.literal_eval(node.value)
    return values


@pytest.mark.parametrize("variable", ["datas", "tester_datas"])
def test_pyinstaller_build_carries_the_licences(variable: str) -> None:
    assert ("licenses", "licenses") in _spec_lists()[variable]


def test_installer_ships_the_licences_folder() -> None:
    text = (_ROOT / "installer" / "gremlin_platforms.iss").read_text(encoding="utf-8")
    files = text.split("[Files]", 1)[1].split("\n[", 1)[0]
    entries = [
        line for line in files.splitlines()
        if line.strip().startswith("Source:") and "licenses" in line
    ]
    assert entries, "the installer's [Files] has no licenses entry"
    assert 'Source: "..\\licenses\\*"' in entries[0]
    assert 'DestDir: "{app}\\licenses"' in entries[0]
