# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Hands-on fix G2: Button Map Options labels are not cut short.

In an 800 px wide Button Map window the Options pane's "Seconds between
recovery copies" read "Seconds betw…" (hands-on 07, "Other things seen",
q16_options_after_down.png). The pane's setting rows
(qml/RigOptionsPanel.qml) now let a label go onto a second line instead.

The real Button Map off-screen in its own process
(handson_G2_options_labels_smoke.py), 800 px wide, at 100 and 175 %.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

import pytest

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture(scope="module", params=[100, 175])
def run(
    request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory
) -> dict:
    home = tmp_path_factory.mktemp("g2options")
    (home / "Gremlin Platforms").mkdir()
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        HTTPS_PROXY="http://127.0.0.1:9",
    )
    env.setdefault(
        "QT_QPA_FONTDIR", os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts")
    )
    args = [
        sys.executable,
        "test/unit/handson_G2_options_labels_smoke.py",
        str(request.param),
    ]
    if os.environ.get("GREMLIN_SHOTS"):
        args.append(os.environ["GREMLIN_SHOTS"])
    done = subprocess.run(
        args,
        cwd=_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, done.stdout[-1500:] + done.stderr[-1500:]
    return json.loads(lines[0][len("RESULT ") :])


def test_the_window_is_800_wide(run: dict) -> None:
    assert run["window"] == 800


def test_every_group_has_settings(run: dict) -> None:
    groups = {label["group"] for label in run["labels"]}
    assert groups == {"labels", "editing", "autosave", "view", "colours"}


def test_the_recovery_copies_label_is_whole(run: dict) -> None:
    label = next(lb for lb in run["labels"] if lb["key"] == "autosave-seconds")
    assert label["text"] == "Seconds between recovery copies"
    assert not label["truncated"], label
    assert label["content"] <= label["width"] + 0.5, label


def test_no_label_is_cut_short(run: dict) -> None:
    cut = [
        lb
        for lb in run["labels"]
        if lb["truncated"] or lb["content"] > lb["width"] + 0.5
    ]
    assert cut == []


def test_every_row_is_inside_the_pane(run: dict) -> None:
    out = [lb for lb in run["labels"] if lb["row-end"] > lb["pane-end"] + 0.5]
    assert out == []


def test_number_boxes_and_lists_show_their_value(run: dict) -> None:
    squeezed = [
        lb for lb in run["labels"] for text, width in lb["box"] if text > width + 0.5
    ]
    assert squeezed == []
