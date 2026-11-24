# -*- coding: utf-8; -*-
"""02 S89, S90, S90a (D-B5-UPSTREAM): what auto-load does when a program
with no profile of its own comes to the front: Stop the profile, Keep
running or Load the default profile."""

from __future__ import annotations

import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from gremlin import config
from gremlin.ui import backend

_AUTOLOAD: Any = backend.Backend.klass._active_process_changed_cb
_ACTION = ("profile", "automation", "no-profile-action")
_DEFAULT = ("profile", "automation", "default-profile")


def _fake(
    action: str, default: str = "", unsaved: bool = False, running: bool = True
) -> types.SimpleNamespace:
    values = {
        ("profile", "automation", "enable-auto-loading"): True,
        _ACTION: action,
        _DEFAULT: default,
    }
    calls: list = []
    fake = types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *key: values[key]),
        profile=types.SimpleNamespace(
            fpath="open.xml", has_unsaved_changes=lambda: unsaved
        ),
        _wanted_active=running,
        _autoload_held=None,
        _autoload_missing=set(),
        calls=calls,
    )

    def activate(on: bool) -> None:
        calls.append(("active", on))
        fake._wanted_active = on

    def load(path: str) -> None:
        calls.append(("load", path))
        fake.profile.fpath = path

    fake.activate_gremlin = activate
    fake.loadProfile = load
    return fake


@pytest.fixture
def notes() -> Iterator[list]:
    seen: list = []

    def note(*args: str) -> None:
        seen.append(args)

    backend.signal.showNotification.connect(note)
    yield seen
    backend.signal.showNotification.disconnect(note)


@pytest.fixture
def no_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: None)


def test_settings_are_registered(register_config_options: None) -> None:
    cfg = config.Configuration()
    assert cfg.value(*_ACTION) == "stop"
    assert cfg.value(*_DEFAULT) == ""
    assert not cfg.exists("profile", "automation", "remain-active-on-focus-loss")


def test_stop_the_profile(no_profile: None) -> None:
    fake = _fake("stop")
    _AUTOLOAD(fake, "C:/x/other.exe")
    assert fake.calls == [("active", False)]


def test_keep_running(no_profile: None) -> None:
    fake = _fake("keep")
    _AUTOLOAD(fake, "C:/x/other.exe")
    assert fake.calls == []


def test_load_the_default_profile(no_profile: None, tmp_path: Path) -> None:
    default = tmp_path / "default.xml"
    default.write_text("<profile/>")
    fake = _fake("default", str(default))
    _AUTOLOAD(fake, "C:/x/other.exe")
    assert fake.calls == [
        ("active", False), ("load", str(default)), ("active", True)
    ]
    # Already open: no reload.
    fake.calls.clear()
    _AUTOLOAD(fake, "C:/x/third.exe")
    assert fake.calls == []


def test_missing_default_file_says_so_once_and_stops(
    no_profile: None, tmp_path: Path, notes: list
) -> None:
    fake = _fake("default", str(tmp_path / "gone.xml"))
    _AUTOLOAD(fake, "C:/x/other.exe")
    _AUTOLOAD(fake, "C:/x/other.exe")
    assert fake.calls == [("active", False)]
    assert len(notes) == 1
    assert "gone.xml" in notes[0][1]


def test_missing_own_profile_says_so_then_loads_the_default(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, notes: list
) -> None:
    own = tmp_path / "game.xml"  # never written
    default = tmp_path / "default.xml"
    default.write_text("<profile/>")
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(own))
    fake = _fake("default", str(default))
    _AUTOLOAD(fake, "C:/x/game.exe")
    _AUTOLOAD(fake, "C:/x/game.exe")
    assert ("load", str(default)) in fake.calls
    assert fake._wanted_active
    assert len(notes) == 1
    assert "game.xml" in notes[0][1]


def test_missing_own_profile_with_keep_running_keeps_running(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, notes: list
) -> None:
    own = tmp_path / "game.xml"
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(own))
    fake = _fake("keep")
    _AUTOLOAD(fake, "C:/x/game.exe")
    assert fake.calls == []
    assert len(notes) == 1


def test_unsaved_edits_wait_for_the_default(
    no_profile: None, tmp_path: Path, notes: list
) -> None:
    default = tmp_path / "default.xml"
    default.write_text("<profile/>")
    fake = _fake("default", str(default), unsaved=True)
    _AUTOLOAD(fake, "C:/x/other.exe")
    _AUTOLOAD(fake, "C:/x/other.exe")
    assert ("load", str(default)) not in fake.calls
    assert len(notes) == 1
    assert notes[0][0] == "Auto-load Waited"


def test_own_window_changes_nothing(tmp_path: Path) -> None:
    default = tmp_path / "default.xml"
    default.write_text("<profile/>")
    for action in ("stop", "keep", "default"):
        fake = _fake(action, str(default))
        _AUTOLOAD(fake, sys.executable)
        assert fake.calls == []


def test_own_and_default_both_missing_each_said_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, notes: list
) -> None:
    own = tmp_path / "game.xml"
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(own))
    fake = _fake("default", str(tmp_path / "gone.xml"))
    for _ in range(3):
        _AUTOLOAD(fake, "C:/x/game.exe")
    assert [n[1].split(" ")[0] for n in notes] == ["game.xml", "gone.xml"]
