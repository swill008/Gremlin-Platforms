# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The old OSC converters are gone (09 S3, S9, S48, S96; AD7): an old
"output_host" / "output_port" in OSC's file is not read or kept, "Default"
is 127.0.0.1:8000, and an older profile's <osc-device> is not read."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from xml.etree import ElementTree

import pytest

from gremlin import history_modules, shared_state
from gremlin import osc_device_file as odf
from gremlin.modules import store
from gremlin.osc import OscDevice
from gremlin.profile import Profile


@pytest.fixture
def modules(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(store, "_saved", lambda: None)
    monkeypatch.setattr(history_modules, "note_write", lambda *a, **k: None)
    monkeypatch.setattr(shared_state, "current_profile", Profile())
    rows = OscDevice().rows
    kept = rows.to_dict()
    rows.load_dict({"inputs": []})
    rows.mark_saved()
    yield folder
    rows.load_dict(kept)
    rows.mark_saved()


def test_old_output_keys_are_not_read_or_kept(modules: Path) -> None:
    (modules / "osc.json").write_text(
        json.dumps({"server": {"output_host": "10.0.0.7", "output_port": 7001}}),
        encoding="utf-8",
    )
    targets = odf.read_targets()
    assert [(t["name"], t["host"], t["port"]) for t in targets] == [
        ("Default", "127.0.0.1", 8000)
    ]
    server = odf.read_server()
    assert "output_host" not in server and "output_port" not in server


def test_an_older_profiles_osc_device_is_not_read(
    modules: Path, tmp_path: Path
) -> None:
    root = ElementTree.fromstring(Profile(bind=False)._xml_text())
    root.set("version", "15")
    section = ElementTree.SubElement(root, "osc-device")
    node = ElementTree.SubElement(section, "input")
    ElementTree.SubElement(node, "input-type").text = "button"
    ElementTree.SubElement(node, "input-id").text = "1"
    ElementTree.SubElement(node, "label").text = "/jump"
    path = tmp_path / "old.xml"
    path.write_text(ElementTree.tostring(root, encoding="unicode"), encoding="utf-8")

    profile = Profile()
    profile.from_xml(path)

    assert OscDevice().rows.to_dict()["inputs"] == []
    assert not (modules / "osc.json").exists()
    assert not getattr(profile, "osc_migration_note", None)
