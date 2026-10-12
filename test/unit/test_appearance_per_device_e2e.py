# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Bindings Appearance per device, end to end on the real program
(batch J, user 2026-10-12 "1a 2a 3a").

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE and three fake sticks (A "pJoy
Pro", B and C), each with button 1 bound to two actions. Before the start
the program settings hold a shared "device-bindings" look (Brackets on, a
target text color). Everything else goes through the page's own controls:

1. Device A: Brackets off, Save Appearance: A's row shows "2" and only A's
   entry ("device-bindings/<scope>") is written.
2. The title's next-device arrow to B, then C: both show "[2]" and the
   shared color (no entry of their own).
3. On B: Corners Square, Apply to all devices: the shared entry is B's look
   and every device entry is gone; A and C show square boxes with brackets.
4. Reset Appearance on A: A is back to the defaults (saved as A's own
   entry); B and C keep B's look.
5. The Keyboard page's Appearance still saves under "keyboard", with no
   Apply to all devices button.

Spec: 05 S125; batch J contract (per-device Appearance, 1a 2a 3a).
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
    Journey,
    JourneyIncomplete,
    run_journey,
)

PAGE = "device-bindings"
B1 = "parent:button:1"
A, B, C = "pJoy Pro", "Stick Bravo", "Stick Charlie"
SHARED_COLOR = "#ff6d00"
SHARED = {"bindingsBrackets": True, "bindingTargetTextColor": SHARED_COLOR}


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


def _named(root: Any, name: str) -> list[Any]:  # noqa: ANN401
    return [i for i in Journey.walk(root) if i.objectName() == name]


def _shown(item: Any) -> bool:  # noqa: ANN401
    return item is not None and item.isVisible() and item.width() > 0


def _text_of(item: Any) -> str:  # noqa: ANN401
    value = item.property("text")
    if isinstance(value, str) and value:
        return value
    for child in Journey.walk(item):
        value = child.property("text")
        if isinstance(value, str) and value and child.isVisible():
            return value
    return ""


def _find(root: Any, test: Any) -> Any:  # noqa: ANN401
    for item in Journey.walk(root):
        try:
            if test(item):
                return item
        except Exception:  # noqa: BLE001, S112
            continue
    return None


def _tree(j: Journey) -> Any:  # noqa: ANN401
    """The Device Bindings page's ControlTree (the list, not the find bar)."""

    def find() -> Any:  # noqa: ANN401
        for item in j.walk(j.win.contentItem()):
            if (
                item.property("namePrefix") == "deviceBindings"
                and item.property("dragMime") is not None
                and item.isVisible()
            ):
                return item
        return None

    return j.wait_until(find, "the Device Bindings list")


def _row(tree: Any, key: str) -> Any:  # noqa: ANN401
    for item in Journey.walk(tree):
        if item.property("key") == key and item.property("shown") is not None:
            return item
    return None


def _look(j: Journey, page: Any) -> dict:  # noqa: ANN401
    """What the shown device's list and its button 1 row look like now."""
    tree = _tree(j)
    j.wait_until(lambda: _row(tree, B1) is not None, "button 1's row")
    j.settle()
    row = _row(tree, B1)
    counts = [i for i in _named(row, "bindingsCount") if _shown(i)]
    boxes = [i for i in _named(row, "bindingBox") if _shown(i)]
    color = tree.property("bindingTargetTextColor")
    return {
        "device": str(page.property("deviceName") or ""),
        "count": _text_of(counts[0]) if counts else None,
        "box_radius": [float(b.property("radius") or 0) for b in boxes],
        "brackets": tree.property("bindingsBrackets"),
        "rounded": tree.property("bindingTargetRounded"),
        "color": color.name().lower() if color else None,
    }


def _saved() -> dict:
    from gremlin.ui import window_placement

    return window_placement._all_list_appearances()


def _panel(j: Journey, page: Any, name: str, button: str) -> Any:  # noqa: ANN401
    """The page's Appearance panel, opened with the page bar's
    "Appearance…" when hidden; its Bindings section unfolded."""
    panel = j.item(j.win, name)
    assert panel is not None, f"no {name} panel"
    if not panel.isVisible():
        bar = j.wait_until(lambda: j.item(j.win, button), f"the {button} button")
        assert _text_of(bar) == "Appearance…", _text_of(bar)
        j.click(bar)
        j.wait_until(panel.isVisible, "the Appearance panel")
    fold = _find(
        panel,
        lambda i: i.property("title") == "Bindings" and i.property("open") is not None,
    )
    assert fold is not None, "no Bindings section in the Appearance panel"
    if not fold.property("open"):
        j.ev("toggled(true); true", fold)
        j.settle()
    return panel


def _db_panel(j: Journey, page: Any) -> Any:  # noqa: ANN401
    return _panel(j, page, "deviceBindingsAppearance", "deviceBindingsAppearanceButton")


def _brackets(panel: Any) -> Any:  # noqa: ANN401
    box = _find(
        panel,
        lambda i: i.property("text") == "Brackets"
        and i.property("checked") is not None,
    )
    assert box is not None, "no Brackets checkbox"
    return box


def _corners(panel: Any) -> Any:  # noqa: ANN401
    label = _find(
        panel,
        lambda i: str(i.property("text") or "").startswith("Corners")
        and i.property("checked") is None
        and i.property("currentIndex") is None,
    )
    assert label is not None, "no Corners row"
    combo = _find(
        label.parentItem(),
        lambda i: i is not label and i.property("currentIndex") is not None,
    )
    assert combo is not None, "no Corners choice"
    return combo


def _button(panel: Any, text: str) -> Any:  # noqa: ANN401
    found = _find(
        panel,
        lambda i: str(i.property("text") or "") == text
        and i.property("highlighted") is not None
        and i.isVisible(),
    )
    assert found is not None, f"no {text!r} button"
    return found


def _apply_all(panel: Any) -> Any:  # noqa: ANN401
    found = _named(panel, "applyAppearanceAll")
    return found[0] if found else None


def _arrow(j: Journey, glyph: str) -> Any:  # noqa: ANN401
    """The title's previous ("") or next ("") device arrow
    (Main.qml, "Previous/Next input module")."""
    return _find(
        j.win.contentItem(),
        lambda i: i.property("text") == glyph
        and i.isVisible()
        and i.property("enabled"),
    )


def _go_to(j: Journey, name: str) -> Any:  # noqa: ANN401
    """Steps with the title's device arrows until the Device Bindings page
    shows name. The steps stay between the sticks (towards name in the
    cycle's order, never round the end): past the last stick the cycle
    reaches the Logical Device page, which hides the arrows."""
    from gremlin.modules.registry import plain_slug

    hops: list = []
    for _ in range(6):
        page = j.ev("deviceBindingsPane()")
        if (
            page is not None
            and page.isVisible()
            and page.property("deviceName") == name
        ):
            tree = _tree(j)
            j.wait_until(lambda: _row(tree, B1) is not None, f"{name}'s rows")
            j.settle()
            return page
        order = [str(s) for s in j.ev("_moduleModel.pileLeaders('source')")]
        here = str(j.ev("_moduleModel.focusedSlug"))
        hops.append(here)
        step = 1 if order.index(plain_slug(name)) > order.index(here) else -1
        arrow = _arrow(j, "" if step > 0 else "")
        assert arrow is not None, f"no device arrow on {here}"
        j.click(arrow)
        j.settle()
    raise AssertionError(f"the arrows never reached {name}: {hops}")


def _scope(panel: Any) -> str:  # noqa: ANN401
    return str(panel.property("scopeKey") or "")


def _part_a_save(j: Journey) -> None:
    out = j.out
    j.open_device_bindings("pjoy_pro")
    page = _go_to(j, A)
    panel = _db_panel(j, page)
    out["1:start"] = _look(j, page)
    out["1:scope"] = _scope(panel)
    apply = _apply_all(panel)
    out["1:apply-shown"] = bool(apply is not None and _shown(apply))
    j.ev("toggle(); clicked(); true", _brackets(panel))
    j.settle()
    j.click(_button(panel, "Save\nAppearance"))
    j.settle()
    out["1:after-save"] = _look(j, page)
    out["1:saved"] = _saved()


def _part_b_c(j: Journey) -> None:
    out = j.out
    for name, tag in ((B, "b"), (C, "c")):
        page = _go_to(j, name)
        panel = _db_panel(j, page)
        out[f"2:{tag}"] = _look(j, page)
        out[f"2:{tag}-scope"] = _scope(panel)


def _part_apply(j: Journey) -> None:
    out = j.out
    page = _go_to(j, B)
    panel = _db_panel(j, page)
    corners = _corners(panel)
    index = j.ev("find('Square')", corners)
    assert index is not None and int(index) >= 0, "no Square corner choice"
    j.ev(f"currentIndex = {int(index)}; activated({int(index)}); true", corners)
    j.settle()
    out["3:b-before"] = _look(j, page)
    apply = _apply_all(panel)
    assert apply is not None, "no applyAppearanceAll button"
    out["3:apply-text"] = _text_of(apply)
    j.click(apply)
    j.settle()
    out["3:saved"] = _saved()
    out["3:b"] = _look(j, page)
    for name, tag in ((C, "c"), (A, "a")):
        out[f"3:{tag}"] = _look(j, _go_to(j, name))


def _part_reset(j: Journey) -> None:
    out = j.out
    page = _go_to(j, A)
    panel = _db_panel(j, page)
    out["4:a-scope"] = _scope(panel)
    j.click(_button(panel, "Reset\nAppearance"))
    j.settle()
    out["4:a"] = _look(j, page)
    out["4:saved"] = _saved()
    for name, tag in ((B, "b"), (C, "c")):
        out[f"4:{tag}"] = _look(j, _go_to(j, name))
    # Back on A: still the defaults (its own entry, not the shared look).
    out["4:a-again"] = _look(j, _go_to(j, A))


def _part_keyboard(j: Journey) -> None:
    out = j.out
    j.ev('openDeviceBindingsForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(
        lambda: j.backend.uiState.currentTab == "keyboard", "the Keyboard page"
    )
    j.settle()
    page = j.ev("keyboardPane()")
    panel = _panel(j, page, "keyboardAppearance", "keyboardAppearanceButton")
    out["5:scope"] = _scope(panel)
    apply = _apply_all(panel)
    out["5:apply-shown"] = bool(apply is not None and _shown(apply))
    before = _saved()
    j.ev("toggle(); clicked(); true", _brackets(panel))
    j.settle()
    j.click(_button(panel, "Save\nAppearance"))
    j.settle()
    after = _saved()
    out["5:keyboard"] = after.get("keyboard")
    out["5:keyboard-scoped"] = [k for k in after if k.startswith("keyboard/")]
    out["5:others-kept"] = {k: v for k, v in after.items() if k != "keyboard"} == {
        k: v for k, v in before.items() if k != "keyboard"
    }


def _action(name: str, vjoy_button: int = 0) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        name, InputType.JoystickButton
    )
    if name == "Map to vJoy":
        action.vjoy_device_id = 1
        action.vjoy_input_id = vjoy_button
        action.vjoy_input_type = InputType.JoystickButton
    return action


def story(j: Journey) -> None:
    from gremlin.signal import signal
    from gremlin.types import InputType

    for n, name in enumerate((A, B, C)):
        uid = j.stick(name).device_guid.uuid
        item = j.profile.get_input_item(
            uid, InputType.JoystickButton, 1, "Default", True
        )
        root = item.add_item_binding().root_action
        for action in (_action("Map to vJoy", 3 + n), _action("Map to Xbox")):
            root.insert_action(action, "children")
    signal.profileChanged.emit()
    j.settle()
    j.out["0:saved-at-start"] = _saved()
    for name, part in (
        ("1", _part_a_save),
        ("2", _part_b_c),
        ("3", _part_apply),
        ("4", _part_reset),
        ("5", _part_keyboard),
    ):
        with _Part(j, name):
            part(j)


def main() -> None:
    def before(j: Journey) -> None:
        from gremlin.ui import window_placement

        bravo = j.add_stick(B, 21)
        charlie = j.add_stick(C, 22)
        j.input_module(buttons=[1, 2])
        j.input_module(B, buttons=[1, 2], guid=bravo)
        j.input_module(C, buttons=[1, 2], guid=charlie)
        j.vjoy_module()
        # The shared look, as Save Appearance stored it before this batch.
        window_placement.set_list_appearance(PAGE, dict(SHARED))

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("appearance_per_device"))


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


def _scoped(saved: dict) -> dict:
    return {k: v for k, v in saved.items() if k.startswith(PAGE + "/")}


def _is_shared(look: dict) -> bool:
    return look["brackets"] is True and look["color"] == SHARED_COLOR


def test_the_shared_look_is_there_at_the_start(run: dict) -> None:
    saved = _step(run, "0:saved-at-start")
    assert saved.get(PAGE) == SHARED, saved
    start = _step(run, "1:start")
    assert start["device"] == A, start
    assert _is_shared(start) and start["count"] == "[2]", start


def test_each_device_has_its_own_scope_and_the_apply_button(run: dict) -> None:
    scopes = [_step(run, "1:scope"), _step(run, "2:b-scope"), _step(run, "2:c-scope")]
    assert all(scopes), scopes
    assert len(set(scopes)) == 3, scopes
    assert _step(run, "1:apply-shown") is True


def test_save_on_a_writes_only_a(run: dict) -> None:
    look = _step(run, "1:after-save")
    assert look["brackets"] is False and look["count"] == "2", look
    saved = _step(run, "1:saved")
    assert saved.get(PAGE) == SHARED, saved
    scope = _step(run, "1:scope")
    assert list(_scoped(saved)) == [f"{PAGE}/{scope}"], saved
    assert saved[f"{PAGE}/{scope}"]["bindingsBrackets"] is False, saved


def test_b_and_c_keep_the_shared_look(run: dict) -> None:
    for tag, name in (("b", B), ("c", C)):
        look = _step(run, f"2:{tag}")
        assert look["device"] == name, look
        assert look["count"] == "[2]", look
        assert _is_shared(look), look


def test_apply_to_all_devices_gives_every_device_bs_look(run: dict) -> None:
    # On two lines, like Save Appearance.
    assert " ".join(_step(run, "3:apply-text").split()) == "Apply to all devices"
    b_before = _step(run, "3:b-before")
    assert b_before["rounded"] is False and _is_shared(b_before), b_before
    saved = _step(run, "3:saved")
    assert _scoped(saved) == {}, saved
    assert saved[PAGE]["bindingTargetRounded"] is False, saved
    assert saved[PAGE]["bindingsBrackets"] is True, saved
    for tag in ("b", "c", "a"):
        look = _step(run, f"3:{tag}")
        assert look["count"] == "[2]", (tag, look)
        assert look["rounded"] is False, (tag, look)
        assert look["box_radius"] == [0.0, 0.0], (tag, look)
        assert _is_shared(look), (tag, look)


def test_reset_on_a_resets_only_a(run: dict) -> None:
    for key in ("4:a", "4:a-again"):
        look = _step(run, key)
        assert look["device"] == A, look
        assert look["brackets"] is True and look["rounded"] is True, look
        assert look["color"] != SHARED_COLOR, look
        assert look["count"] == "[2]", look
        assert all(r > 0 for r in look["box_radius"]), look
    saved = _step(run, "4:saved")
    scope = _step(run, "4:a-scope")
    assert scope == _step(run, "1:scope")
    assert list(_scoped(saved)) == [f"{PAGE}/{scope}"], saved
    assert saved[PAGE]["bindingTargetRounded"] is False, saved
    for tag in ("b", "c"):
        look = _step(run, f"4:{tag}")
        assert look["rounded"] is False and _is_shared(look), (tag, look)


def test_the_keyboard_page_still_saves_under_keyboard(run: dict) -> None:
    assert _step(run, "5:scope") == ""
    assert _step(run, "5:apply-shown") is False
    keyboard = _step(run, "5:keyboard")
    assert isinstance(keyboard, dict) and keyboard["bindingsBrackets"] is False
    assert _step(run, "5:keyboard-scoped") == []
    assert _step(run, "5:others-kept") is True


if __name__ == "__main__":
    main()
