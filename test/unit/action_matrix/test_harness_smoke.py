# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The action editor matrix harness, end to end with one action (Map to
vJoy) on every surface: Add Action, the editor's fields, a change, save and
reload, Undo/Redo, a fake input through the real runner, and the editor QML
in the off-screen program (one process for all of them)."""

from __future__ import annotations

import pathlib
from typing import Any

import pytest

from test.unit.action_matrix.harness import (  # pyright: ignore[reportMissingImports]
    Surface,
    actions,
    cases,
    open_editors,
    record,
)

TAG = "map-to-vjoy"
SURFACE_CASES = [
    (Surface.CONFIG_PAGE, "button"),
    (Surface.CONFIG_PAGE, "axis"),
    (Surface.PANE_BUTTON_MAP, "button"),
    (Surface.PANE_BUTTON_MAP, "hat"),
    (Surface.PANE_LOGICAL, "button"),
    (Surface.PANE_LOGICAL, "axis"),
    (Surface.PANE_KEYBOARD, "key"),
]


def test_every_plugin_is_listed() -> None:
    tags = dict(actions())
    assert len(tags) == 27, sorted(tags)  # 26 actions and Root
    assert "root" in tags
    assert tags[TAG] == ("axis", "button", "hat", "key")
    assert any(c[0] == TAG and c[2] == Surface.PANE_KEYBOARD for c in cases())


def _expected(kind: str) -> tuple:
    """What Map to vJoy's start writes for the event sent."""
    return {
        "button": ("button", True),
        "key": ("button", True),
        "axis": ("axis", 0.5),
        "hat": ("hat",),
    }[kind]


@pytest.mark.parametrize(("surface", "kind"), SURFACE_CASES)
def test_map_to_vjoy_on_each_surface(
    matrix: Any,  # noqa: ANN401
    surface: str,
    kind: str,
) -> None:
    case = matrix.open(TAG, kind, surface)
    assert case.action.tag == TAG

    fields = {f["name"]: f for f in case.fields()}
    assert {"vjoyDeviceId", "vjoyInputId", "vjoyInputType"} <= set(fields)
    changed, before, after = case.set("vjoyInputId", 7)
    record(TAG, surface, kind, "set", changed, f"vjoyInputId {before} -> {after}")
    assert changed and after == 7

    ok, diff = case.save_reload()
    record(TAG, surface, kind, "save_reload", ok, diff)
    assert ok, diff

    value = 0.5 if kind == "axis" else ("north" if kind == "hat" else True)
    sent = case.run(value=value)
    record(TAG, surface, kind, "run", bool(sent), sent)
    writes = [s for s in sent if s[0] in ("write_vjoy", "write_vjoy_axis_linear")]
    assert writes, sent
    want = _expected(kind)
    write = writes[-1]
    assert write[1] == 1 and write[2] == want[0] and write[3] == 7, sent
    if len(want) > 1:
        assert write[4] == pytest.approx(want[1]), sent

    case.reopen()
    case.set("vjoyInputId", 9)
    ok_undo, detail = case.undo_redo()
    record(TAG, surface, kind, "undo_redo", ok_undo, detail)
    if surface == Surface.CONFIG_PAGE:
        assert ok_undo is None  # no Undo on the live editor
    else:
        assert ok_undo, detail


def test_map_to_vjoy_editor_qml_off_screen(tmp_path: pathlib.Path) -> None:
    shots = tmp_path / "shots"
    requests = [
        {"tag": TAG, "input": kind, "shot": str(shots / f"{TAG}-{kind}.png")}
        for kind in ("button", "axis", "hat", "key")
    ] + [{"tag": "root", "input": "button", "shot": ""}]
    got = open_editors(requests, tmp_path)
    for req, editor in zip(requests, got, strict=True):
        record(
            req["tag"],
            "editor_qml",
            req["input"],
            "open_editor",
            editor.get("ok"),
            {"warnings": editor.get("warnings"), "error": editor.get("error", "")},
        )
        assert editor.get("ok"), editor
        assert editor.get("plugin_warnings") == [], editor
        if req["shot"]:
            assert pathlib.Path(req["shot"]).is_file(), editor
