# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 S94 (Q14): while a profile has unsaved changes a recovery copy is kept
about every minute; the next open of that profile (or a start after a crash)
offers Restore / Discard / Not now; Save, Discard and a clean close remove
it. The module on real profiles here; the real program off-screen with real
clicks in profile_recovery_smoke.py."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
from pathlib import Path

import pytest

from gremlin import profile_recovery
from gremlin.profile import Profile

_HERE = pathlib.Path(__file__).parent


@pytest.fixture
def keeper(tmp_path: Path) -> profile_recovery.ProfileRecovery:
    return profile_recovery.ProfileRecovery(lambda: tmp_path / "recovery")


def _saved_profile(path: Path) -> Profile:
    p = Profile()
    p.mark_clean()
    p.to_xml(path)
    opened = Profile()
    opened.from_xml(path)
    return opened


def _edit(p: Profile, mode: str) -> None:
    p.modes.add_mode(mode)
    p.note_edit()


def test_kept_about_every_minute() -> None:
    assert 30 <= profile_recovery.INTERVAL_SECONDS <= 90


def test_nothing_unsaved_keeps_no_copy(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    p = _saved_profile(tmp_path / "a.xml")
    keeper.tick(p)
    assert not keeper.file_for(p.fpath).exists()
    untitled = Profile()
    untitled.mark_clean()
    keeper.tick(untitled)
    assert not keeper.file_for(None).exists()


def test_unsaved_edits_are_kept_and_undoing_them_removes_the_copy(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    p = _saved_profile(tmp_path / "a.xml")
    _edit(p, "Combat")
    keeper.tick(p)
    copy = keeper.file_for(p.fpath)
    doc = json.loads(copy.read_text(encoding="utf-8"))
    assert "Combat" in doc["xml"] and doc["path"] == str(p.fpath) and doc["savedAt"]
    # Its own copy is no crash's: not offered in this session.
    assert keeper.offer_for(p.fpath) is None
    p.modes.delete_mode("Combat")
    p.note_edit()
    keeper.tick(p)
    assert not copy.exists()


def test_one_file_per_profile_path_and_untitled(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    a, b = keeper.file_for(tmp_path / "a.xml"), keeper.file_for(tmp_path / "b.xml")
    assert a != b and a.parent == b.parent == tmp_path / "recovery"
    assert keeper.file_for(str(tmp_path / "A.XML")) == a
    assert keeper.file_for(None).name == "profile-untitled.json"
    untitled = Profile()
    untitled.mark_clean()
    _edit(untitled, "Draft")
    keeper.tick(untitled)
    assert "Draft" in keeper.file_for(None).read_text(encoding="utf-8")


def test_save_and_a_clean_close_remove_the_copy(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    p = _saved_profile(tmp_path / "a.xml")
    _edit(p, "Combat")
    keeper.tick(p)
    keeper.saved(p.fpath)
    assert not keeper.file_for(p.fpath).exists()
    _edit(p, "Other")
    keeper.tick(p)
    assert keeper.file_for(p.fpath).exists()
    keeper.forget_session()
    assert not keeper.file_for(p.fpath).exists()


def _crash_copy(tmp_path: Path, path: Path | None, mode: str) -> None:
    """Another session's copy, left by a crash."""
    crashed = Profile()
    if path is not None:
        crashed.from_xml(path)
    else:
        crashed.mark_clean()
    _edit(crashed, mode)
    profile_recovery.ProfileRecovery(lambda: tmp_path / "recovery").tick(crashed)


def test_a_crash_copy_is_offered_and_restore_makes_it_unsaved(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    path = tmp_path / "a.xml"
    opened = _saved_profile(path)
    _crash_copy(tmp_path, path, "Recovered")
    offer = keeper.offer_for(path)
    assert offer is not None and offer["name"] == "a.xml" and offer["savedAt"]
    restored = keeper.restore(path, opened)
    assert isinstance(restored, Profile)
    assert restored.modes.mode_exists("Recovered")
    assert Path(str(restored.fpath)) == path
    assert restored.has_unsaved_changes() and restored.looks_unsaved()
    # The file itself is untouched until Save.
    assert "Recovered" not in path.read_text(encoding="utf-8-sig")


def test_untitled_crash_copy_restores_as_untitled(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    _crash_copy(tmp_path, None, "Draft")
    offer = keeper.offer_for(None)
    assert offer is not None and offer["name"] == "Untitled" and offer["path"] == ""
    fresh = Profile()
    fresh.mark_clean()
    restored = keeper.restore(None, fresh)
    assert isinstance(restored, Profile)
    assert restored.fpath is None and restored.modes.mode_exists("Draft")
    assert restored.has_unsaved_changes()


def test_not_now_keeps_the_copy_and_discard_deletes_it(
    keeper: profile_recovery.ProfileRecovery, tmp_path: Path
) -> None:
    path = tmp_path / "a.xml"
    _saved_profile(path)
    _crash_copy(tmp_path, path, "Recovered")
    # Not now: nothing is done; a clean close leaves a copy it didn't write.
    keeper.forget_session()
    assert keeper.offer_for(path) is not None
    keeper.discard(path)
    assert keeper.offer_for(path) is None
    assert not keeper.file_for(path).exists()


# --- the real program off-screen --------------------------------------------


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("profile_recovery_home")
    (home / "Gremlin Platforms").mkdir()
    proc = subprocess.run(
        [sys.executable, str(_HERE / "profile_recovery_smoke.py")],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=150,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ,
            "USERPROFILE": str(home),
            "QT_QPA_PLATFORM": "offscreen",
            "PYTHONUNBUFFERED": "1",
        },
    )
    results: dict = {"errors": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
        elif line.startswith("ERROR"):
            results["errors"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


_TEXT = (
    "The profile Flight.xml has edits from {when} that were never saved, "
    "probably because the program closed unexpectedly.\n\n"
    "Restore opens them; save to keep them. Discard deletes them."
)


def _check_offer(shown: dict) -> None:
    assert shown["open"] is True
    assert shown["title"] == "Unsaved Edits Found"
    assert shown["buttons"] == ["Restore", "Discard", "Not now"]
    head, _, tail = _TEXT.partition("{when}")
    assert shown["text"].startswith(head) and shown["text"].endswith(tail)
    assert " at " in shown["text"]


def test_app_runs_without_errors(run: dict) -> None:
    assert run["errors"] == []


def test_app_start_after_a_crash_offers_and_restore_is_unsaved(run: dict) -> None:
    assert run["copy-before-start"] is True
    _check_offer(run["start-offer"])
    assert run["restore-clicked"] is True
    restored = run["restored"]
    assert restored["mode"] is True and restored["unsaved"] is True
    assert restored["path"].endswith("Flight.xml")
    assert restored["title"].startswith("* Flight.xml - Gremlin-Platforms R1 ")


def test_app_keeps_edits_and_save_removes_the_copy(run: dict) -> None:
    assert run["edit-kept"] is True
    assert run["save-ok"] is True
    assert run["after-save"] is False
    assert run["clean-no-copy"] is False


def test_app_discard_then_new_removes_the_copy(run: dict) -> None:
    assert run["edit-again-kept"] is True
    assert run["after-new"] is False


def test_app_open_offers_not_now_keeps_discard_deletes(run: dict) -> None:
    _check_offer(run["open-offer"])
    assert run["notnow-clicked"] is True
    assert run["after-notnow"] == {"copy": True, "mode": False, "unsaved": False}
    assert run["again-offer"] is True
    assert run["discard-clicked"] is True
    assert run["after-discard"] == {"copy": False, "mode": False, "unsaved": False}


def test_app_clean_close_removes_the_copy(run: dict) -> None:
    assert run["closing-kept"] is True
    assert run["after-close"] is False
