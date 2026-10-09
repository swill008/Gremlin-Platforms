# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Rule checks over the program's state: report only.

Each check returns a list of problems, "CODE: what is wrong", and never
raises or changes anything (a check that fails says so as a VALIDATE-ERROR
problem). The tests run profile() and after_stop() after every test
(test/conftest.py); a problem whose code is in WARNINGS may be fine (an
action kept in memory for Undo, 04 S14).

- profile(p): the profile's inputs, actions, library and mode tree hold
  together (spec 04 S14, S27, S42, S46, S68, S71, S75; 05 library rules).
- modules(): the module files read, each connected device has its own file
  and every saved binding points at a file (spec 03 S1, S6, S7, S22, S64).
- after_stop(): a stopped Run left nothing behind (spec 06 S17-S29).

Imports are made inside the checks, so importing this module is cheap and
loads nothing the caller didn't.
"""

from __future__ import annotations

import sys
import uuid
from collections import Counter
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from gremlin.profile import Profile

# Codes that may be expected (not a broken rule by themselves).
WARNINGS = frozenset({"PROFILE-UNUSED-ACTION"})

# The threads (gremlin.threads names, without the prefix) a Run starts and
# Stop ends.
RUN_THREADS = frozenset(
    {
        "user script timers",
        "macro scheduler",
        "macro",
        "mouse controller",
        "OSC listener",
        "audio player",
        "logical device relative axis",
        "vJoy relative axis",
        "double tap",
        "smart toggle",
        "tempo",
    }
)

# Walks over the mode tree and action children stop here (a broken tree
# must not hang the check).
_LIMIT = 100_000


def code_of(problem: str) -> str:
    """The code of a problem ("PROFILE-DANGLING: ..." -> "PROFILE-DANGLING")."""
    return problem.split(":", 1)[0].strip()


def is_warning(problem: str) -> bool:
    """True when the problem's code is a warning (WARNINGS)."""
    return code_of(problem) in WARNINGS


def _guarded(name: str, check: Callable[[list[str]], None]) -> list[str]:
    """Runs check(problems); an exception becomes a VALIDATE-ERROR problem."""
    problems: list[str] = []
    try:
        check(problems)
    except Exception as exc:  # report only: never raise
        problems.append(f"VALIDATE-ERROR: {name} could not finish: {exc!r}")
    return problems


def _children(action: Any) -> list[Any]:  # noqa: ANN401
    try:
        return list(action.get_actions()[0])
    except Exception:
        return []


def _name(action: Any) -> str:  # noqa: ANN401
    return (
        f"{getattr(action, 'name', type(action).__name__)} {getattr(action, 'id', '?')}"
    )


def _input_label(device_id: object, item: Any) -> str:  # noqa: ANN401
    try:
        from gremlin.types import InputType

        kind = InputType.to_string(item.input_type)
    except Exception:
        kind = str(getattr(item, "input_type", "?"))
    return (
        f"input {device_id} {kind} {getattr(item, 'input_id', '?')} "
        f"in mode '{getattr(item, 'mode', '?')}'"
    )


# --- profile ------------------------------------------------------------------


def profile(p: Profile) -> list[str]:
    """Problems in a profile's inputs, library and modes.

    - PROFILE-DANGLING: an input uses an action (or an action inside one)
      that isn't in the library; PROFILE-NOT-LIBRARY-COPY: it uses another
      object than the library holds under that id (a save would write the
      library's). Spec 04 S14, S71; 05 library.
    - PROFILE-BINDING-EMPTY: a binding with no root action (04 S69).
    - PROFILE-ITEM-LIBRARY: an input item that points at another library.
    - PROFILE-CHILD-MISSING: a library action whose child isn't in the
      library (04 S26: such a file is refused on load).
    - PROFILE-MODE-MISSING: an input in a mode the profile doesn't have
      (04 S46, S48).
    - PROFILE-MODE-LOOP / -SELF-PARENT / -PARENT / -DUPLICATE / -BLANK: the
      mode tree has a loop, a mode that is its own parent, a child whose
      parent link disagrees, two modes of one name, or a blank name
      (04 S27, S39-S42; gap 04 #13).
    - PROFILE-UNUSED-ACTION (warning): a library action no input uses and
      no open pane draft holds (Library.draft_held). Deleted and
      replaced actions stay in memory for Undo (04 S14, S75).
    - PROFILE-LOGICAL-MISSING: a used action (Map to Logical Device, a
      Logical Device condition) names a Logical Device input that the
      Logical Device file (LogicalDevice(), 04 R3) doesn't have: a saved
      permanent id it doesn't know, or, with no id, a type+number it
      doesn't have (D-04-LD-FILE decision 4).
    - PROFILE-OSC-MISSING: a binding on an OSC input (or an Assign Hardware
      link from one) whose saved permanent id OSC's file doesn't have, or,
      with no id, a type+number it doesn't have (D-09-OSC-FILE 2).
    """
    out: list[str] = []
    modes: set[str] = set()
    out += _guarded("profile modes", lambda found: _check_modes(p, found, modes))
    used: dict[uuid.UUID, Any] = {}
    out += _guarded(
        "profile inputs", lambda found: _check_inputs(p, found, modes, used)
    )
    out += _guarded("profile library", lambda found: _check_library(p, found, used))
    out += _guarded(
        "profile logical", lambda found: _check_logical(p, found, used)
    )
    out += _guarded("profile osc", lambda found: _check_osc(p, found))
    return out


def _check_modes(p: Profile, out: list[str], names_out: set[str]) -> None:
    root = p.modes._hierarchy
    if root.value != "":
        out.append(f"PROFILE-MODE-ROOT: the hidden root mode is named '{root.value}'")
    names: list[str] = []
    seen: set[int] = set()
    reached: list[Any] = []
    pending: list[tuple[Any, Any]] = [(root, None)]
    steps = 0
    while pending and steps < _LIMIT:
        steps += 1
        node, came_from = pending.pop()
        if id(node) in seen:
            out.append(
                f"PROFILE-MODE-LOOP: mode '{node.value}' is reached twice in "
                "the mode tree"
            )
            continue
        seen.add(id(node))
        reached.append(node)
        if node.parent is node:
            out.append(
                f"PROFILE-MODE-SELF-PARENT: mode '{node.value}' is its own parent"
            )
        elif came_from is not None and node.parent is not came_from:
            out.append(
                f"PROFILE-MODE-PARENT: mode '{node.value}' is listed under "
                f"'{came_from.value}' but names another parent"
            )
        if node is not root:
            names.append(node.value)
        for child in node.children:
            pending.append((child, node))
    # Every mode's parents lead to the root.
    for node in reached:
        if node is root:
            continue
        current, hops = node, 0
        while current is not None and current is not root and hops <= len(seen):
            current = current.parent
            hops += 1
        if current is not root:
            out.append(
                f"PROFILE-MODE-LOOP: the parents of mode '{node.value}' never "
                "reach the top"
            )
    for name, count in Counter(names).items():
        if count > 1:
            out.append(f"PROFILE-MODE-DUPLICATE: {count} modes are named '{name}'")
    if any(not str(name or "").strip() for name in names):
        out.append("PROFILE-MODE-BLANK: a mode has a blank name")
    names_out.update(name for name in names if name)


def _check_inputs(
    p: Profile, out: list[str], modes: set[str], used: dict[uuid.UUID, Any]
) -> None:
    library = p.library
    for device_id, items in p.inputs.items():
        for item in items:
            label = _input_label(device_id, item)
            if item.mode not in modes:
                out.append(f"PROFILE-MODE-MISSING: {label}: the mode doesn't exist")
            if item.library is not library:
                out.append(f"PROFILE-ITEM-LIBRARY: {label} uses another library")
            pending: list[Any] = []
            for binding in item.action_sequences:
                if binding.root_action is None:
                    out.append(
                        f"PROFILE-BINDING-EMPTY: {label} has a binding with no action"
                    )
                else:
                    pending.append(binding.root_action)
            steps = 0
            while pending and steps < _LIMIT:
                steps += 1
                action = pending.pop()
                if action is None:
                    out.append(f"PROFILE-DANGLING: {label} holds an empty child slot")
                    continue
                if action.id in used:
                    continue
                used[action.id] = action
                if not library.has_action(action.id):
                    out.append(
                        f"PROFILE-DANGLING: {label} uses {_name(action)}, which "
                        "isn't in the library"
                    )
                elif library.get_action(action.id) is not action:
                    out.append(
                        f"PROFILE-NOT-LIBRARY-COPY: {label} uses {_name(action)}, "
                        "but the library holds another object under that id"
                    )
                pending.extend(_children(action))


def _check_library(p: Profile, out: list[str], used: dict[uuid.UUID, Any]) -> None:
    library = p.library
    actions: dict[uuid.UUID, Any] = dict(library._actions)
    for aid, action in actions.items():
        if getattr(action, "id", aid) != aid:
            out.append(f"PROFILE-LIBRARY-ID: {_name(action)} is stored under id {aid}")
        for child in _children(action):
            if child is None or child.id not in actions:
                out.append(
                    f"PROFILE-CHILD-MISSING: {_name(action)} holds "
                    f"{_name(child) if child is not None else 'an empty slot'}, "
                    "which isn't in the library"
                )
    in_drafts = library.draft_held()
    for aid, action in actions.items():
        if aid not in used and aid not in in_drafts:
            out.append(
                f"PROFILE-UNUSED-ACTION: {_name(action)} is in the library but "
                "no input uses it and no open pane holds it"
            )


def _logical_refs(
    action: Any,  # noqa: ANN401
    skip_own: bool = False,
) -> list[tuple[Any, Any, str | None]]:
    """(input type, input id, uid) of each Logical Device input the action
    names; uid None for a reference saved before permanent ids. skip_own:
    leave out a Map to Logical Device that reports logical_missing itself."""
    refs: list[tuple[Any, Any, str | None]] = []
    own = hasattr(action, "logical_input_type") and hasattr(action, "logical_input_id")
    if own and not (skip_own and hasattr(action, "logical_missing")):
        refs.append(
            (
                action.logical_input_type,
                action.logical_input_id,
                _uid_of_ref(action, "logical_input_uid"),
            )
        )
    for condition in getattr(action, "conditions", None) or []:
        if type(condition).__name__ != "LogicalDeviceCondition":
            continue
        for state in getattr(condition, "_states", None) or []:
            refs.append((state.input_type, state.input_id, _uid_of_ref(state, "uid")))
    return refs


def _uid_of_ref(holder: Any, name: str) -> str | None:  # noqa: ANN401
    value = getattr(holder, name, None)
    return value if isinstance(value, str) and value else None


def _check_logical(p: Profile, out: list[str], used: dict[uuid.UUID, Any]) -> None:
    if not any(_logical_refs(action) for action in used.values()):
        return
    from gremlin.logical_device import LogicalDevice

    # One Logical Device for every profile: its module file (D-04-LD-FILE).
    logical = _singleton(LogicalDevice)
    if logical is None:
        return
    for action in used.values():
        if getattr(action, "logical_missing", False) is True:
            # Map to Logical Device says itself (its uid, else type+number).
            out.append(
                f"PROFILE-LOGICAL-MISSING: {_name(action)} names Logical "
                f"Device input {action.logical_input_type} "
                f"{action.logical_input_id}, which the Logical Device doesn't have"
            )
        for input_type, input_id, uid in _logical_refs(action, skip_own=True):
            if uid is not None:
                if logical.identifier_of_uid(uid) is None:
                    out.append(
                        f"PROFILE-LOGICAL-MISSING: {_name(action)} names Logical "
                        f"Device input {input_type} {input_id} (id {uid}), "
                        "which the Logical Device doesn't have"
                    )
                continue
            ident = LogicalDevice.Input.Identifier(input_type, input_id)
            if not logical.exists(ident):
                out.append(
                    f"PROFILE-LOGICAL-MISSING: {_name(action)} names Logical "
                    f"Device input {input_type} {input_id}, which doesn't exist"
                )


def _check_osc(p: Profile, out: list[str]) -> None:
    from gremlin.osc import OSC_DEVICE_UUID, OscDevice

    items = list((p.inputs or {}).get(OSC_DEVICE_UUID, []) or [])
    if not items:
        return
    # Report only: with no OSC device yet the check skips, makes none.
    if _singleton(OscDevice) is None:
        return
    from gremlin.osc_persist import resolve_osc_reference

    seen: set[tuple[Any, Any, Any]] = set()
    for item in items:
        uid = _uid_of_ref(item, "osc_uid")
        key = (uid, item.input_type, item.input_id)
        if key in seen:
            continue
        seen.add(key)
        number = item.input_id if isinstance(item.input_id, int) else None
        ident, _ = resolve_osc_reference(uid, item.input_type, number)
        if ident is not None:
            continue
        kind = getattr(item.input_type, "name", item.input_type)
        out.append(
            f"PROFILE-OSC-MISSING: a binding in mode '{item.mode}' is on OSC "
            f"input {kind} {item.input_id}"
            + (f" (id {uid})" if uid else "")
            + ", which OSC's file doesn't have"
        )


# --- module files -------------------------------------------------------------


def modules() -> list[str]:
    """Problems with the module files and which device uses which.

    - MODULES-DAMAGED: a file in the modules folder that can't be read (bad
      JSON, not UTF-8, not an object); it blocks its device (03 S22, S64).
    - MODULES-SHARED-FILE: two connected devices use one file (03 S1, S6,
      S7: each twin and each vJoy has its own). Found with the one rule,
      registry.resolve_module_slug (what hardware_profile._active_module_path
      uses).
    - MODULES-BINDING-MISSING: a saved file choice (module-file-bindings)
      names a file that isn't there.

    The binding checks are skipped until the program has registered its
    bindings setting (reading it would register it).
    """
    return _guarded("modules", _check_modules)


def _bindings_registered() -> bool:
    from gremlin.config import Configuration

    return Configuration().exists("global", "internal", "module-file-bindings")


def _check_modules(out: list[str]) -> None:
    from gremlin.modules import registry, store

    folder = store.folder()
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            if not path.is_file():
                continue
            if registry.read_doc(path) is None:
                out.append(f"MODULES-DAMAGED: {path.name} can't be read")
    if not _bindings_registered():
        return
    out += _guarded("modules shared files", _check_shared_files)
    for key, value in sorted(store.bindings().items()):
        slug = store.own_slug(value) if str(value or "").strip() else ""
        if not slug or not store.path_of(slug).is_file():
            out.append(
                f"MODULES-BINDING-MISSING: the saved choice for {key} names "
                f"'{value}', which isn't in the modules folder"
            )


def _check_shared_files(out: list[str]) -> None:
    from gremlin import device_initialization
    from gremlin.modules import store

    users: dict[str, list[str]] = {}
    devices = [
        (str(getattr(dev, "name", "") or ""), dev)
        for dev in device_initialization.physical_devices() or []
    ] + [
        (f"vJoy {getattr(dev, 'vjoy_id', '')}", dev)
        for dev in device_initialization.vjoy_devices() or []
    ]
    for name, dev in devices:
        guid = str(getattr(dev, "device_guid", "") or "")
        slug = store.slug_for(name, guid)
        users.setdefault(slug, []).append(f"{name} ({guid})")
    for slug, names in sorted(users.items()):
        if len(names) > 1:
            out.append(
                f"MODULES-SHARED-FILE: {slug}.json is used by {', '.join(names)}"
            )


# --- after Stop ---------------------------------------------------------------


def after_stop() -> list[str]:
    """Problems a stopped Run left behind (spec 06 S17-S29).

    - RUN-HELD-KEYS: keys a macro, Map to Keyboard or a script still holds
      (S21, S31).
    - RUN-HELD-BUTTONS: mouse buttons still held (S22).
    - RUN-PENDING-PULSES: pulse releases still waiting (S24).
    - RUN-TIMERS-LEFT: a timer a Run started (Tempo, Double Tap, Smart
      Toggle) can still fire (S30).
    - RUN-OPEN: run_scope still counts a Run as on, or Stop is half done.
    - RUN-MODE-TEMPORARY: a temporary mode outlived the Run (Q3, R3).
    - RUN-ACTIVE: the runtime still counts as running (S1, S4).
    - RUN-MACRO-RUNNING: the macro manager still runs (S20).
    - RUN-VJOY-HELD: a vJoy device is still held (S17, S29).
    - RUN-XBOX-PLUGGED: an Xbox pad is still plugged in (S17, S29).
    - RUN-THREADS-LEFT: a thread a Run starts is still running (S25, S27).
      Main-thread timers are listed too (gremlin.threads).

    Only modules already loaded are looked at: one that isn't loaded holds
    nothing, and nothing is created to be checked.
    """
    return _guarded("after stop", _check_after_stop)


def _loaded(name: str) -> Any | None:  # noqa: ANN401
    return sys.modules.get(name)


def _singleton(cls: type) -> Any | None:  # noqa: ANN401
    from gremlin.common import SingletonMetaclass

    return SingletonMetaclass._instances.get(cls)


def _check_after_stop(out: list[str]) -> None:
    # What a Run holds is run_scope's (map 3); the older per-module lists are
    # read too while they exist.
    keys: list[object] = []
    buttons: list[object] = []
    pulses = 0
    scope = _loaded("gremlin.run_scope")
    if scope is not None:
        if scope.running() or scope.stopping():
            out.append("RUN-OPEN: a Run is still on or its Stop is not done")
        for kind, ident in scope.held():
            (keys if kind == "key" else buttons).append(ident)
        timers = scope.pending_timers()
        stale = [t for t in timers if not scope.alive(t.run)]
        pulses += len([t for t in stale if t.at_stop == "fire"])
        others = sorted({t.name for t in stale if t.at_stop != "fire"})
        if others:
            out.append(f"RUN-TIMERS-LEFT: can still fire: {', '.join(others)}")
    macro = _loaded("gremlin.macro")
    if macro is not None:
        keys += [k for k in (getattr(macro, "_held_keys", {}) or {}) if k not in keys]
        manager = _singleton(macro.MacroManager)
        if manager is not None and getattr(manager, "_is_running", False):
            out.append("RUN-MACRO-RUNNING: the macro manager still runs")
    sendinput = _loaded("gremlin.sendinput")
    if sendinput is not None:
        old_buttons = list(getattr(sendinput, "_held_buttons", []) or [])
        buttons += [b for b in old_buttons if b not in buttons]
    if keys:
        out.append(f"RUN-HELD-KEYS: {len(keys)} key(s) still held: {keys}")
    if buttons:
        out.append(f"RUN-HELD-BUTTONS: mouse button(s) still held: {buttons}")
    base = _loaded("gremlin.base_classes")
    if base is not None:
        # The list keeps a release that already ran until the next pulse;
        # only one still waiting counts.
        pulses += len(
            [
                p
                for p in getattr(base, "_pending_pulses", []) or []
                if p.is_alive()
            ]
        )
    if pulses:
        out.append(f"RUN-PENDING-PULSES: {pulses} pulse release(s) still waiting")
    modes = _loaded("gremlin.mode_manager")
    if modes is not None:
        manager = modes.ModeManager.instance
        stack = list(getattr(manager, "_mode_stack", []) or []) if manager else []
        temporary = [m.name for m in stack if getattr(m, "is_temporary", False)]
        if temporary:
            out.append(
                f"RUN-MODE-TEMPORARY: temporary mode(s) still on: {temporary}"
            )
    state = _loaded("gremlin.shared_state")
    if state is not None and state.runtime_active():
        out.append("RUN-ACTIVE: the runtime still counts as running")
    # Asked of the output module, which alone holds the drivers (layer rule).
    output = _loaded("gremlin.modules.output")
    if output is not None:
        held_ids = [str(k) for k in output.held_vjoy_ids()]
        if held_ids:
            out.append(
                f"RUN-VJOY-HELD: vJoy device(s) {', '.join(held_ids)} still held"
            )
        pads = [str(k) for k in output.plugged_xbox_pads()]
        if pads:
            out.append(
                f"RUN-XBOX-PLUGGED: Xbox pad(s) {', '.join(pads)} still plugged in"
            )
    threads = _loaded("gremlin.threads")
    if threads is not None:
        left = [
            name
            for name in threads.running()
            if name.removeprefix(threads.PREFIX) in RUN_THREADS
        ]
        if left:
            out.append(f"RUN-THREADS-LEFT: still running: {', '.join(left)}")
