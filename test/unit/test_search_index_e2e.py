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

Spec: 01 S157-S164, D-01-SEARCH-INDEX; batch R contract item 8.
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
        lambda: _index(model).status().get("state") == "ready"
        and _index(model).rows(),
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


def _bind(j: Journey, device: Any, kind: Any, control: Any, action: Any) -> None:  # noqa: ANN401
    item = j.profile.get_input_item(device, kind, control, "Default", True)
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


def test_no_program_errors(run: dict) -> None:
    assert run.get("_errors") == [], run.get("_errors")
    assert "error" not in run, run.get("traceback")


if __name__ == "__main__":
    main()
