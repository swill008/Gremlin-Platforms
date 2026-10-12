# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Guard: Search's five plug-in points (D-01-SEARCH-INDEX). A new piece is
found by Search without anyone adding it to a list in the search code:

1. every target kind a piece can point at (gremlin.references and every
   plugin's references()) has a DISPLAY entry in gremlin.search_query and a
   PREFIXES entry that finds it;
2. every source registered on SearchIndex yields rows with every SearchRow
   field, of the right type;
3. every device kind that holds bindings has a go-to handler in Main.qml;
4. a new action type with references() shows up in the index;
5. register_source with a new lister shows its rows."""

from __future__ import annotations

import ast
import dataclasses
import functools
import pathlib
import re
import sys
import types
import typing
import uuid
from collections.abc import Iterable, Iterator

sys.path.append(".")

import pytest

from gremlin import references as refs
from gremlin import shared_state
from gremlin.modules import device_class, ids, output
from gremlin.references import Reference
from gremlin.types import InputType

_ROOT = pathlib.Path(__file__).resolve().parents[2]
B = InputType.JoystickButton
_STICK = uuid.UUID("{4DCB3090-97EC-11EB-8003-444553540000}")
_FAKE_TAG = "search-plug-fake"


# --- 1. target kinds -------------------------------------------------------


def _literal_kind(node: ast.AST) -> str | None:
    """The kind of a target written as a tuple literal ("kind", ...)."""
    if (
        isinstance(node, ast.Tuple)
        and node.elts
        and isinstance(node.elts[0], ast.Constant)
        and isinstance(node.elts[0].value, str)
    ):
        return node.elts[0].value
    return None


def _kinds_in_references() -> set[str]:
    """Kinds the target shapes in gremlin/references.py return."""
    tree = ast.parse((_ROOT / "gremlin" / "references.py").read_text("utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Return) and node.value is not None:
            kind = _literal_kind(node.value)
            if kind:
                found.add(kind)
    return found


def _kinds_in_pieces() -> set[str]:
    """Kinds written as literals in a Reference(...) anywhere in the
    program (a plugin making its own target without a shape function)."""
    found: set[str] = set()
    files = [
        *(_ROOT / "action_plugins").rglob("*.py"),
        *(_ROOT / "gremlin").rglob("*.py"),
    ]
    for path in files:
        try:
            tree = ast.parse(path.read_bytes())
        except (SyntaxError, ValueError):
            continue  # a file being written; the lint checks it
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", getattr(node.func, "attr", ""))
            if name == "Reference" and len(node.args) >= 2:
                kind = _literal_kind(node.args[1])
                if kind:
                    found.add(kind)
            if name == "Ref" and node.args:
                kind = _literal_kind(node.args[0])
                if kind:
                    found.add(kind)
    return found


@functools.cache
def _all_kinds() -> frozenset[str]:
    return frozenset(_kinds_in_references() | _kinds_in_pieces())


def _samples(tmp: pathlib.Path) -> dict[str, list[tuple]]:
    """One or more real targets per kind, made by the shape functions."""
    made = [
        refs.vjoy(2, B, 30),
        refs.xbox(1, "A"),
        refs.input_ref(_STICK, B, 7),
        refs.keyboard((0x1E, False)),
        refs.mode("Flight"),
        refs.action("map-to-vjoy"),
        refs.osc_out("t-desk", "/gear"),
        refs.mouse("WheelUp"),
        refs.profile(tmp / "Other.xml"),
    ]
    out: dict[str, list[tuple]] = {}
    for target in made:
        out.setdefault(target[0], []).append(target)
    return out


def test_kinds_are_found() -> None:
    """The scan sees the shapes Search is known to have today."""
    assert {"vjoy", "xbox", "input", "mode", "action", "osc-out", "mouse"} <= (
        _all_kinds()
    )


def test_every_kind_has_a_sample(tmp_path: pathlib.Path) -> None:
    """A new kind needs a sample here too, so the checks below cover it."""
    missing = _all_kinds() - set(_samples(tmp_path))
    assert not missing, f"add a sample target for {sorted(missing)} to _samples()"


@pytest.mark.parametrize("kind", sorted(_all_kinds()))
def test_every_kind_has_a_display(kind: str, tmp_path: pathlib.Path) -> None:
    from gremlin import search_query

    assert kind in search_query.DISPLAY, (
        f"target kind {kind!r} has no DISPLAY entry in gremlin/search_query.py"
    )
    for target in _samples(tmp_path).get(kind, []):
        shown = search_query.display(target)
        assert isinstance(shown, str) and shown.strip(), (kind, target, shown)


def test_display_names_the_control() -> None:
    """A target with a control reads as the program shows that control
    ("vJoy 2 Button 30", "Keyboard F5"), not as raw numbers."""
    from gremlin import search_query

    key = (0x3F, False)
    cases = [
        (refs.vjoy(2, B, 30), ["vJoy 2", refs.input_label(B, 30)]),
        (refs.input_ref(_STICK, B, 7), [refs.input_label(B, 7)]),
        (
            refs.keyboard(key),
            [refs.device_name(ids.KEYBOARD), refs.input_label(InputType.Keyboard, key)],
        ),
    ]
    for target, words in cases:
        shown = search_query.display(target)
        assert shown == shown.strip(), (target, shown)
        for word in words:
            assert word in shown, (target, shown, word)


def _prefix_names() -> list[str]:
    from gremlin import search_query

    return [str(name).rstrip(":") for name in search_query.PREFIXES]


def test_prefixes_are_declared() -> None:
    from gremlin import search_query

    assert search_query.PREFIXES
    for name, value in search_query.PREFIXES.items():
        assert isinstance(name, str) and name.strip(":"), name
        field, description = value
        assert (isinstance(field, str) and field) or callable(field), name
        assert isinstance(description, str) and description, name


def _row(**fields: object) -> object:
    """A SearchRow with every field filled with words nothing searches for."""
    from gremlin import search_index

    values: dict[str, object] = {}
    for f in dataclasses.fields(search_index.SearchRow):
        values[f.name] = _filler(f.name, _hints()[f.name])
    values.update(fields)
    return search_index.SearchRow(**values)  # type: ignore[arg-type]


def _hints() -> dict[str, object]:
    from gremlin import search_index

    return typing.get_type_hints(search_index.SearchRow)


def _filler(name: str, hint: object) -> object:  # noqa: PLR0911
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    if name == "source":
        return "open"
    if hint is bool:
        return False
    if hint is int:
        return 0
    if hint is str:
        return "zzqq"
    if origin in (types.UnionType, typing.Union):
        return None if type(None) in args else _filler(name, args[0])
    if origin is tuple:
        return ()
    if origin is frozenset or hint is frozenset:
        return frozenset()
    return "zzqq"


def _query(text: str) -> object:
    from gremlin import search_query

    return search_query.parse(text, False, False, False)


@pytest.mark.parametrize("kind", sorted(_all_kinds()))
def test_every_kind_is_reachable_by_a_prefix(kind: str, tmp_path: pathlib.Path) -> None:
    """Some prefix finds a row that uses a target of this kind, by the
    target alone (every other field holds words that don't match)."""
    from gremlin import search_query

    for target in _samples(tmp_path).get(kind, []):
        shown = search_query.display(target)
        row = _row(targets=(shown,), target_keys=(target,))
        hits = [
            name
            for name in _prefix_names()
            if search_query.match(row, _query(f'{name}:"{shown}"')) is not None
        ]
        assert hits, (
            f"no prefix in PREFIXES finds a {kind!r} target {target} shown as {shown!r}"
        )


# --- 2. sources ------------------------------------------------------------


def _check_value(name: str, hint: object, value: object) -> None:  # noqa: C901
    origin = typing.get_origin(hint)
    args = typing.get_args(hint)
    where = f"SearchRow.{name}={value!r} is not {hint}"
    if hint is typing.Any or hint is object:
        return
    if origin in (types.UnionType, typing.Union):
        errors = 0
        for arg in args:
            try:
                _check_value(name, arg, value)
            except AssertionError:
                errors += 1
        assert errors < len(args), where
        return
    if hint is type(None):
        assert value is None, where
        return
    if origin is typing.Literal:
        assert value in args, where
        return
    if origin is tuple:
        assert isinstance(value, tuple), where
        if len(args) == 2 and args[1] is Ellipsis:
            for item in value:
                _check_value(name, args[0], item)
        return
    if origin is frozenset:
        assert isinstance(value, frozenset), where
        for item in value:
            _check_value(name, args[0] if args else object, item)
        return
    if hint is bool:
        assert isinstance(value, bool), where
        return
    if hint is int:
        assert isinstance(value, int) and not isinstance(value, bool), where
        return
    if isinstance(hint, type):
        assert isinstance(value, hint), where


_REQUIRED = {
    "source": str,
    "source_name": str,
    "source_path": str,
    "device_guid": str,
    "device_name": str,
    "mode": str,
    "input_type": int,
    "input_label": str,
    "custom_name": str,
    "action_tag": str,
    "action_name": str,
    "text": str,
    "targets": tuple,
    "target_keys": tuple,
    "role": str,
    "not_found": bool,
    "why": str,
    "used_twice": bool,
    "binding_index": int,
    "path": tuple,
    "kinds": frozenset,
}


def test_searchrow_has_the_contract_fields() -> None:
    from gremlin import search_index

    names = {f.name for f in dataclasses.fields(search_index.SearchRow)}
    missing = (set(_REQUIRED) | {"plugged", "input_id"}) - names
    assert not missing, f"SearchRow lacks {sorted(missing)}"


def _check_row(row: object) -> None:
    from gremlin import search_index

    assert isinstance(row, search_index.SearchRow), row
    hints = _hints()
    for f in dataclasses.fields(search_index.SearchRow):
        value = getattr(row, f.name)
        _check_value(f.name, hints[f.name], value)
        want = _REQUIRED.get(f.name)
        if want is not None:
            assert isinstance(value, want), f"SearchRow.{f.name}={value!r}"
    assert row.source in ("profile", "open", "library") or row.source  # type: ignore[attr-defined]
    assert row.plugged is None or isinstance(row.plugged, bool)  # type: ignore[attr-defined]
    assert all(isinstance(t, str) for t in row.targets)  # type: ignore[attr-defined]
    assert all(isinstance(t, tuple) and t for t in row.target_keys)  # type: ignore[attr-defined]
    assert all(isinstance(k, str) for k in row.kinds)  # type: ignore[attr-defined]


def _bind(profile: object, guid: object, input_id: object, *actions: object) -> None:
    from action_plugins.root import RootData
    from gremlin.profile import InputItemBinding

    input_type = InputType.Keyboard if guid == ids.KEYBOARD else B
    item = profile.get_input_item(guid, input_type, input_id, "Default", True)  # type: ignore[attr-defined]
    assert item is not None
    root = RootData(B)
    root.children = list(actions)
    binding = InputItemBinding(item)
    binding.root_action = root
    binding.behavior = B
    item.action_sequences.append(binding)
    for action in [root, *actions]:
        profile.library.add_action(action)  # type: ignore[attr-defined]


def _vjoy(vjoy_id: int, input_id: int) -> object:
    from action_plugins.map_to_vjoy import MapToVjoyData

    action = MapToVjoyData(B)
    action.vjoy_device_id = vjoy_id
    action.vjoy_input_type = B
    action.vjoy_input_id = input_id
    return action


@pytest.fixture
def home(monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path) -> pathlib.Path:
    """A temp user folder; no outputs needed to tell what can be sent."""
    folder = tmp_path / "home"
    folder.mkdir()
    monkeypatch.setenv("USERPROFILE", str(folder))
    monkeypatch.setenv("HOME", str(folder))
    monkeypatch.setattr(output, "cant_send_text", lambda *a, **k: None)
    monkeypatch.setattr(output, "xbox_cant_send_text", lambda *a, **k: None)
    monkeypatch.setattr(output, "osc_cant_send_text", lambda *a, **k: None)
    return folder


@pytest.fixture
def open_profile(home: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> object:
    """The open profile: Stick button 1 sends to vJoy 2 button 30."""
    from gremlin.profile import Profile

    made = Profile()
    monkeypatch.setattr(shared_state, "current_profile", made)
    _bind(made, _STICK, 1, _vjoy(2, 30))
    return made


def _index(folder: pathlib.Path) -> Iterator[object]:
    """A SearchIndex on this profiles folder (every device plugged in),
    stopped afterwards."""
    from gremlin import search_index

    index = search_index.SearchIndex(folder=folder, plugged=lambda g, n: True)
    try:
        yield index
    finally:
        index.stop()
        index.wait(10.0)


@pytest.fixture
def folder(home: pathlib.Path, monkeypatch: pytest.MonkeyPatch) -> pathlib.Path:
    """A profiles folder with one saved profile: Stick button 2 sends to
    vJoy 3 button 4. Saved before the open profile is made current."""
    from gremlin.profile import Profile

    there = home / "profiles"
    there.mkdir()
    saved = Profile()
    monkeypatch.setattr(shared_state, "current_profile", saved)
    _bind(saved, _STICK, 2, _vjoy(3, 4))
    saved.to_xml(there / "Saved.xml")
    return there


@pytest.fixture
def index(folder: pathlib.Path, open_profile: object) -> Iterator[object]:
    yield from _index(folder)


def _sources(index: object) -> dict[str, object]:
    """The registered sources as {name: lister}."""
    for name in ("sources", "_sources"):
        found = getattr(index, name, None)
        if callable(found):
            found = found()
        if isinstance(found, dict):
            return dict(found)
    pytest.fail("SearchIndex has no sources() to list its registered sources")


def _rebuilt(index: object) -> list:
    """Every row after a full build, waited for (bounded)."""
    index.build()  # type: ignore[attr-defined]
    assert index.wait(10.0), "the index build did not end in 10 s"  # type: ignore[attr-defined]
    return list(index.rows())  # type: ignore[attr-defined]


def test_the_device_library_is_a_registered_source(index: object) -> None:
    assert "Device Library" in _sources(index), sorted(_sources(index))


def test_every_source_yields_well_formed_rows(index: object) -> None:
    for name, lister in _sources(index).items():
        rows = list(lister())  # type: ignore[operator]
        for row in rows:
            _check_row(row)
        assert all(r.source for r in rows), name


def test_the_built_in_places_yield_well_formed_rows(index: object) -> None:
    """The profiles folder and the open profile (built in, not sources)."""
    rows = _rebuilt(index)
    places = {r.source for r in rows}
    assert {"open", "profile"} <= places, places
    assert {r.source_name for r in rows if r.source == "profile"} == {"Saved"}
    for row in rows:
        _check_row(row)
    status = index.status()  # type: ignore[attr-defined]
    assert {"state", "done", "total", "unreadable"} <= set(status)
    assert status["state"] == "ready" and not status["unreadable"], status


# --- 3. go-to handlers -----------------------------------------------------


def _card_kinds() -> set[str]:
    """The kinds Main's registry is keyed by: each built-in device's Home
    card key (device_class.home_key) and "physical" for an external device
    (its card's tab)."""
    builtin = [
        slug
        for table in (device_class.INTERNAL_INPUTS, device_class.INTERNAL_OUTPUTS)
        for _, slug in table.values()
    ]
    return {device_class.home_key(kind) or "physical" for kind in [*builtin, ""]}


def _main_text() -> str:
    return (_ROOT / "qml" / "Main.qml").read_text("utf-8")


def _handler_keys() -> set[str]:
    """Keys of Main's go-to handler registry: the object literal of a
    property (or var) whose name holds "goTo" and "andler"."""
    text = _main_text()
    start = re.search(
        r"(?:property\s+var|var|readonly\s+property\s+var)\s+"
        r"(\w*[gG]o[tT]o\w*[hH]andlers?\w*)\s*[:=]\s*\(?\s*\{",
        text,
    )
    assert start, "Main.qml has no go-to handler registry (…goToHandlers…)"
    depth = 0
    body_start = start.end() - 1
    for at in range(body_start, len(text)):
        ch = text[at]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                body = text[body_start + 1 : at]
                break
    else:
        pytest.fail("Main.qml go-to handler registry is not closed")
    keys: set[str] = set()
    depth = 0
    for line in body.splitlines():
        if depth == 0:
            hit = re.match(r"\s*(?:\"([^\"]*)\"|'([^']*)'|([A-Za-z_]\w*))\s*:", line)
            if hit:
                keys.add(next(g for g in hit.groups() if g is not None))
        depth += line.count("{") + line.count("(") + line.count("[")
        depth -= line.count("}") + line.count(")") + line.count("]")
    return keys


def test_every_device_kind_has_a_go_to_handler() -> None:
    keys = _handler_keys()
    missing = _card_kinds() - keys
    assert not missing, (
        f"Main.qml go-to handler registry lacks {sorted(missing)} (has {sorted(keys)})"
    )


# --- 4. a new action type --------------------------------------------------


def _fake_type() -> type:
    from action_plugins.description import DescriptionData

    class FakeSearchData(DescriptionData):
        """A new action type: only its own references() say what it uses."""

        tag = _FAKE_TAG
        name = "Search Plug Fake"

        def references(self) -> Iterable[Reference]:
            return (
                Reference("sends-output", refs.vjoy(7, B, 99), "Fake sends to vJoy 7"),
            )

    return FakeSearchData


def test_a_new_action_type_shows_up_in_the_index(
    folder: pathlib.Path, open_profile: object
) -> None:
    fake = _fake_type()(B)
    _bind(open_profile, _STICK, 5, fake)
    for index in _index(folder):
        rows = _rebuilt(index)
        ours = [r for r in rows if r.action_tag == _FAKE_TAG]
        assert ours, "a new action type's references() did not reach the index"
        assert any(refs.vjoy(7, B, 99) in r.target_keys for r in ours), ours
        for row in ours:
            _check_row(row)


# --- 5. register_source ----------------------------------------------------


def test_register_source_shows_its_rows(index: object) -> None:
    mine = _row(
        source="plug-test",
        source_name="Plug Test",
        device_name="Fake Device",
        input_label="Button 42",
        text="from a fake source",
        targets=("vJoy 8 Button 3",),
        target_keys=(refs.vjoy(8, B, 3),),
    )
    index.register_source("plug-test", lambda: [mine])  # type: ignore[attr-defined]
    assert "plug-test" in _sources(index)
    rows = _rebuilt(index)
    assert mine in rows
    assert any(r.source == "open" for r in rows), "built-in sources went missing"
