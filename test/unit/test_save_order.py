# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""File > Save when a file the Save also writes fails (AUD-MOD-03,
AUD-FILES-06; 04 S13).

Save writes the profile, then the Logical Device's file, OSC's file and the
Device Bindings layouts held unsaved. When one of those fails, the profile is
still saved and said so: its History entry is made, a Save As moves to the new
path, and the message names the file that was not written. What failed stays
unsaved (the title keeps its "*") so a second Save tries it again.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from types import SimpleNamespace

import pytest

from gremlin import history_profile, osc_device_file, shared_state
from gremlin.modules import store
from gremlin.profile import Profile, SaveIncomplete
from gremlin.signal import signal
from gremlin.ui.backend import Backend
from test.unit._device_folders import put_module

GUID = "{11111111-2222-3333-4444-555555555556}"
LAYOUT = {"groups": ["Weapons"], "order": ["button:2", "button:1"], "group_of": {}}


@pytest.fixture
def device(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    path = put_module(
        folder,
        "Save Order Stick",
        {
            "kind": "control.hardware",
            "device": "Save Order Stick",
            "direction": "source",
            "claim": {"buttons": [1, 2]},
            "nodes": [],
        },
        GUID,
    )
    monkeypatch.setattr(
        store, "_layout_path", lambda guid, name="": path if guid == GUID else None
    )
    store.discard_pending()
    yield path
    store.discard_pending()


@pytest.fixture
def history(monkeypatch: pytest.MonkeyPatch) -> list[Path]:
    got: list[Path] = []
    monkeypatch.setattr(
        history_profile,
        "record_save",
        lambda path, before, text: got.append(Path(path)),
    )
    return got


@pytest.fixture
def profile(qapp: object, device: Path) -> Iterator[Profile]:
    saved = shared_state.current_profile
    shown = Profile()
    shared_state.current_profile = shown
    yield shown
    shared_state.current_profile = saved


def _fail_layout_write(monkeypatch: pytest.MonkeyPatch, device: Path) -> None:
    def refuse(*args: object, **kwargs: object) -> bool:
        raise PermissionError(13, "Access is denied", str(device))

    monkeypatch.setattr(store, "write_layout", refuse)


def _fail_osc_write(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: object, **kwargs: object) -> bool:
        raise OSError(28, "No space left on device", str(osc_device_file.path()))

    monkeypatch.setattr(osc_device_file, "save_if_dirty", refuse)


def _fake_backend(shown: Profile, old: Path) -> SimpleNamespace:
    shown.fpath = old
    fake = SimpleNamespace(
        profile=shown,
        used=[],
        recovery=[],
        titles=[],
    )
    fake._record_profile_use = lambda path: fake.used.append(Path(path))
    fake._recovery = SimpleNamespace(
        saved=lambda path: fake.recovery.append(Path(path))
    )
    fake.windowTitleChanged = SimpleNamespace(emit=lambda: fake.titles.append(True))
    return fake


def test_a_failed_layout_write_still_saves_the_profile(
    profile: Profile, device: Path, history: list[Path], tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fpath = tmp_path / "p.xml"
    profile.to_xml(fpath)
    history.clear()
    profile.modes.add_mode("Combat")
    store.set_pending_layout(GUID, LAYOUT)
    _fail_layout_write(monkeypatch, device)
    with pytest.raises(SaveIncomplete) as caught:
        profile.to_xml(fpath)
    # The profile is on disk and counted saved, with its History entry.
    assert "Combat" in fpath.read_text(encoding="utf-8-sig")
    assert history == [fpath]
    assert profile._xml_text() == profile._saved_snapshot
    # The message names the file that was not written.
    assert device.name in str(caught.value)
    assert "profile was saved" in str(caught.value).lower()
    # The layout stays held: the "*" stays and a second Save tries again.
    assert store.has_pending()
    assert profile.has_unsaved_changes()
    monkeypatch.undo()
    monkeypatch.setattr(store, "folder", lambda: device.parent)
    monkeypatch.setattr(
        store, "_layout_path", lambda guid, name="": device if guid == GUID else None
    )
    profile.to_xml(fpath)
    assert not store.has_pending()


def test_save_as_with_a_failed_osc_write_moves_to_the_new_path(
    profile: Profile, history: list[Path], tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old = tmp_path / "old.xml"
    new = tmp_path / "new.xml"
    profile.to_xml(old)
    history.clear()
    profile.modes.add_mode("Combat")
    _fail_osc_write(monkeypatch)
    heard: list[tuple[str, str]] = []
    listener = lambda title, text: heard.append((title, text))  # noqa: E731
    signal.showNotification.connect(listener)
    fake = _fake_backend(profile, old)
    try:
        ok = Backend.klass.saveProfile(fake, new.as_uri())  # type: ignore[attr-defined]
    finally:
        signal.showNotification.disconnect(listener)
    # Not all of it was written ...
    assert ok is False
    # ... but the profile was, at its new path, and the program knows it.
    assert new.is_file()
    assert profile.fpath == new
    assert fake.used == [new]
    assert fake.recovery == [new]
    assert fake.titles
    assert history == [new]
    # One message naming the file that failed.
    assert len(heard) == 1
    assert "OSC's file" in heard[0][1]
    assert Backend.klass.saveProblem(fake) == heard[0][1]  # type: ignore[attr-defined]


def test_a_full_save_is_as_before(
    profile: Profile, history: list[Path], tmp_path: Path,
) -> None:
    old = tmp_path / "old.xml"
    new = tmp_path / "new.xml"
    profile.to_xml(old)
    history.clear()
    profile.modes.add_mode("Combat")
    heard: list[tuple[str, str]] = []
    listener = lambda title, text: heard.append((title, text))  # noqa: E731
    signal.showNotification.connect(listener)
    fake = _fake_backend(profile, old)
    try:
        ok = Backend.klass.saveProfile(fake, new.as_uri())  # type: ignore[attr-defined]
    finally:
        signal.showNotification.disconnect(listener)
    assert ok is True
    assert profile.fpath == new
    assert fake.used == [new]
    assert history == [new]
    assert heard == []
    assert Backend.klass.saveProblem(fake) == ""  # type: ignore[attr-defined]
    assert not profile.has_unsaved_changes()
