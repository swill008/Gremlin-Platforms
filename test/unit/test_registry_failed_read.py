# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A module file that couldn't be read for a moment (a sharing violation
from antivirus or backup) is read again on the next call, not remembered as
missing until the file changes (AUD-RUN-06, 03/06 S47). A damaged file is
remembered by its stamp so it isn't logged on every call."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from unittest import mock

import pytest

from gremlin.modules import registry


@pytest.fixture
def folder(tmp_path: Path) -> Iterator[Path]:
    registry._cache.clear()
    with mock.patch.object(registry, "_folder", return_value=tmp_path):
        yield tmp_path
    registry._cache.clear()


def test_a_failed_read_is_retried_on_the_next_call(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = folder / "stick.json"
    path.write_text(json.dumps({"device": "Stick"}), encoding="utf-8")
    real_read_text = Path.read_text
    calls = {"n": 0}

    def flaky(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError(32, "sharing violation", str(self))
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", flaky)

    assert registry.modules() == []
    # Same mtime and size: only a retry finds it.
    assert [m.name for m in registry.modules()] == ["Stick"]


def test_a_damaged_file_is_read_once_per_stamp(
    folder: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = folder / "broken.json"
    path.write_text("{not json", encoding="utf-8")
    real_read_text = Path.read_text
    calls = {"n": 0}

    def counting(self: Path, *args: object, **kwargs: object) -> str:
        if self == path:
            calls["n"] += 1
        return real_read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", counting)

    assert registry.modules() == []
    assert registry.modules() == []
    assert calls["n"] == 1
