# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The OSC page's groups, order and your names follow OSC's file rule
(D-09-OSC-FILE part 1): an edit marks OSC's file changed (the title's "*"),
File > Save Profile writes it with the inputs in one write, Discard drops it.

Spec: 09 S129-S133; D-09-OSC-FILE.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import osc_device_file, shared_state
from gremlin.osc import OscDevice, OscRuntime
from gremlin.profile import Profile
from gremlin.types import InputType
from gremlin.ui import osc_device_model
from gremlin.ui.backend import Backend
from gremlin.ui.osc_layout import OscLayoutModel


@pytest.fixture
def modules(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    from gremlin.modules import store

    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


@pytest.fixture
def writes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Each write of OSC's file, by who."""
    from gremlin.modules import store

    got: list[str] = []
    real = store.update_path

    def counting(path: Path, change: Any, who: str = "", **kw: Any) -> Any:  # noqa: ANN401
        if Path(path) == osc_device_file.path():
            got.append(who)
        return real(path, change, who, **kw)

    monkeypatch.setattr(store, "update_path", counting)
    return got


@pytest.fixture
def setup(
    qapp: object, modules: Path, tmp_path: Path
) -> Iterator[tuple[OscLayoutModel, Profile, Path]]:
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    saved = shared_state.current_profile
    profile = Profile()
    shared_state.current_profile = profile
    fpath = tmp_path / "osc_layout_save.xml"
    for address in ("/deck/1", "/deck/2"):
        row, error = osc_device_model.add_input({"address": address})
        assert row is not None and not error, error
    osc_device_file.save()
    profile.to_xml(fpath)
    assert not profile.has_unsaved_changes()
    model = OscLayoutModel()
    yield model, profile, fpath
    model.endPane()
    OscDevice().rows.reset()
    OscRuntime().reset_live()
    shared_state.current_profile = saved


def _key(address: str) -> str:
    row = OscDevice().find_address(address)
    assert row is not None
    word = "axis" if row.input_type == InputType.JoystickAxis else "button"
    return f"parent:{word}:{row.input_id}"


def _doc(modules: Path) -> dict:
    return json.loads((modules / "osc.json").read_text(encoding="utf-8"))


def _group_and_name(page: OscLayoutModel) -> None:
    page.addGroup("Stream Deck")
    page.setSelection([_key("/deck/1")])
    page.moveSelected("Stream Deck")
    page.setUserName(_key("/deck/2"), "Mute")


def test_a_layout_change_waits_for_save_and_shows_the_star(
    setup: tuple[OscLayoutModel, Profile, Path], modules: Path, writes: list[str]
) -> None:
    page, profile, _ = setup
    before = _doc(modules)
    _group_and_name(page)
    assert _doc(modules) == before
    assert writes == []
    assert profile.has_unsaved_changes()
    assert profile.looks_unsaved()
    # Page Undo still works before Save.
    page.undo()
    assert page.canUndo


def test_save_writes_layout_and_names_with_the_inputs_once(
    setup: tuple[OscLayoutModel, Profile, Path], modules: Path, writes: list[str]
) -> None:
    page, profile, fpath = setup
    _group_and_name(page)
    profile.to_xml(fpath)
    assert len(writes) == 1
    doc = _doc(modules)
    one = OscDevice().find_address("/deck/1").uid
    two = OscDevice().find_address("/deck/2").uid
    assert doc["layout"]["groups"] == ["Stream Deck"]
    assert doc["layout"]["group_of"] == {f"osc:{one}": "Stream Deck"}
    assert doc["claim"]["friendly"] == {f"osc:{two}": "Mute"}
    assert len(doc["inputs"]) == 2
    assert not profile.has_unsaved_changes()

    # Read again from the file: the page shows what was saved.
    osc_device_file.load()
    again = OscLayoutModel()
    try:
        assert list(again._layout.group_names()) == ["Stream Deck"]
        assert again._layout[two].second_name == "Mute"
    finally:
        again.endPane()


def test_discard_drops_unsaved_layout_changes(
    setup: tuple[OscLayoutModel, Profile, Path], modules: Path
) -> None:
    page, profile, _ = setup
    before = _doc(modules)
    _group_and_name(page)
    # The window's Discard (it uses nothing of the window itself).
    Backend.klass.discardOscDevice(None)  # type: ignore[attr-defined]
    # (Reading the file again may first copy the server settings into it.)
    after = _doc(modules)
    assert "layout" not in after and "claim" not in after
    assert after["inputs"] == before["inputs"]
    assert page._layout.group_names() == []
    assert page._layout[OscDevice().find_address("/deck/2").uid].second_name == ""
    assert not profile.has_unsaved_changes()


def test_a_save_keeps_names_written_to_the_file_another_way(
    setup: tuple[OscLayoutModel, Profile, Path], modules: Path
) -> None:
    # A Device Pack or Module Setup writes a name straight into OSC's file;
    # the page's next save writes only the names it changed (D-09-OSC-FILE).
    page, profile, fpath = setup
    one = OscDevice().find_address("/deck/1").uid
    path = osc_device_file.path()
    doc = json.loads(path.read_text("utf-8"))
    doc.setdefault("claim", {}).setdefault("friendly", {})[f"osc:{one}"] = "Fire"
    path.write_text(json.dumps(doc), "utf-8")
    _group_and_name(page)
    profile.to_xml(fpath)
    two = OscDevice().find_address("/deck/2").uid
    assert _doc(modules)["claim"]["friendly"] == {
        f"osc:{one}": "Fire",
        f"osc:{two}": "Mute",
    }
