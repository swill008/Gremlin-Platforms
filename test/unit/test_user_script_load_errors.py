# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""User scripts that can't be loaded.

A script with a syntax error used to stop the whole profile from loading,
and a script whose file was missing was silently dropped on the next save.
Now such a script stays in the profile with the reason: its saved settings
are written back unchanged, and it is tried again (at each Run).
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
from xml.etree import ElementTree

from gremlin.profile import Profile, ScriptManager
from gremlin.user_script import Script

GOOD = (
    "import gremlin.user_script as us\n"
    "speed = us.IntegerVariable('speed', 'How fast', True, 5, 0, 10)\n"
)
BROKEN = "import gremlin.user_script as us\nspeed = us.IntegerVariable(\n"


def _saved_profile_scripts(path: pathlib.Path, speed: int) -> ElementTree.Element:
    """A profile's <scripts> node for one script with speed set."""
    path.write_text(GOOD, encoding="utf-8")
    script = Script(path, "Instance 1")
    script.variables["speed"].value = speed
    root = ElementTree.Element("profile")
    scripts = ElementTree.SubElement(root, "scripts")
    scripts.append(script.to_xml())
    return root


def _speed_in(node: ElementTree.Element) -> str | None:
    for variable in node.iter("variable"):
        for prop in variable.iter("property"):
            if prop.findtext("name") == "value":
                return prop.findtext("value")
    return None


def test_syntax_error_keeps_the_script_and_its_settings(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "throttle.py"
    root = _saved_profile_scripts(path, 7)
    path.write_text(BROKEN, encoding="utf-8")

    manager = ScriptManager(Profile())
    manager.from_xml(root)  # used to raise SyntaxError: profile not loaded

    assert len(manager.scripts) == 1
    script = manager.scripts[0]
    assert script.load_error.startswith("Syntax error, line ")
    assert script.variables == {}
    saved = manager.to_xml()
    assert len(saved) == 1
    assert _speed_in(saved) == "7"  # nothing lost on save


def test_missing_file_is_kept_not_dropped(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "gone.py"
    root = _saved_profile_scripts(path, 3)
    path.unlink()

    manager = ScriptManager(Profile())
    manager.from_xml(root)  # used to drop it, so the next save deleted it

    assert [s.load_error for s in manager.scripts] == ["File not found"]
    assert _speed_in(manager.to_xml()) == "3"


def test_fixed_script_loads_again_with_its_settings(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "throttle.py"
    root = _saved_profile_scripts(path, 9)
    path.write_text(BROKEN, encoding="utf-8")
    manager = ScriptManager(Profile())
    manager.from_xml(root)
    script = manager.scripts[0]
    assert script.load_error

    path.write_text(GOOD, encoding="utf-8")
    assert script.retry()
    assert script.load_error == ""
    assert script.variables["speed"].value == 9


def test_adding_a_broken_script_does_not_raise(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "new.py"
    path.write_text(BROKEN, encoding="utf-8")
    manager = ScriptManager(Profile())
    manager.add_script(path)
    assert manager.scripts[0].load_error.startswith("Syntax error")


def test_script_broken_after_loading_is_not_run(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "throttle.py"
    path.write_text(GOOD, encoding="utf-8")
    script = Script(path, "Instance 1")
    script.variables["speed"].value = 4
    path.write_text(BROKEN, encoding="utf-8")

    assert script.reload() is False  # Run skips it instead of failing
    assert script.load_error.startswith("Syntax error")
    assert _speed_in(script.to_xml()) == "4"
