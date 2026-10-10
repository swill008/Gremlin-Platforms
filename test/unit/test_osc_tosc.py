# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""TouchOSC layout import (09 S162): .tosc files built here with zlib + XML,
plus a real editor-made file (test/fixtures/tosc/controls.tosc, from
tosclib, MIT) holding one of every control."""

from __future__ import annotations

import zlib
from pathlib import Path

import pytest

from gremlin import osc_tosc
from gremlin.error import GremlinError
from gremlin.osc_rows import check_settings

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "tosc" / "controls.tosc"


def _partial(kind: str, value: str, low: float = 0.0, high: float = 1.0) -> str:
    return (
        f"<partial><type>{kind}</type><conversion>STRING</conversion>"
        f"<value>{value}</value><scaleMin>{low}</scaleMin>"
        f"<scaleMax>{high}</scaleMax></partial>"
    )


DEFAULT_PATH = [("CONSTANT", "/"), ("PROPERTY", "name")]


def _osc(
    path: list[tuple[str, str]] = DEFAULT_PATH,
    args: tuple[tuple[str, float, float], ...] = (("x", 0.0, 1.0),),
    send: int = 1,
) -> str:
    path_xml = "".join(_partial(k, v) for k, v in path)
    args_xml = "".join(_partial("VALUE", v, lo, hi) for v, lo, hi in args)
    return (
        f"<osc><enabled>1</enabled><send>{send}</send><receive>1</receive>"
        f"<path>{path_xml}</path><arguments>{args_xml}</arguments></osc>"
    )


def _node(kind: str, name: str, messages: str = "", children: str = "") -> str:
    return (
        f'<node ID="id-{name}" type="{kind}"><properties>'
        f'<property type="s"><key>name</key><value>{name}</value></property>'
        f"</properties><values/><messages>{messages}</messages>"
        f"<children>{children}</children></node>"
    )


def _write(tmp_path: Path, body: str, name: str = "layout.tosc") -> Path:
    xml = f'<?xml version="1.0" encoding="UTF-8"?><lexml version="3">{body}</lexml>'
    path = tmp_path / name
    path.write_bytes(zlib.compress(xml.encode("utf-8")))
    return path


def test_fader_button_xy_and_label_give_four_rows(tmp_path: Path) -> None:
    children = (
        _node("FADER", "fader1", _osc(args=(("x", -1.0, 2.0),)))
        + _node("BUTTON", "btn1", _osc())
        + _node("XY", "xy1", _osc(args=(("x", 0.0, 1.0), ("y", 0.0, 100.0))))
        + _node("LABEL", "label1")
    )
    rows, skipped = osc_tosc.parse(
        _write(tmp_path, _node("GROUP", "root", "", children))
    )
    assert [(r["address"], r["mode"], r["source"]) for r in rows] == [
        ("/fader1", "axis", 0),
        ("/btn1", "button", 0),
        ("/xy1", "axis", 0),
        ("/xy1", "axis", 1),
    ]
    assert (rows[0]["range_min"], rows[0]["range_max"]) == (-1.0, 2.0)
    assert (rows[3]["range_min"], rows[3]["range_max"]) == (0.0, 100.0)
    assert [r["label"] for r in rows[2:]] == ["xy1 (XY P1)", "xy1 (XY P2)"]
    assert any("label1" in note for note in skipped)
    # Same shape the add path takes: settings keys pass the row checks.
    for row in rows:
        check_settings({k: v for k, v in row.items() if k not in ("address", "label")})


def test_radio_and_pager_are_change_encoder_and_radial_are_axes(
    tmp_path: Path,
) -> None:
    body = _node(
        "GROUP",
        "root",
        "",
        (
            _node("RADIO", "radio1", _osc())
            + _node("PAGER", "pager1", _osc(args=(("page", 0.0, 1.0),)))
            + _node("ENCODER", "enc1", _osc(args=(("x", 0.0, 5.0),)))
            + _node("RADIAL", "rad1", _osc(args=(("x", 0.0, 10.0),)))
        ),
    )
    rows, _ = osc_tosc.parse(_write(tmp_path, body))
    modes = {r["address"]: r for r in rows}
    assert modes["/radio1"]["mode"] == "change"
    assert modes["/pager1"]["mode"] == "change"
    assert modes["/enc1"]["mode"] == "axis"
    assert (modes["/enc1"]["range_min"], modes["/enc1"]["range_max"]) == (0.0, 5.0)
    assert "enc_format" not in modes["/enc1"]
    assert modes["/rad1"]["mode"] == "axis"
    assert modes["/rad1"]["range_max"] == 10.0


def test_radar_gives_two_axes_like_xy(tmp_path: Path) -> None:
    radar = _node("RADAR", "radar1", _osc(args=(("x", 0.0, 1.0), ("y", 0.0, 360.0))))
    rows, _ = osc_tosc.parse(_write(tmp_path, _node("GROUP", "root", "", radar)))
    assert [(r["address"], r["mode"], r["source"], r["label"]) for r in rows] == [
        ("/radar1", "axis", 0, "radar1 (Radar P1)"),
        ("/radar1", "axis", 1, "radar1 (Radar P2)"),
    ]
    assert rows[1]["range_max"] == 360.0


def test_grid_is_a_container_and_index_is_the_child_position(tmp_path: Path) -> None:
    template = [
        ("CONSTANT", "/"),
        ("PROPERTY", "parent.name"),
        ("CONSTANT", "/"),
        ("INDEX", ""),
    ]
    kids = "".join(
        _node("BUTTON", name, _osc(path=template)) for name in ("a", "b", "c")
    )
    body = _node(
        "GROUP",
        "root",
        "",
        _node("LABEL", "l") + _node("GRID", "pads", _osc(path=template), kids),
    )
    rows, skipped = osc_tosc.parse(_write(tmp_path, body))
    assert [(r["address"], r["mode"]) for r in rows] == [
        ("/pads/1", "button"),
        ("/pads/2", "button"),
        ("/pads/3", "button"),
    ]
    assert not any("pads" in note for note in skipped)


def test_nested_group_name_prefix(tmp_path: Path) -> None:
    path = [
        ("CONSTANT", "/"),
        ("PROPERTY", "parent.name"),
        ("CONSTANT", "/"),
        ("PROPERTY", "name"),
    ]
    body = _node(
        "GROUP",
        "root",
        "",
        _node("GROUP", "mixer", "", _node("FADER", "vol", _osc(path=path))),
    )
    rows, _ = osc_tosc.parse(_write(tmp_path, body))
    assert [r["address"] for r in rows] == ["/mixer/vol"]


def test_runtime_path_and_send_off_are_skipped_with_a_note(tmp_path: Path) -> None:
    body = _node(
        "GROUP",
        "root",
        "",
        (
            _node("FADER", "dyn", _osc(path=[("CONSTANT", "/"), ("VALUE", "x")]))
            + _node("FADER", "quiet", _osc(send=0))
            + _node(
                "FADER", "bad", _osc(path=[("PROPERTY", "parent.parent.parent.name")])
            )
            + _node("FADER", "nopath", _osc(path=[]))
        ),
    )
    rows, skipped = osc_tosc.parse(_write(tmp_path, body))
    assert rows == []
    assert len(skipped) == 4
    assert any("dyn" in note and "run time" in note for note in skipped)
    # No documented default for an empty path: skipped, not "/" + name.
    assert any("nopath" in note for note in skipped)


@pytest.mark.parametrize(
    "kind", ["not_zlib", "doctype", "entity", "bad_xml", "wrong_root"]
)
def test_refused_files_raise_and_give_no_rows(tmp_path: Path, kind: str) -> None:
    path = tmp_path / "bad.tosc"
    xml = {
        "doctype": '<?xml version="1.0"?><!DOCTYPE lexml [<!ENTITY a "x">]><lexml/>',
        "entity": '<lexml><!ENTITY a "x"></lexml>',
        "bad_xml": "<lexml><node>",
        "wrong_root": "<other/>",
    }.get(kind)
    path.write_bytes(b"plain text" if xml is None else zlib.compress(xml.encode()))
    with pytest.raises(GremlinError):
        osc_tosc.parse(path)


def test_oversized_layout_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(osc_tosc, "MAX_BYTES", 1000)
    path = _write(tmp_path, _node("GROUP", "root", "", "x" * 2000))
    with pytest.raises(GremlinError, match="too big"):
        osc_tosc.parse(path)


def test_missing_file_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(GremlinError):
        osc_tosc.parse(tmp_path / "nope.tosc")


def test_real_editor_file_gives_an_input_per_sending_control() -> None:
    """controls.tosc (tosclib, made in the TouchOSC editor): one of every
    control; the grid holds faders 1-4, the pager three pages."""
    rows, skipped = osc_tosc.parse(FIXTURE)
    got = [
        (r["address"], r["mode"], r["source"], r.get("range_min"), r.get("range_max"))
        for r in rows
    ]
    assert got == [
        ("/button2", "button", 0, None, None),
        ("/fader1", "axis", 0, 0.0, 1.0),
        ("/xy1", "axis", 0, 0.0, 1.0),
        ("/xy1", "axis", 1, 0.0, 1.0),
        ("/radial1", "axis", 0, 0.0, 1.0),
        ("/encoder1", "axis", 0, 0.0, 1.0),
        ("/radar1", "axis", 0, 0.0, 1.0),
        ("/radar1", "axis", 1, 0.0, 1.0),
        ("/radio1", "change", 0, None, None),
        ("/pager1", "change", 0, None, None),
        ("/grid1/1", "axis", 0, 0.0, 1.0),
        ("/grid1/2", "axis", 0, 0.0, 1.0),
        ("/grid1/3", "axis", 0, 0.0, 1.0),
        ("/grid1/4", "axis", 0, 0.0, 1.0),
    ]
    assert sorted(skipped) == [
        "box1 (BOX): not an input, skipped",
        "label1 (LABEL): not an input, skipped",
        "text1 (TEXT): not an input, skipped",
    ]
    for row in rows:
        check_settings({k: v for k, v in row.items() if k not in ("address", "label")})
