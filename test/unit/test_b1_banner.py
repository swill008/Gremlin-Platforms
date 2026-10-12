# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Device Mapping Editor's view-only banner (D-FIXLIST-B1 item 1), in the running
window off-screen in its own process and user folder (b1_banner_smoke.py):

- one slim line just below the menu bar while the map is live (not
  editing): "View only. To edit this device map, choose File › Edit
  Mapping.", slimmer than the Background-mode banner, no close button;
- its "Edit Mapping" link starts editing as File › Edit Mapping does, and
  the banner hides while editing;
- it is back after Cancel, after Save once the edit ends, and when the
  window closed mid-edit opens again;
- with no device the banner says to choose one first (File › Device link)
  and starting is refused.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

_ROOT = pathlib.Path(__file__).parents[2]
_SMOKE = _ROOT / "test" / "unit" / "b1_banner_smoke.py"
_TEXT = "View only. To edit this device map, choose File › Edit Mapping."


@pytest.fixture(scope="module")
def seen(tmp_path_factory: pytest.TempPathFactory) -> dict:
    home = tmp_path_factory.mktemp("banner")
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
    done = proc_tree.run(
        [sys.executable, str(_SMOKE)],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    if not lines:
        raise RuntimeError(done.stdout[-2000:] + done.stderr[-2000:])
    out = json.loads(lines[-1][len("RESULT ") :])
    if "error" in out:
        raise RuntimeError(out.get("traceback") or out["error"])
    return out


def _part(seen: dict, key: str) -> dict:
    """One step's result; a step that raised fails here with its traceback."""
    value = seen[key]
    if isinstance(value, dict) and "error" in value:
        raise RuntimeError(value.get("traceback") or value["error"])
    assert isinstance(value, dict)
    return value


def test_banner_shows_under_the_menu_bar_while_live(seen: dict) -> None:
    live = _part(seen, "live")
    assert live["visible"] is True
    assert live["editing"] is False
    assert live["text"] == _TEXT
    assert live["linkText"] == "Edit Mapping"
    assert live["linkEnabled"] is True
    # Just below the menu bar, slimmer than the Background-mode banner.
    assert 0 <= live["gap"] <= 8
    assert 0 < live["height"] < live["bgHeight"]
    # No close button.
    assert live["buttons"] == []


def test_link_starts_editing_and_banner_hides(seen: dict) -> None:
    clicked = _part(seen, "clicked")
    assert clicked["started"] is True
    assert clicked["editing"] is True
    assert clicked["visible"] is False


def test_banner_back_after_cancel_and_save(seen: dict) -> None:
    cancelled = _part(seen, "cancelled")
    assert cancelled["editing"] is False
    assert cancelled["visible"] is True
    # Save keeps the edit open: still hidden; back once the edit ends.
    saved = _part(seen, "saved")
    assert saved["started"] is True
    assert saved["saved"] is True
    assert saved["whileEditing"]["editing"] is True
    assert saved["whileEditing"]["visible"] is False
    assert saved["editing"] is False
    assert saved["visible"] is True


def test_banner_back_after_closing_mid_edit(seen: dict) -> None:
    reopened = _part(seen, "reopened")
    assert reopened["started"] is True
    assert reopened["closed"] is True
    assert reopened["editing"] is False
    assert reopened["visible"] is True


def test_no_device_refuses_like_the_menu(seen: dict) -> None:
    none = _part(seen, "nodevice")
    assert none["linkEnabled"] is False
    assert none["canEnterEdit"] is False
    assert none["editing"] is False
