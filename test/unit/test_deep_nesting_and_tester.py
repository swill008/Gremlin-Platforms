# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Damaged files that are valid JSON/XML but can't be used (SHAKE-DAMAGE-05,
-06, AUD-OSC-03).

Before: an expected.json with wrong types made the Input Tester's compare
raise on every 1 s poll, so the window stopped updating; absurdly deep
nesting raised RecursionError, which the readers didn't catch (with such a
configuration.json the program didn't start; a .tosc gave a traceback).

Now: expected.json is checked when read and an unusable one is named once
in tester.log; deep nesting is a damaged file like any other: the settings
file is moved aside, a module file is skipped (and kept), a .tosc is
refused with a GremlinError the preview shows.
"""

from __future__ import annotations

import sys

sys.path.append(".")

import json
import pathlib
import zlib
from collections.abc import Iterator

import pytest

import gremlin.config
from gremlin import deferred_write, osc_tosc
from gremlin.common import SingletonMetaclass
from gremlin.error import GremlinError
from gremlin.input_tester import compare as cmp
from gremlin.input_tester.model import InputTesterModel
from gremlin.modules import registry

DEEP = "[" * 100_000 + "]" * 100_000
DEEP_OBJECT = '{"a": ' + DEEP + "}"


# Input Tester: expected.json with wrong types ------------------------------------


def _good() -> dict:
    return {
        "version": 1,
        "written": "2026-10-10T03:14:22",
        "hidhide": {
            "present": True,
            "cloak": True,
            "mode": "block",
            "tester_on_list": True,
            "apps": [],
        },
        "sticks": [
            {
                "name": "Right stick",
                "windows_name": "VKBsim Gladiator EVO R",
                "vid": 0x231D,
                "pid": 0x0200,
                "guid": "{11111111-2222-3333-4444-555555555555}",
                "instance_ids": [],
                "feeds": ["vJoy 3"],
                "expect": "hidden",
            }
        ],
        "vjoy": [
            {"id": 1, "guid": "", "fed_by": [], "used": True, "expect": "visible"}
        ],
        "xbox": [{"pad": 1, "on": True, "expect": "visible"}],
    }


def _with(path: tuple, value: object) -> dict:
    doc = _good()
    target: object = doc
    for key in path[:-1]:
        target = target[key]  # type: ignore[index]
    target[path[-1]] = value  # type: ignore[index]
    return doc


BAD_TYPES = [
    _with(("hidhide",), 7),
    _with(("hidhide", "apps"), 5),
    _with(("hidhide", "mode"), ["block"]),
    _with(("sticks",), ["x"]),
    _with(("sticks",), 5),
    _with(("sticks", 0, "vid"), "abc"),
    _with(("sticks", 0, "pid"), [1]),
    _with(("sticks", 0, "expect"), [1]),
    _with(("sticks", 0, "instance_ids"), 5),
    _with(("sticks", 0, "feeds"), [1, 2]),
    _with(("sticks", 0, "guid"), 12),
    _with(("vjoy",), [None]),
    _with(("vjoy", 0, "fed_by"), "vJoy"),
    _with(("vjoy", 0, "expect"), {"a": 1}),
    _with(("xbox", 0, "pad"), "one"),
    _with(("xbox", 0, "pad"), None),
    _with(("xbox",), {"pad": 1}),
]


@pytest.mark.parametrize("doc", BAD_TYPES)
def test_wrong_types_are_refused_not_raised(tmp_path: pathlib.Path, doc: dict) -> None:
    path = tmp_path / "expected.json"
    path.write_text(json.dumps(doc), encoding="utf-8")
    loaded = cmp.load_expected(path)
    assert loaded is None
    problem = cmp.read_expected(path)[1]
    assert problem  # names why it can't be used
    # Nothing raises on what was read.
    cmp.compare(loaded, [], True)


def test_good_file_still_reads(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "expected.json"
    path.write_text(json.dumps(_good()), encoding="utf-8")
    assert cmp.load_expected(path) == _good()
    assert cmp.read_expected(path) == (_good(), "")
    assert cmp.read_expected(tmp_path / "none.json") == (None, "")


def test_deep_expected_json_is_unreadable(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "expected.json"
    path.write_text(DEEP_OBJECT, encoding="utf-8")
    loaded, problem = cmp.read_expected(path)
    assert loaded is None and problem


def _model(gremlin_dir: pathlib.Path) -> InputTesterModel:
    return InputTesterModel(
        str(gremlin_dir),
        snapshot=lambda: [],
        hid_list=lambda: [],
        steam_running=lambda: True,
        clock=lambda: 0.0,
        start_timers=False,
    )


def test_tester_keeps_updating_and_says_once(qapp, tmp_path: pathlib.Path) -> None:  # noqa: ANN001
    tester = tmp_path / "tester"
    tester.mkdir()
    path = tester / "expected.json"
    path.write_text(json.dumps(_with(("sticks", 0, "vid"), "abc")), encoding="utf-8")
    model = _model(tmp_path)
    model.refresh()
    for _ in range(3):
        model.check_changes()  # the 1 s poll
    assert model.verdict == "none"
    unreadable = [
        line
        for line in model._log.lines()
        if "expected.json" in line and "can't be read" in line
    ]
    assert len(unreadable) == 1, model._log.lines()
    assert "not found" not in " ".join(unreadable)

    # Fixed by the program: read again and compared.
    path.write_text(json.dumps(_good()), encoding="utf-8")
    import os

    os.utime(path, (1, 1))
    model.check_changes()
    assert model.compareMode is True


# Deep nesting --------------------------------------------------------------------


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


def test_deep_settings_file_is_kept_aside(settings_file: pathlib.Path) -> None:
    settings_file.write_text(DEEP_OBJECT, encoding="utf-8")
    gremlin.config.Configuration()
    copies = list(settings_file.parent.glob("configuration.json.bad-*"))
    assert len(copies) == 1
    assert copies[0].read_text(encoding="utf-8") == DEEP_OBJECT
    assert not settings_file.exists()


def test_deep_settings_file_before_qt_loads(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import joystick_gremlin

    folder = tmp_path / "Gremlin Platforms"
    folder.mkdir()
    (folder / "configuration.json").write_text(DEEP_OBJECT, encoding="utf-8")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert joystick_gremlin._windows_scaling_disabled() is False


def test_deep_module_file_is_skipped_and_kept(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "deep.json"
    path.write_text(DEEP_OBJECT, encoding="utf-8")
    assert registry.read_doc(path) is None
    assert path.read_text(encoding="utf-8") == DEEP_OBJECT


def test_deep_result_and_recovery_files(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import input_tester_link
    from gremlin.profile_recovery import ProfileRecovery

    result_path = tmp_path / "result.json"
    result_path.write_text(DEEP_OBJECT, encoding="utf-8")
    monkeypatch.setattr(input_tester_link, "result_file", lambda: result_path)
    assert input_tester_link.last_result() is None

    recovery = ProfileRecovery(lambda: tmp_path)
    recovery.file_for("x.xml").write_text(DEEP_OBJECT, encoding="utf-8")
    assert recovery._read("x.xml") is None


def _tosc(depth: int) -> str:
    return '<node type="GROUP"><children>' * depth + "</children></node>" * depth


def test_deep_tosc_is_refused_with_a_message(tmp_path: pathlib.Path) -> None:
    xml = f'<?xml version="1.0"?><lexml version="5">{_tosc(5000)}</lexml>'
    path = tmp_path / "deep.tosc"
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    with pytest.raises(GremlinError, match="nested too deeply"):
        osc_tosc.parse(path)


def test_tosc_at_normal_depth_still_reads(tmp_path: pathlib.Path) -> None:
    xml = f'<?xml version="1.0"?><lexml version="5">{_tosc(20)}</lexml>'
    path = tmp_path / "ok.tosc"
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    rows, skipped = osc_tosc.parse(path)
    assert rows == [] and skipped == []
