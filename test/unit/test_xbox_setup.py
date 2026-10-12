# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Xbox Setup (D-XBOX-PADS): "Xbox Setup…" only on the Xbox card's menu and
in the command palette, Main opens the window (card, palette, the Xbox
Output View's link), the model reads and applies the pad count, and the
window off-screen: OK applies, Cancel leaves it, lowering past bound pads
asks first and lists the bindings (Yes applies, No goes back)."""

from __future__ import annotations

import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_home_image_menu import card_menu  # noqa: E402

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parents[1]
_SMOKE = _HERE / "xbox_setup_smoke.py"


def _text(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8")


def test_the_menu_item_is_only_on_the_xbox_card(qapp: object) -> None:
    assert "Xbox Setup…" in card_menu("xbox", "dest", "XInput", "xbox")
    others = (
        ("vjoy_1", "dest", "DirectInput", "physical"),
        ("pjoy_pro", "source", "HID", "physical"),
        ("keyboard", "source", "HID", "keyboard"),
        ("osc", "source", "HID", "osc"),
        ("logical", "source", "Logical", "logical"),
    )
    for slug, direction, bus, tab in others:
        assert "Xbox Setup…" not in card_menu(slug, direction, bus, tab), slug
    # Xbox still has no Module Setup of its own.
    assert "Module Setup…" not in card_menu("xbox", "dest", "XInput", "xbox")


def test_main_opens_xbox_setup_from_the_card_palette_and_output_view() -> None:
    main = _text("qml/Main.qml")
    assert "function openXboxSetup()" in main
    assert 'Helpers.createComponent("DialogXboxSetup.qml")' in main
    # The Xbox card's configureModule is Xbox Setup; Tools' Output Module
    # Setup still opens nothing for Xbox.
    handler = main[main.index("onConfigureModule: function(card)") :]
    handler = handler[: handler.index("onOpenAutoMappingTool")]
    assert "openXboxSetup()" in handler
    loader = main[main.index("id: _xboxLoader") :]
    loader = loader[: loader.index("Loader {")]
    assert "target: _xboxLoader.item" in loader
    assert "function onXboxSetupRequested() { _root.openXboxSetup() }" in loader
    commands = _text("qml/main_commands.js")
    entry = commands[commands.index('id: "tools.xboxSetup"') :]
    entry = entry[: entry.index("},")]
    assert '"Xbox Setup…"' in entry and "openXboxSetup()" in entry


def test_the_model_reads_and_applies_the_count(
    qapp: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.modules import output
    from gremlin.signal import signal
    from gremlin.ui.xbox_setup import XboxSetupModel

    count = {"n": 2}
    applied: list[int] = []
    asked: list[list[int]] = []

    def _set(n: int, who: str = "Xbox Setup") -> None:
        applied.append(n)
        count["n"] = n
        signal.xboxPadsChanged.emit()

    def _on(pads: list[int]) -> list[str]:
        asked.append(list(pads))
        return [f"pad {p}" for p in pads]

    monkeypatch.setattr(output, "xbox_pad_count", lambda: count["n"])
    monkeypatch.setattr(output, "set_xbox_pad_count", _set)
    monkeypatch.setattr(output, "xbox_bindings_on_pads", _on)
    model = XboxSetupModel()
    seen: list[bool] = []
    model.padCountChanged.connect(lambda: seen.append(True))
    try:
        assert model.property("padCount") == 2
        assert model.property("maxPads") == 4
        assert model.bindingsOutside(1) == ["pad 2", "pad 3", "pad 4"]
        assert asked == [[2, 3, 4]]
        assert model.bindingsOutside(4) == []
        model.apply(2)  # unchanged: nothing to do
        assert applied == []
        model.apply(9)  # clamped to 4
        assert applied == [4] and model.property("padCount") == 4 and seen
    finally:
        signal.xboxPadsChanged.disconnect(model.padCountChanged)


def _run(tmp_path: pathlib.Path, scenario: str) -> dict:
    home = tmp_path / "home"
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        PYTHONIOENCODING="utf-8",
    )
    done = proc_tree.run(
        [sys.executable, str(_SMOKE), scenario], cwd=_ROOT, env=env,
        text=True, encoding="utf-8", errors="replace", timeout=90,
    )
    lines = [ln for ln in (done.stdout or "").splitlines() if ln.startswith("{")]
    assert lines, (done.stdout, done.stderr)
    result = json.loads(lines[-1])
    assert "errors" not in result, result
    return result


def _opened(r: dict) -> None:
    assert r["title"] == "Xbox Setup" and r["visible"] is True
    assert r["driverRow"] is True
    assert (r["ok"], r["cancel"]) == ("OK", "Cancel")


def test_the_window_opens_and_ok_applies_a_raise(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path, "raise")
    _opened(r)
    assert r["start"] == 1
    assert r["question"] is False
    assert r["applied"] == [3] and r["count"] == 3 and r["closed"] is True


def test_cancel_leaves_the_count(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path, "cancel")
    _opened(r)
    assert r["applied"] == [] and r["count"] == 1 and r["closed"] is True


def test_lowering_with_bindings_asks_and_lists_them(tmp_path: pathlib.Path) -> None:
    r = _run(tmp_path, "lower")
    _opened(r)
    assert r["start"] == 3
    assert r["asked"][0] == [2, 3, 4]
    assert r["question"] is True and r["appliedBeforeYes"] == []
    assert r["questionTitle"] == "Use 1 Xbox pad?"
    assert "VKBsim Gladiator EVO R · Button 1 → Xbox 360 3 · A" in r["questionText"]
    assert r["yes"] == "Yes"
    # No goes back to the window, nothing applied.
    assert r["afterNo"] == {"applied": [], "visible": True, "question": False}
    # Yes applies (the bindings are kept: nothing here deletes them).
    assert r["applied"] == [1] and r["count"] == 1 and r["closed"] is True
