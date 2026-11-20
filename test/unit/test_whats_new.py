# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib

import pytest
from PySide6 import QtCore

from gremlin import (
    util,
    whats_new,
)
from gremlin.config import Configuration
from gremlin.types import PropertyType

_app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


@pytest.fixture
def notes(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    for version in ("1.0.9", "1.0.10", "1.0.11", "1.0.12"):
        (tmp_path / f"{version}.md").write_text(
            f"## What's new in {version}\n\n### New\n- thing {version}\n",
            encoding="utf-8",
        )
    (tmp_path / "README.md").write_text("readme", encoding="utf-8")
    monkeypatch.setattr(whats_new, "notes_dir", lambda: tmp_path)
    return tmp_path


def test_range_is_numeric_newest_first(notes: pathlib.Path) -> None:
    assert whats_new.versions_between("1.0.9", "1.0.12") == [
        "1.0.12", "1.0.11", "1.0.10",
    ]


def test_range_none_when_same_or_newer(notes: pathlib.Path) -> None:
    assert whats_new.versions_between("1.0.12", "1.0.12") == []
    assert whats_new.versions_between("1.0.13", "1.0.12") == []


def test_first_install_has_no_banner(notes: pathlib.Path) -> None:
    assert whats_new.banner_versions("", "1.0.12") == []
    assert whats_new.banner_versions(None, "1.0.12") == []
    assert whats_new.banner_versions("1.0.11", "1.0.12") == ["1.0.12"]


def test_notes_newest_first_and_missing_file(notes: pathlib.Path) -> None:
    text = whats_new.notes_html(["1.0.12", "1.0.10"])
    assert text.index("1.0.12") < text.index("1.0.10")
    assert "thing 1.0.12" in text
    (notes / "1.0.12.md").unlink()
    assert "Release notes unavailable." in whats_new.notes_html(["1.0.12"])
    assert "Release notes unavailable." in whats_new.notes_html([])


def test_shipped_notes_include_running_version() -> None:
    assert util.get_code_version() in whats_new.available_versions()


def test_model(notes: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from gremlin.ui.whats_new_model import WhatsNewModel

    cfg = Configuration()
    cfg.register(
        "global", "internal", "last-run-version", PropertyType.String, "", "x", {}
    )
    monkeypatch.setattr(util, "get_code_version", lambda: "1.0.12")
    cfg.set("global", "internal", "last-run-version", "1.0.10")
    model = WhatsNewModel()
    assert model.bannerVisible
    assert model.bannerTitle == "Updated to 1.0.12"
    assert model.bannerMessage == "See what changed in this version."
    model.showBannerNotes()
    assert "thing 1.0.11" in model.notesHtml and "thing 1.0.12" in model.notesHtml
    assert "thing 1.0.10" not in model.notesHtml
    model.showCurrentNotes()
    assert "thing 1.0.11" not in model.notesHtml
    model.dismissBanner()
    assert not model.bannerVisible
    cfg.set("global", "internal", "last-run-version", "")
    assert not WhatsNewModel().bannerVisible
    cfg.set("global", "internal", "last-run-version", "1.0.12")
    assert not WhatsNewModel().bannerVisible
