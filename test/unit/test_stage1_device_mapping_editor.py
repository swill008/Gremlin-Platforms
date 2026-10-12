# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Mapping Editor safety net (Stage 1): GL-019, GL-020, GL-021.

Spec: claude/program-map/07-device-mapping-editor.md (section 8, decided by section 9).

GL-019 (07-T2), the window driven as the user drives it, in the running
program off-screen (stage1_device_mapping_editor_smoke.py, its own process and user
folder): Save says so and reads back (S20, S24); Cancel asks when there are
changes, Save there saves and leaves Edit, Discard keeps the file and leaves
no undo (S25, S26, S19); closing with unsaved edits asks once (S28); the
recovery copy is written, removed when undone, offered with Restore /
Discard / Not now, quietly dropped when it equals the saved map, put off
when another device shows, never written more often than every 10 seconds
(S32-S35, S37); Copy Device Map from Device (S75-S77); Add Picture to
Background and Clear Background, then Cancel (S26, S40, S41).

GL-020 (07-T3): the module file changed elsewhere while the map is open
(History Restore, Module Setup's photo, a Device Pack import), Delete Device
in the middle of an edit, a copy onto a device with fewer controls.

GL-021 (07-T4): the
picture folder and a read-only install folder, the pool of an unplugged
device (S46), other devices' damaged module files (S75).

Known gaps were marked xfail(strict) until fixed; all are fixed in batch 2:
GL-176 (Delete Device mid-edit, 07 Q7), GL-173 (print area
and guides, 07 Q1), GL-174 (a new picture waits for Save, 07 Q2), GL-175 (no
module file made by a guide change, S29), GL-178 (no folder in the install
folder, 07 Q13), GL-182 (chips for controls the device lacks, 07 Q8).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import types
import uuid
from collections.abc import Iterator

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

from gremlin.modules import store
from gremlin.types import InputType
from gremlin.ui import hardware_profile, input_pairing
from test.unit._device_folders import put_module

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "stage1_device_mapping_editor_smoke.py"
# A started part: its process and its user folder (which holds its output).
_Smoke = tuple[proc_tree.Tree, pathlib.Path]


def _start(part: str, home: pathlib.Path) -> _Smoke:
    """One part of the window smoke, started in its own process and user folder.

    Its output goes to files in that folder: a pipe nobody reads yet (the
    other part is being waited on) could fill and stall it.
    """
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
    with (home / "stdout.txt").open("w", encoding="utf-8") as out, (
        home / "stderr.txt"
    ).open("w", encoding="utf-8") as err:
        tree = proc_tree.popen(
            [sys.executable, str(_SMOKE), part],
            cwd=_ROOT, env=env, stdout=out, stderr=err,
        )
    return tree, home


def _result(smoke: _Smoke) -> dict:
    """The started part's result (its RESULT line)."""
    tree, home = smoke
    try:
        tree.process.wait(timeout=240)
    except subprocess.TimeoutExpired:
        tree.kill()
        tree.process.wait()
    stdout, stderr = (
        (home / name).read_text(encoding="utf-8", errors="replace")
        for name in ("stdout.txt", "stderr.txt")
    )
    # The smoke not getting through is RuntimeError, so a strict xfail
    # (raises=AssertionError) never takes it for the known gap.
    lines = [ln for ln in stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        # A stall report starts with its headline (blocked or idle) and
        # lists every thread: keep it whole, not only its tail.
        at = stderr.find("=== STALLED")
        err = stderr[at:at + 12000] if at >= 0 else stderr[-2000:]
        raise RuntimeError(stdout[-2000:] + err)
    out = json.loads(lines[-1][len("RESULT "):])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    return out


def _run(part: str, home: pathlib.Path) -> dict:
    """One part of the window smoke, run to its end (test_stage1_modules)."""
    return _result(_start(part, home))


@pytest.fixture(scope="module")
def _smokes(
    tmp_path_factory: pytest.TempPathFactory,
) -> Iterator[dict[str, _Smoke]]:
    """Both parts started at once; each fixture below takes its own result."""
    smokes = {
        part: _start(part, tmp_path_factory.mktemp(f"bm_{part}"))
        for part in ("flows", "outside")
    }
    yield smokes
    for tree, _home in smokes.values():
        tree.close()
        tree.process.wait()


@pytest.fixture(scope="module")
def flows(_smokes: dict[str, _Smoke]) -> dict:
    return _result(_smokes["flows"])


@pytest.fixture(scope="module")
def outside(_smokes: dict[str, _Smoke]) -> dict:
    return _result(_smokes["outside"])


# +-------------------------------------------------------------------------
# | GL-019: Save, Cancel, leave prompts


def test_save_writes_reads_back_and_says_so(flows: dict) -> None:
    # S19: entering Edit is no change; S20, S24.
    assert flows["dirty-on-entering-edit"] is False
    # 01 S142: on the window's message line, plain, no box.
    assert flows["save-said"] == [False, "Saved to the module file.", False]
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
# | GL-019: background (07 S40, S41, S57; D-07-BACKGROUND-PLANES)


def test_add_picture_to_background_then_cancel_leaves_nothing(flows: dict) -> None:
    # S26, S40: the picture becomes the top background layer; Cancel puts
    # the starting background back and leaves no file behind.
    added = flows["add-background"]
    assert added["shown"][:-1] == added["start"]
    assert added["shown"][-1].endswith(".jpg")
    assert added["dirty"] is True
    back = flows["add-background-cancel"]
    assert back["file"] == back["start"] == ["pictures/photo.png"]
    assert back["shown"] == back["start"]
    assert back["old-photo"] is True
    assert back["new-jpg"] is False


def test_add_picture_to_background_writes_nothing_until_save(flows: dict) -> None:
    # 07 Q2, S29, S40: nothing in the module file or History until Save.
    added = flows["add-background"]
    assert added["file-before-save"] == added["start"]
    assert added["history-before-save"] == 0
    assert flows["add-background-cancel"]["history-after-cancel"] == 0


def test_add_picture_to_background_then_save_is_one_history_entry(flows: dict) -> None:
    saved = flows["add-background-save"]
    assert saved["file"][0] == "pictures/photo.png"
    assert saved["file"][-1].endswith(".jpg")
    # Copied into the device's folder on Save (S40).
    assert saved["jpg-in-pictures"] == [saved["file"][-1]]
    assert saved["after-save"] == 1


def test_the_background_history_entry_comes_with_save(flows: dict) -> None:
    assert flows["add-background-save"]["before-save"] == 0


def test_clear_background_then_cancel_brings_it_back_without_history(
    flows: dict,
) -> None:
    # S41: every background layer goes, without asking; an unsaved change
    # (S30); no stock or card picture (Q4); files only go on Save (S106).
    assert flows["clear-background-ran"] is True
    cleared = flows["clear-background"]
    assert cleared["shown"] == []
    assert cleared["asked"] is False
    assert cleared["dirty"] is True
    assert cleared["history-before-save"] == 0
    assert cleared["files-kept"] is True
    # S26: Cancel puts the saved background back.
    back = flows["clear-background-cancel"]
    assert back["history"] == 0
    assert back["file"] == back["saved"]
    assert back["shown"] == back["saved"]
    assert len(back["saved"]) == 2


def test_add_picture_and_clear_background_are_undo_steps(flows: dict) -> None:
    # S57: each is one Undo step; back at the start nothing is unsaved.
    undone = flows["background-undo"]
    assert undone["after-one"]["shown"][:-1] == undone["saved"]
    assert undone["after-one"]["shown"][-1].endswith(".png")
    # 07 S107: the chosen picture waits in the edit's temporary folder.
    assert undone["after-one"]["in-pictures"] is False
    assert undone["after-two"] == undone["saved"]
    assert undone["dirty"] is False
    assert flows["background-redo"][-1].endswith(".png")
    assert undone["after-cancel"] is True


def test_print_area_and_guides_are_undo_steps(flows: dict) -> None:
    # 07 Q3, GL-179.
    undone = flows["ui-undo"]
    assert undone["after-one"]["guidesX"] == [0.25]
    drawn = {"fx": 0.1, "fy": 0.1, "fw": 0.3, "fh": 0.3}
    assert undone["after-one"]["printArea"] != drawn
    assert undone["after-two"]["guidesX"] != [0.25]
    assert undone["dirty"] is False


def test_a_mirrored_copy_is_one_undo(flows: dict) -> None:
    # S78 (AU-27, GL-184).
    assert flows["mirror-copy-undo"] == {"ids": True, "fx": True}


# +-------------------------------------------------------------------------
# | GL-019: print area and guides


def test_cancel_takes_back_print_area_and_guides(flows: dict) -> None:
    # 07 Q1 (decided): part of the edit; Save writes, Cancel takes back.
    before = flows["ui-before"]
    assert flows["ui-mid-edit"] == before
    assert flows["ui-after-cancel"] == before
    assert flows["ui-shown-after-cancel"] == before


def test_guide_change_makes_no_module_file(flows: dict) -> None:
    # S29: the module file is written only on Save.
    assert flows["third-file-at-start"] is False
    assert flows["third-file-mid-edit"] is False
    assert flows["third-file-after-cancel"] is False


# +-------------------------------------------------------------------------
# | GL-019, GL-020: Copy Device Map from Device


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


def test_copy_says_how_many_chips_the_device_lacks(flows: dict) -> None:
    # 07 Q8: "N chips are for controls this device does not have".
    wanted = "2 chips are for controls this device does not have"
    assert wanted in flows["copy"]["message"]


# +-------------------------------------------------------------------------
# | GL-019: recovery copies


def test_recovery_copies_never_more_often_than_every_10_seconds(flows: dict) -> None:
    assert flows["recovery-interval-at-1s"] == 10000  # S33


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


def test_the_map_follows_a_history_restore_outside_edit(outside: dict) -> None:
    # 07 Q6: outside Edit, reload.
    assert outside["history-restore"]["shown-follows"] is True


def test_module_setup_photo_reaches_the_file(outside: dict) -> None:
    assert outside["setup-photo-written"] is True


def test_save_does_not_write_over_module_setup_photo(outside: dict) -> None:
    # 07 Q6: in Edit, Save warns first (Keep mine / Take theirs); nothing is
    # written over the change until the user chooses.
    saved = outside["setup-photo-save"]
    assert saved["file-image"] == saved["setup-image"]
    # The changed-elsewhere question really appeared.
    assert str(saved["said"]).startswith(
        "The module file changed since you started editing"
    ), saved["said"]


def test_pack_import_reaches_the_file(outside: dict) -> None:
    imported = outside["pack-import"]
    assert imported["made"] is True and imported["imported"] is True, imported
    assert 80 in imported["file-ids"]


def test_save_does_not_write_over_a_pack_import(outside: dict) -> None:
    saved = outside["pack-save"]
    assert saved["file-ids"] == saved["pack-ids"]
    # The changed-elsewhere question really appeared.
    assert str(saved["said"]).startswith(
        "The module file changed since you started editing"
    ), saved["said"]


def test_delete_device_removes_the_module_file(outside: dict) -> None:
    assert outside["delete-ok"] == [True, False]


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
    monkeypatch.setattr(store, "folder", lambda: folder)
    return folder


def test_saved_layouts_skip_damaged_other_files(maps: pathlib.Path) -> None:
    # S75: other devices' files that can't be read are left out quietly.
    put_module(maps, "Good", {"device": "Good", "nodes": [{"id": "b1"}]})
    put_module(maps, "Not UTF8", b"\xff\xfe{ nodes")
    put_module(maps, "A List", "[1, 2]")
    put_module(maps, "A Number", "7")
    profile = hardware_profile.HardwareProfile()
    # Each device's folder is its slug (03 S128).
    assert profile.savedLayouts("Mine") == [{"name": "Good", "slug": "Good"}]
    for slug in ("Not UTF8", "A List", "A Number"):
        assert profile.layoutNodes(slug) == ""


def test_picture_folder_is_not_made_in_the_install_folder(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    # 07 Q13: open in Pictures or the last folder used.
    install = tmp_path / "install"
    install.mkdir()
    monkeypatch.setattr(hardware_profile, "_install_root", lambda: install)
    hardware_profile.HardwareProfile().imagesFolderUrl()
    assert list(install.iterdir()) == []


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
    monkeypatch.setattr(store, "read", lambda name, g="": claim)
    rows = hardware_profile.chips_for_guid(guid)
    assert [(r["kind"], r["hwId"]) for r in rows] == [
        ("btn", 2), ("axis", 1), ("axis", 2), ("hat", 1),
    ]
    monkeypatch.setattr(store, "read", lambda name, g="": {})
    rows = hardware_profile.chips_for_guid(guid)
    assert [(r["kind"], r["hwId"]) for r in rows] == [
        ("btn", 1), ("btn", 2), ("btn", 3), ("axis", 1), ("axis", 2), ("hat", 1),
    ]
