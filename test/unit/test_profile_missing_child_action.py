# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A profile whose library names a child action that isn't there.

Loading used to spin forever on the UI thread (the "no progress" check in
Library.from_xml never fired), so the program hung. Now it stops and the
profile is refused with a ProfileError, which the program shows as "Could not
load the profile" while keeping the previous profile open.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
import threading
from xml.etree import ElementTree

import gremlin.plugin_manager
from gremlin.config import Configuration
from gremlin.error import ProfileError
from gremlin.profile import Profile, read_action_ids


def _without_one_child(xml_dir: pathlib.Path, out: pathlib.Path) -> str:
    tree = ElementTree.parse(xml_dir / "profile_hierarchy.xml")
    library = tree.getroot().find("library")
    assert library is not None
    parent = next(a for a in library.findall("action") if read_action_ids(a))
    child = str(read_action_ids(parent)[0])
    library.remove(next(a for a in library.findall("action") if a.get("id") == child))
    tree.write(out)
    return child


def test_load_finishes_when_a_child_action_is_missing(
    xml_dir: pathlib.Path, tmp_path: pathlib.Path
) -> None:
    gremlin.plugin_manager.PluginManager()
    Configuration()
    path = tmp_path / "missing_child.xml"
    _without_one_child(xml_dir, path)
    outcome: list[object] = []

    def load() -> None:
        try:
            Profile().from_xml(str(path))
            outcome.append("loaded")
        except Exception as error:  # noqa: BLE001 - the outcome is what is tested
            outcome.append(error)

    worker = threading.Thread(target=load, daemon=True)
    worker.start()
    worker.join(10)
    assert outcome, "loading the profile did not finish (hang)"
    assert isinstance(outcome[0], ProfileError), outcome[0]
