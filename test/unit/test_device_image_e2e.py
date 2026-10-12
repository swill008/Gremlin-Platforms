# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Image on the real path (D-03-DEVICE-IMAGE; 03 S52, S88, S136,
01 S143, 07 S127), checked in the running program off-screen
(device_image_e2e_smoke.py, its own process and user folder): the main
window's Home card menu and picker, Home Undo / Redo, the Module Setup
window's Add Image… / Remove Image / Save / Discard, and the Device Mapping
Editor's Save slot, over the stand-in stick "pJoy Pro" whose map has a
background (so it has a generated picture, device-photo.png).

- Home: Add Image… names pictures/device-image.<ext> in the module file and
  the card shows it; Change Image… replaces it (the old file goes); Remove
  Image drops the key and the file and the card shows the generated
  picture. Each is one Home Undo step and Redo puts it back. None of them
  makes the generated picture again (3a).
- Module Setup: Add Image… waits in the window until Save; Save names it
  and the card shows it; Remove Image -> Save drops it; Add Image… then
  Discard leaves the device folder exactly as it was.
- The Device Mapping Editor's Save keeps the image, even when its own
  document names another one.
- Output cards offer no image and refuse one; the Logical Device card keeps
  its own Add Image… (the bottom background picture, no Device Image key).
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "device_image_e2e_smoke.py"


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("home-devimg")
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )  # fmt: skip
    fonts = os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    env.setdefault("QT_QPA_FONTDIR", fonts)
    with (home / "stdout.txt").open("w") as out, (home / "stderr.txt").open("w") as err:
        tree = proc_tree.popen(
            [sys.executable, str(_SMOKE)],
            cwd=_ROOT / "test" / "unit", env=env, stdout=out, stderr=err,
        )  # fmt: skip
    try:
        tree.process.wait(timeout=170)
    except subprocess.TimeoutExpired:
        tree.kill()
        tree.process.wait()
        raise
    stdout = (home / "stdout.txt").read_text(errors="replace")
    stderr = (home / "stderr.txt").read_text(errors="replace")
    lines = [ln for ln in stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, stdout[-1500:] + stderr[-1500:]
    return json.loads(lines[0][len("RESULT ") :])


def _ok(run: dict, *steps: str) -> None:
    for name in steps:
        assert name not in run["errors"], run["errors"][name]


def _shows(state: dict, file: str) -> bool:
    return f"/pictures/{file}" in state.get("photo", "")


IMAGE = "device-image.png"
CHANGED = "device-image_1.png"


def test_the_stick_starts_with_its_generated_picture(run: dict) -> None:
    _ok(run, "start")
    assert run["generated"] is True, run
    assert run["start-card"]["hasImage"] is False
    assert _shows(run["start-card"], "device-photo.png"), run["start-card"]


def test_home_add_image_names_the_image_and_the_card_shows_it(run: dict) -> None:
    _ok(run, "start", "home")
    assert "  Add Image…" in run["home-rows-before"], run["home-rows-before"]
    assert "  Remove Image" not in run["home-rows-before"]
    assert run["home-add-ran"] is True and run["home-add-picked"] is True
    add = run["home-add"]
    assert add["ref"] == f"pictures/{IMAGE}", add
    assert add["red"] is True and add["files"] == [IMAGE], add
    assert add["hasImage"] is True and _shows(add, IMAGE), add
    rows = run["home-rows-with-image"]
    assert "  Change Image…" in rows and "  Remove Image" in rows, rows
    assert "  Add Image…" not in rows


def test_home_change_image_replaces_it(run: dict) -> None:
    _ok(run, "home")
    change = run["home-change"]
    assert change["ref"] == f"pictures/{CHANGED}", change
    assert change["blue"] is True and change["files"] == [CHANGED], change
    assert change["hasImage"] is True and _shows(change, CHANGED), change


def test_home_remove_image_shows_the_generated_picture(run: dict) -> None:
    _ok(run, "home")
    remove = run["home-remove"]
    assert remove["ref"] == "" and remove["files"] == [], remove
    assert remove["hasImage"] is False
    assert _shows(remove, "device-photo.png"), remove


def test_setting_the_image_makes_no_generated_picture_again(run: dict) -> None:
    _ok(run, "home")
    assert run["home-renders"] == 0, run["home-renders"]
    assert run["home-renders-after-undo"] == 0
    assert run["home-photo-mtime"] == run["start-photo-mtime"]


def test_home_undo_and_redo_step_through_each_change(run: dict) -> None:
    _ok(run, "home")
    undo = run["home-undo"]
    assert [u["tip"].split(" (")[0] for u in undo] == [
        "Undo Remove Image", "Undo Change Image", "Undo Add Image",
    ], undo  # fmt: skip
    # Undo Remove: the changed image (and its file) is back.
    assert undo[0]["bytes"] == "blue" and undo[0]["files"] == [CHANGED], undo[0]
    assert undo[0]["hasImage"] is True and _shows(undo[0], CHANGED)
    # Undo Change: the first image is back, the changed one's file gone.
    assert undo[1]["bytes"] == "red" and undo[1]["files"] == [IMAGE], undo[1]
    assert _shows(undo[1], IMAGE)
    # Undo Add: no image, the generated picture shows.
    assert undo[2]["ref"] == "" and undo[2]["files"] == [], undo[2]
    assert undo[2]["hasImage"] is False and _shows(undo[2], "device-photo.png")
    redo = run["home-redo"]
    assert [r["bytes"] for r in redo] == ["red", "blue", ""], redo
    assert redo[1]["hasImage"] is True and _shows(redo[1], CHANGED)
    assert redo[2]["files"] == [] and _shows(redo[2], "device-photo.png")


def test_module_setup_add_image_waits_for_save_then_the_card_shows_it(
    run: dict,
) -> None:
    _ok(run, "setup-add")
    assert run["setup-add-text"] == "Add Image…"
    assert run["setup-add-picked"] is True
    # Nothing in the device folder changes before Save (03 S52, 07 S107).
    assert run["setup-add-waits"] is True
    assert run["setup-remove-shown"] is True
    add = run["setup-add"]
    assert add["ref"] == f"pictures/{IMAGE}" and add["yellow"] is True, add
    assert add["files"] == [IMAGE]
    assert add["hasImage"] is True and _shows(add, IMAGE), add


def test_module_setup_remove_image_then_save_drops_it(run: dict) -> None:
    _ok(run, "setup-remove")
    assert run["setup-change-text"] == "Change Image…"
    assert run["setup-remove-visible"] is True
    assert run["setup-remove-waits"] is True
    remove = run["setup-remove"]
    assert remove["ref"] == "" and remove["files"] == [], remove
    assert remove["hasImage"] is False and _shows(remove, "device-photo.png")


def test_module_setup_discard_leaves_the_folder_as_it_was(run: dict) -> None:
    _ok(run, "setup-discard")
    assert run["setup-discard-picked"] is True
    assert run["setup-discard-asked"] is True
    discard = run["setup-discard"]
    assert discard["same"] is True, discard
    assert discard["ref"] == "" and discard["hasImage"] is False


def test_the_device_mapping_editors_save_keeps_the_image(run: dict) -> None:
    _ok(run, "editor")
    assert run["editor-set"] is True
    ref = run["editor-ref-before"]
    assert ref.startswith("pictures/device-image"), ref
    assert run["editor-save-1"] is True
    assert run["editor-after-1"] == {"ref": ref, "red": True}
    assert run["editor-save-2"] is True
    after = run["editor-after-2"]
    assert after["ref"] == ref and after["red"] is True, after
    assert run["editor-card"]["hasImage"] is True


def test_output_cards_take_no_image(run: dict) -> None:
    _ok(run, "others")
    if "output-rows" not in run:
        pytest.skip("no output card on Home")
    rows = run["output-rows"]
    assert not [r for r in rows if "Image" in r], rows
    assert run["output-set"] is False


def test_the_logical_device_card_keeps_its_own_picture(run: dict) -> None:
    _ok(run, "others")
    if "logical-rows" in run:
        assert "  Add Image…" in run["logical-rows"], run["logical-rows"]
    assert run["logical-set"] is True
    ld = run["logical-doc"]
    # Its photo is still the bottom background picture; no Device Image.
    assert ld["key"] is None and ld["image-files"] == [], ld
    assert ld["photo"].startswith("pictures/photo"), ld
    assert run["logical-remove"] is True
    assert run["logical-after-remove"] == ""
