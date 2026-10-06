# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Button Map safety net (Stage 1): GL-019, GL-020, GL-021.

Spec: claude/program-map/07-button-map.md (section 8, decided by section 9).

GL-019 (07-T2), the window driven as the user drives it, in the running
program off-screen (stage1_button_map_smoke.py, its own process and user
folder): Save says so and reads back (S20, S24); Cancel asks when there are
changes, Save there saves and leaves Edit, Discard keeps the file and leaves
no undo (S25, S26, S19); closing with unsaved edits asks once (S28); the
recovery copy is written, removed when undone, offered with Restore /
Discard / Not now, quietly dropped when it equals the saved map, put off
when another device shows, never written more often than every 10 seconds
(S32-S35, S37); Copy Button Map from Device (S75-S77); Choose Photo and
Clear Photo, then Cancel (S26, S40, S41).

GL-020 (07-T3): the module file changed elsewhere while the map is open
(History Restore, Module Setup's photo, a Device Pack import), Delete Device
in the middle of an edit, a copy onto a device with fewer controls.

GL-021 (07-T4): Clear Photo when the file is open elsewhere (S41), the
picture folder and a read-only install folder, the pool of an unplugged
device (S46), other devices' damaged module files (S75).

Known gaps, written for the spec and marked xfail(strict) until fixed:
GL-071 (outside changes, 07 Q6), GL-173 (print area and guides, 07 Q1),
GL-174 (Choose Photo waits for Save, 07 Q2), GL-175 (no module file made by
a guide change, S29), GL-176 (Delete Device mid-edit, 07 Q7), GL-178 (no
folder in the install folder, 07 Q13), GL-182 (chips for controls the device
lacks, 07 Q8).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import types
import uuid

import pytest

from gremlin.types import InputType
from gremlin.ui import hardware_profile, input_pairing, module_model

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "stage1_button_map_smoke.py"


def _run(part: str, home: pathlib.Path) -> dict:
    """One part of the window smoke, in its own process and user folder."""
    (home / "Gremlin Platforms").mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        QT_QPA_FONTDIR=os.environ.get(
            "QT_QPA_FONTDIR",
            os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
        ),
        PYTHONIOENCODING="utf-8",
    )
    done = subprocess.run(
        [sys.executable, str(_SMOKE), part],
        cwd=_ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=240,
    )
    # The smoke not getting through is RuntimeError, so a strict xfail
    # (raises=AssertionError) never takes it for the known gap.
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        raise RuntimeError(done.stdout[-2000:] + done.stderr[-2000:])
    out = json.loads(lines[-1][len("RESULT "):])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    return out


@pytest.fixture(scope="module")
def flows(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run("flows", tmp_path_factory.mktemp("bm_flows"))


@pytest.fixture(scope="module")
def outside(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return _run("outside", tmp_path_factory.mktemp("bm_outside"))


# +-------------------------------------------------------------------------
# | GL-019: Save, Cancel, leave prompts


def test_save_writes_reads_back_and_says_so(flows: dict) -> None:
    # S19: entering Edit is no change; S20, S24.
    assert flows["dirty-on-entering-edit"] is False
    assert flows["save-said"] == ["Saved", "Saved to the module file."]
    assert flows["save-wrote"] is True
    assert flows["dirty-after-save"] is False
    assert flows["editing-after-save"] is True


def test_cancel_with_changes_asks_and_discard_keeps_the_file(flows: dict) -> None:
    # S25, S26: the question, then nothing written and no undo left.
    assert flows["cancel-asks"] == [True, "Unsaved Changes", "cancel"]
    assert flows["cancel-discard"] == {
        "editing": False, "file-kept": True, "shown": True, "can-undo": False,
    }


def test_save_in_the_cancel_question_saves_and_leaves_edit(flows: dict) -> None:
    assert flows["cancel-save"] == {"editing": False, "written": True}


def test_cancel_without_changes_does_not_ask(flows: dict) -> None:
    assert flows["cancel-clean"] == [False, False]


def test_closing_with_unsaved_edits_asks_once(flows: dict) -> None:
    # S28: asked, still open; Discard then finishes the close.
    assert flows["close-asks"] == [True, "close", True]
    assert flows["close-discard"] == {"closed": True, "file-kept": True}


# +-------------------------------------------------------------------------
# | GL-019: photo


def test_choose_photo_then_cancel_puts_the_starting_photo_back(flows: dict) -> None:
    # S26, S40.
    chosen = flows["choose-photo"]
    assert chosen["shown"].endswith("/photo.jpg")
    assert chosen["dirty"] is True
    back = flows["choose-photo-cancel"]
    assert back["file-image"] == back["start-image"]
    assert back["shown"] == back["start-image"]
    assert back["old-photo"] is True
    assert back["new-photo"] is False


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-174: Choose Photo writes the module file and History at once;"
    " Cancel adds a second entry",
)
def test_choose_photo_writes_nothing_until_save(flows: dict) -> None:
    # 07 Q2, S29: the new photo waits beside the old one; nothing in the
    # module file or History until Save.
    chosen = flows["choose-photo"]
    assert chosen["file-image-before-save"] == chosen["start-image"]
    assert chosen["history-before-save"] == 0
    assert flows["choose-photo-cancel"]["history-after-cancel"] == 0


def test_choose_photo_then_save_is_one_history_entry(flows: dict) -> None:
    saved = flows["choose-photo-save"]
    assert saved["file-image"].endswith("/photo.jpg")
    assert saved["after-save"] == 1


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-174: the History entry is made by Choose Photo, not by Save"
)
def test_the_photo_history_entry_comes_with_save(flows: dict) -> None:
    assert flows["choose-photo-save"]["before-save"] == 0


def test_clear_photo_then_cancel_brings_it_back_without_history(flows: dict) -> None:
    # S26, S41: an unsaved change; Cancel puts the photo back.
    assert flows["clear-photo-ran"] is True
    assert flows["clear-photo"]["dirty"] is True
    assert flows["clear-photo"]["history-before-save"] == 0
    back = flows["clear-photo-cancel"]
    assert back["photo-back"] is True
    assert back["history"] == 0
    assert back["file-image"].endswith("/photo.jpg")


def test_clear_photo_failure_keeps_the_photo_and_says_so(flows: dict) -> None:
    # S41 (GL-021): the file is open elsewhere.
    failed = flows["clear-photo-fails"]
    assert failed["said"] == [True, "Clear Photo Failed"]
    assert failed["photo-kept"] is True
    assert failed["shown"].endswith("/photo.jpg")
    assert failed["after-cancel"] is True


# +-------------------------------------------------------------------------
# | GL-019: print area and guides


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-173: print area and guides are written mid-edit and Cancel keeps them",
)
def test_cancel_takes_back_print_area_and_guides(flows: dict) -> None:
    # 07 Q1 (decided): part of the edit; Save writes, Cancel takes back.
    before = flows["ui-before"]
    assert flows["ui-mid-edit"] == before
    assert flows["ui-after-cancel"] == before
    assert flows["ui-shown-after-cancel"] == before


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-175: a guide change in Edit creates the module file with the old map",
)
def test_guide_change_makes_no_module_file(flows: dict) -> None:
    # S29: the module file is written only on Save.
    assert flows["third-file-at-start"] is False
    assert flows["third-file-mid-edit"] is False
    assert flows["third-file-after-cancel"] is False


# +-------------------------------------------------------------------------
# | GL-019, GL-020: Copy Button Map from Device


def test_copy_lists_other_devices_and_skips_damaged_files(flows: dict) -> None:
    # S75; GL-021: a file that is not UTF-8, or not an object, is left out.
    assert flows["copy-list"] == ["Other Stick"]


def test_copy_mirror_tick_follows_device_or_template(flows: dict) -> None:
    # S76: ticked for a device, unticked for a template.
    assert flows["mirror-tick-device"] is True
    assert flows["mirror-tick-template"] is False


def test_copy_onto_fewer_controls_keeps_chips_saves_nothing_and_undoes(
    flows: dict,
) -> None:
    # S76, S77, 07 Q8 (keep them): Button 70 and 80 on a 64-button stick.
    copied = flows["copy"]
    assert copied["editing"] is True
    assert copied["hw-ids"] == [1, 2, 70, 80]
    assert copied["file-untouched"] is True
    assert copied["dirty"] is True
    assert flows["copy-undo"] is True


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-182: no notice of chips for controls the device does not have",
)
def test_copy_says_how_many_chips_the_device_lacks(flows: dict) -> None:
    # 07 Q8: "N chips are for controls this device does not have".
    wanted = "2 chips are for controls this device does not have"
    assert wanted in flows["copy"]["message"]


# +-------------------------------------------------------------------------
# | GL-019: recovery copies


def test_recovery_copies_never_more_often_than_every_10_seconds(flows: dict) -> None:
    assert flows["autosave-interval-at-1s"] == 10000  # S33


def test_recovery_copy_written_removed_when_undone_and_on_cancel(flows: dict) -> None:
    # S32.
    assert flows["copy-written"] is True
    assert flows["copy-gone-when-undone"] is True
    assert flows["copy-gone-after-cancel"] is True


def test_recovery_offer_not_now_restore_and_discard(flows: dict) -> None:
    # S34.
    assert flows["offer"] == [True, "Unsaved Edits Found", False]
    assert flows["not-now"] == [False, True]
    assert flows["offered-again"] is True
    assert flows["restore"] == {
        "editing": True, "edits-back": True, "dirty": True, "file-untouched": True,
    }
    assert flows["copy-gone-after-restore-cancel"] is True
    assert flows["discard"] == [False, False, True]


def test_a_copy_equal_to_the_saved_map_goes_quietly(flows: dict) -> None:
    # S37.
    assert flows["same-copy-written"] is True
    assert flows["same-copy-offered"] is False
    assert flows["same-copy-removed"] is True


def test_an_open_offer_is_put_off_when_another_device_shows(flows: dict) -> None:
    # S35.
    assert flows["switch-puts-off"] == {
        "offer-open": False, "copy-kept": True, "editing": False,
    }


# +-------------------------------------------------------------------------
# | GL-020: the module file changed elsewhere; Delete Device


def test_history_restore_puts_the_file_back(outside: dict) -> None:
    restored = outside["history-restore"]
    assert restored["ok"] is True
    assert restored["file-restored"] is True


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-071: the map does not reload after History Restore"
)
def test_the_map_follows_a_history_restore_outside_edit(outside: dict) -> None:
    # 07 Q6: outside Edit, reload.
    assert outside["history-restore"]["shown-follows"] is True


def test_module_setup_photo_reaches_the_file(outside: dict) -> None:
    assert outside["setup-photo-written"] is True


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-071: Save writes the old photo over Module Setup's without a word",
)
def test_save_does_not_write_over_module_setup_photo(outside: dict) -> None:
    # 07 Q6: in Edit, Save warns first (Keep mine / Take theirs); nothing is
    # written over the change until the user chooses.
    saved = outside["setup-photo-save"]
    assert saved["file-image"] == saved["setup-image"]


def test_pack_import_reaches_the_file(outside: dict) -> None:
    imported = outside["pack-import"]
    assert imported["made"] is True and imported["imported"] is True, imported
    assert 80 in imported["file-ids"]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-071: Save writes the old map over a Device Pack import without a word",
)
def test_save_does_not_write_over_a_pack_import(outside: dict) -> None:
    saved = outside["pack-save"]
    assert saved["file-ids"] == saved["pack-ids"]


def test_delete_device_removes_the_module_file(outside: dict) -> None:
    assert outside["delete-ok"] == [True, False]


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-176: Delete Device mid-edit asks Save, which would recreate the file",
)
def test_delete_device_mid_edit_closes_without_asking(outside: dict) -> None:
    # S13, 07 Q7: closes without saving (a short note says why).
    assert outside["delete-mid-edit"] == {"closed": True, "asked": False, "file": False}


# +-------------------------------------------------------------------------
# | GL-021: edge paths of hardware_profile


@pytest.fixture
def maps(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> pathlib.Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(hardware_profile, "_maps_dir", lambda: folder)
    monkeypatch.setattr(
        hardware_profile,
        "resolve_module_slug",
        lambda name, guid="": name.lower().replace(" ", "_"),
    )
    return folder


def test_clear_image_fails_while_the_photo_is_open(maps: pathlib.Path) -> None:
    # S41: the window then puts the photo back and says so (flows above).
    photo = maps / "test_stick" / "photo.png"
    photo.parent.mkdir()
    photo.write_bytes(b"png")
    profile = hardware_profile.HardwareProfile()
    with photo.open("rb"):
        assert profile.clearImage("Test Stick") is False
        assert photo.is_file()
    assert profile.clearImage("Test Stick") is True
    assert not photo.exists()


def test_saved_layouts_skip_damaged_other_files(maps: pathlib.Path) -> None:
    # S75: other devices' files that can't be read are left out quietly.
    (maps / "good.json").write_text(
        json.dumps({"device": "Good", "nodes": [{"id": "b1"}]}), encoding="utf-8")
    (maps / "not_utf8.json").write_bytes(b"\xff\xfe{ nodes")
    (maps / "a_list.json").write_text("[1, 2]", encoding="utf-8")
    (maps / "a_number.json").write_text("7", encoding="utf-8")
    profile = hardware_profile.HardwareProfile()
    assert profile.savedLayouts("Mine") == [{"name": "Good", "slug": "good"}]
    for slug in ("not_utf8", "a_list", "a_number"):
        assert profile.layoutNodes(slug) == ""


@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="GL-178: Choose Photo makes qml/images in the install folder"
)
def test_picture_folder_is_not_made_in_the_install_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    # 07 Q13: open in Pictures or the last folder used.
    install = tmp_path / "install"
    install.mkdir()
    monkeypatch.setattr(hardware_profile, "_install_root", lambda: install)
    hardware_profile.HardwareProfile().imagesFolderUrl()
    assert list(install.iterdir()) == []


@pytest.mark.xfail(
    strict=True,
    raises=PermissionError,
    reason="GL-178: a read-only install folder makes the picture folder fail",
)
def test_picture_folder_with_a_read_only_install_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    install = tmp_path / "install"
    install.mkdir()
    monkeypatch.setattr(hardware_profile, "_install_root", lambda: install)
    real_mkdir = pathlib.Path.mkdir

    def mkdir(self: pathlib.Path, *args: object, **kwargs: object) -> None:
        if install in self.parents or self == install:
            raise PermissionError(13, "Access is denied", str(self))
        real_mkdir(self, *args, **kwargs)  # type: ignore[arg-type]

    # The class, not a shared instance: monkeypatch puts it back.
    monkeypatch.setattr(pathlib.Path, "mkdir", mkdir)
    url = hardware_profile.HardwareProfile().imagesFolderUrl()
    assert str(install).replace("\\", "/") not in url


def _item(kind: InputType, number: int) -> types.SimpleNamespace:
    return types.SimpleNamespace(input_id=number, input_type=kind, action_sequences=[])


def test_pool_of_an_unplugged_device_comes_from_the_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # S46: not connected, no module file: the controls the profile uses.
    guid = str(uuid.uuid4())
    items = [
        _item(InputType.JoystickButton, 4),
        _item(InputType.JoystickButton, 2),
        _item(InputType.JoystickAxis, 3),
        _item(InputType.JoystickHat, 1),
        _item(InputType.JoystickButton, 0),
    ]
    # The profile's inputs for this device (a stand-in profile would upset
    # the shared one; a new Profile object wipes global rows, GL-074).
    monkeypatch.setattr(
        input_pairing, "_items_for_guid", lambda g: items if g == guid else [])
    rows = hardware_profile.chips_for_guid(guid)
    assert [(r["kind"], r["hwId"]) for r in rows] == [
        ("btn", 2), ("btn", 4), ("axis", 3), ("hat", 1),
    ]


def test_pool_takes_claims_first_then_what_the_device_reports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # S46: claimed controls; with no claims, what the device reports.
    guid = str(uuid.uuid4())
    monkeypatch.setattr(input_pairing, "_device_name", lambda g: "Test Stick")
    monkeypatch.setattr(
        hardware_profile, "_device_input_ids", lambda g: ([1, 2, 3], [1, 2], [1]))
    monkeypatch.setattr(
        hardware_profile, "_profile_input_ids", lambda g: ([9], [9], [9]))
    claim = {"claim": {"buttons": [2], "axes": [], "hats": []}}
    monkeypatch.setattr(module_model, "_load_module_doc", lambda name, g="": claim)
    rows = hardware_profile.chips_for_guid(guid)
    assert [(r["kind"], r["hwId"]) for r in rows] == [
        ("btn", 2), ("axis", 1), ("axis", 2), ("hat", 1),
    ]
    monkeypatch.setattr(module_model, "_load_module_doc", lambda name, g="": {})
    rows = hardware_profile.chips_for_guid(guid)
    assert [(r["kind"], r["hwId"]) for r in rows] == [
        ("btn", 1), ("btn", 2), ("btn", 3), ("axis", 1), ("axis", 2), ("hat", 1),
    ]
