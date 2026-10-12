# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""gremlin.search_query: parsing, fuzzy matching, highlights, prefixes,
display texts, "Did you mean" and suggestions (Search, 01 S157-S164)."""

from __future__ import annotations

import ast
import pathlib
import sys
import time
from types import SimpleNamespace

from gremlin import search_query as sq

ROOT = pathlib.Path(__file__).resolve().parents[2]


def row(**kw: object) -> SimpleNamespace:
    base: dict[str, object] = dict(
        source="profile",
        source_name="DCS Hornet",
        source_path="C:/p/DCS Hornet.xml",
        device_guid="g",
        device_name="T.16000M",
        plugged=True,
        mode="Default",
        input_type=3,
        input_id=5,
        input_label="Button 5",
        custom_name="",
        action_tag="map-to-vjoy",
        action_name="Map to vJoy",
        text="vJoy 1 Button 3",
        targets=("vJoy 1 Button 3",),
        target_keys=(("vjoy", 1, 3, 3),),
        role="sends-output",
        not_found=False,
        why="",
        used_twice=False,
        binding_index=0,
        path=(),
        kinds=frozenset({"action", "vjoy"}),
    )
    base.update(kw)
    return SimpleNamespace(**base)


def test_module_is_pure_python() -> None:
    tree = ast.parse((ROOT / "gremlin" / "search_query.py").read_text("utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            names.append(node.module or "")
    assert not [n for n in names if "PySide" in n or "Qt" in n]


def test_parse_free_prefixed_and_quoted() -> None:
    q = sq.parse('gr tog device:"T.16000M" mode:Combat foo:bar')
    assert [t.text for t in q.free] == ["gr", "tog", "foo:bar"]
    assert [(t.prefix, t.text) for t in q.prefixed] == [
        ("device", "T.16000M"),
        ("mode", "Combat"),
    ]
    assert sq.parse("").empty
    assert sq.parse('"Group Toggle"').free[0].text == "Group Toggle"


def test_bad_regex_gives_error_not_crash() -> None:
    q = sq.parse("([", regex=True)
    assert q.error
    assert sq.match(row(), q) is None


def test_exact_beats_word_start_beats_contiguous_beats_scattered() -> None:
    q = sq.parse("button")
    exact = sq.match(row(input_label="Button"), q)
    start = sq.match(row(input_label="Fire Button"), q)
    inner = sq.match(row(input_label="Xbuttonx", text="", targets=()), q)
    scattered = sq.match(
        row(input_label="Button", text="", targets=(), action_name=""),
        sq.parse("btn"),
    )
    assert exact and start and inner and scattered
    assert exact.score > start.score > inner.score > scattered.score


def test_fuzzy_subsequence_and_highlights() -> None:
    r = row(action_name="Group Toggle", text="", targets=())
    m = sq.match(r, sq.parse("grtog"))
    assert m is not None
    assert m.spans["action_name"] == [(0, 2), (6, 9)]
    # Too scattered: no match.
    assert (
        sq.match(row(input_label="axbxcxdxex", text="", targets=()), sq.parse("abcde"))
        is None
    )


def test_terms_are_and() -> None:
    r = row(action_name="Group Toggle")
    assert sq.match(r, sq.parse("gr tog")) is not None
    assert sq.match(r, sq.parse("gr zzz")) is None


def test_case_and_whole_word() -> None:
    r = row(input_label="Button 5", custom_name="Fire")
    assert sq.match(r, sq.parse("button", case=True)) is None
    assert sq.match(r, sq.parse("Button", case=True)) is not None
    assert sq.match(r, sq.parse("butt", word=True)) is None
    m = sq.match(r, sq.parse("button", word=True))
    assert m is not None and m.spans["input_label"] == [(0, 6)]


def test_regex_on_turns_fuzzy_off() -> None:
    r = row(action_name="Group Toggle", text="", targets=())
    assert sq.match(r, sq.parse("grtog", regex=True)) is None
    m = sq.match(r, sq.parse(r"Gr.*le", regex=True))
    assert m is not None and m.spans["action_name"] == [(0, 12)]
    # Spaces are part of the pattern.
    assert sq.match(r, sq.parse("Group Tog", regex=True)) is not None


def test_prefixes() -> None:
    key_row = row(input_type=1, input_label="F5", kinds=frozenset({"key"}))
    assert sq.match(key_row, sq.parse("key:F5")) is not None
    assert sq.match(row(input_label="F5"), sq.parse("key:F5")) is None
    m = sq.match(row(), sq.parse('vjoy:"Button 3"'))
    assert m is not None and "targets:0" in m.spans
    assert sq.match(row(), sq.parse("xbox:")) is None
    assert sq.match(row(), sq.parse("vjoy:")) is not None
    assert sq.match(row(), sq.parse('device:"T.16000M"')) is not None
    assert sq.match(row(), sq.parse("device:warthog")) is None
    assert sq.match(row(), sq.parse("profile:hornet")) is not None
    assert sq.match(row(), sq.parse("action:map-to")) is not None
    assert sq.match(row(), sq.parse("mode:default")) is not None
    osc = row(targets=("OSC t /fader1",), target_keys=(("osc-out", "t", "/fader1"),))
    assert sq.match(osc, sq.parse("osc:/fader1")) is not None
    mouse = row(targets=("Mouse Left",), target_keys=(("mouse", "Left"),))
    assert sq.match(mouse, sq.parse("mouse:left")) is not None
    for name, (_, description) in sq.PREFIXES.items():
        assert description, name


def test_display_every_kind_and_fallback() -> None:
    from gremlin import references as refs

    assert sq.display(("xbox", 1, "A")) == "Xbox 360 Controller A"
    assert sq.display(("xbox", 2, "A")) == "Xbox 360 2 A"
    assert sq.display(("mode", "Combat")) == "Mode Combat"
    assert sq.display(("mouse", "Left")) == "Mouse Left"
    assert sq.display(("osc-out", "deck", "/a")) == "OSC deck /a"
    assert sq.display(refs.profile("C:/x/My Profile.xml")).lower() == "my profile"
    assert sq.display(("vjoy", 1, 3, 4)).startswith("vJoy 1 ")
    assert sq.display(("nope", 1)) == "nope 1"
    assert sq.display(("vjoy",)) == "vjoy"
    assert sq.display(()) == "()"
    # Every target shape references.py makes has a DISPLAY entry.
    tree = ast.parse((ROOT / "gremlin" / "references.py").read_text("utf-8"))
    kinds = {
        node.elts[0].value
        for node in ast.walk(tree)
        if isinstance(node, ast.Tuple)
        and node.elts
        and isinstance(node.elts[0], ast.Constant)
        and isinstance(node.elts[0].value, str)
        and isinstance(node.ctx, ast.Load)
    } - {
        "sends-output",
        "reads-input",
        "checks-output",
        "checks-input",
        "switches-mode",
        "loads-profile",
    }
    assert kinds and kinds <= set(sq.DISPLAY), kinds - set(sq.DISPLAY)


def test_did_you_mean() -> None:
    vocab = ["Group Toggle", "Map to vJoy", "Throttle"]
    assert sq.did_you_mean("trhottle", vocab) == "Throttle"
    assert sq.did_you_mean("throttle", vocab) is None
    assert sq.did_you_mean("zzzzzzzz", vocab) is None
    assert sq.did_you_mean('action:"Map to vjoi"', vocab) == 'action:"Map to vJoy"'
    assert sq.did_you_mean("x", []) is None


def test_suggestions() -> None:
    vocab = ["T.16000M", "Throttle", "Thrustmaster Warthog"]
    recent = ["throttle combat", "vjoy:1"]
    got = sq.suggestions("thr", vocab, recent)
    assert got[0] == "throttle combat"
    assert "Throttle" in got and '"Thrustmaster Warthog"' in got
    assert sq.suggestions("dev", vocab, []) == ["device:"]
    assert sq.suggestions("device:T.", vocab, []) == ["device:T.16000M"]
    assert sq.suggestions("", vocab, recent) == recent
    assert len(sq.suggestions("t", vocab * 5, [], limit=2)) <= 2


def test_twenty_thousand_rows_are_fast() -> None:
    rows = [
        row(
            input_label=f"Button {i}",
            custom_name=f"name {i % 97}",
            text=f"vJoy {i % 8} Button {i % 128}",
        )
        for i in range(20000)
    ]
    q = sq.parse("button 12")
    [sq.match(r, q) for r in rows]  # the first pass fills the text cache
    start = time.perf_counter()
    found = [r for r in rows if sq.match(r, q) is not None]
    took = time.perf_counter() - start
    assert found
    # Target well under 0.1 s; generous for slow CI machines.
    assert took < 1.0, took
    print(f"20k rows: {took * 1000:.0f} ms", file=sys.stderr)
    sq.clear_cache()


def test_cache_follows_the_row_object() -> None:
    a = row(input_label="Alpha")
    q = sq.parse("alpha")
    assert sq.match(a, q) is not None
    b = row(input_label="Beta")
    assert sq.match(b, q) is None
    sq.clear_cache()
    assert sq.match(a, q) is not None


def test_prefixes_reach_targets() -> None:
    from gremlin import references as refs
    from gremlin.types import InputType

    f5 = refs.keyboard((0x3F, False))
    shown = sq.display(f5)
    assert "F5" in shown and "(63" not in shown
    sends_f5 = row(targets=(shown,), target_keys=(f5,), kinds=frozenset({"action"}))
    assert sq.match(sends_f5, sq.parse("key:F5")) is not None
    assert sq.display(refs.vjoy(2, InputType.JoystickButton, 30)) == "vJoy 2 Button 30"
    change = row(
        mode="Default", targets=("Mode Combat",), target_keys=(("mode", "Combat"),)
    )
    assert sq.match(change, sq.parse("mode:combat")) is not None
    load = row(targets=("Other",), target_keys=(refs.profile("C:/x/Other.xml"),))
    assert sq.match(load, sq.parse("profile:other")) is not None


def test_fuzzy_tries_later_starts() -> None:
    r = row(
        input_label="",
        action_name="",
        text="Text to Speech: Gremlin toggle",
        targets=(),
        device_name="",
        source_name="",
        mode="",
    )
    m = sq.match(r, sq.parse("tggl"))
    assert m is not None and m.spans["text"] == [(24, 25), (26, 29)]
    assert sq.match(r, sq.parse("grml tggl")) is not None
