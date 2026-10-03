# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Settings left by a newer version survive an older copy of the program
(installed and source copies share one settings file)."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path

import pytest

import gremlin.config
from gremlin import deferred_write, util
from gremlin.common import SingletonMetaclass

_KEY = ("global", "internal", "settings-version")


def _write(path: Path, version: str | None) -> None:
    data: dict = {"global": {"internal": {"new-feature": {
        "value": "x", "data_type": "string", "properties": {}, "expose": False,
    }}}}
    if version:
        data["global"]["internal"]["settings-version"] = {
            "value": version, "data_type": "string", "properties": {}, "expose": False,
        }
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def fresh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: None)  # write at once
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    yield path
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


def _start(
    version: str, monkeypatch: pytest.MonkeyPatch,
) -> gremlin.config.Configuration:
    monkeypatch.setattr(util, "get_code_version", lambda: version)
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    cfg = gremlin.config.Configuration()
    cfg.purge_unused()
    return cfg


def test_an_older_version_keeps_a_newer_versions_settings(
    fresh: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(fresh, "1.0.15")
    cfg = _start("1.0.13", monkeypatch)
    assert cfg.exists("global", "internal", "new-feature")
    # The newest version stays recorded, so the older one keeps its hands off
    # next time too.
    assert cfg.value(*_KEY) == "1.0.15"


def test_the_same_or_a_newer_version_removes_retired_settings(
    fresh: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(fresh, "1.0.13")
    cfg = _start("1.0.15", monkeypatch)
    assert not cfg.exists("global", "internal", "new-feature")
    assert cfg.value(*_KEY) == "1.0.15"


def test_settings_without_a_version_are_cleaned_and_stamped(
    fresh: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(fresh, None)
    cfg = _start("1.0.15", monkeypatch)
    assert not cfg.exists("global", "internal", "new-feature")
    assert cfg.value(*_KEY) == "1.0.15"
