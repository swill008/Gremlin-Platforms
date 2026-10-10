# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The new OSC page, end to end on the real program (OSC rewrite, batch 1).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver and a
fake vJoy behind the output module. The story opens the OSC page and
drives its own models, as the screens do:

1. Add the OSC input /deck/1 (button): a parent row on the page's
   OscLayoutModel with the settings line under its title (OP12). Add Map
   to vJoy in the shared action pane, OK: the profile has the binding.
   Undo takes it away, Redo puts it back (OP1, OP2, OP3).
2. Groups: add "Stream Deck", move the input into it, reorder; save and
   open the profile again: the groups and order are still there, kept in
   OSC's own file (osc.json) (OP1, OP11).
3. Run: a real UDP packet on the loopback to the listener (bound to a
   port the OS picks, never a fixed one) at /deck/1 with value 1 fires
   the Map to vJoy action; 0 lets it go.
4. Monitor dock (OP6, OP8): folded on the page, the port is not held;
   Tools > OSC Monitor shows it unfolded and holds the port (through the
   runtime's hold_open); folding it again or leaving the page lets it go.

Each part records its own values, so one part failing doesn't hide the
others. Parts that need the batch 1 wave 2 code (the OSC page on the shared
base: gremlin/ui/osc_layout.py OscLayoutModel and the page QML with the
docked Monitor) are marked xfail(strict) while that code is missing: they
then show as XFAIL "needs wave 2", and turn into ordinary tests once it
lands.

Spec: 09 (OSC) OP1-OP3, OP6, OP8, OP11, OP12; 05 (the shared pane).
"""

from __future__ import annotations

import pathlib
import sys
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, JourneyIncomplete, run_journey  # noqa: E402

ADDRESS = "/deck/1"
SECOND = "/deck/2"
GROUP = "Stream Deck"
VJOY_BUTTON = 3

_WAVE2_FILES = (
    ROOT / "gremlin" / "ui" / "osc_layout.py",
    ROOT / "gremlin" / "ui" / "control_layout.py",
)
_WAVE2_MISSING = [str(p.relative_to(ROOT)) for p in _WAVE2_FILES if not p.exists()]

# Fails only because batch 1 wave 2 code is not in yet (strict: the mark
# must come off once it lands).
needs_wave2 = pytest.mark.xfail(
    bool(_WAVE2_MISSING),
    reason="needs wave 2 (OSC page on the shared base): missing "
    + ", ".join(_WAVE2_MISSING),
    raises=(AssertionError, JourneyIncomplete),
    strict=True,
)


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part of the story; an error is recorded under the part's
    name and the next part still runs."""

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


def _loopback_listener() -> None:
    """The OSC listener binds 127.0.0.1 on a port the OS picks (port 0):
    never the PC's network, never a fixed port another program may hold.
    It keeps the configured host and port as its own (the runtime compares
    them to know when to rebind); _bound() reads the real one."""
    from gremlin import osc

    real = osc.OscListener

    class LoopbackListener(real):  # type: ignore[misc, valid-type]
        bound: list[LoopbackListener] = []

        def start(self) -> None:
            host, port = self.host, self.port
            self.host, self.port = "127.0.0.1", 0
            try:
                super().start()
            finally:
                self.host, self.port = host, port
            LoopbackListener.bound.append(self)

    osc.OscListener = LoopbackListener  # type: ignore[misc]


def _bound(listener: Any) -> tuple[str, int]:  # noqa: ANN401
    """The host and port a listener really holds (port 0 picked by the OS)."""
    host, port = listener._server.server_address[:2]
    method = getattr(listener, "bound_port", None)  # OX3 adds it
    if callable(method):
        port = method()
    return str(host), int(port)


def _rows(model: Any) -> list[dict]:  # noqa: ANN401
    """Every row of a layout model, as {role name: value}."""
    names = {int(k): bytes(v).decode() for k, v in model.roleNames().items()}
    out = []
    for r in range(model.rowCount()):
        index = model.index(r, 0)
        row = {}
        for role, name in names.items():
            value = model.data(index, role)
            plain = isinstance(value, (str, int, float, bool, type(None)))
            row[name] = value if plain else str(value)
        out.append(row)
    return out


def _parent_key(address: str) -> str:
    from gremlin.osc import OscDevice
    from gremlin.types import InputType

    row = OscDevice().find_address(address)
    assert row is not None, f"no OSC input {address}"
    word = {InputType.JoystickAxis: "axis", InputType.JoystickHat: "hat"}.get(
        row.input_type, "button"
    )
    return f"parent:{word}:{row.input_id}"


def _osc_item(j: Journey, address: str) -> Any:  # noqa: ANN401
    """The open profile's InputItem for an OSC input (None when it has
    none)."""
    from gremlin.osc import OSC_DEVICE_UUID, OscDevice

    row = OscDevice().find_address(address)
    if row is None:
        return None
    for item in j.profile.inputs.get(OSC_DEVICE_UUID, []):
        if item.input_type == row.input_type and item.input_id == row.input_id:
            return item
    return None


def _vjoy_targets(item: Any) -> list[int]:  # noqa: ANN401
    """The vJoy buttons an input's actions send."""
    if item is None:
        return []
    return [
        getattr(action, "vjoy_input_id", -1)
        for seq in item.action_sequences
        for action in seq.root_action.get_actions()[0]
        if action.name == "Map to vJoy"
    ]


def _open_osc_page(j: Journey) -> Any:  # noqa: ANN401
    """Opens the OSC card's page as a click on its Home card does; returns
    the page's own OscLayoutModel."""
    from gremlin.ui.osc_layout import OscLayoutModel

    state = j.backend.uiState
    j.ev('openConfigurationForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: state.currentTab == "osc", "the OSC page")
    return j.wait_until(
        lambda: j.win.findChild(OscLayoutModel), "the OSC page's layout model"
    )


def _add_model(j: Journey) -> Any:  # noqa: ANN401
    """The model behind the page's Add window (OscDeviceManagementModel)."""
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    return j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()


def _map_to_vjoy(button: int) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Map to vJoy", InputType.JoystickButton
    )
    action.vjoy_device_id = 1
    action.vjoy_input_id = button
    action.vjoy_input_type = InputType.JoystickButton
    return action


def _part_pane(j: Journey, page: Any) -> None:  # noqa: ANN401
    """1: add /deck/1, map it in the shared pane, Undo, Redo."""
    out = j.out
    assert _add_model(j).createConfiguredInput({"address": ADDRESS, "mode": "button"})
    j.settle()
    key = _parent_key(ADDRESS)
    out["1:key"] = key
    parents = [r for r in _rows(page) if r.get("key") == key]
    out["1:parent-rows"] = len(parents)
    if parents:
        out["1:title"] = parents[0].get("title")
        out["1:subtitle"] = parents[0].get("subtitle")
        out["1:row-kind"] = parents[0].get("rowKind")
    # Before any action (OP2: a new input with no actions still shows,
    # so its first action can be added).
    out["1:item-before"] = _vjoy_targets(_osc_item(j, ADDRESS))

    page.beginNewAction(key)
    shadow = page._pane_shadow
    shadow.action_sequences[0].root_action.insert_action(
        _map_to_vjoy(VJOY_BUTTON), "children"
    )
    out["1:dirty"] = page.paneDirty()
    out["1:commit-index"] = page.commitPane()
    page.endPane()
    j.settle()
    out["1:after-ok"] = _vjoy_targets(_osc_item(j, ADDRESS))
    item = _osc_item(j, ADDRESS)
    out["1:osc-uid-set"] = bool(item is not None and getattr(item, "osc_uid", ""))
    out["1:child-rows"] = sum(
        1 for r in _rows(page) if r.get("parentKey") == key and r.get("key") != key
    )
    out["1:can-undo"] = bool(page.property("canUndo"))

    page.undo()
    j.settle()
    out["1:after-undo"] = _vjoy_targets(_osc_item(j, ADDRESS))
    out["1:can-redo"] = bool(page.property("canRedo"))
    page.redo()
    j.settle()
    out["1:after-redo"] = _vjoy_targets(_osc_item(j, ADDRESS))


def _ordered_in_group(page: Any, group: str) -> list[str]:  # noqa: ANN401
    """The parent keys shown in a group, in page order."""
    return [
        r["key"]
        for r in _rows(page)
        if str(r.get("key", "")).startswith("parent:")
        and (r.get("groupName") or "") == group
    ]


def _part_groups(j: Journey, page: Any) -> None:  # noqa: ANN401
    """2: a group, the input moved into it, reordered; saved and opened
    again."""
    from gremlin import osc_device_file

    out = j.out
    assert _add_model(j).createConfiguredInput({"address": SECOND, "mode": "button"})
    j.settle()
    first, second = _parent_key(ADDRESS), _parent_key(SECOND)
    page.addGroup(GROUP)
    page.setSelection([first, second])
    page.moveSelected(GROUP)
    j.settle()
    out["2:groups"] = list(page.property("groups") or [])
    out["2:order-before"] = _ordered_in_group(page, GROUP)
    # Drag /deck/2 above /deck/1.
    page.moveParent(second, first, "before")
    j.settle()
    out["2:order-after"] = _ordered_in_group(page, GROUP)

    # Save, open another profile, then this one again.
    j.save_and_reopen("osc_page_e2e")
    j.settle()
    page = _open_osc_page(j)
    out["2:groups-reloaded"] = list(page.property("groups") or [])
    out["2:order-reloaded"] = _ordered_in_group(page, GROUP)
    out["2:binding-reloaded"] = _vjoy_targets(_osc_item(j, ADDRESS))

    # Kept in OSC's own file, not the profile.
    text = osc_device_file.path().read_text(encoding="utf-8")
    out["2:osc-json-has-group"] = GROUP in text
    profile_text = pathlib.Path(j.backend.profilePath()).read_text(encoding="utf-8")
    out["2:profile-has-group"] = GROUP in profile_text


def _part_run(j: Journey) -> None:
    """3: Run; a loopback UDP packet at /deck/1 presses vJoy button 3."""
    from pythonosc.udp_client import SimpleUDPClient

    from gremlin import osc, osc_device_file

    out = j.out
    osc_device_file.write_server({"enabled": True, "host": "127.0.0.1", "port": 9000})
    j.backend.toggleActiveState()
    out["3:running"] = j.backend.runner.is_running()
    runtime = osc.OscRuntime()
    listener = j.wait_until(lambda: runtime._listener, "the OSC listener", 10)
    host, port = _bound(listener)
    out["3:bound-loopback"] = host == "127.0.0.1" and port > 0
    client = SimpleUDPClient("127.0.0.1", port)
    client.send_message(ADDRESS, 1)
    out["3:held-after-1"] = j.await_value(j.vjoy.held_buttons, [VJOY_BUTTON])
    client.send_message(ADDRESS, 0)
    out["3:held-after-0"] = j.await_value(j.vjoy.held_buttons, [])
    j.backend.toggleActiveState()
    out["3:running-after-stop"] = j.backend.runner.is_running()
    out["3:port-open-after-stop"] = runtime.is_open()


def _find_panel(j: Journey) -> Any:  # noqa: ANN401
    for found in j.walk(j.win.contentItem()):
        if found.objectName() == "oscMonitorPanel":
            return found
    return None


def _part_monitor(j: Journey) -> None:
    """4: the docked Monitor holds the port only while unfolded on the page."""
    from gremlin import osc

    out = j.out
    runtime = osc.OscRuntime()
    _open_osc_page(j)
    panel = j.wait_until(lambda: _find_panel(j), "the docked OSC Monitor")
    j.settle()

    def state() -> list:
        return [
            bool(panel.property("folded")),
            bool(panel.property("holdsPort")),
            runtime.is_open(),
            len(runtime._holders),
        ]

    out["4:default"] = state()
    # Tools > OSC Monitor: the OSC page with the Monitor shown.
    j.ev('Commands.trigger("tools.oscMonitor")')
    j.wait_until(lambda: runtime.is_open(), "the Monitor holding the port", 5)
    out["4:tools-menu"] = state()
    panel = _find_panel(j) or panel
    panel.setProperty("folded", True)
    j.settle()
    out["4:folded-again"] = state()
    panel.setProperty("folded", False)
    j.settle()
    out["4:unfolded"] = state()
    # Leaving the page lets the port go (OP8).
    j.ev('openConfigurationForCard(_moduleModel.cardMap("keyboard"))')
    j.wait_until(
        lambda: j.backend.uiState.currentTab == "keyboard", "the Keyboard page"
    )
    j.settle()
    out["4:left-page"] = [runtime.is_open(), len(runtime._holders)]


def story(j: Journey) -> None:
    _loopback_listener()
    page = None
    with _Part(j, "1"):
        page = _open_osc_page(j)
        _part_pane(j, page)
    with _Part(j, "2"):
        if page is None:
            raise RuntimeError("part 1 did not open the page")
        _part_groups(j, page)
    with _Part(j, "3"):
        _part_run(j)
    with _Part(j, "4"):
        _part_monitor(j)


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_page_e2e"))


def _step(out: dict, key: str) -> Any:  # noqa: ANN401
    """A value the story recorded; when its part stopped first, that
    part's error and traceback."""
    if key in out:
        return out[key]
    part = key.split(":", 1)[0]
    raise JourneyIncomplete(
        f"Part {part} never reached {key!r}.\n"
        f"Error: {out.get(part + ':error', out.get('error', '(none)'))}\n"
        f"{out.get(part + ':traceback', out.get('traceback', ''))}\n"
        f"--- stderr\n{out.get('_stderr', '')}"
    )


@needs_wave2
def test_new_osc_input_shows_as_a_parent_row_with_its_settings_line(run: dict) -> None:
    assert _step(run, "1:parent-rows") == 1
    assert ADDRESS in str(_step(run, "1:title"))
    subtitle = str(_step(run, "1:subtitle"))
    # OP12: the settings line, starting with the input's type.
    assert subtitle.startswith("Button"), subtitle
    assert _step(run, "1:item-before") == []


@needs_wave2
def test_map_to_vjoy_in_the_shared_pane_binds_it_with_undo_and_redo(run: dict) -> None:
    assert _step(run, "1:dirty") is True
    assert _step(run, "1:commit-index") == 0
    assert _step(run, "1:after-ok") == [VJOY_BUTTON]
    assert _step(run, "1:osc-uid-set") is True
    assert _step(run, "1:child-rows") >= 1
    assert _step(run, "1:can-undo") is True
    assert _step(run, "1:after-undo") == []
    assert _step(run, "1:can-redo") is True
    assert _step(run, "1:after-redo") == [VJOY_BUTTON]


@needs_wave2
def test_groups_and_order_are_kept_in_osc_json_across_a_reload(run: dict) -> None:
    first = _step(run, "1:key")
    assert GROUP in [g["name"] for g in _step(run, "2:groups")]
    assert sorted(_step(run, "2:order-before")) == sorted(_step(run, "2:order-after"))
    order = _step(run, "2:order-after")
    assert order[0] != first and order[-1] == first  # /deck/2 dragged above
    assert GROUP in [g["name"] for g in _step(run, "2:groups-reloaded")]
    assert _step(run, "2:order-reloaded") == order
    assert _step(run, "2:binding-reloaded") == [VJOY_BUTTON]
    assert _step(run, "2:osc-json-has-group") is True
    assert _step(run, "2:profile-has-group") is False


@needs_wave2
def test_a_loopback_osc_packet_fires_map_to_vjoy_while_running(run: dict) -> None:
    assert _step(run, "3:running") is True
    assert _step(run, "3:bound-loopback") is True
    assert _step(run, "3:held-after-1") == [VJOY_BUTTON]
    assert _step(run, "3:held-after-0") == []
    assert _step(run, "3:running-after-stop") is False
    assert _step(run, "3:port-open-after-stop") is False


@needs_wave2
def test_docked_monitor_holds_the_port_only_while_unfolded_on_the_page(
    run: dict,
) -> None:
    # [folded, holdsPort, runtime port open, holders]
    assert _step(run, "4:default") == [True, False, False, 0]
    assert _step(run, "4:tools-menu") == [False, True, True, 1]
    assert _step(run, "4:folded-again") == [True, False, False, 0]
    assert _step(run, "4:unfolded") == [False, True, True, 1]
    assert _step(run, "4:left-page") == [False, 0]


if __name__ == "__main__":
    main()
