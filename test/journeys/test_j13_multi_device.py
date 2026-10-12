# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Journey 13: four sticks and two vJoys (the multi-device rig).

The rig (_harness.RIG): the pJoy Pro, a Saitek X52 and two identical "Twin
Stick"s (shown as "Twin Stick" and "Twin Stick (2)"), vJoy 1 and vJoy 2;
every stick has its module file, each vJoy its output module. Each part
records its own values (an error in one doesn't hide the others):

1. Two sticks to two vJoys: the pJoy's button 1 sends to vJoy 1, the X52's
   to vJoy 2; Home's vJoy cards say "Driven by" each.
2. Swap (Device Library, bindings, the open profile ticked): the pJoy now
   drives vJoy 2 and the X52 vJoy 1.
3. Change vJoy Output of the X52, vJoy 1 to 2, with "swap the other
   sticks": the X52 goes back to vJoy 2 and the pJoy (on vJoy 2) to vJoy 1.
4. Change vJoy Output on a saved profile that is not the open one: the
   file changes, the open profile doesn't.
5. vJoy Viewer (the Input Viewer window) with the twins wired too: its
   device list has all four sticks and both vJoys; so has the Device Mapping Editor's.
6. Twin rename (the Device Library's rename, device_names.set_alias) of
   "Twin Stick (2)":
   Home, the Device Library and both viewer lists show the new name; the
   other twin keeps its own.
7. Unplug and plug the X52 back in (the driver's device change): its card,
   wires and "Driven by" come back.

Spec: 02 S16 (twin names), 03 S90a, 10 S7, S26, S30-S32, S58,
D-01-OWNER-NOTICES; to-do 105.
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from _harness import RIG, Journey, run_journey, step  # noqa: E402

TWIN_NAME = "Right Twin"


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part; an error is recorded under the part's name and the
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


def _model(j: Journey) -> Any:  # noqa: ANN401
    return j.ev("_moduleModel")


def _row(j: Journey, name: str, direction: str = "") -> Any:  # noqa: ANN401
    for row in _model(j)._rows:
        if row.name == name and (not direction or row.direction == direction):
            return row
    return None


def _row_target(j: Journey, name: str) -> str:
    row = _row(j, name, "dest")
    return str(getattr(row, "target", "") or "") if row is not None else "NO ROW"


def _cards(j: Journey) -> list[Any]:  # noqa: ANN401
    return [
        it
        for it in j.walk(j.win.contentItem())
        if it.metaObject().indexOfSignal("cardFocused()") >= 0
    ]


def _card_target(j: Journey, name: str) -> str:
    for card in _cards(j):
        if card.property("cardName") == name or card.property("rawName") == name:
            return str(card.property("target") or "")
    return "NO CARD"


def _card_names(j: Journey) -> list[str]:
    return sorted(str(c.property("cardName") or "") for c in _cards(j))


def _driven_by(j: Journey) -> list[str]:
    """[vJoy 1's, vJoy 2's] "Driven by" on the Home cards."""
    return [_card_target(j, "vJoy 1"), _card_target(j, "vJoy 2")]


def _rows_driven_by(j: Journey) -> list[str]:
    return [_row_target(j, "vJoy 1"), _row_target(j, "vJoy 2")]


def _go_home(j: Journey) -> None:
    j.ev('uiState.setCurrentRoom("status")')
    j.wait_until(lambda: j.ev("uiState.currentRoom") == "status", "Home")
    j.settle()


def _actions_edited() -> None:
    """What an action editor sends after an edit (ActionModel)."""
    from gremlin.signal import signal

    signal.actionsChanged.emit()


def _dests(profile: Any, uid: Any, button: int = 1) -> list[int]:  # noqa: ANN401
    """The vJoy each Map to vJoy on the stick's button sends to."""
    return [
        int(action.vjoy_device_id)
        for item in (profile.inputs or {}).get(uid, [])
        if item.input_id == button
        for binding in item.action_sequences
        for action in binding.root_action.get_actions()[0]
        if hasattr(action, "vjoy_device_id")
    ]


def _library_key(library: Any, uid: Any) -> str:  # noqa: ANN401
    return next(
        str(d["key"])
        for d in library._devices
        if uid.hex in str(d.get("guid") or "").lower().replace("-", "")
    )


def _library_run(j: Journey, library: Any, start: Any, label: str) -> dict:  # noqa: ANN401
    """Starts a Device Library action (start() returns its ticket) and
    waits for its result."""
    results: list[dict] = []

    def keep(r: Any) -> None:  # noqa: ANN401
        results.append(dict(r))

    library.result.connect(keep)
    try:
        ticket = start()
        assert ticket, f"{label} was refused"
        done = j.wait_until(
            lambda: next((r for r in results if r.get("ticket") == ticket), None),
            f"{label}'s result",
            timeout=30,
        )
    finally:
        library.result.disconnect(keep)
    j.settle()
    return done


def _url(path: pathlib.Path) -> str:
    from PySide6 import QtCore

    return QtCore.QUrl.fromLocalFile(str(path)).toString()


def _ids(j: Journey) -> dict[str, Any]:
    return {
        "pjoy": j.stick("pJoy Pro").device_guid.uuid,
        "x52": j.stick("Saitek X52").device_guid.uuid,
        "twin1": j.stick("Twin Stick").device_guid.uuid,
        "twin2": j.stick("Twin Stick (2)").device_guid.uuid,
    }


def _part_two_vjoys(j: Journey) -> None:
    from gremlin import device_initialization, util

    out = j.out
    ids = _ids(j)
    out["two:names"] = sorted(d.name for d in device_initialization.physical_devices())
    j.map_button(ids["pjoy"], 1, "Default", 1, vjoy=1)
    j.map_button(ids["x52"], 1, "Default", 2, vjoy=2)
    _actions_edited()
    out["two:rows"] = j.await_value(
        lambda: _rows_driven_by(j), ["pJoy Pro", "Saitek X52"]
    )
    out["two:cards"] = j.await_value(lambda: _driven_by(j), ["pJoy Pro", "Saitek X52"])
    path = util.profiles_dir() / "rig.xml"
    assert j.backend.saveProfile(_url(path)), "the profile was not saved"
    j.settle()


def _part_swap(j: Journey) -> None:
    from gremlin import util
    from gremlin.ui.device_library_model import DeviceLibraryModel

    out = j.out
    ids = _ids(j)
    url = _url(util.profiles_dir() / "rig.xml")
    library = DeviceLibraryModel()
    library.refresh()
    j.settle()
    pjoy_key = _library_key(library, ids["pjoy"])
    x52_key = _library_key(library, ids["x52"])
    done = _library_run(
        j,
        library,
        lambda: library.swap(pjoy_key, x52_key, ["bindings"], [url]),
        "Swap",
    )
    out["swap:ok"] = bool(done.get("ok"))
    out["swap:message"] = str(done.get("error") or "")
    out["swap:dests"] = [_dests(j.profile, ids["pjoy"]), _dests(j.profile, ids["x52"])]
    out["swap:rows"] = j.await_value(
        lambda: _rows_driven_by(j), ["Saitek X52", "pJoy Pro"]
    )
    out["swap:cards"] = j.await_value(lambda: _driven_by(j), ["Saitek X52", "pJoy Pro"])


def _part_change_swap_other(j: Journey) -> None:
    from gremlin import util
    from gremlin.ui.device_library_model import DeviceLibraryModel

    out = j.out
    ids = _ids(j)
    url = _url(util.profiles_dir() / "rig.xml")
    library = DeviceLibraryModel()
    library.refresh()
    j.settle()
    x52_key = _library_key(library, ids["x52"])
    out["other:before"] = [
        _dests(j.profile, ids["pjoy"]),
        _dests(j.profile, ids["x52"]),
    ]
    done = _library_run(
        j,
        library,
        lambda: library.changeOutput(x52_key, {"1": 2}, True, [url]),
        "Change vJoy Output",
    )
    out["other:ok"] = bool(done.get("ok"))
    out["other:message"] = str(done.get("error") or "")
    out["other:dests"] = [
        _dests(j.profile, ids["pjoy"]),
        _dests(j.profile, ids["x52"]),
    ]
    out["other:rows"] = j.await_value(
        lambda: _rows_driven_by(j), ["pJoy Pro", "Saitek X52"]
    )
    out["other:cards"] = j.await_value(
        lambda: _driven_by(j), ["pJoy Pro", "Saitek X52"]
    )


def _part_change_saved_profile(j: Journey) -> None:
    from gremlin import library_profiles, util
    from gremlin.ui.device_library_model import DeviceLibraryModel

    out = j.out
    ids = _ids(j)
    rig = util.profiles_dir() / "rig.xml"
    other = util.profiles_dir() / "other.xml"
    # A second saved profile (Save As), then the first one opened again.
    assert j.backend.saveProfile(_url(rig)), "rig.xml was not saved"
    assert j.backend.saveProfile(_url(other)), "other.xml was not saved"
    j.backend.loadProfile(_url(rig))
    j.settle()
    out["saved:open"] = pathlib.Path(j.backend.profilePath()).name
    other_text = other.read_text(encoding="utf-8")
    library = DeviceLibraryModel()
    library.refresh()
    j.settle()
    pjoy_key = _library_key(library, ids["pjoy"])
    done = _library_run(
        j,
        library,
        lambda: library.changeOutput(pjoy_key, {"1": 2}, False, [_url(other)]),
        "Change vJoy Output (saved profile)",
    )
    out["saved:ok"] = bool(done.get("ok"))
    out["saved:message"] = str(done.get("error") or "")
    out["saved:file-changed"] = other.read_text(encoding="utf-8") != other_text
    read = library_profiles.read_profile(other)
    out["saved:file-dests"] = (
        [_dests(read, ids["pjoy"]), _dests(read, ids["x52"])]
        if not isinstance(read, str)
        else read
    )
    out["saved:open-after"] = pathlib.Path(j.backend.profilePath()).name
    out["saved:open-dests"] = [
        _dests(j.profile, ids["pjoy"]),
        _dests(j.profile, ids["x52"]),
    ]
    out["saved:cards"] = _driven_by(j)


def _viewer_rows(model: Any) -> list[dict]:  # noqa: ANN401
    return [dict(r) for r in model._rows]


def _part_viewer(j: Journey) -> None:
    from gremlin.ui.module_pairing import ModulePairDeviceModel
    from gremlin.ui.viewer_devices import ViewerDeviceModel

    out = j.out
    ids = _ids(j)
    j.map_button(ids["twin1"], 1, "Default", 3, vjoy=1)
    j.map_button(ids["twin2"], 1, "Default", 4, vjoy=2)
    _actions_edited()
    j.settle()
    j.ev('Helpers.createComponent("DialogInputViewer.qml")')
    window = j.window("vJoy Viewer")
    model = j.wait_until(
        lambda: window.findChild(ModulePairDeviceModel), "the vJoy Viewer list"
    )
    j.await_value(lambda: len(model._rows), 4)
    rows = _viewer_rows(model)
    out["viewer:names"] = sorted(str(r["name"]) for r in rows)
    out["viewer:pairs"] = {str(r["name"]): str(r["pairLabel"]) for r in rows}
    out["viewer:vjoys"] = sorted(
        {p.strip() for r in rows for p in str(r["pairLabel"]).split(",") if p.strip()}
    )
    editor_list = ViewerDeviceModel()
    mapped = [r for r in editor_list._rows if r.get("mapped")]
    out["map:names"] = sorted(str(r["name"]) for r in mapped)
    out["map:vjoys"] = sorted(
        {p.strip() for r in mapped for p in str(r["pairLabel"]).split(",") if p.strip()}
    )
    j.ev("close()", window)
    j.settle()


def _part_twin_rename(j: Journey) -> None:
    from gremlin.ui import device_names
    from gremlin.ui.device_library_model import DeviceLibraryModel
    from gremlin.ui.module_pairing import ModulePairDeviceModel
    from gremlin.ui.viewer_devices import ViewerDeviceModel

    out = j.out
    ids = _ids(j)
    library = DeviceLibraryModel()
    library.refresh()
    viewer = ViewerDeviceModel()
    pairs = ModulePairDeviceModel()
    j.settle()
    _go_home(j)
    out["rename:cards-before"] = _card_names(j)
    device_names.set_alias(str(ids["twin2"]), TWIN_NAME)
    j.settle()

    def twins(names: list[str]) -> list[str]:
        return sorted(n for n in names if "Twin" in n)

    out["rename:cards"] = j.await_value(
        lambda: twins(_card_names(j)), ["Right Twin", "Twin Stick"]
    )
    out["rename:library"] = j.await_value(
        lambda: twins([str(d.get("name", "")) for d in library._devices]),
        ["Right Twin", "Twin Stick"],
    )
    out["rename:viewer"] = j.await_value(
        lambda: twins([str(r["name"]) for r in viewer._rows]),
        ["Right Twin", "Twin Stick"],
    )
    out["rename:vjoy-viewer"] = j.await_value(
        lambda: twins([str(r["name"]) for r in pairs._rows]),
        ["Right Twin", "Twin Stick"],
    )
    # Evidence: a vJoy Viewer list built after the rename.
    out["rename:vjoy-viewer-fresh"] = twins(
        [str(r["name"]) for r in ModulePairDeviceModel()._rows]
    )
    out["rename:twin1-wires"] = j.wires(ids["twin1"])
    out["rename:twin2-wires"] = j.wires(ids["twin2"])


def _part_unplug(j: Journey) -> None:
    from gremlin import device_initialization

    out = j.out
    _go_home(j)
    x52 = j.stick("Saitek X52").device_guid.uuid
    out["plug:wires-before"] = j.wires(x52)
    out["plug:card-before"] = "Saitek X52" in _card_names(j)
    out["plug:driven-before"] = _driven_by(j)[1]
    j.unplug("Saitek X52")
    j.settle()
    out["plug:listed-unplugged"] = sorted(
        d.name for d in device_initialization.physical_devices()
    )
    # 03 S96: an unplugged stick's card goes (its place is kept).
    out["plug:card-unplugged"] = j.await_value(
        lambda: "Saitek X52" in _card_names(j), False
    )
    out["plug:wires-unplugged"] = j.wires(x52)
    j.replug("Saitek X52")
    j.settle()
    out["plug:listed-replugged"] = sorted(
        d.name for d in device_initialization.physical_devices()
    )
    out["plug:same-id"] = j.stick("Saitek X52").device_guid.uuid == x52
    out["plug:card-after"] = j.await_value(lambda: "Saitek X52" in _card_names(j), True)
    out["plug:wires-after"] = j.wires(x52)
    out["plug:driven-after"] = j.await_value(
        lambda: _driven_by(j)[1], out["plug:driven-before"]
    )


def story(j: Journey) -> None:
    import time

    import shiboken6
    from PySide6 import QtQuick

    started = time.monotonic()
    root: Any = shiboken6.wrapInstance(
        shiboken6.getCppPointer(j.win)[0], QtQuick.QQuickWindow
    )
    j.win.setProperty("visible", True)
    root.setWidth(1400)
    root.setHeight(900)
    _go_home(j)
    j.wait_until(lambda: _card_target(j, "vJoy 2") != "NO CARD", "the vJoy 2 card")
    for name, part in (
        ("two", _part_two_vjoys),
        ("swap", _part_swap),
        ("other", _part_change_swap_other),
        ("saved", _part_change_saved_profile),
        ("viewer", _part_viewer),
        ("rename", _part_twin_rename),
        ("plug", _part_unplug),
    ):
        with _Part(j, name):
            part(j)
    j.out["seconds"] = round(time.monotonic() - started, 1)


def _guid_of(j: Journey, name: str, nth: int = 0) -> Any:  # noqa: ANN401
    """The id of the nth stick the fake driver calls name."""
    import dill

    found = [d for d in j.dill_fake.devices if d.name.decode("utf-8") == name]
    return dill.GUID(found[nth].device_guid)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.input_module("Saitek X52", guid=_guid_of(j, "Saitek X52"))
        j.input_module("Twin Stick", guid=_guid_of(j, "Twin Stick", 0))
        j.input_module(
            "Twin Stick (2)", guid=_guid_of(j, "Twin Stick", 1), slug="twin_stick_2"
        )
        j.vjoy_module(1)
        j.vjoy_module(2)

    Journey(before, **RIG).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("j13"))


def _no_error(run: dict, part: str) -> None:
    assert "error" not in run, (run.get("error"), run.get("traceback"))
    assert f"{part}:error" not in run, (
        run.get(f"{part}:error"),
        run.get(f"{part}:traceback"),
    )


def test_two_sticks_drive_two_vjoys(run: dict) -> None:
    _no_error(run, "two")
    assert step(run, "two:names") == [
        "Saitek X52",
        "Twin Stick",
        "Twin Stick (2)",
        "pJoy Pro",
    ]
    assert step(run, "two:rows") == ["pJoy Pro", "Saitek X52"]
    assert step(run, "two:cards") == ["pJoy Pro", "Saitek X52"]


def test_swap_swaps_driven_by(run: dict) -> None:
    _no_error(run, "swap")
    assert step(run, "swap:ok") is True, step(run, "swap:message")
    assert step(run, "swap:dests") == [[2], [1]]
    assert step(run, "swap:rows") == ["Saitek X52", "pJoy Pro"]
    assert step(run, "swap:cards") == ["Saitek X52", "pJoy Pro"]


def test_change_vjoy_output_swaps_the_other_sticks(run: dict) -> None:
    _no_error(run, "other")
    assert step(run, "other:before") == [[2], [1]]
    assert step(run, "other:ok") is True, step(run, "other:message")
    assert step(run, "other:dests") == [[1], [2]]
    assert step(run, "other:rows") == ["pJoy Pro", "Saitek X52"]
    assert step(run, "other:cards") == ["pJoy Pro", "Saitek X52"]


def test_change_vjoy_output_on_a_saved_profile_leaves_the_open_one(run: dict) -> None:
    _no_error(run, "saved")
    assert step(run, "saved:open") == "rig.xml"
    assert step(run, "saved:ok") is True, step(run, "saved:message")
    assert step(run, "saved:file-changed") is True
    assert step(run, "saved:file-dests") == [[2], [2]]
    assert step(run, "saved:open-after") == "rig.xml"
    assert step(run, "saved:open-dests") == [[1], [2]]
    assert step(run, "saved:cards") == ["pJoy Pro", "Saitek X52"]


def test_input_viewer_lists_every_stick_and_both_vjoys(run: dict) -> None:
    _no_error(run, "viewer")
    sticks = ["Saitek X52", "Twin Stick", "Twin Stick (2)", "pJoy Pro"]
    assert step(run, "viewer:names") == sticks, step(run, "viewer:pairs")
    assert step(run, "viewer:vjoys") == ["vJoy 1", "vJoy 2"]
    assert step(run, "map:names") == sticks
    assert step(run, "map:vjoys") == ["vJoy Device 1", "vJoy Device 2"]


def test_twin_rename_renames_only_that_twin(run: dict) -> None:
    _no_error(run, "rename")
    assert "Twin Stick (2)" in step(run, "rename:cards-before")
    assert step(run, "rename:cards") == ["Right Twin", "Twin Stick"]
    assert step(run, "rename:library") == ["Right Twin", "Twin Stick"]
    assert step(run, "rename:viewer") == ["Right Twin", "Twin Stick"]
    # 03 S122a: the vJoy Viewer's device list follows the device names notice.
    assert step(run, "rename:vjoy-viewer") == ["Right Twin", "Twin Stick"], step(
        run, "rename:vjoy-viewer-fresh"
    )
    assert step(run, "rename:twin1-wires") == {"Default": [[1, [3]]]}
    assert step(run, "rename:twin2-wires") == {"Default": [[1, [4]]]}


def test_unplug_and_replug_bring_the_x52_back(run: dict) -> None:
    _no_error(run, "plug")
    # After Swap the X52 has the pJoy's old wire (vJoy button 1), sent to
    # vJoy 2 since Change vJoy Output.
    wires = {"Default": [[1, [1]]]}
    assert step(run, "plug:wires-before") == wires
    assert step(run, "plug:card-before") is True
    # vJoy 2 is driven by the X52 and the renamed twin.
    assert step(run, "plug:driven-before") == "Saitek X52, Right Twin"
    assert "Saitek X52" not in step(run, "plug:listed-unplugged")
    assert step(run, "plug:wires-unplugged") == wires
    assert "Saitek X52" in step(run, "plug:listed-replugged")
    assert step(run, "plug:same-id") is True
    assert step(run, "plug:card-after") is True
    assert step(run, "plug:card-unplugged") is False
    assert step(run, "plug:wires-after") == wires
    assert step(run, "plug:driven-after") == "Saitek X52, Right Twin"


if __name__ == "__main__":
    main()
