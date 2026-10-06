# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Module Setup and device fixes from the code audit (AU-04, 05, 06, 22, 23,
24, 25, 61)."""

from __future__ import annotations

import json
import sys
import types
from collections.abc import Iterator
from pathlib import Path
from typing import Any

sys.path.append(".")

import pytest
from PySide6 import QtCore

from gremlin import device_initialization
from gremlin.modules import calibration, claim, registry

_APPS: list[QtCore.QCoreApplication] = []


@pytest.fixture(scope="module", autouse=True)
def _app() -> Iterator[QtCore.QCoreApplication]:
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    _APPS.append(app)
    yield app


def _pjoy_guid() -> str:
    devices = device_initialization.physical_devices()
    return str(next(d for d in devices if d.name == "pJoy Pro").device_guid)


@pytest.fixture
def setup() -> Iterator[Any]:
    from gremlin.ui.module_model import DriverInputModel

    model = DriverInputModel()
    yield model
    model.deleteLater()


def test_keyboard_saved_with_no_keys_passes_none() -> None:
    saved = claim.read_claim({"claim": {"keys": [], "keysChosen": True}})
    never = claim.read_claim({"claim": {"keys": []}})
    assert claim.claim_allows_key(saved, (30, False)) is False
    assert claim.claim_allows_key(never, (30, False)) is True


def test_keyboard_setup_shows_a_saved_empty_choice_unticked(setup: Any) -> None:  # noqa: ANN401
    setup._is_keyboard = lambda: True
    setup._load_keyboard({"keys": [], "keysChosen": True, "friendly": {}})
    assert setup._rows and not any(r["claimed"] for r in setup._rows)
    setup._load_keyboard({"keys": [], "friendly": {}})
    assert all(r["claimed"] for r in setup._rows)


def test_keyboard_undo_still_works_after_a_new_key_row(setup: Any) -> None:  # noqa: ANN401
    setup._is_keyboard = lambda: True
    setup._load_keyboard({"keys": [], "keysChosen": True, "friendly": {}})
    setup.setClaimed(0, True)
    count = setup.rowCount()
    # A key that isn't listed (scan code 0x7F, extended) is pressed.
    setup._on_key(types.SimpleNamespace(is_pressed=True, identifier=(0x7F, True)))
    assert setup.rowCount() == count + 1 and setup._rows[-1]["claimed"]
    setup.undo()
    assert not setup._rows[-1]["claimed"]
    setup.undo()
    assert not setup._rows[0]["claimed"]


def test_an_unplugged_xbox_pad_is_not_the_xbox_output(setup: Any) -> None:  # noqa: ANN401
    setup.loadDevice("{DEADBEEF-0000-0000-0000-000000000001}", "Controller (Xbox One)")
    assert setup.saveBlockedReason()  # refused: not connected
    assert not any(r.get("label") == "LB" for r in setup._rows)


def test_save_writes_to_the_bound_file(
    setup: Any, monkeypatch: pytest.MonkeyPatch  # noqa: ANN401
) -> None:
    from gremlin.ui import module_model

    guid = _pjoy_guid()
    monkeypatch.setattr(
        module_model, "resolve_module_slug", lambda name, guid="": "renamed_stick"
    )
    from gremlin.ui.hardware_profile import _clear_device_binding

    setup.loadDevice(guid, "pJoy Pro")
    setup.setClaimed(0, True)
    folder = Path(module_model._maps_dir())
    try:
        assert setup.saveClaim("pJoy Pro", "source")
        assert (folder / "renamed_stick.json").is_file()
    finally:
        (folder / "renamed_stick.json").unlink(missing_ok=True)
        _clear_device_binding("pJoy Pro", guid)


def test_an_input_module_stays_an_input_module(setup: Any) -> None:  # noqa: ANN401
    from gremlin.ui import module_model

    guid = _pjoy_guid()
    setup.loadDevice(guid, "pJoy Pro")
    setup.setClaimed(0, True)
    assert setup.saveClaim("pJoy Pro", "source")
    assert setup.saveClaim("pJoy Pro", "dest")  # the Output menu on an input
    slug = module_model.resolve_module_slug("pJoy Pro", guid)
    path = Path(module_model._maps_dir()) / f"{slug}.json"
    try:
        assert json.loads(path.read_text(encoding="utf-8"))["direction"] == "source"
    finally:
        path.unlink(missing_ok=True)


def test_calibration_with_low_above_high_is_not_used() -> None:
    assert calibration._as_tuple([100, 0, 0, -100, True]) is None
    assert calibration._as_tuple([-100, 50, 0, 100, True]) is None
    assert calibration._as_tuple([-100, 0, 0, 100, True]) == (-100, 0, 0, 100, True)
    # Without a center the center values aren't used.
    assert calibration._as_tuple([0, 0, 0, 100, False]) == (0, 0, 0, 100, False)


def _module(slug: str, guid: str, buttons: list[int]) -> registry.Module:
    doc = {"claim": {"buttons": buttons}}
    return registry.Module(
        slug=slug, path=Path(f"{slug}.json"), doc=doc, name="pJoy Pro",
        bound_guid=guid, bound_name="pJoy Pro", direction="source",
        claim=claim.read_claim(doc),
    )


def test_runtime_uses_the_module_setup_file_for_a_stick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gremlin.modules import runtime
    from gremlin.modules.ids import guid_key

    guid = _pjoy_guid()
    stale = _module("old_copy", guid, [1])
    bound = _module("pjoy_pro", guid, [5])
    monkeypatch.setattr(registry, "modules", lambda: [stale])
    monkeypatch.setattr(registry, "for_device", lambda name, device_guid="": bound)
    gate = runtime.InputModuleRuntime()
    gate.reload()  # one shared instance: it may exist from an earlier test
    try:
        assert gate._claims[guid_key(guid)]["buttons"] == [5]
    finally:
        # The shared instance stays (deleting it broke later tests that use
        # it); it reads the real modules again.
        monkeypatch.undo()
        gate.reload()


def test_a_stick_marked_as_an_output_is_repaired_by_saving(setup: Any) -> None:  # noqa: ANN401
    # The old Output menu bug left input sticks' files marked "dest".
    from gremlin.ui import module_model

    guid = _pjoy_guid()
    slug = module_model.resolve_module_slug("pJoy Pro", guid)
    path = Path(module_model._maps_dir()) / f"{slug}.json"
    path.write_text(json.dumps({
        "device": "pJoy Pro", "direction": "dest", "boundGuidLocal": guid,
        "claim": {"buttons": [1], "axes": [], "hats": []},
    }), encoding="utf-8")
    try:
        setup.loadDevice(guid, "pJoy Pro")
        assert setup.saveClaim("pJoy Pro", "source")
        assert json.loads(path.read_text(encoding="utf-8"))["direction"] == "source"
    finally:
        path.unlink(missing_ok=True)


def test_module_setup_run_and_calibration_use_the_same_file() -> None:
    # A stick with an old file bound to it and a file of its own name: Module
    # Setup used one, Run and Calibration the other (ticks did nothing).
    from gremlin.modules import calibration, runtime
    from gremlin.modules.ids import guid_key
    from gremlin.ui import module_model

    guid = _pjoy_guid()
    folder = Path(module_model._maps_dir())
    files = {
        "old_name": ("Old Name", guid, [1, 2, 3]),
        "pjoy_pro": ("pJoy Pro", "", [9]),
    }
    for slug, (name, bound, buttons) in files.items():
        (folder / f"{slug}.json").write_text(json.dumps({
            "device": name, "direction": "source", "boundGuidLocal": bound,
            "claim": {"buttons": buttons, "axes": [1], "hats": [], "keys": []},
        }), encoding="utf-8")
    try:
        setup = module_model.resolve_module_slug("pJoy Pro", guid)
        gate = runtime.InputModuleRuntime()
        gate.reload()
        assert gate._claims[guid_key(guid)]["buttons"] == files[setup][2]
        rows = {guid_key(r["guid"]): r["slug"] for r in calibration._source_modules()}
        assert rows[guid_key(guid)] == setup
    finally:
        for slug in files:
            (folder / f"{slug}.json").unlink(missing_ok=True)

