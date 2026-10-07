# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Final fix round X5: a failed Button Map write is False, not an error out
of the Qt slot, and the old file stays whole (07 S20, S23)."""

from __future__ import annotations

import json
import logging
import pathlib

import pytest

from gremlin.modules import module_file, store
from gremlin.ui import hardware_profile, windows_scale_option


@pytest.fixture
def maps(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    monkeypatch.setattr(store, "folder", lambda: tmp_path)
    monkeypatch.setattr(
        store,
        "slug_for",
        lambda name, guid="": name.lower().replace(" ", "_"),
    )
    return tmp_path


def _fail_writes(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(path: pathlib.Path, data: bytes) -> None:
        raise PermissionError(13, "Access is denied", str(path))

    monkeypatch.setattr(module_file, "write_bytes", refuse)


_OLD = {"device": "Stick R", "claim": {"buttons": [1]}, "nodes": [{"id": "old"}]}


@pytest.mark.parametrize("slot", ["save", "saveUi"])
def test_a_failed_write_is_false_logged_once_and_the_file_stays(
    maps: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    slot: str,
) -> None:
    path = maps / "stick_r.json"
    old_text = json.dumps(_OLD)
    path.write_text(old_text, encoding="utf-8")
    _fail_writes(monkeypatch)
    payload = {"device": "Stick R", "image": "", "photo": {}, "ui": {"a": 1},
               "nodes": [{"id": "new"}]}
    with caplog.at_level(logging.WARNING, logger="system"):
        result = getattr(hardware_profile.HardwareProfile(), slot)(
            "Stick R", json.dumps(payload)
        )
    assert result is False
    said = [r for r in caplog.records if "Button Map not written" in r.getMessage()]
    assert len(said) == 1
    assert path.read_text(encoding="utf-8") == old_text


def test_the_scaling_option_description_says_ignore() -> None:
    # D-09-Q15: the stored description matches the check box.
    assert windows_scale_option.DESCRIPTION.startswith(
        "Ignore Windows display scaling"
    )
