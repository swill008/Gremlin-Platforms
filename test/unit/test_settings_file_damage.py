# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A damaged settings file (configuration.json).

Before: loading the settings logged an activity line, which (before the
application ran) needed the log folder, which read the settings again while
they were still being made: 91 nested loads at every start, and a hang with
no window when the file held a bad value. A file that couldn't be read was
silently replaced by defaults.

Now: one load; a bad setting falls back to its default and the rest are
kept; a file that can't be read is kept aside as configuration.json.bad-<date>
and the user is told once.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import os
import pathlib
import subprocess
from collections.abc import Iterator

import pytest

import gremlin.config
from gremlin import deferred_write
from gremlin.common import SingletonMetaclass
from gremlin.signal import signal
from gremlin.types import PropertyType

_ROOT = pathlib.Path(__file__).parents[2]


@pytest.fixture
def settings_file(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[pathlib.Path]:
    path = tmp_path / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    monkeypatch.setattr(gremlin.config, "_damaged_copy", "")
    monkeypatch.setattr(deferred_write, "_scheduler", lambda: None)
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    yield path
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)


def _entry(data_type: str, value: object) -> dict:
    return {"data_type": data_type, "value": value, "properties": {}, "expose": False}


def _fresh_process(home: pathlib.Path, code: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    return subprocess.run(
        [sys.executable, "-c", code], cwd=_ROOT, env=env,
        capture_output=True, text=True, timeout=60,
    )


def test_settings_are_read_once_before_the_application_runs(
    tmp_path: pathlib.Path,
) -> None:
    code = (
        "import gremlin.config as c\n"
        "n = [0]\n"
        "orig = c.Configuration.load\n"
        "def load(self):\n"
        "    n[0] += 1\n"
        "    return orig(self)\n"
        "c.Configuration.load = load\n"
        "c.Configuration()\n"
        "print('LOADS', n[0])\n"
    )
    result = _fresh_process(tmp_path, code)
    assert "LOADS 1" in result.stdout, result.stdout + result.stderr  # was 91


def test_bad_value_does_not_hang_start_up(tmp_path: pathlib.Path) -> None:
    folder = tmp_path / "Gremlin Platforms"
    folder.mkdir()
    (folder / "configuration.json").write_text(
        json.dumps({"global": {"general": {"x": _entry("int", "abc")}}}),
        encoding="utf-8",
    )
    code = "import gremlin.config as c\nc.Configuration()\nprint('STARTED')\n"
    assert "STARTED" in _fresh_process(tmp_path, code).stdout  # used to hang


def test_bad_settings_fall_back_and_good_ones_are_kept(
    settings_file: pathlib.Path,
) -> None:
    settings_file.write_text(
        json.dumps({
            "global": {
                "general": {
                    "good": _entry("int", "42"),
                    "bad-int": _entry("int", "abc"),
                    "bad-bool": _entry("bool", "maybe"),
                    "no-type": {"value": "1", "properties": {}, "expose": False},
                    "odd-type": _entry("no-such-type", "1"),
                },
                "broken-group": "not a group",
            }
        }),
        encoding="utf-8",
    )
    cfg = gremlin.config.Configuration()
    for name, data_type, default in [
        ("good", PropertyType.Int, 1),
        ("bad-int", PropertyType.Int, 7),
        ("bad-bool", PropertyType.Bool, True),
    ]:
        properties = {"min": 0, "max": 100} if data_type == PropertyType.Int else {}
        cfg.register("global", "general", name, data_type, default, "", properties)
    assert cfg.value("global", "general", "good") == 42
    assert cfg.value("global", "general", "bad-int") == 7
    assert cfg.value("global", "general", "bad-bool") is True
    assert settings_file.is_file()  # a partly bad file is not set aside
    assert gremlin.config._damaged_copy == ""


@pytest.mark.parametrize("text", ["[]", '{"global": {"gen', "not json"])
def test_unreadable_file_is_kept_aside_and_announced_once(
    settings_file: pathlib.Path, text: str
) -> None:
    settings_file.write_text(text, encoding="utf-8")
    gremlin.config.Configuration()

    copies = list(settings_file.parent.glob("configuration.json.bad-*"))
    assert len(copies) == 1
    assert copies[0].read_text(encoding="utf-8") == text  # nothing lost
    assert not settings_file.exists()

    shown: list[tuple[str, str]] = []
    signal.showNotification.connect(lambda t, m: shown.append((t, m)))
    try:
        gremlin.config.announce_damaged_settings()
        gremlin.config.announce_damaged_settings()
    finally:
        signal.showNotification.disconnect()
    assert len(shown) == 1
    assert str(copies[0]) in shown[0][1]


@pytest.mark.parametrize("text", ["", "  \n"])
def test_empty_file_is_like_no_file(settings_file: pathlib.Path, text: str) -> None:
    # Nothing to keep aside and nothing to tell: there were no settings.
    settings_file.write_text(text, encoding="utf-8")
    gremlin.config.Configuration()
    assert list(settings_file.parent.glob("configuration.json.bad-*")) == []
    assert gremlin.config._damaged_copy == ""


def test_activity_lines_before_the_application_runs_are_kept(
    tmp_path: pathlib.Path,
) -> None:
    code = (
        "from gremlin.ui import live_debug\n"
        "from gremlin import deferred_write\n"
        "live_debug.trace('READ', 'Test', 'early', 'x.txt', 'ok')\n"
        "live_debug.start()\n"
        "deferred_write.flush_all()\n"
        "print(live_debug.log_path().read_text(encoding='utf-8'))\n"
    )
    result = _fresh_process(tmp_path, code)
    assert "READ | Test | early" in result.stdout, result.stdout + result.stderr


def test_saving_creates_the_settings_folder(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # It used to exist only as a side effect of the nested loads (fixed above).
    path = tmp_path / "Gremlin Platforms" / "configuration.json"
    monkeypatch.setattr(gremlin.config, "_config_file_path", str(path))
    SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    try:
        gremlin.config.Configuration().save_now()
    finally:
        SingletonMetaclass._instances.pop(gremlin.config.Configuration, None)
    assert path.is_file()
