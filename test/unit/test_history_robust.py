# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""History holds up against damaged entries and failed writes.

- 08 S21: a line that is valid JSON but has a bad field (an "at" that isn't
  a time, a subject that isn't an object, a group's parts that aren't a
  list, a side of the wrong type) is skipped like a cut line; the rest of
  the list still shows and every row can be opened (SHAKE-DAMAGE-02).
- A kept copy cut short by a crash is written again the next time the same
  content is kept, and a short copy is never put back (AUD-FILES-04).
- A module file Restore whose module write fails leaves the device's
  pictures as they were (AUD-FILES-05).
- AD6: Restore of a whole profile writes only into the profiles folder or
  the folder the profile is still in; anywhere else it asks first and
  writes nothing until the user says yes (SHAKE-DAMAGE-07).
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history, history_modules, history_profile, util
from gremlin.modules import store as module_store
from gremlin.ui import history_model
from test.unit import test_stage1_modules
from test.unit._device_folders import ensure_dir, picture_file, put_picture

_app = test_stage1_modules._app


@pytest.fixture
def hist(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    test_stage1_modules.settle_history()
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    monkeypatch.setattr(history, "_kept_now", set(), raising=False)
    monkeypatch.setattr(history_modules, "_last_pictures", {})
    yield folder
    test_stage1_modules.settle_history()


def _entry(**fields: object) -> dict:
    entry = {
        "id": uuid.uuid4().hex,
        "at": 1_700_000_000.0,
        "area": "modules",
        "kind": "save",
        "title": "Saved Stick",
        "subject": {"fileName": "stick.json"},
        "before": {"text": "{}"},
        "after": {"text": "{}"},
    }
    entry.update(fields)
    return entry


def _write(folder: Path, area: str, entries: list[dict]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / f"{area}.jsonl", "a", encoding="utf-8", newline="") as out:
        for entry in entries:
            out.write(json.dumps(entry) + "\n")


def _role(model: history_model.HistoryModel, row: int, name: str) -> object:
    role = (
        history_model._ROLES.index(name)
        + 1
        + int(history_model.QtCore.Qt.ItemDataRole.UserRole)
    )
    return model.data(model.index(row, 0), role)


# --- 08 S21: a bad field is a damaged line -----------------------------------

_BAD = {
    "at text": {"at": "abc"},
    "at list": {"at": [1]},
    "at huge": {"at": 1e300},
    "at not a number": {"at": float("nan")},
    "subject text": {"subject": "abc"},
    "id number": {"id": 7},
    "group parts text": {"kind": "group", "before": "abc", "after": []},
    "group part not object": {"kind": "group", "before": ["x"], "after": ["y"]},
    "group part subject text": {
        "kind": "group",
        "before": [{"area": "modules", "subject": "abc", "side": None}],
        "after": [{"area": "modules", "subject": "abc", "side": None}],
    },
}


@pytest.mark.parametrize("bad", list(_BAD), ids=list(_BAD))
def test_a_line_with_a_bad_field_is_skipped_and_the_rest_read(
    hist: Path, bad: str
) -> None:
    good = _entry(title="Good one")
    _write(hist, "modules", [_entry(**_BAD[bad]), good])
    assert [e["id"] for e in history.entries()] == [good["id"]]
    model = history_model.HistoryModel()
    model.reload()
    assert model.rowCount() == 1
    assert _role(model, 0, "title") == "Good one"


@pytest.mark.parametrize("depth", [100, 100_000], ids=["deep", "too deep to read"])
def test_a_deeply_nested_line_is_skipped_and_the_rest_read(
    hist: Path, depth: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(history, "_limits", lambda: (100_000, 20))
    good = _entry(title="Good one")
    nested = "[" * depth + "]" * depth
    deep = json.dumps(_entry(after="X")).replace('"X"', nested)
    hist.mkdir(parents=True)
    (hist / "modules.jsonl").write_text(
        deep + "\n" + json.dumps(good) + "\n", encoding="utf-8"
    )
    assert [e["id"] for e in history.entries()] == [good["id"]]
    model = history_model.HistoryModel()
    model.reload()
    assert model.rowCount() == 1
    history.prune()  # the clean-up walks every line too
    assert [e["id"] for e in history.entries()] == [good["id"]]


# Lines whose sides are the wrong type for their kind: the list still shows
# and every row and its detail can be read (none raises).
_ODD_SIDES = {
    "module side text": _entry(before="abc", after="abc"),
    "module parts text": _entry(subject={"fileName": "s.json", "parts": "abc"}),
    "module parts number": _entry(subject={"fileName": "s.json", "parts": 5}),
    "settings side text": _entry(area="settings", before="abc", after=["x"]),
    "profile side text": _entry(area="profile", kind="profile", before="abc"),
    "profile packed bad": _entry(
        area="profile", kind="profile", before={"packed": "not base64 !"}
    ),
    "input side text": _entry(area="profile", kind="input", before="abc"),
    "input actions text": _entry(
        area="profile", kind="input", before={"input": "<input/>", "actions": 5}
    ),
    "library side text": _entry(kind="library", before="abc", after=7),
    "group side text": _entry(
        kind="group",
        before=[{"area": "modules", "kind": "save", "subject": {}, "side": "abc"}],
        after=[{"area": "modules", "kind": "save", "subject": {}, "side": 5}],
    ),
}


def test_rows_with_sides_of_the_wrong_type_can_still_be_read(hist: Path) -> None:
    _write(hist, "modules", list(_ODD_SIDES.values()))
    model = history_model.HistoryModel()
    model.reload()
    # Changes to the same thing fold into one row (D-TESTLIST-1): open them.
    for row in range(model.rowCount()):
        if _role(model, row, "groupSize") > 1 and not _role(model, row, "groupOpen"):
            model.toggleGroup(str(_role(model, row, "groupKey")))
    assert model.rowCount() == len(_ODD_SIDES)
    for row in range(model.rowCount()):
        for name in history_model._ROLES:
            _role(model, row, name)
        shown = json.loads(model.detail(str(_role(model, row, "entryId"))))
        assert shown["title"]


def test_a_time_out_of_range_shows_no_time() -> None:
    assert history_model._when(1e300) == ""
    assert history_model._when(float("inf")) == ""


# --- AUD-FILES-04: a cut-short kept copy ---------------------------------------


def test_a_cut_short_kept_copy_is_written_again(hist: Path, tmp_path: Path) -> None:
    photo = tmp_path / "photo.png"
    photo.write_bytes(b"the whole picture")
    name = hashlib.sha1(b"the whole picture").hexdigest() + ".png"
    files = hist / "files"
    files.mkdir(parents=True)
    # A crash mid-write left half of it under the right name.
    (files / name).write_bytes(b"the who")
    assert history.keep_file(photo) == name
    assert (files / name).read_bytes() == b"the whole picture"
    assert not list(files.glob("*.tmp"))


def test_a_cut_short_kept_copy_is_never_put_back(hist: Path, tmp_path: Path) -> None:
    name = hashlib.sha1(b"the whole picture").hexdigest() + ".png"
    files = hist / "files"
    files.mkdir(parents=True)
    (files / name).write_bytes(b"the who")
    assert history.kept_file(name) is None
    dest = tmp_path / "back.png"
    assert not history.restore_file(name, dest)
    assert not dest.exists()


# --- AUD-FILES-05: failed module write leaves the pictures --------------------


def test_a_failed_module_write_leaves_the_pictures_as_they_were(
    hist: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    modules = tmp_path / "modules"
    modules.mkdir()
    monkeypatch.setattr(util, "modules_dir", lambda: modules)
    folder = ensure_dir(modules, "Pic Stick")
    put_picture(modules, "Pic Stick", "photo.png", b"today's photo")
    photo = picture_file(modules, "Pic Stick", "photo.png")
    other = picture_file(modules, "Pic Stick", "new.png")  # not there today
    source = tmp_path / "old.png"
    source.write_bytes(b"the old photo")
    kept = history.keep_file(source)
    path = folder / "module.json"
    path.write_text('{"device": "Pic Stick"}', encoding="utf-8")

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(module_store, "write_text", refuse)
    entry = {
        "subject": {
            "device": "Pic Stick",
            "deviceId": "name:pic_stick",
            "folder": folder.name,
            "file": str(path),
            "fileName": f"{folder.name}/module.json",
        }
    }
    # One ref as History kept it before device folders, one as today.
    side = {
        "text": '{"device": "Pic Stick", "image": "pic_stick/photo.png"}',
        "pictures": [
            {"ref": "pic_stick/photo.png", "keptFile": kept},
            {"ref": "pictures/new.png", "keptFile": kept},
        ],
    }
    ok, message = history_model._restore_module(entry, side)
    assert not ok
    assert "could not be put back" in message
    assert photo.read_bytes() == b"today's photo"
    assert not other.exists()
    assert path.read_text(encoding="utf-8") == '{"device": "Pic Stick"}'


# --- AD6: where a profile Restore may write -----------------------------------


def _profile_entry(profile: Path) -> dict:
    return _entry(
        area="profile",
        kind="profile",
        title=f"Saved {profile.name}",
        subject={"profile": str(profile), "profileName": profile.name},
        before={"packed": history_profile.pack_text("<profile/>")},
        after={"packed": history_profile.pack_text("<profile/>")},
    )


@pytest.fixture
def profiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    folder = tmp_path / "profiles"
    folder.mkdir()
    monkeypatch.setattr(util, "profiles_dir", lambda: folder)
    return folder


def test_a_profile_restore_into_the_profiles_folder_writes(
    hist: Path, profiles: Path
) -> None:
    entry = _profile_entry(profiles / "gone.xml")  # deleted since: still fine
    _write(hist, "profile", [entry])
    result = history_model.restore(entry["id"], "before")
    assert result["ok"], result
    assert len(list(profiles.glob("gone (history *before).xml"))) == 1


def test_a_profile_restore_next_to_the_profile_where_it_still_is_writes(
    hist: Path, profiles: Path, tmp_path: Path
) -> None:
    elsewhere = tmp_path / "my games"
    elsewhere.mkdir()
    (elsewhere / "dcs.xml").write_text("<profile/>", encoding="utf-8")
    entry = _profile_entry(elsewhere / "dcs.xml")
    _write(hist, "profile", [entry])
    result = history_model.restore(entry["id"], "after")
    assert result["ok"], result
    assert len(list(elsewhere.glob("dcs (history *after).xml"))) == 1


def test_a_profile_restore_anywhere_else_asks_and_writes_nothing(
    hist: Path, profiles: Path, tmp_path: Path
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    entry = _profile_entry(outside / "victim.xml")  # no such profile there
    _write(hist, "profile", [entry])
    result = history_model.restore(entry["id"], "before")
    assert not result["ok"]
    assert result.get("ask") is True
    assert str(outside) in result["message"]
    assert list(outside.iterdir()) == []
    # Through the window's slots: asked first, written only after the OK.
    model = history_model.HistoryModel()
    asked = json.loads(model.restore(entry["id"], "before"))
    assert asked.get("ask") is True and list(outside.iterdir()) == []
    done = json.loads(model.restoreOutside(entry["id"], "before"))
    assert done["ok"], done
    assert len(list(outside.glob("victim (history *before).xml"))) == 1
