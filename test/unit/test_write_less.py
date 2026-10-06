# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Writes to disk only when necessary: deferred settings saves, no forced
saves of unchanged lists, the last mode kept in memory during play, repeating
errors logged once, calibration Save All in one write, and the activity log
written in batches."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from gremlin import deferred_write, log_once
from gremlin.types import PropertyType


class _FakeScheduler:
    """Stands in for the Qt timer: records requests; flushes run by hand."""

    def __init__(self) -> None:
        self.requests: list[tuple[str, int]] = []

        class _Signal:
            def emit(_self, key: str, delay: int) -> None:  # noqa: N805
                self.requests.append((key, delay))

        self.request = _Signal()


@pytest.fixture
def deferred(monkeypatch: pytest.MonkeyPatch) -> Iterator[_FakeScheduler]:
    fake = _FakeScheduler()
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: fake)
    deferred_write._pending.clear()
    yield fake
    deferred_write._pending.clear()


def test_deferred_write_runs_once_and_on_flush(deferred: _FakeScheduler) -> None:
    runs: list[int] = []
    for _ in range(5):
        deferred_write.schedule("k", lambda: runs.append(1))
    assert runs == [] and deferred_write.pending("k")
    assert len(deferred.requests) == 5  # each request moves the timer
    deferred_write.flush_all()
    assert runs == [1] and not deferred_write.pending("k")


def test_without_qt_a_write_happens_at_once(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: None)
    runs: list[int] = []
    deferred_write.schedule("k", lambda: runs.append(1))
    assert runs == [1]


@pytest.fixture
def cfg(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[object]:
    import gremlin.config
    from gremlin.common import SingletonMetaclass

    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(tmp_path / "c.json"))
    try:
        yield gremlin.config.Configuration()
    finally:
        SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


def test_many_settings_changes_make_one_write(
    cfg: object, deferred: _FakeScheduler, tmp_path: Path,
) -> None:
    from gremlin.config import Configuration

    assert isinstance(cfg, Configuration)
    cfg.register("t", "g", "n", PropertyType.Int, 1, "", {"min": 0, "max": 99})
    deferred_write.flush_all()
    writes: list[str | None] = []
    real = cfg.save_now
    cfg.save_now = lambda path=None: (writes.append(path), real(path))  # type: ignore[method-assign]
    for value in range(2, 12):
        cfg.set("t", "g", "n", value)
    cfg.set("t", "g", "n", 11)  # unchanged: nothing new to save
    assert writes == []
    deferred_write.flush_all()
    assert len(writes) == 1
    saved = json.loads((tmp_path / "c.json").read_text())
    assert str(saved["t"]["g"]["n"]["value"]) == "11"  # ints are stored as text


def test_unchanged_auto_load_list_is_not_saved(
    cfg: object, deferred: _FakeScheduler,
) -> None:
    from gremlin.config import Configuration
    from gremlin.ui.option import ProfileAutoLoadingModel

    assert isinstance(cfg, Configuration)
    cfg.register(
        "profile", "automation", "entries-auto-loading", PropertyType.List,
        [["a.xml", "a.exe", True]], "", {},
    )
    deferred_write.flush_all()
    model = ProfileAutoLoadingModel()
    index = model.index(0, 0)
    role = next(r for r, n in model.roles.items() if bytes(n) == b"profile")
    model.setData(index, "a.xml", role)  # same value: no save
    assert not deferred_write.pending("configuration")
    model.setData(index, "b.xml", role)
    assert deferred_write.pending("configuration")


def test_last_mode_waits_while_running(
    cfg: object, deferred: _FakeScheduler, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin import mode_manager, shared_state
    from gremlin.config import Configuration

    assert isinstance(cfg, Configuration)
    cfg.register(
        "global", "internal", "last-mode-per-profile", PropertyType.Dict, {}, "", {},
    )
    deferred_write.flush_all()

    class _Profile:
        fpath = Path("p.xml")

    class _Mode:
        def __init__(self, name: str) -> None:
            self.name = name
            self.is_temporary = False

    monkeypatch.setattr(shared_state, "current_profile", _Profile())
    monkeypatch.setattr(mode_manager, "_profile_running", lambda: True)
    class _Manager:
        _mode_stack = [_Mode("Flight")]

    # The real method on a stand-in (ModeManager is a Qt singleton).
    mode_manager.ModeManager.klass._store_last_mode(_Manager())  # type: ignore[arg-type]
    # Kept in memory, read back from there; the settings are not touched.
    assert cfg.value("global", "internal", "last-mode-per-profile") == {}
    assert mode_manager._stored_last_modes()[str(Path("p.xml"))] == "Flight"
    mode_manager.flush_last_modes()  # the profile stops
    assert cfg.value("global", "internal", "last-mode-per-profile") == {
        str(Path("p.xml")): "Flight"
    }


def test_repeating_errors_are_logged_once(caplog: pytest.LogCaptureFixture) -> None:
    log_once.reset()
    with caplog.at_level(logging.ERROR, logger="event"):
        for _ in range(100):
            log_once.log_once("event", ("vjoy", 1), logging.ERROR, "vJoy failed")
        log_once.log_once("event", ("vjoy", 2), logging.ERROR, "vJoy 2 failed")
    assert len([r for r in caplog.records if r.name == "event"]) == 2
    log_once.reset()
    with caplog.at_level(logging.ERROR, logger="event"):
        log_once.log_once("event", ("vjoy", 1), logging.ERROR, "vJoy failed")
    assert len([r for r in caplog.records if r.name == "event"]) == 3


def test_calibration_save_all_writes_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import calibration, module_file

    path = tmp_path / "stick.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        calibration, "module_for_slug", lambda slug: {"slug": slug, "path": path},
    )
    saves: list[Path] = []
    real_save: Callable[..., None] = module_file.write_bytes

    def counting_save(target: Path, data: bytes) -> None:
        saves.append(Path(target))
        real_save(target, data)

    disk: list[Path] = []
    real_disk: Callable[..., int] = Path.write_bytes

    def counting_disk(self: Path, *args: object, **kwargs: object) -> int:
        disk.append(self)
        return real_disk(self, *args, **kwargs)

    monkeypatch.setattr(module_file, "write_bytes", counting_save)
    monkeypatch.setattr(Path, "write_bytes", counting_disk)
    axes = {0: (0, 10, 20, 30, True), 1: (1, 2, 3, 4, False)}
    assert calibration.write_axes("stick", axes)
    # One save of the file, through the store's one writer
    # (module_file.write_bytes) ...
    assert saves == [path]
    # ... to a temporary file that then replaces the real one, so a crash
    # can't leave half a file.
    assert disk == [path.with_name(path.name + ".tmp")]
    saved = json.loads(path.read_text(encoding="utf-8"))["calibration"]
    assert saved == {"0": [0, 10, 20, 30, True], "1": [1, 2, 3, 4, False]}


def test_activity_log_is_written_in_batches(
    deferred: _FakeScheduler, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.ui import live_debug

    log = tmp_path / "logs.txt"
    monkeypatch.setattr(live_debug, "log_path", lambda: log)
    live_debug._buffer.clear()
    for i in range(20):
        live_debug.trace("READ", "Test", "load", f"f{i}.json")
    assert not log.exists()  # nothing written yet
    live_debug.flush()
    lines = log.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20 and lines[0].startswith("READ | Test | load")
