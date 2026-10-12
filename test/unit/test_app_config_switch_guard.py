"""Item 130: the session's app (the qapp fixture) answers configChanged, and a
test may switch to a settings file of its own that has none of the program's
settings registered. Announcing a change there must not fail in the app's
listener (Log When Not Responding read an unregistered key)."""

from __future__ import annotations

import pathlib

import pytest

import gremlin.config
from gremlin import deferred_write, signal
from gremlin.common import SingletonMetaclass


def test_config_changed_on_a_fresh_settings_file_does_not_fail(
    qapp: object, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    errors: list[BaseException] = []
    monkeypatch.setattr(
        "sys.excepthook", lambda kind, exc, tb: errors.append(exc)
    )
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    try:
        cfg = gremlin.config.Configuration()
        assert not cfg.exists("global", "general", "log-when-not-responding")
        signal.signal.configChanged.emit()
    finally:
        deferred_write.flush("configuration")
        SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    assert errors == []
