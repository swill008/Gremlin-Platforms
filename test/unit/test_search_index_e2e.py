# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Search, the real one (batch R, D-01-SEARCH-INDEX), end to end.

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake "pJoy Pro" stick and
vJoy 1 and 2 (vJoy 2 has 56 buttons). Three sources:

- profiles/Alpha.xml (saved): the stick's Buttons 1 and 2 both send vJoy 1
  Button 5 in Default (Used twice), Button 3 presses the key F5, Button 4
  sends vJoy 2 Button 60 (vJoy 2 has 56: Binding output not found), Button 5
  speaks "Gremlin toggle", Button 6 speaks "press F5 to reload" (F5 only
  as words, not as a key);
- profiles/Bravo.xml (saved): the key F5 sends vJoy 1 Button 9; the stick's
  Button 2 sends vJoy 1 Button 5 once (no clash: Used twice is per profile);
- the open profile (unsaved): the key F5 sends vJoy 1 Button 11;
- a Device Library setup of the stick, from Alpha.

Through the real Search window (Main.openSearch) and its SearchModel, on
the real SearchIndex and search_query:

1. "F5" finds rows from all four places, each saying its profile.
2. "gr tog" finds "Gremlin toggle" (fuzzy, in order).
3. Regex on: "^Button [12]$" finds Buttons 1 and 2 only; off, it finds none.
4. "key:F5" finds the key rows, not the "press F5" note.
5. Alpha's Buttons 1 and 2 are tagged Used twice; Bravo's Button 2 is not.
6. The Binding output not found filter shows Alpha's Button 4 only.
7. Listen: a stick press fills the box; an OSC message fills it too.
8. Opening a Bravo result asks to save the open profile (answered
   Discard), loads Bravo and shows the row's input.
9. A typo finds nothing and says "Did you mean …?".

Charlie (saved, batch R2: SEARCH-NOTES-DETAIL, SEARCH-INHERIT) has the
mode Ground under Default. Default: the stick's Button 1 sends vJoy 2
Button 3, Button 8 sends vJoy 2 Button 7, Button 9 sends vJoy 2 Button 8,
Button 10 has the Description "Flaps lowered gently here". Ground: Button 2
sends vJoy 2 Button 3 and Button 9 (its own binding) sends vJoy 2 Button 10.

10. "flaps gently" finds the Description row and its detail shows the note.
11. vJoy 2 Button 7 is found in Default and in Ground, the Ground row tagged
    Inherited from Default; vJoy 2 Button 8 is not found in Ground (Ground
    has its own Button 9).
12. In Ground, the inherited Button 1 and Ground's Button 2 both send vJoy 2
    Button 3: both Used twice there; Default's Button 1 alone is not.

Spec: 01 S157-S164, D-01-SEARCH-INDEX; batch R contract item 8;
batch R2 (SEARCH-NOTES-DETAIL, SEARCH-INHERIT).
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    RIG,
    Journey,
    JourneyIncomplete,
    run_journey,
)

STICK = "pJoy Pro"
F5 = (0x3F, False)


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """One part of the story; an error is recorded under its name and the
    next part still runs."""

    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()
        return True


def _get(row: dict, *names: str) -> Any:  # noqa: ANN401
    for name in names:
        if name in row and row[name] is not None:
            return row[name]
    return None


def _brief(row: dict) -> dict:
    """What the checks read of one result row."""
    return {
        "source": str(_get(row, "source") or ""),
        "profile": str(_get(row, "sourceName", "source_name") or ""),
        "device": str(_get(row, "deviceName", "device_name") or ""),
        "mode": str(_get(row, "mode") or ""),
        "input": str(_get(row, "inputLabel", "input_label") or ""),
        "text": str(_get(row, "text") or ""),
        "targets": [str(t) for t in (_get(row, "targets") or [])],
        "usedTwice": bool(_get(row, "usedTwice", "used_twice")),
        "notFound": bool(_get(row, "notFound", "not_found")),
        "inheritedFrom": str(_get(row, "inheritedFrom", "inherited_from") or ""),
        "tags": [str(t) for t in (_get(row, "tags") or [])],
    }


def _model(window: Any) -> Any:  # noqa: ANN401
    from gremlin.ui.search_model import SearchModel

    found = window.findChild(SearchModel)
    assert found is not None, "no SearchModel in the Search window"
    return found


def _results(model: Any) -> list[dict]:  # noqa: ANN401
    """The result rows (not the profile and device group rows)."""
    rows = Journey.catalog_rows(model)
    return [
        {**_brief(r), "_row": n}
        for n, r in enumerate(rows)
        if str(r.get("rowKind") or "") == "result"
    ]


def _index(model: Any) -> Any:  # noqa: ANN401
    """The index the window searches."""
    return model.search_index()


def _ready(j: Journey, model: Any) -> None:  # noqa: ANN401
    """The index has read every place (it is built in the background)."""
    j.wait_until(
        lambda: _index(model).status().get("state") == "ready" and _index(model).rows(),
        "the search index to be built",
        timeout=30.0,
    )
    j.settle()


def _search(j: Journey, model: Any, text: str, **toggles: bool) -> list[dict]:  # noqa: ANN401
    """Types text (after the toggles) and waits out the typing debounce."""
    for name in ("matchCase", "wholeWord", "regex"):
        model.setProperty(name, bool(toggles.get(name, False)))
    model.setProperty("text", text)
    j.wait_until(
        lambda: not model._debounce.isActive(), "the typed search to run", timeout=5.0
    )
    j.settle()
    return _results(model)


# --- the parts -----------------------------------------------------------------


def _part_all_sources(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["1:rows"] = _search(j, model, "F5")
    j.out["1:status"] = str(model.property("statusText") or "")


def _part_fuzzy(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["2:rows"] = _search(j, model, "gr tog")
    # Letters in order with gaps (no term is a plain substring).
    j.out["2:scattered"] = _search(j, model, "grml tggl")


def _part_regex(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["3:on"] = _search(j, model, "^Button [12]$", regex=True)
    j.out["3:off"] = _search(j, model, "^Button [12]$")


def _part_key_prefix(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["4:plain"] = _search(j, model, "F5")
    j.out["4:key"] = _search(j, model, "key:F5")


def _part_used_twice(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["5:rows"] = _search(j, model, 'vjoy:"vJoy 1 Button 5"')


def _part_not_found(j: Journey, model: Any) -> None:  # noqa: ANN401
    _search(j, model, "")
    j.out["6:none"] = _results(model)
    model.setFilter("notFound", True)
    j.settle()
    j.out["6:all"] = len(_index(model).rows())
    j.out["6:rows"] = _results(model)
    model.clearFilters()
    j.settle()


def _part_listen(j: Journey, window: Any, model: Any) -> None:  # noqa: ANN401
    from gremlin.osc import OscRuntime

    _search(j, model, "")
    model.listen()
    j.settle()
    j.out["7:listening"] = bool(model.property("listening"))
    stick = j.stick(STICK)
    j.press(stick, 7, True)
    j.press(stick, 7, False)
    j.await_value(lambda: bool(model.property("text")), True, timeout=5.0)
    j.out["7:stick"] = str(model.property("text") or "")
    j.out["7:heard"] = str(model.property("heardText") or "")
    j.out["7:after"] = bool(model.property("listening"))
    model.stopListen()

    # OSC, Listen for OSC messages off (the journey's default): Listen says
    # so and a message fills nothing.
    model.setProperty("text", "")
    j.settle()
    runtime = OscRuntime()
    j.out["7:osc-on"] = runtime.listenInfo().get("state") == "listening"
    model.listen()
    j.settle()
    j.out["7:osc-error"] = str(model.property("listenError") or "")
    runtime.incoming.emit("/fire", [1.0], ("127.0.0.1", 9000))
    j.settle()
    j.out["7:osc-off-text"] = str(model.property("text") or "")
    model.stopListen()
    j.settle()

    # OSC on (a stand-in for the listening port): the message fills the box.
    real = runtime.listenInfo
    runtime.listenInfo = lambda: {**real(), "state": "listening"}
    try:
        model.listen()
        j.settle()
        j.out["7:osc-on-error"] = str(model.property("listenError") or "")
        runtime.incoming.emit("/fire", [1.0], ("127.0.0.1", 9000))
        j.await_value(lambda: bool(model.property("text")), True, timeout=3.0)
        j.out["7:osc"] = str(model.property("text") or "")
        model.stopListen()
    finally:
        runtime.listenInfo = real
    j.settle()


def _part_open_other(j: Journey, window: Any, model: Any, bravo: str) -> None:  # noqa: ANN401
    rows = _search(j, model, 'vjoy:"vJoy 1 Button 5"')
    target = [r for r in rows if r["profile"] == "Bravo"]
    assert target, f"no Bravo result among {rows}"
    j.out["8:dirty"] = bool(j.backend.profileContainsUnsavedChanges)
    n = target[0]["_row"]
    j.out["8:row"] = target[0]
    # The window's Open (Enter, a double-click, the detail pane's Open).
    j.ev(f"open({n}); true", window)
    j.wait_until(
        lambda: j.ev("_saveBeforeContinueDialog.pendingAction !== null"),
        "the save question",
        timeout=8.0,
    )
    j.out["8:asked"] = True
    j.ev("_saveBeforeContinueDialog.discardChosen(); true")
    j.wait_until(
        lambda: pathlib.Path(j.backend.profilePath()).name == "Bravo.xml",
        "Bravo to load",
        timeout=10.0,
    )
    j.wait_until(
        lambda: j.ev(
            "(function() { var p = deviceBindingsPane(); "
            'return !!p && p.paneKey === "parent:button:2" })()'
        ),
        "Bravo's Button 2 shown",
        timeout=10.0,
    )
    j.settle()
    j.out["8:profile"] = pathlib.Path(j.backend.profilePath()).name
    j.out["8:at"] = j.ev(
        "(function() { var p = deviceBindingsPane(); return { "
        "tab: uiState.currentTab, mode: uiState.currentMode, "
        'pane: p ? p.paneKey : "" } })()'
    )
    j.out["8:bravo"] = bravo


def _part_did_you_mean(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["9:rows"] = _search(j, model, "Bxtton")
    j.out["9:dym"] = str(model.property("didYouMean") or "")


def _part_notes(j: Journey, model: Any) -> None:  # noqa: ANN401
    rows = _search(j, model, "flaps gently")
    j.out["10:rows"] = rows
    hit = [r for r in rows if r["profile"] == "Charlie" and r["mode"] == "Default"]
    assert hit, f"no Charlie row among {rows}"
    detail = dict(model.detail(hit[0]["_row"]))
    j.out["10:notes"] = [str(n) for n in (detail.get("notes") or [])]


def _part_inherited(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["11:inherited"] = _search(j, model, 'vjoy:"vJoy 2 Button 7"')
    rows = [r for r in j.out["11:inherited"] if r["mode"] == "Ground"]
    if rows:  # the detail of the row on show now, before the next search
        j.out["11:detail"] = dict(model.detail(rows[0]["_row"])).get("inheritedFrom")
    j.out["11:overridden"] = _search(j, model, 'vjoy:"vJoy 2 Button 8"')
    j.out["11:own"] = _search(j, model, 'vjoy:"vJoy 2 Button 10"')


def _part_used_twice_inherited(j: Journey, model: Any) -> None:  # noqa: ANN401
    j.out["12:rows"] = _search(j, model, 'vjoy:"vJoy 2 Button 3"')


# --- the profiles ---------------------------------------------------------------


def _vjoy(vjoy: int, button: int) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = vjoy
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _note(text: str) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Text to Speech", InputType.JoystickButton
    )
    action.text = text
    return action


def _f5_key() -> Any:  # noqa: ANN401
    from gremlin import keyboard, plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Map to Keyboard", InputType.JoystickButton
    )
    action.keys = [keyboard.key_from_code(*F5)]
    return action


def _description(text: str) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Description", InputType.JoystickButton
    )
    action.description = text
    return action


def _bind(
    j: Journey,
    device: Any,  # noqa: ANN401
    kind: Any,  # noqa: ANN401
    control: Any,  # noqa: ANN401
    action: Any,  # noqa: ANN401
    mode: str = "Default",
) -> None:
    item = j.profile.get_input_item(device, kind, control, mode, True)
    item.add_item_binding().root_action.insert_action(action, "children")


def _save_as(j: Journey, name: str) -> pathlib.Path:
    from PySide6 import QtCore

    from gremlin import util

    path = pathlib.Path(util.profiles_dir()) / f"{name}.xml"
    url = QtCore.QUrl.fromLocalFile(str(path)).toString()
    assert j.backend.saveProfile(url), f"{name} was not saved"
    return path


def _profiles(j: Journey) -> dict:
    import dill
    from gremlin import device_library
    from gremlin.signal import signal
    from gremlin.types import InputType

    B, K = InputType.JoystickButton, InputType.Keyboard
    uid = j.stick(STICK).device_guid.uuid

    _bind(j, uid, B, 1, _vjoy(1, 5))
    _bind(j, uid, B, 2, _vjoy(1, 5))
    _bind(j, uid, B, 3, _f5_key())
    _bind(j, uid, B, 4, _vjoy(2, 60))
    _bind(j, uid, B, 5, _note("Gremlin toggle"))
    _bind(j, uid, B, 6, _note("press F5 to reload"))
    signal.profileChanged.emit()
    alpha = _save_as(j, "Alpha")
    saved = device_library.save_setup(STICK, str(j.stick(STICK).device_guid), [alpha])
    j.out["0:library"] = bool(saved.get("ok", True))

    j.backend.newProfile()
    j.profile.modes.add_mode("Ground")
    j.profile.modes.set_parent("Ground", "Default")
    _bind(j, uid, B, 1, _vjoy(2, 3))
    _bind(j, uid, B, 8, _vjoy(2, 7))
    _bind(j, uid, B, 9, _vjoy(2, 8))
    _bind(j, uid, B, 10, _description("Flaps lowered gently here"))
    _bind(j, uid, B, 2, _vjoy(2, 3), "Ground")
    _bind(j, uid, B, 9, _vjoy(2, 10), "Ground")
    signal.profileChanged.emit()
    _save_as(j, "Charlie")

    j.backend.newProfile()
    _bind(j, dill.UUID_Keyboard, K, F5, _vjoy(1, 9))
    _bind(j, uid, B, 2, _vjoy(1, 5))
    signal.profileChanged.emit()
    bravo = _save_as(j, "Bravo")

    j.backend.newProfile()
    _bind(j, dill.UUID_Keyboard, K, F5, _vjoy(1, 11))
    signal.profileChanged.emit()
    j.settle()
    j.out["0:open-unsaved"] = bool(j.backend.profileContainsUnsavedChanges)
    return {"alpha": str(alpha), "bravo": str(bravo)}


def story(j: Journey) -> None:
    files = _profiles(j)
    window = j.ev('_root.openSearch("")')
    assert window is not None, "openSearch gave no window"
    model = _model(window)
    _ready(j, model)
    j.out["0:window"] = str(window.title())
    for name, part in (
        ("1", lambda: _part_all_sources(j, model)),
        ("2", lambda: _part_fuzzy(j, model)),
        ("3", lambda: _part_regex(j, model)),
        ("4", lambda: _part_key_prefix(j, model)),
        ("5", lambda: _part_used_twice(j, model)),
        ("6", lambda: _part_not_found(j, model)),
        ("9", lambda: _part_did_you_mean(j, model)),
        ("10", lambda: _part_notes(j, model)),
        ("11", lambda: _part_inherited(j, model)),
        ("12", lambda: _part_used_twice_inherited(j, model)),
        ("7", lambda: _part_listen(j, window, model)),
        ("8", lambda: _part_open_other(j, window, model, files["bravo"])),
    ):
        with _Part(j, name):
            part()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module(1)
        j.vjoy_module(2)

    Journey(before, vjoy_ids=RIG["vjoy_ids"]).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("search_index_e2e"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {out.get(part + ':error', out.get('error', '(none)'))}\n"
        f"{out.get(part + ':traceback', out.get('traceback', ''))}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


def _where(rows: list[dict]) -> set[tuple[str, str]]:
    return {(r["source"], r["profile"]) for r in rows}


def test_the_profiles_are_set_up(run: dict) -> None:
    assert _step(run, "0:library") is True
    assert _step(run, "0:open-unsaved") is True
    assert _step(run, "0:window").startswith("Search")


def test_f5_finds_rows_in_every_profile_the_open_one_and_the_library(
    run: dict,
) -> None:
    rows = _step(run, "1:rows")
    sources = {r["source"] for r in rows}
    assert sources == {"profile", "open", "library"}, rows
    profiles = {r["profile"] for r in rows if r["source"] == "profile"}
    assert profiles == {"Alpha", "Bravo"}, rows
    # Every row says where it is.
    assert all(r["profile"] for r in rows), rows


def test_gr_tog_finds_gremlin_toggle(run: dict) -> None:
    rows = _step(run, "2:rows")
    assert rows, "nothing found for 'gr tog'"
    assert any("Gremlin toggle" in r["text"] for r in rows), rows
    # In order: "press F5 to reload" has no g...r...t...o...g in order.
    assert not any("press F5" in r["text"] for r in rows), rows


def test_fuzzy_finds_letters_in_order_with_gaps(run: dict) -> None:
    rows = _step(run, "2:scattered")
    assert rows, "nothing found for 'grml tggl'"
    assert all("Gremlin toggle" in r["text"] for r in rows), rows


def test_regex_finds_buttons_1_and_2_and_off_it_is_plain_text(run: dict) -> None:
    on = _step(run, "3:on")
    assert {r["input"] for r in on} == {"Button 1", "Button 2"}, on
    assert _step(run, "3:off") == [], "regex off: the pattern is plain text"


def test_key_prefix_finds_keys_not_words(run: dict) -> None:
    plain = _step(run, "4:plain")
    keyed = _step(run, "4:key")
    assert any("press F5" in r["text"] for r in plain), plain
    assert keyed, "key:F5 found nothing"
    # The F5 key itself, in Bravo and in the open profile.
    keys = {(r["source"], r["profile"]) for r in keyed if r["input"] == "F5"}
    assert {("profile", "Bravo"), ("open", "Untitled")} <= keys, keyed
    assert not any("press F5" in r["text"] for r in keyed), keyed
    assert len(keyed) < len(plain), (keyed, plain)


def test_two_inputs_sending_the_same_button_are_used_twice(run: dict) -> None:
    rows = _step(run, "5:rows")
    alpha = {r["input"]: r["usedTwice"] for r in rows if r["profile"] == "Alpha"}
    assert alpha.get("Button 1") is True and alpha.get("Button 2") is True, rows
    bravo = [r for r in rows if r["profile"] == "Bravo"]
    assert bravo and not any(r["usedTwice"] for r in bravo), rows


def test_binding_output_not_found_filter(run: dict) -> None:
    rows = _step(run, "6:rows")
    assert _step(run, "6:all") > len(rows), "the filter left every row"
    assert rows, "the filter found nothing"
    assert all(r["notFound"] for r in rows), rows
    assert {(r["profile"], r["input"]) for r in rows if r["source"] == "profile"} == {
        ("Alpha", "Button 4")
    }, rows


def test_listen_fills_the_box_from_a_stick_and_osc(run: dict) -> None:
    assert _step(run, "7:listening") is True
    stick = _step(run, "7:stick")
    assert "Button 7" in stick and STICK in stick, stick
    assert _step(run, "7:heard").startswith("Heard: "), run["7:heard"]
    assert run["7:after"] is False, "Listen stops after the first input"
    assert _step(run, "7:osc-on") is False
    assert "Listen for OSC messages is off" in run["7:osc-error"], run["7:osc-error"]
    assert run["7:osc-off-text"] == "", run["7:osc-off-text"]
    assert _step(run, "7:osc-on-error") == ""
    assert _step(run, "7:osc") == 'osc:"/fire"', run["7:osc"]


def test_opening_a_result_in_another_profile_asks_then_goes_there(run: dict) -> None:
    assert _step(run, "8:dirty") is True
    assert _step(run, "8:asked") is True
    assert _step(run, "8:profile") == "Bravo.xml"
    at = _step(run, "8:at")
    assert at["pane"] == "parent:button:2", at
    assert at["mode"] == "Default", at


def test_nothing_found_says_did_you_mean(run: dict) -> None:
    assert _step(run, "9:rows") == []
    assert "Button" in _step(run, "9:dym"), run["9:dym"]


def test_a_description_is_found_by_its_words_and_shown_in_the_detail(
    run: dict,
) -> None:
    rows = [r for r in _step(run, "10:rows") if r["profile"] == "Charlie"]
    # Ground inherits it, so it shows there too.
    assert _at(rows) == {
        ("Default", "Button 10", ""),
        ("Ground", "Button 10", "Default"),
    }, rows
    assert "Flaps lowered gently here" in _step(run, "10:notes"), run["10:notes"]


def _at(rows: list[dict]) -> set[tuple[str, str, str]]:
    """(mode, input, inherited from) of Charlie's rows."""
    return {
        (r["mode"], r["input"], r["inheritedFrom"])
        for r in rows
        if r["profile"] == "Charlie"
    }


def test_a_child_mode_shows_the_binding_it_inherits(run: dict) -> None:
    rows = _step(run, "11:inherited")
    assert _at(rows) == {
        ("Default", "Button 8", ""),
        ("Ground", "Button 8", "Default"),
    }, rows
    ground = [r for r in rows if r["profile"] == "Charlie" and r["mode"] == "Ground"]
    assert all("inherited" in r["tags"] for r in ground), ground
    own = [r for r in rows if r["profile"] == "Charlie" and r["mode"] == "Default"]
    assert not any("inherited" in r["tags"] for r in own), own
    assert _step(run, "11:detail") == "Default"


def test_a_child_mode_that_binds_the_input_itself_inherits_nothing(
    run: dict,
) -> None:
    assert _at(_step(run, "11:overridden")) == {("Default", "Button 9", "")}
    assert _at(_step(run, "11:own")) == {("Ground", "Button 9", "")}


def test_used_twice_counts_an_inherited_binding(run: dict) -> None:
    rows = [r for r in _step(run, "12:rows") if r["profile"] == "Charlie"]
    seen = {(r["mode"], r["input"], r["inheritedFrom"]): r["usedTwice"] for r in rows}
    assert seen == {
        ("Default", "Button 1", ""): False,
        ("Ground", "Button 1", "Default"): True,
        ("Ground", "Button 2", ""): True,
    }, rows


def test_no_program_errors(run: dict) -> None:
    assert run.get("_errors") == [], run.get("_errors")
    assert "error" not in run, run.get("traceback")


if __name__ == "__main__":
    main()
