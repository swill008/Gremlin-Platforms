# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Device Bindings Appearance "Copy from device…", end to end on the real
program (batch K, user 2026-10-12 "ok, code it").

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE and three fake sticks (A "pJoy
Pro", B and C), each with button 1 bound to two actions. Before the start
the program settings hold a shared "device-bindings" look (Brackets on, a
target text color). Everything else goes through the page's own controls:

1. Device A: Corners Square, Brackets off, Save Appearance.
2. The title's arrows to B; "Copy from device…" opens a list with
   "Shared Device Bindings look", A and C (not B, not Keyboard, OSC or the
   Logical Device). Picking A shows A's look on B's rows at once with
   nothing saved for B; Save Appearance then writes B's entry as A's.
3. On C: "Copy from device…", "Shared Device Bindings look", Save
   Appearance: C's entry is the shared look.
A's entry is never touched.

Spec: 05 S125; decision D-05-APPEARANCE-COPY-FROM (batch K contract).
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
SHARED_ENTRY = "Shared Device Bindings look"


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


def _square(j: Journey, panel: Any) -> None:  # noqa: ANN401
    corners = _corners(panel)
    index = j.ev("find('Square')", corners)
    assert index is not None and int(index) >= 0, "no Square corner choice"
    j.ev(f"currentIndex = {int(index)}; activated({int(index)}); true", corners)
    j.settle()


def _menu(j: Journey) -> Any:  # noqa: ANN401
    """The "Copy from device…" list (a popup: not always under contentItem)."""
    from PySide6 import QtCore

    found = j.item(j.win, "copyAppearanceMenu")
    if found is None:
        found = j.win.findChild(QtCore.QObject, "copyAppearanceMenu")
    return found


def _open_copy(j: Journey, panel: Any) -> list[tuple[str, Any]]:  # noqa: ANN401
    """Presses "Copy from device…"; the list's visible entries (text, item)."""
    button = _named(panel, "copyAppearanceFrom")
    assert button, "no copyAppearanceFrom button"
    assert _shown(button[0]), "copyAppearanceFrom is hidden"
    j.click(button[0])
    j.settle()
    menu = j.wait_until(lambda: _menu(j), "the copyAppearanceMenu list")
    j.wait_until(
        lambda: bool(menu.property("opened") or menu.property("visible")),
        "the copyAppearanceMenu list to open",
    )
    j.settle()
    root = menu if hasattr(menu, "childItems") else menu.property("contentItem")
    assert root is not None, "the copyAppearanceMenu list has no content"
    entries: list[tuple[str, Any]] = []
    for item in Journey.walk(root):
        text = item.property("text")
        if (
            isinstance(text, str)
            and text
            and item.property("highlighted") is not None
            and item.isVisible()
        ):
            entries.append((text, item))
    return entries


def _pick(j: Journey, entries: list[tuple[str, Any]], text: str) -> None:
    hits = [item for label, item in entries if label == text]
    assert hits, f"no {text!r} in {[label for label, _ in entries]}"
    # AbstractButton.click(): the real press (a MenuItem triggers and closes).
    j.ev("typeof click === 'function' ? click() : clicked(); true", hits[0])
    j.settle()


def _part_a_save(j: Journey) -> None:
    out = j.out
    j.open_device_bindings("pjoy_pro")
    page = _go_to(j, A)
    panel = _db_panel(j, page)
    out["1:scope"] = _scope(panel)
    _square(j, panel)
    j.ev("toggle(); clicked(); true", _brackets(panel))
    j.settle()
    j.click(_button(panel, "Save\nAppearance"))
    j.settle()
    out["1:a"] = _look(j, page)
    out["1:saved"] = _saved()


def _part_copy_a_to_b(j: Journey) -> None:
    out = j.out
    page = _go_to(j, B)
    panel = _db_panel(j, page)
    out["2:scope"] = _scope(panel)
    out["2:before"] = _look(j, page)
    entries = _open_copy(j, panel)
    out["2:entries"] = [label for label, _ in entries]
    _pick(j, entries, A)
    out["2:copied"] = _look(j, page)
    out["2:saved-before-save"] = _saved()
    j.click(_button(panel, "Save\nAppearance"))
    j.settle()
    out["2:after-save"] = _look(j, page)
    out["2:saved"] = _saved()


def _part_shared_to_c(j: Journey) -> None:
    out = j.out
    page = _go_to(j, C)
    panel = _db_panel(j, page)
    out["3:scope"] = _scope(panel)
    entries = _open_copy(j, panel)
    out["3:entries"] = [label for label, _ in entries]
    _pick(j, entries, SHARED_ENTRY)
    out["3:copied"] = _look(j, page)
    out["3:saved-before-save"] = _saved()
    j.click(_button(panel, "Save\nAppearance"))
    j.settle()
    out["3:after-save"] = _look(j, page)
    out["3:saved"] = _saved()
    out["3:a"] = _look(j, _go_to(j, A))


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

    # Button 1 on every stick: two actions, so its row shows a count and boxes.
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
        ("2", _part_copy_a_to_b),
        ("3", _part_shared_to_c),
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
        # The shared look, as Save Appearance stores it.
        window_placement.set_list_appearance(PAGE, dict(SHARED))

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("appearance_copy_from"))


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


def _entry(saved: dict, scope: str) -> Any:  # noqa: ANN401
    return saved.get(f"{PAGE}/{scope}")


def _is_shared(look: dict) -> bool:
    return look["brackets"] is True and look["color"] == SHARED_COLOR


def _is_a(look: dict) -> bool:
    """A's look: square boxes, no brackets, the shared target color."""
    return (
        look["brackets"] is False
        and look["rounded"] is False
        and look["count"] == "2"
        and look["box_radius"] == [0.0, 0.0]
        and look["color"] == SHARED_COLOR
    )


def test_a_saves_its_own_look(run: dict) -> None:
    assert _step(run, "0:saved-at-start").get(PAGE) == SHARED
    scope = _step(run, "1:scope")
    assert scope
    a = _entry(_step(run, "1:saved"), scope)
    assert a is not None, _step(run, "1:saved")
    assert a["bindingsBrackets"] is False and a["bindingTargetRounded"] is False, a
    assert _is_a(_step(run, "1:a")), _step(run, "1:a")


def test_the_list_holds_shared_and_the_other_devices(run: dict) -> None:
    for key, here, other in (("2:entries", B, C), ("3:entries", C, B)):
        entries = _step(run, key)
        assert entries and entries[0] == SHARED_ENTRY, entries
        assert A in entries and other in entries, entries
        assert here not in entries, entries
        for word in ("Keyboard", "OSC", "Logical"):
            assert not any(word in e for e in entries), entries
        assert len(entries) == 3, entries


def test_copy_from_a_shows_at_once_and_saves_only_on_save(run: dict) -> None:
    before = _step(run, "2:before")
    assert _is_shared(before) and before["rounded"] is True, before
    copied = _step(run, "2:copied")
    assert copied["device"] == B and _is_a(copied), copied
    b_scope = _step(run, "2:scope")
    early = _step(run, "2:saved-before-save")
    assert _entry(early, b_scope) is None, early
    assert early == _step(run, "1:saved"), early
    saved = _step(run, "2:saved")
    a_scope = _step(run, "1:scope")
    assert _entry(saved, b_scope) is not None, saved
    assert _entry(saved, b_scope) == _entry(saved, a_scope), saved
    assert _is_a(_step(run, "2:after-save")), _step(run, "2:after-save")


def test_copy_the_shared_look_onto_c(run: dict) -> None:
    copied = _step(run, "3:copied")
    assert copied["device"] == C, copied
    assert _is_shared(copied) and copied["rounded"] is True, copied
    assert copied["count"] == "[2]", copied
    c_scope = _step(run, "3:scope")
    assert _entry(_step(run, "3:saved-before-save"), c_scope) is None
    saved = _step(run, "3:saved")
    c = _entry(saved, c_scope)
    assert c is not None, saved
    for key, value in SHARED.items():
        assert c[key] == value, (key, c)
    assert c.get("bindingTargetRounded", True) is True, c
    assert saved[PAGE] == SHARED, saved
    assert _is_shared(_step(run, "3:after-save")), _step(run, "3:after-save")


def test_a_is_untouched(run: dict) -> None:
    a_scope = _step(run, "1:scope")
    first = _entry(_step(run, "1:saved"), a_scope)
    for key in ("2:saved", "3:saved"):
        assert _entry(_step(run, key), a_scope) == first, key
    assert _is_a(_step(run, "3:a")), _step(run, "3:a")


if __name__ == "__main__":
    main()
