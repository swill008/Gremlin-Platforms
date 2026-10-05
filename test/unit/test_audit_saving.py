# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Saving, History and settings fixes from the code audit (AU-03, 38, 40,
42, 43, 44, 46, 47, 48, 54)."""

from __future__ import annotations

import errno
import json
import sys
import time
import types
from pathlib import Path

sys.path.append(".")

import pytest

from gremlin import config, history
from gremlin.modules import module_file
from gremlin.ui import backend, history_model


def test_a_failed_safe_write_leaves_the_file_whole(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "x.json"
    path.write_text('{"old": 1}', encoding="utf-8")
    real = Path.write_text

    def full_disk(self: Path, text: str, *args: object, **kwargs: object) -> int:
        if self.name.endswith(".tmp"):
            raise OSError(errno.ENOSPC, "disk full")
        return real(self, text, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", full_disk)
    with pytest.raises(OSError):
        module_file.write_text(path, '{"new": 2}')
    assert path.read_text(encoding="utf-8") == '{"old": 1}'
    assert not (tmp_path / "x.json.tmp").exists()


def test_a_refused_swap_still_writes_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "x.json"
    path.write_text('{"old": 1}', encoding="utf-8")

    def busy(*_args: object) -> None:
        raise PermissionError("in use")

    monkeypatch.setattr(module_file.os, "replace", busy)
    module_file.write_text(path, '{"new": 2}')
    assert path.read_text(encoding="utf-8") == '{"new": 2}'


@pytest.fixture
def area_file() -> Path:
    path = history._file("settings")
    path.parent.mkdir(parents=True, exist_ok=True)
    yield path
    path.unlink(missing_ok=True)


def _line(entry_id: str, title: str = "t") -> str:
    entry = {"id": entry_id, "at": time.time(), "area": "settings", "title": title}
    return json.dumps(entry, ensure_ascii=False)


def test_history_reads_past_a_cut_character(area_file: Path) -> None:
    cut = _line("b", "Joystick é").encode("utf-8")
    cut = cut[: cut.index("é".encode()) + 1]
    area_file.write_bytes((_line("a") + "\n").encode() + cut)
    assert [e["id"] for e in history.entries("settings")] == ["a"]
    history.prune()  # no error


def test_an_entry_after_a_cut_line_is_kept(area_file: Path) -> None:
    area_file.write_text(_line("a") + "\n" + '{"id": "c", "at": 1', encoding="utf-8")
    history._append(json.loads(_line("d")))
    assert [e["id"] for e in history._lines("settings")] == ["a", "d"]


def test_prune_drops_the_oldest_until_the_file_fits(
    area_file: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    lines = [_line(f"e{i}", "x" * 1000) for i in range(300)]
    area_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(history, "_limits", lambda: (90, 0.1))
    history.prune()
    kept = [e["id"] for e in history._lines("settings")]
    assert kept and kept[-1] == "e299"
    assert area_file.stat().st_size <= 0.1 * 1024 * 1024
    assert kept == [f"e{i}" for i in range(300 - len(kept), 300)]


def test_a_list_setting_is_put_back() -> None:
    cfg = config.Configuration()
    key = ("action", "general", "action-priorities")
    before = cfg.value(*key)
    try:
        ok, _message = history_model._restore_settings(
            {"/".join(key): [["Map to vJoy", True]]}
        )
        assert ok and cfg.value(*key) == [["Map to vJoy", True]]
    finally:
        cfg.set(*key, before)


def test_restored_profile_copies_never_overwrite(tmp_path: Path) -> None:
    from gremlin import history_profile

    entry = {
        "at": time.time(),
        "subject": {"profile": str(tmp_path / "My.xml")},
        "before": {"packed": history_profile.pack_text("<profile>B</profile>")},
        "after": {"packed": history_profile.pack_text("<profile>A</profile>")},
    }
    history_model._restore_profile(entry, entry["before"], "before")
    history_model._restore_profile(entry, entry["after"], "after")
    history_model._restore_profile(entry, entry["after"], "after")
    texts = sorted(
        p.read_text(encoding="utf-8-sig") for p in tmp_path.glob("My (history*")
    )
    assert texts == [
        "<profile>A</profile>", "<profile>A</profile>", "<profile>B</profile>"
    ]


def test_history_close_writes_at_once(area_file: Path) -> None:
    history.flush()
    history._closing = True
    try:
        history.record("settings", "Changed x", {}, 1, 2)
        assert any(e["title"] == "Changed x" for e in history._lines("settings"))
    finally:
        history._closing = False


def test_remembered_choices_are_registered_at_start() -> None:
    cfg = config.Configuration()
    for name in ("live-log-tab", "live-log-file", "live-log-level",
                 "button-map-options-group"):
        assert cfg.exists("global", "internal", name), name


def test_hidhide_picture_links_are_not_a_user_change() -> None:
    assert "module-links" in config.Configuration._HIDHIDE_PLACES


_AUTOLOAD = backend.Backend.klass._active_process_changed_cb


def _fake(open_path: object) -> types.SimpleNamespace:
    calls: list = []
    return types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *key: True),
        profile=types.SimpleNamespace(
            fpath=open_path, has_unsaved_changes=lambda: False
        ),
        gremlinActive=True,
        _autoload_held=None,
        activate_gremlin=lambda on: calls.append(("active", on)),
        loadProfile=lambda path: calls.append(("load", path)),
        calls=calls,
    )


def test_auto_load_leaves_the_open_profile_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    game = tmp_path / "game.xml"
    game.write_text("<profile/>")
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(game))
    fake = _fake(Path(game))
    for _ in range(3):
        _AUTOLOAD(fake, "C:/x/game.exe")
    assert fake.calls == []


def test_auto_load_with_a_missing_profile_runs_nothing_else(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    gone = tmp_path / "gone.xml"
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(gone))
    fake = _fake(tmp_path / "open.xml")
    fake.gremlinActive = False
    notes: list = []

    def note(*args: str) -> None:
        notes.append(args)

    backend.signal.showNotification.connect(note)
    try:
        _AUTOLOAD(fake, "C:/x/game.exe")
        _AUTOLOAD(fake, "C:/x/game.exe")
    finally:
        backend.signal.showNotification.disconnect(note)
    assert fake.calls == []
    assert len(notes) == 1


def test_a_failed_save_as_keeps_the_profile_on_its_file(tmp_path: Path) -> None:
    from gremlin.profile import Profile

    first = tmp_path / "first.xml"
    fake = types.SimpleNamespace(
        profile=Profile(),
        windowTitleChanged=types.SimpleNamespace(emit=lambda: None),
        _record_profile_use=lambda path: None,
    )
    fake.profile.fpath = first
    folder = tmp_path / "adir.xml"
    folder.mkdir()
    assert not backend.Backend.klass.saveProfile(fake, folder.as_uri())
    assert fake.profile.fpath == first
