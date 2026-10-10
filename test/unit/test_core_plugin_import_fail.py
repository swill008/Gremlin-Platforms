# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A built-in action plugin that can't be imported stops start-up (05 S1);
a user plugin that can't be imported is skipped with a logged message."""

from __future__ import annotations

import logging
import pathlib
import sys
import uuid

sys.path.append(".")

import pytest

from gremlin import plugin_manager


def _fresh_manager() -> plugin_manager.PluginManager:
    manager = object.__new__(plugin_manager.PluginManager)
    manager._plugins = {}
    manager._type_to_action_map = {}
    manager._name_to_type_map = {}
    manager._tag_to_type_map = {}
    manager._parameter_requirements = {}
    return manager


def _write_broken(root: pathlib.Path, module: str) -> None:
    folder = root / module
    folder.mkdir(parents=True)
    (folder / "__init__.py").write_text(
        f"import no_such_module_{uuid.uuid4().hex[:8]}\n", encoding="utf-8"
    )


@pytest.fixture(autouse=True)
def _own_sys_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "path", list(sys.path))


def test_a_core_plugin_that_cant_import_stops_start_up(
    tmp_path: pathlib.Path,
) -> None:
    package = f"core_import_{uuid.uuid4().hex[:8]}"
    (tmp_path / package).mkdir()
    (tmp_path / package / "__init__.py").write_text("", encoding="utf-8")
    _write_broken(tmp_path / package, "broken")
    sys.path.insert(0, str(tmp_path))
    manager = _fresh_manager()
    with pytest.raises(ImportError):
        manager._discover_plugins(tmp_path / package, True)
    assert manager._plugins == {}


def test_a_user_plugin_that_cant_import_is_skipped_and_logged(
    tmp_path: pathlib.Path, caplog: pytest.LogCaptureFixture
) -> None:
    module = f"user_import_{uuid.uuid4().hex[:8]}"
    _write_broken(tmp_path, module)
    manager = _fresh_manager()
    with caplog.at_level(logging.ERROR, logger="system"):
        manager._discover_plugins(tmp_path, False)
    assert manager._plugins == {}
    assert any(module in r.getMessage() for r in caplog.records)
