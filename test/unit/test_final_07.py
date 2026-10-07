# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final test plan, Button Map: the section 8 statements no other test
checked (claude/final-test-plan/07-button-map.md).

Spec: claude/program-map/07-button-map.md S1, S2, S4, S11, S15, S23, S39,
S45, S47, S50, S56, S59, S60, S61, S63, S71, S74, S84, S94, S96, S100.

The window checks run final_07_smoke.py (the program off-screen, stand-in
hardware, its own process and user folder); S15 and S23 drive the owner
modules here.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import uuid

import pytest

from gremlin.event_handler import Event, EventListener
from gremlin.modules import store
from gremlin.modules.ids import guid_key
from gremlin.modules.runtime import InputModuleRuntime
from gremlin.types import InputType
from gremlin.ui import hardware_profile
from gremlin.ui.pair_live import PairLiveThrottle

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "final_07_smoke.py"


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("final_07")
    (home / "Gremlin Platforms").mkdir()
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
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=240,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        raise RuntimeError(done.stdout[-2000:] + done.stderr[-2000:])
    out = json.loads(lines[-1][len("RESULT "):])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    return out


def _part(seen: dict, key: str) -> object:
    """One step's result; a step that raised fails here with its traceback
    (RuntimeError, so a strict xfail never takes it for the known gap)."""
    value = seen[key]
    if isinstance(value, dict) and "error" in value:
        raise RuntimeError(value.get("traceback") or value["error"])
    return value


# +-------------------------------------------------------------------------
# | Opening and devices


def test_one_window_for_every_device_and_the_blank_page(seen: dict) -> None:
    # S1: opening for another device (or blank) reuses the window.
    assert _part(seen, "one-window") == {"card": True, "other": True, "blank": True}


def test_the_blank_page_says_choose_a_device_and_writes_nothing(seen: dict) -> None:
    # S2: the hint, and grid / view changes create no file.
    assert _part(seen, "blank") == {"hint": True, "files-same": True}


def test_the_device_menu_lists_no_outputs(seen: dict) -> None:
    # S4: no vJoy, no program Xbox pad; sticks and the built-in devices.
    rows = _part(seen, "device-menu")
    assert isinstance(rows, list)
    assert not [r for r in rows if r.lower().startswith("vjoy") or "xbox" in r.lower()]
    for wanted in ("pJoy Pro", "Third Stick", "Keyboard"):
        assert wanted in rows


def test_a_device_without_a_photo_shows_none(seen: dict) -> None:
    # S11: after a device with a photo, one without shows no photo; S96: its
    # zoom and grid changes make no module file.
    assert _part(seen, "no-file") == {
        "first-photo": True, "third-photo": "", "photo-override": "",
        "files-same": True,
    }


# +-------------------------------------------------------------------------
# | Live map


def test_presses_come_only_from_the_input_module_feed(
    qtbot: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    # S15: a claimed button lights; an unclaimed one never reaches the map,
    # though the hardware sent it.
    guid = uuid.uuid4()
    runtime = InputModuleRuntime()
    monkeypatch.setattr(
        runtime, "_claims",
        {guid_key(str(guid)): {"buttons": [2], "axes": [], "hats": []}},
    )
    monkeypatch.setattr(runtime, "_dest_guids", set())
    monkeypatch.setattr(runtime, "_passthrough", set())
    live = PairLiveThrottle()
    try:
        live.setProperty("guid", str(guid))
        for number in (2, 3):
            EventListener().joystick_event.emit(Event(
                InputType.JoystickButton, number, guid, "Default", is_pressed=True))
        assert live.buttonValue(2) == 1.0
        assert live.buttonValue(3) == 0.0
    finally:
        live.deleteLater()


# +-------------------------------------------------------------------------
# | Edit, Save


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    folder = tmp_path / "modules"
    folder.mkdir()
    monkeypatch.setattr(store, "folder", lambda: folder)
    monkeypatch.setattr(
        store, "slug_for", lambda name, guid="": name.lower().replace(" ", "_")
    )
    return folder


def test_a_save_cut_short_leaves_the_old_file_whole(
    maps: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # S23: written whole through a temporary file; a crash part way leaves
    # the file as it was.
    path = maps / "test_stick.json"
    old = {"kind": "control.hardware", "device": "Test Stick",
           "nodes": [{"id": "b1", "kind": "btn", "hwId": 1}]}
    path.write_text(json.dumps(old), encoding="utf-8")
    real = pathlib.Path.write_bytes

    def cut_short(self: pathlib.Path, data: bytes) -> int:
        if self.name.endswith(".tmp"):
            real(self, data[: len(data) // 2])
            raise OSError(28, "No space left on device")
        return real(self, data)

    monkeypatch.setattr(pathlib.Path, "write_bytes", cut_short)
    hw = hardware_profile.HardwareProfile()
    new = {"nodes": [{"id": "b9", "kind": "btn", "hwId": 9}]}
    # The store raises OSError for a failed write (the window then says
    # "Not written", S20); either way nothing counts as written.
    try:
        written = hw.save("Test Stick", json.dumps(new))
    except OSError:
        written = False
    assert written is False
    assert json.loads(path.read_text(encoding="utf-8")) == old
    assert not (maps / "test_stick.json.tmp").exists()
    monkeypatch.setattr(pathlib.Path, "write_bytes", real)
    assert hw.save("Test Stick", json.dumps(new)) is True
    assert json.loads(path.read_text(encoding="utf-8"))["nodes"] == new["nodes"]


# +-------------------------------------------------------------------------
# | Photo


def test_the_photo_menu_only_while_editing(seen: dict) -> None:
    # S39.
    assert _part(seen, "outside-edit")["photo-menu"] is False  # type: ignore[index]
    assert _part(seen, "inside-edit") == {"photo-menu": True}


# +-------------------------------------------------------------------------
# | Editing the map


def test_the_pool_lists_what_is_not_placed_and_filters(seen: dict) -> None:
    # S45.
    assert _part(seen, "pool") == {
        "placed-left-out": True, "has-17": True, "filtered": ["btn:17"],
    }


def test_chip_only_places_no_leader_and_no_hotspot(seen: dict) -> None:
    # S47: ticked, no leader and the hotspot hidden; not ticked, as usual.
    assert _part(seen, "chip-only") == {"on": [[], True], "off": [None, False]}


def test_a_leader_end_at_a_removed_chip_stays_where_it_is(seen: dict) -> None:
    # S50.
    assert _part(seen, "free-end") == {
        "type": "free", "kept-place": True, "chip-gone": True,
    }


def test_undo_and_redo_only_while_editing_80_by_default(seen: dict) -> None:
    # S56.
    outside = _part(seen, "outside-edit")
    assert outside["undo"] is False and outside["redo"] is False  # type: ignore[index]
    assert outside["hist-cap"] == 80  # type: ignore[index]
    steps = _part(seen, "undo-steps")
    assert steps["cap"] == 3 and steps["cap-back"] == 80  # type: ignore[index]


@pytest.mark.xfail(strict=True, reason=(
    "FINAL-07-1: Undo steps 3 goes back only 2 steps; histCap counts kept "
    "states (the start is one), not steps back (S56)"))
def test_undo_goes_back_as_many_steps_as_the_option(seen: dict) -> None:
    # S56: six changes with Undo steps 3: three steps back.
    assert _part(seen, "undo-steps")["undos"] == 3  # type: ignore[index]


def test_mirror_layout_flips_pictures_only_when_asked(seen: dict) -> None:
    # S59: the map mirrored, pictures flipped only with Mirror pictures;
    # Undo puts it back.
    assert _part(seen, "mirror") == {
        "plain": [False, True], "undo": True, "pictures": True,
        "undo-pictures": False,
    }


def test_fit_to_photo_frame_once_and_undo_makes_it_available(seen: dict) -> None:
    # S60: chips and hotspots shrink into the frame (0.25 + v / 2), once per
    # edit; Undo puts them back and Fit is offered again.
    assert _part(seen, "fit") == {
        "chip": [0.2, 0.35], "hot": [0.2, 0.35], "once": True, "undo": True,
        "again": True,
    }


def test_reset_layout_asks_clears_and_undoes(seen: dict) -> None:
    # S61.
    assert _part(seen, "reset") == {
        "asked": True, "unchanged": True, "cleared": 0, "undo": True,
    }


def test_a_picture_dropped_outside_edit_is_refused(seen: dict) -> None:
    # S63: the message, and no picture copied.
    assert _part(seen, "drop-outside") == {
        "took": False,
        "said": "Click Edit Mapping first, then drop the picture again.",
        "files-same": True,
    }


# +-------------------------------------------------------------------------
# | Action labels


def test_labels_follow_the_program_or_the_chosen_mode(seen: dict) -> None:
    # S71: Follow the Program takes the main window's mode while stopped; a
    # chosen Labels Mode stays whatever the main window shows.
    assert _part(seen, "follow") == {
        "follows": ["Combat", "Default"], "chosen": ["Chosen", "Chosen"],
    }


def test_the_labels_mode_is_forgotten_when_the_window_closes(seen: dict) -> None:
    # S74.
    assert _part(seen, "forgotten") == {"label-mode": ""}


# +-------------------------------------------------------------------------
# | Print and export, view, palette


def test_an_export_is_capped_at_16384_pixels(seen: dict) -> None:
    # S84: 800% of a 2400 pixel photo, its shape kept.
    sizes = _part(seen, "export-cap")
    small, big = sizes["100"], sizes["800"]  # type: ignore[index]
    assert max(big["w"], big["h"]) == 16384
    assert max(small["w"], small["h"]) < 16384
    assert abs(big["w"] / big["h"] - small["w"] / small["h"]) < 0.01


def test_zoom_from_50_to_600_percent_with_its_keys(seen: dict) -> None:
    # S94.
    assert _part(seen, "zoom") == {
        "most": 6.0, "least": 0.5, "hints": ["Ctrl+1", "Ctrl+2", "Ctrl+0"],
    }


def test_the_command_palette_lists_the_usable_menu_commands(seen: dict) -> None:
    # S100: while editing, the commands of every menu; Edit Mapping (not
    # usable in Edit) is left out.
    texts = _part(seen, "palette")
    assert isinstance(texts, list)
    for wanted in ("Save", "Cancel", "Reset Layout", "Fit to Photo Frame",
                   "Print & Export…", "Mirror Layout", "Button Map Options…",
                   "Zoom to Fit Page", "Show Grid", "Choose Photo…",
                   "Adjust Photo…", "Button Map Guide"):
        assert wanted in texts
    assert "Edit Mapping" not in texts
