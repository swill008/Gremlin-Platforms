# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Saving and History (audit 2, group F).

- A deleted device's photo survives the start-of-session History clean-up,
  and Restore says which pictures it couldn't put back.
- History has an entry only for a write that happened; a line or paragraph
  separator in a name no longer loses the entry; Restore writes into the
  modules folder of today.
- Auto-load: a game whose profile file is missing stops the open profile
  (unless it is set to keep running).
- Quit to install carries on when the settings can't be saved.
- The installed program's error reports are written as UTF-8.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import time
import types
from collections.abc import Iterator
from pathlib import Path

sys.path.append(".")

import pytest

from gremlin import config, history, history_modules, util
from gremlin.modules import module_file
from gremlin.modules import store as module_store
from gremlin.ui import backend, history_model, update_model

_ROOT = pathlib.Path(__file__).parents[2]


def _settle() -> list[dict]:
    deadline = time.monotonic() + 5
    while history._writer is not None and time.monotonic() < deadline:
        time.sleep(0.02)
    return history.entries()


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(history, "_kept_now", set(), raising=False)
    yield folder
    _settle()


def test_a_deleted_device_keeps_its_photo_through_the_first_clean_up(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    modules = util.modules_dir()
    (modules / "gone_stick").mkdir(parents=True, exist_ok=True)
    photo = modules / "gone_stick" / "photo.png"
    photo.write_bytes(b"the photo")
    path = modules / "gone_stick.json"
    module_file.write_json(
        path, {"device": "Gone Stick", "image": "gone_stick/photo.png"}
    )
    _settle()
    # A photo no entry has a copy of yet (a new one, not saved since).
    photo.write_bytes(b"the new photo")
    # A new session: the delete is its first History change.
    monkeypatch.setattr(history, "_pruned", False)
    monkeypatch.setattr(history, "_kept_now", set(), raising=False)
    history_modules.note_delete(path)
    path.unlink()
    photo.unlink()
    entry = _settle()[0]
    assert entry["title"] == "Deleted the module file of Gone Stick"
    result = history_model.restore(entry["id"], "before")
    assert result["ok"], result
    assert result["message"] == "Put back gone_stick.json."
    assert photo.read_bytes() == b"the new photo"


def test_restore_names_the_pictures_it_could_not_put_back(store: Path) -> None:
    modules = util.modules_dir()
    modules.mkdir(parents=True, exist_ok=True)
    entry = {
        "subject": {
            "file": str(modules / "lost_stick.json"),
            "fileName": "lost_stick.json",
        },
    }
    side = {
        "text": '{"device": "Lost Stick"}',
        "pictures": [{"ref": "lost_stick/photo.png", "keptFile": "missing.png"}],
    }
    ok, message = history_model._restore_module(entry, side)
    assert ok
    assert "lost_stick/photo.png" in message
    (modules / "lost_stick.json").unlink()


def test_restore_writes_into_the_modules_folder_of_today(
    store: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    moved = tmp_path / "moved modules"
    moved.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: moved)
    old = tmp_path / "old modules" / "moved_stick.json"
    entry = {"subject": {"file": str(old), "fileName": "moved_stick.json"}}
    ok, _ = history_model._restore_module(entry, {"text": "{}", "pictures": []})
    assert ok
    assert (moved / "moved_stick.json").is_file()
    assert not old.exists()


def _lock_the_file(m: pytest.MonkeyPatch) -> None:
    """The file is locked: the swap is refused and so is the direct write the
    safe writer falls back to (GL-068). The temporary copy can be written."""

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("locked")

    real = Path.write_bytes

    def write_bytes(self: Path, data: bytes) -> int:
        if self.name.endswith(".tmp"):
            return real(self, data)
        raise OSError("locked")

    m.setattr(module_file.os, "replace", refuse)
    m.setattr(Path, "write_bytes", write_bytes)


def test_a_save_that_failed_is_no_history_entry(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    modules = util.modules_dir()
    modules.mkdir(parents=True, exist_ok=True)
    path = modules / "locked_stick.json"
    module_file.write_json(path, {"device": "Locked Stick"})
    count = len(_settle())

    with monkeypatch.context() as m, pytest.raises(OSError):
        _lock_the_file(m)
        module_file.write_text(path, '{"device": "Locked Stick", "x": 1}')
    assert len(_settle()) == count
    # The temporary copy goes too when the direct write fails.
    assert not path.with_name(path.name + ".tmp").exists()


def test_an_import_write_that_failed_is_no_history_entry(
    store: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    modules = util.modules_dir()
    modules.mkdir(parents=True, exist_ok=True)
    path = modules / "import_stick.json"
    module_file.write_json(path, {"device": "Import Stick"})
    count = len(_settle())

    with monkeypatch.context() as m, pytest.raises(OSError):
        _lock_the_file(m)
        module_store.replace(path, b'{"device": "Import Stick", "x": 1}', force=True)
    assert len(_settle()) == count
    module_store.replace(path, b'{"device": "Import Stick", "x": 1}', force=True)
    assert len(_settle()) == count + 1


def test_a_line_separator_in_a_name_keeps_the_entry(store: Path) -> None:
    history.record("settings", "Renamed A\u2028B\u2029C\x85D", {}, None, None)
    assert [e["title"] for e in _settle()] == ["Renamed A\u2028B\u2029C\x85D"]


# Backend is a singleton wrapper; the method lives on the class inside it.
_AUTOLOAD = backend.Backend.klass._active_process_changed_cb


@pytest.mark.parametrize("keep_running", [False, True])
def test_a_missing_auto_load_profile_stops_the_open_one(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, keep_running: bool
) -> None:
    gone = tmp_path / "gone.xml"
    monkeypatch.setattr(config, "get_profile_with_regex", lambda path: str(gone))
    calls: list = []
    settings = {
        ("profile", "automation", "enable-auto-loading"): True,
        ("profile", "automation", "remain-active-on-focus-loss"): keep_running,
    }
    fake = types.SimpleNamespace(
        config=types.SimpleNamespace(value=lambda *key: settings[key]),
        profile=types.SimpleNamespace(
            fpath="open.xml", has_unsaved_changes=lambda: False
        ),
        gremlinActive=True,
        _autoload_held=None,
        activate_gremlin=lambda on: calls.append(("active", on)),
        loadProfile=lambda path: calls.append(("load", path)),
    )
    _AUTOLOAD(fake, "C:/x/game.exe")  # pyright: ignore[reportArgumentType]
    assert calls == ([] if keep_running else [("active", False)])


def test_quit_to_install_carries_on_when_settings_cannot_be_saved(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from PySide6 import QtCore

    from gremlin import updater

    monkeypatch.setattr(updater, "updates_dir", lambda: tmp_path)
    started: list = []
    monkeypatch.setattr(
        QtCore.QProcess, "startDetached", lambda *args: started.append(args) or True
    )
    setup = tmp_path / "Gremlin-Platforms-R1-9.9.9-Setup.exe"
    setup.write_bytes(b"x")
    model = update_model.UpdateModel()
    model._ready_path = setup
    model.setInstallOnExit(True)

    def locked(*_args: object) -> None:
        raise PermissionError("configuration.json is read-only")

    monkeypatch.setattr(model._config, "save_now", locked)
    # The scheduled save (a timer in the program; at once in tests).
    monkeypatch.setattr(model._config, "save", lambda *args: None)
    assert model.start_pending_install() is True
    assert started


_STDERR_SCRIPT = r"""
import sys
sys.path.insert(0, ".")
from pathlib import Path
folder = Path(sys.argv[1])
sys.stderr = None  # the installed program has no console stream
from gremlin import qt_log, threads
assert qt_log.install(folder, cap=5_000_000, limit=100)
print("Путь C:/Игры 日本語", file=sys.stderr, flush=True)
left = threads.shutdown(timeout=3.0)
print("LEFT", left, flush=True)
"""


def test_error_reports_keep_non_english_text(tmp_path: Path) -> None:
    done = subprocess.run(
        [sys.executable, "-c", _STDERR_SCRIPT, str(tmp_path)],
        cwd=_ROOT,
        capture_output=True,
        timeout=60,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    assert b"LEFT []" in done.stdout, done.stdout + done.stderr
    text = (tmp_path / "qt.log").read_text(encoding="utf-8")
    assert "Путь C:/Игры 日本語" in text


# --- 05 S34 (GL-104): saving with the action pane open -----------------------


def test_a_save_with_the_pane_open_leaves_the_draft_alone(tmp_path: Path) -> None:
    import uuid

    from gremlin import plugin_manager, shared_state
    from gremlin.profile import Profile
    from gremlin.types import InputType
    from gremlin.ui.binding_catalog import BindingCatalogModel

    stick = uuid.UUID("12121212-3434-5656-7878-909090909090")
    profile = Profile()
    before, shared_state.current_profile = shared_state.current_profile, profile
    try:
        item = profile.get_input_item(
            stick, InputType.JoystickAxis, 1, "Default", create_if_missing=True
        )
        root = item.add_item_binding().root_action
        manager = plugin_manager.PluginManager()
        root.insert_action(
            manager.create_instance("Merge Axis", InputType.JoystickAxis), "children"
        )  # unfinished: no axes yet
        note = manager.create_instance("Description", InputType.JoystickAxis)
        note.description = "on the input"
        root.insert_action(note, "children")

        model = BindingCatalogModel()
        model._control_spec = lambda _i: (
            profile, stick, InputType.JoystickAxis, 1, "Default",
            profile.get_input_item(stick, InputType.JoystickAxis, 1, "Default"),
        )
        model.beginPane(0, 0)
        pane_root = model._pane_shadow.action_sequences[0].root_action
        pane_root.get_actions()[0][1].description = "in the pane"

        profile.to_xml(tmp_path / "while_open.xml")  # File > Save
        kids = pane_root.get_actions()[0]
        assert [a.tag for a in kids] == ["merge-axis", "description"]
        assert all(profile.library.has_action(a.id) for a in kids)
        assert "in the pane" not in (tmp_path / "while_open.xml").read_text(
            encoding="utf-8"
        )

        assert model.commitPane() == 0  # OK after the save still writes
        model.endPane()
        item = profile.get_input_item(stick, InputType.JoystickAxis, 1, "Default")
        assert item is not None
        tags = [a.tag for a in item.action_sequences[0].root_action.get_actions()[0]]
        assert tags == ["merge-axis", "description"]
        model.deleteLater()
    finally:
        shared_state.current_profile = before
