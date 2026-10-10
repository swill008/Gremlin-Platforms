# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Action editor matrix harness: one action, one input, one editing surface.

Surfaces (the ways a user edits an action):

- ``Surface.CONFIG_PAGE``: the live editor path. Add Action is the root
  action model's ``appendAction`` (``Library.create`` + ``start_new``) on the
  real input, no draft and no OK. No Undo: Configuration Undo steps come
  only from the pane's OK and Delete (05 S35).
- ``Surface.PANE_BUTTON_MAP``: the Configuration pane as the Button Map and
  the Configuration page open it, ``BindingCatalogModel.beginPane`` (a stick
  axis, button or hat of the fake "pJoy Pro").
- ``Surface.PANE_LOGICAL``: the Logical Device page's pane,
  ``LogicalLayoutModel.beginPane`` (a Logical Device axis, button or hat).
- ``Surface.PANE_KEYBOARD``: the Keyboard page's pane,
  ``KeyboardPaneModel.showInput`` (key A).

Every pane edit happens in the draft the pane's own models show; OK is
``commitPane`` (``Case.commit``).

Typical use, in a test (the ``matrix`` fixture closes each case)::

    case = matrix.open("map-to-vjoy", "button", Surface.PANE_BUTTON_MAP)
    for field in case.fields():
        case.set(field["name"])          # a dummy value
    ok, diff = case.save_reload()
    ok, detail = case.undo_redo()
    outputs = case.run("button", [True, False])
    ok, warnings = case.open_editor()    # the editor QML, off-screen app

What the harness can't drive is recorded, not changed in the program:
open_editor always shows the editor in the Configuration page pane of the
off-screen app (the Logical Device and Keyboard pages host the same
InputConfiguration and editor files); a Keyboard case's editor is shown
on a stick button there.
"""

from __future__ import annotations

import contextlib
import difflib
import json
import os
import pathlib
import sys
import tempfile
import time
import uuid
from collections.abc import Callable, Iterator
from typing import Any
from unittest import mock
from xml.etree import ElementTree

from PySide6 import QtCore

ROOT = pathlib.Path(__file__).resolve().parents[3]
_HERE = pathlib.Path(__file__).resolve().parent

DEFAULT_RESULTS = pathlib.Path(
    r"C:\Users\Stacie\AppData\Local\Temp\claude"
    r"\E--Users-Stacie-Documents-GitHub-Gremlin-Platforms"
    r"\f29f32c5-d945-4e62-b89f-3680504a29c8\scratchpad\aematrix\results.jsonl"
)
RESULTS_ENV = "AE_MATRIX_RESULTS"

# Keyboard page key used by every Keyboard case (A, not extended).
KEY = (30, False)
MODE = "Default"


class Surface:
    CONFIG_PAGE = "config_page"
    PANE_BUTTON_MAP = "pane_button_map"
    PANE_LOGICAL = "pane_logical"
    PANE_KEYBOARD = "pane_keyboard"

    ALL = (CONFIG_PAGE, PANE_BUTTON_MAP, PANE_LOGICAL, PANE_KEYBOARD)
    PANES = (PANE_BUTTON_MAP, PANE_LOGICAL, PANE_KEYBOARD)


# The input kinds each surface edits.
SURFACE_INPUTS: dict[str, tuple[str, ...]] = {
    Surface.CONFIG_PAGE: ("axis", "button", "hat"),
    Surface.PANE_BUTTON_MAP: ("axis", "button", "hat"),
    Surface.PANE_LOGICAL: ("axis", "button", "hat"),
    Surface.PANE_KEYBOARD: ("key",),
}


def _kind(word: str) -> Any:  # noqa: ANN401
    from gremlin.types import InputType

    return {
        "axis": InputType.JoystickAxis,
        "button": InputType.JoystickButton,
        "hat": InputType.JoystickHat,
        "key": InputType.Keyboard,
    }[word]


def _word(kind: Any) -> str:  # noqa: ANN401
    from gremlin.types import InputType

    return {
        InputType.JoystickAxis: "axis",
        InputType.JoystickButton: "button",
        InputType.JoystickHat: "hat",
        InputType.Keyboard: "key",
    }.get(kind, str(kind))


# +-------------------------------------------------------------------------
# | The plugins


def actions() -> list[tuple[str, tuple[str, ...]]]:
    """Every action plugin: (tag, input kinds it allows), sorted by tag.
    Kinds are "axis", "button", "hat", "key". Root is included (it is the
    container every binding has; it is never added with Add Action)."""
    from gremlin import plugin_manager

    out = []
    for tag, cls in plugin_manager.PluginManager().repository.items():
        kinds = tuple(_word(k) for k in getattr(cls, "input_types", ()))
        out.append((tag, kinds))
    return sorted(out)


def plugin(tag: str) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager

    return plugin_manager.PluginManager().tag_map[tag]


def allowed(tag: str, input_kind: str, surface: str) -> bool:
    """The action allows this input kind and the surface edits it."""
    return input_kind in SURFACE_INPUTS[surface] and input_kind in dict(actions())[tag]


def cases(surfaces: tuple[str, ...] = Surface.ALL) -> list[tuple[str, str, str]]:
    """Every (tag, input kind, surface) the matrix covers."""
    return [
        (tag, kind, surface)
        for tag, kinds in actions()
        for surface in surfaces
        for kind in SURFACE_INPUTS[surface]
        if kind in kinds
    ]


# +-------------------------------------------------------------------------
# | Results


def results_path() -> pathlib.Path:
    return pathlib.Path(os.environ.get(RESULTS_ENV) or DEFAULT_RESULTS)


def record(
    tag: str,
    surface: str,
    input_type: str,
    step: str,
    ok: bool | None,
    detail: object = "",
) -> None:
    """One JSON line in the results file ($AE_MATRIX_RESULTS, default the
    scratchpad's aematrix/results.jsonl). ok None: not applicable."""
    path = results_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tag": tag,
        "surface": surface,
        "input": input_type,
        "step": step,
        "ok": ok,
        "detail": detail
        if isinstance(detail, (str, int, float, list, dict))
        else str(detail),
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, default=str) + "\n")


# +-------------------------------------------------------------------------
# | Helpers


def _canon_text(text: str) -> str:
    return ElementTree.canonicalize(text, strip_text=True)


def _pretty(text: str) -> list[str]:
    import xml.dom.minidom

    return xml.dom.minidom.parseString(text).toprettyxml(indent=" ").splitlines()


def _snap_text(snap: dict | None) -> str:
    return json.dumps(snap, sort_keys=True, default=str)


def _snap_lines(text: str) -> list[str]:
    """A snapshot (_snap_text) as readable lines: each XML part pretty."""
    snap = json.loads(text)
    if not isinstance(snap, dict):
        return [text]
    lines: list[str] = []
    for part in [snap.get("input"), *(snap.get("actions") or [])]:
        if isinstance(part, str) and part.startswith("<"):
            lines += _pretty(part)[1:]
        else:
            lines.append(str(part))
    return lines


def _diff(want: str, got: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            _snap_lines(want), _snap_lines(got), "expected", "got", lineterm=""
        )
    )


def _read(model: Any, name: str) -> Any:  # noqa: ANN401
    """A property's value; Qt can't convert some object types (e.g.
    InputIdentifier*, Deadzone*) through property(), so those are read as
    Python attributes. Singleton classes (EventHandler, ModeManager) are
    watched through their instance: Case.watch(EventHandler(), ...)."""
    try:
        return model.property(name)
    except Exception:  # noqa: BLE001
        return getattr(model, name)


def settle(seconds: float = 0.0) -> None:
    """Runs queued Qt events (deleteLater, posted slots), for seconds."""
    end = time.monotonic() + seconds
    while True:
        QtCore.QCoreApplication.processEvents()
        QtCore.QCoreApplication.sendPostedEvents(None, 0)
        if time.monotonic() >= end:
            return
        time.sleep(0.01)


# settle_outputs: how long the recorded outputs must stay the same before
# Run counts them as done.
QUIET = 0.08
# Set to 1 to check every quiet settle against the full wait: a run that
# would have recorded more by then fails (proof that QUIET cut nothing).
SETTLE_CHECK_ENV = "AE_MATRIX_SETTLE_CHECK"


def settle_outputs(
    collected: Callable[[], list[tuple]], wait: float, quiet: float = QUIET
) -> None:
    """Settles until the recorded outputs stop changing for quiet seconds,
    at most wait. Nothing recorded yet: the full wait, so a check that
    nothing is sent (or an output a timer sends late) still gets the old
    time to show up."""
    end = time.monotonic() + wait
    last = len(collected())
    still_since = time.monotonic()
    while True:
        settle()
        now = time.monotonic()
        if now >= end:
            break
        count = len(collected())
        if count != last:
            last, still_since = count, now
        elif count and now - still_since >= quiet:
            break
        time.sleep(0.01)
    if os.environ.get(SETTLE_CHECK_ENV) == "1":
        early = list(collected())
        settle(max(0.0, end - time.monotonic()))
        late = collected()
        assert late == early, (
            f"settle_outputs stopped early: {len(early)} outputs, "
            f"{len(late)} by the full wait {wait} s: {late[len(early) :]}"
        )


def _stick_guid() -> uuid.UUID:
    import dill
    from test import fake_hardware  # pyright: ignore[reportAttributeAccessIssue]

    return dill.GUID(fake_hardware.raw_guid(False)).uuid


class _KeyIdentifier(QtCore.QObject):
    """What the Keyboard page hands showInput for the selected key."""

    def __init__(self) -> None:
        import dill

        super().__init__()
        self.device_guid = dill.UUID_Keyboard
        self.input_type = _kind("key")
        self.input_id = KEY
        self.isValid = True


# Dummy values by Qt type name, given the current value.
def dummy(type_name: str, current: Any) -> Any:  # noqa: ANN401
    """A changed value of the same type (None: no rule for this type)."""
    if type_name == "bool":
        return not bool(current)
    if type_name == "int":
        return int(current or 0) + 1
    if type_name in ("double", "float"):
        value = float(current or 0.0)
        return 0.5 if abs(value - 0.5) > 1e-9 else 0.25
    if type_name == "QString":
        return "matrix" if current != "matrix" else "matrix2"
    return None


# +-------------------------------------------------------------------------
# | One case


class Case:
    """One action on one input on one surface. Make it with open_case (or
    the matrix fixture); close() when done."""

    def __init__(
        self, tag: str, input_type: str, surface: str, tmp: pathlib.Path
    ) -> None:
        from gremlin import shared_state
        from gremlin.profile import Profile

        if surface not in Surface.ALL:
            raise ValueError(f"unknown surface {surface!r}")
        if not allowed(tag, input_type, surface):
            raise ValueError(f"{tag} on a {input_type} isn't on {surface}")
        self.tag = tag
        self.input_type = input_type
        self.surface = surface
        self.tmp = tmp
        self.cls = plugin(tag)
        self._kept: list[QtCore.QObject] = []
        self._prev_profile = shared_state.current_profile
        self.profile = Profile()
        shared_state.current_profile = self.profile
        self.page: Any = None  # the pane's page model (None: live editor)
        self.editor_result: dict | None = None
        self._watched: list[tuple[Any, str]] = []
        self.key = self._make_input()
        self.action = self._add()

    # --- the input -------------------------------------------------------

    def _make_input(self) -> tuple:
        from gremlin.logical_device import LogicalDevice

        kind = _kind(self.input_type)
        if self.surface == Surface.PANE_KEYBOARD:
            import dill

            key = (dill.UUID_Keyboard, kind, KEY, MODE)
        elif self.surface == Surface.PANE_LOGICAL:
            made = LogicalDevice().create(kind)
            self._logical_id = made.id
            key = (LogicalDevice().device_guid, kind, made.id, MODE)
        else:
            key = (_stick_guid(), kind, 1, MODE)
        item = self.profile.get_input_item(*key, create_if_missing=True)
        assert item is not None
        item.add_item_binding()
        return key

    def real_item(self) -> Any:  # noqa: ANN401
        """The profile's input (after an Undo, the one put back)."""
        return self.profile.get_input_item(*self.key, create_if_missing=False)

    # --- opening the surface and adding the action ------------------------

    def _open_page(self) -> None:
        from gremlin.ui import logical_layout
        from gremlin.ui.binding_catalog import BindingCatalogModel, KeyboardPaneModel

        if self.surface == Surface.PANE_BUTTON_MAP:
            model = BindingCatalogModel()
            profile, key = self.profile, self.key

            def spec(device_index: int) -> tuple:
                real = profile.get_input_item(*key, create_if_missing=False)
                return (profile, *key, real)

            model._control_spec = spec  # noqa: SLF001 - the device row stands in
            model.beginPane(0, 0)
        elif self.surface == Surface.PANE_LOGICAL:
            model = logical_layout.LogicalLayoutModel()
            self._parent_key = logical_layout._parent_key(  # noqa: SLF001
                self.key[1], self._logical_id
            )
            model.beginPane(self._parent_key, 0)
        else:
            model = KeyboardPaneModel()
            self._identifier = _KeyIdentifier()
            self._kept.append(self._identifier)
            model.showInput(self._identifier, 0, MODE)
        self.page = model
        self._kept.append(model)
        assert model.paneModel is not None, f"{self.surface}: the pane didn't open"

    def reopen(self) -> None:
        """Opens the pane again on the input (after undo_redo closed it)."""
        if self.surface == Surface.CONFIG_PAGE or self.page is None:
            return
        if self.page.paneModel is not None:
            return
        if self.surface == Surface.PANE_BUTTON_MAP:
            self.page.beginPane(0, 0)
        elif self.surface == Surface.PANE_LOGICAL:
            self.page.beginPane(self._parent_key, 0)
        else:
            self.page.showInput(self._identifier, 0, MODE)

    def binding_model(self) -> Any:  # noqa: ANN401
        """The binding's model as the editor's QML gets it."""
        from gremlin.ui.profile import InputItemModel

        if self.surface == Surface.CONFIG_PAGE:
            owner = InputItemModel(self.real_item(), 0, None)
            self._kept.append(owner)
        else:
            owner = self.page.paneModel
        return owner.data(owner.index(0, 0), 0x0100 + 1)

    def root_model(self) -> Any:  # noqa: ANN401
        return self.binding_model().rootAction

    def _add(self) -> Any:  # noqa: ANN401
        if self.surface != Surface.CONFIG_PAGE:
            self._open_page()
        root = self.root_model()
        if self.tag == "root":
            return root.action_data
        before = list(root.action_data.get_actions()[0])
        root.appendAction(self.cls.name, "children")
        after = list(root.action_data.get_actions()[0])
        made = [a for a in after if all(a is not b for b in before)]
        assert made, f"Add Action made no {self.cls.name}"
        return made[0]

    def model(self) -> Any:  # noqa: ANN401
        """The action's editor model (a fresh lookup: models are rebuilt)."""
        root = self.root_model()
        if root.action_data is self.action:
            return root
        stack = [root]
        while stack:
            current = stack.pop()
            for selector in self._selectors(current):
                for child in current.getActions(selector):
                    if child.action_data is self.action:
                        return child
                    stack.append(child)
        raise LookupError(f"no editor model for {self.tag}")

    @staticmethod
    def _selectors(model: Any) -> list[str]:  # noqa: ANN401
        try:
            return list(model.action_data._valid_selectors())  # noqa: SLF001
        except Exception:  # noqa: BLE001
            return []

    # --- fields ----------------------------------------------------------------

    def fields(self) -> list[dict]:
        """The editor model's own writable properties (not ActionModel's):
        [{"name", "type", "value"}]."""
        model = self.model()
        meta = model.metaObject()
        base = meta
        while base is not None and base.className() != "ActionModel":
            base = base.superClass()
        start = base.propertyCount() if base is not None else meta.propertyOffset()
        out = []
        for i in range(start, meta.propertyCount()):
            prop = meta.property(i)
            if not prop.isWritable():
                continue
            name = prop.name()
            out.append(
                {"name": name, "type": prop.typeName(), "value": _read(model, name)}
            )
        return out

    def get(self, field: str) -> Any:  # noqa: ANN401
        return _read(self.model(), field)

    def set(self, field: str, value: Any = None) -> tuple[bool, Any, Any]:  # noqa: ANN401
        """Sets an editor field as the QML would; value None: a dummy of its
        type. Returns (changed, before, after)."""
        model = self.model()
        meta = model.metaObject()
        prop = meta.property(meta.indexOfProperty(field))
        before = _read(model, field)
        if value is None:
            value = dummy(prop.typeName(), before)
            if value is None:
                return False, before, before
        model.setProperty(field, value)
        settle()
        after = _read(self.model(), field)
        return after != before, before, after

    # --- OK, save, Undo ------------------------------------------------------

    def commit(self) -> bool:
        """OK in the pane (nothing to do on the live editor). True when the
        profile's input now holds the edit (or there was nothing to write)."""
        if self.surface == Surface.CONFIG_PAGE or self.page is None:
            return True
        if self.page.paneModel is None:
            return True
        if not self.page.paneDirty():
            return True
        index = self.page.commitPane()
        settle()
        if index < 0:
            return False
        self._rebind_action()
        return True

    def _rebind_action(self) -> None:
        """After OK the pane edits a new draft: follow the action into it."""
        if self.page is None or self.page.paneModel is None:
            return
        if self.tag == "root":
            self.action = self.root_model().action_data
            return
        root = self.root_model().action_data
        kids = root.get_actions()[0]
        same = [a for a in kids if getattr(a, "tag", "") == self.tag]
        if same:
            self.action = same[-1]

    def xml(self) -> str:
        """The input and its actions as saved (Library.snapshot), as text."""
        return _snap_text(self.profile.library.snapshot(self.real_item()))

    def save_reload(self) -> tuple[bool, str]:
        """OK, save the profile, open it again, save again: (equal, diff)."""
        from gremlin.profile import Profile

        if not self.commit():
            return False, "OK wrote nothing (commitPane -1)"
        first = self.tmp / f"{self.tag}-{self.surface}-{self.input_type}-1.xml"
        second = first.with_name(first.name.replace("-1.xml", "-2.xml"))
        self.profile.to_xml(first)
        back = Profile()
        back.from_xml(first)
        back.to_xml(second)
        a = _canon_text(first.read_text(encoding="utf-8-sig"))
        b = _canon_text(second.read_text(encoding="utf-8-sig"))
        if self.tag != "root" and f'type="{self.tag}"' not in a and self.tag not in a:
            return False, f"{self.tag} isn't in the saved file"
        if a == b:
            return True, ""
        diff = "\n".join(
            difflib.unified_diff(
                _pretty(a), _pretty(b), "saved", "reloaded", lineterm=""
            )
        )
        return False, diff

    def undo_redo(self) -> tuple[bool | None, str]:
        """OK (the edits since the last OK), then Undo and Redo on the
        surface's own Undo: the input as before this OK, then as after it.
        ok None on the live editor (no Undo there, 05 S35). Closes the pane
        (reopen() to go on editing)."""
        if self.surface == Surface.CONFIG_PAGE:
            return None, "the live editor has no Undo (Undo steps come from OK/Delete)"
        before = self.xml()  # the input before this OK
        if not self.commit():
            return False, "OK wrote nothing (commitPane -1)"
        after = self.xml()
        if after == before:
            return False, "OK changed nothing, so there is no Undo step"
        if self.surface == Surface.PANE_BUTTON_MAP:
            self.page.endPane()  # Undo waits while the pane is open
        self.page.undo()
        settle()
        undone = self.xml()
        self.page.redo()
        settle()
        redone = self.xml()
        problems = []
        if undone != before:
            problems.append("Undo didn't put the input back:\n" + _diff(before, undone))
        if redone != after:
            problems.append("Redo didn't give the edit back:\n" + _diff(after, redone))
        if self.surface == Surface.PANE_LOGICAL:
            self.page.endPane()
        return (not problems), "\n".join(problems)

    # --- Run ---------------------------------------------------------------------

    def watch(self, owner: Any, name: str) -> None:  # noqa: ANN401
        """Records calls to owner.name during run() too (default: the
        output module's vJoy/Xbox writes and the keys/mouse fake)."""
        self._watched.append((owner, name))

    def run(
        self,
        event_kind: str | None = None,
        value: Any = True,  # noqa: ANN401
        wait: float = 0.3,
    ) -> list[tuple]:
        """OK, then Run the profile on the real CodeRunner and send the input
        event(s) through the real EventHandler; value may be a list (one
        event each, in order). Returns what reached the outputs:
        ("write_vjoy", vjoy, kind, id, value), ("release_vjoy_button", ...),
        ("write_xbox", ...), ("key", scan, extended, pressed),
        ("input", count) for mouse, and any watch()ed call. wait: the most
        it waits after the last event (settle_outputs: less once the
        outputs have stopped changing; the whole wait when none came)."""
        if not self.commit():
            raise AssertionError("OK wrote nothing (commitPane -1)")
        kind = event_kind or self.input_type
        values = value if isinstance(value, list) else [value]
        with _running(self.profile, self._watched) as collected:
            from gremlin import event_handler

            handler = event_handler.EventHandler()
            for one in values:
                handler.process_event(self._event(kind, one))
                settle(0.02)
            settle_outputs(collected, wait)
            return collected()

    def _event(self, word: str, value: Any) -> Any:  # noqa: ANN401
        from gremlin.event_handler import Event
        from gremlin.types import HatDirection

        guid, kind, input_id, mode = self.key
        if word in ("button", "key"):
            return Event(
                kind,
                input_id,
                guid,
                mode,
                is_pressed=bool(value),
                raw_value=bool(value),
            )
        if word == "axis":
            return Event(
                kind, input_id, guid, mode, value=float(value), raw_value=float(value)
            )
        direction = (
            value if isinstance(value, HatDirection) else HatDirection.to_enum(value)
        )
        return Event(kind, input_id, guid, mode, value=direction, raw_value=direction)

    # --- the editor's QML (off-screen app) ------------------------------------

    def open_editor(
        self, shot: str | pathlib.Path | None = None
    ) -> tuple[bool, list[str]]:
        """Shows this action's editor QML in the off-screen program (its own
        process) and returns (loaded, QML warnings while it loaded). shot:
        also saves a screenshot of the window there."""
        got = open_editors(
            [{"tag": self.tag, "input": self.input_type, "shot": str(shot or "")}],
            self.tmp,
        )[0]
        self.editor_result = got
        return bool(got.get("ok")), list(got.get("warnings", []))

    # --- end ---------------------------------------------------------------------

    def close(self) -> None:
        from gremlin import shared_state

        with contextlib.suppress(Exception):
            if self.page is not None:
                self.page.endPane()
        for obj in self._kept:
            with contextlib.suppress(Exception):
                obj.deleteLater()
        settle()
        shared_state.current_profile = self._prev_profile


def open_case(
    tag: str, input_type: str, surface: str, tmp: pathlib.Path | None = None
) -> Case:
    """A Case: the action added (Add Action) on that input of that surface."""
    folder = tmp or pathlib.Path(tempfile.mkdtemp(prefix="aematrix-"))
    return Case(tag, input_type, surface, folder)


def shot(case: Case, path: str | pathlib.Path) -> bool:
    """Saves an off-screen screenshot of the case's editor (in the program's
    Configuration pane) to path. True when the file was written."""
    ok, _warnings = case.open_editor(shot=path)
    return ok and pathlib.Path(path).is_file()


# +-------------------------------------------------------------------------
# | Running the profile


@contextlib.contextmanager
def _running(
    profile: Any,  # noqa: ANN401
    watched: list[tuple[Any, str]],
) -> Iterator[Callable[[], list[tuple]]]:
    """The profile running on the real CodeRunner; drivers, OSC, sound and
    the input modules are stand-ins, outputs are recorded."""
    from gremlin import code_runner, event_handler, shared_state
    from gremlin.modules import output

    sys.path.insert(0, str(ROOT / "test"))
    import fake_input  # pyright: ignore[reportMissingImports]

    sent: list[tuple] = []
    patches: list[Any] = []

    def patch(owner: Any, name: str, new: Any) -> None:  # noqa: ANN401
        p = mock.patch.object(owner, name, new)
        p.start()
        patches.append(p)

    def recorder(name: str, result: Any = True) -> Callable[..., Any]:  # noqa: ANN401
        def call(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            sent.append((name, *args, *kwargs.values()))
            return result

        return call

    for name in ("output", "OscRuntime", "InputModuleRuntime", "audio_player", "tts"):
        patch(code_runner, name, mock.MagicMock())
    listener = mock.MagicMock(return_value=mock.MagicMock())
    listener.instance = None
    patch(code_runner.event_handler, "EventListener", listener)
    for name in (
        "write_vjoy",
        "write_vjoy_axis_linear",
        "release_vjoy_button",
        "write_xbox",
    ):
        patch(output, name, recorder(name))
    for owner, name in watched:
        patch(owner, name, recorder(name, None))
    mark = len(fake_input.sent)
    run = code_runner.CodeRunner()
    run._refresh_axes = lambda: None  # noqa: SLF001
    try:
        run.start(profile, MODE)
        # What was recorded so far, with the keys and mouse input sent.
        yield lambda: sent + list(fake_input.sent[mark:])
    finally:
        run.stop()
        shared_state.set_runtime_active(False)
        event_handler.EventHandler().resume()
        for p in reversed(patches):
            p.stop()


# +-------------------------------------------------------------------------
# | The editor QML in the off-screen program


def open_editors(requests: list[dict], tmp: pathlib.Path) -> list[dict]:
    """Shows each requested editor in one off-screen program run (one
    process, about 10-20 s to start, then ~1 s per editor).

    requests: [{"tag", "input" ("axis"/"button"/"hat"/"key"), "shot": path
    or ""}]. Returns one dict each: {"tag", "ok", "warnings" (every QML
    warning while it loaded), "plugin_warnings" (those naming the plugin's
    folder), "qml" (the editor's QML type), "shot", "error"}.
    """
    sys.path.insert(0, str(ROOT / "test" / "journeys"))
    from _harness import run_journey  # pyright: ignore[reportMissingImports]

    jobs = []
    for req in requests:
        cls = plugin(req["tag"])
        jobs.append({**req, "name": cls.name, "folder": _plugin_folder(cls)})
    tmp.mkdir(parents=True, exist_ok=True)
    spec = tmp / f"editors-{uuid.uuid4().hex[:8]}.json"
    spec.write_text(json.dumps(jobs), encoding="utf-8")
    home = tmp / f"home-{uuid.uuid4().hex[:8]}"
    out = run_journey(_HERE / "_editor_child.py", home, str(spec))
    got = out.get("editors", [])
    if len(got) != len(requests):
        error = out.get("error", "") + "\n" + out.get("traceback", "")
        got = got + [
            {
                "tag": r["tag"],
                "ok": False,
                "warnings": [],
                "error": error or "no result",
            }
            for r in requests[len(got) :]
        ]
    return got


def _plugin_folder(cls: Any) -> str:  # noqa: ANN401
    module = sys.modules.get(cls.__module__)
    path = pathlib.Path(getattr(module, "__file__", "") or "")
    return path.parent.name
