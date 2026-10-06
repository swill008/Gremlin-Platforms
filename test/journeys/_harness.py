# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Shared harness for the journey tests (test/journeys).

A journey is a user story driven through the real program: the Gremlin
app is built off-screen in its own process (a temporary USERPROFILE, no
network, no hooks), the story calls what the screens call (the QML
functions and the models' slots), and what it saw is printed as one
``RESULT {json}`` line that the pytest side reads.

Each journey file holds both halves: ``main()`` (run as a script, in the
child process) and the pytest tests (in the pytest process).

Nothing reaches the PC: the fake joystick driver and vJoy queries
(test/fake_hardware.py), key and mouse output kept in the process
(test/fake_input.py), and a fake vJoy driver behind the output module
(FakeVJoy below). Waits poll for a result with a generous limit; they never
sleep a fixed time.
"""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback
from collections.abc import Callable, Iterator
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]

# What a journey may take at most (the parts each wait for less).
JOURNEY_TIMEOUT = 110


# +-------------------------------------------------------------------------
# | Pytest side


def run_journey(script: str | pathlib.Path, home: pathlib.Path, *args: str) -> dict:
    """Runs a journey script in its own process and returns its RESULT.

    The child gets home as USERPROFILE, so nothing it writes reaches the
    user's own Gremlin Platforms folder; a second run with the same home
    finds what the first one left (a restart). args go to the script.
    """
    (home / "Gremlin Platforms").mkdir(parents=True, exist_ok=True)
    env = dict(
        os.environ,
        USERPROFILE=str(home),
        QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1",
        HTTPS_PROXY="http://127.0.0.1:9",
        QT_QPA_FONTDIR=os.environ.get(
            "QT_QPA_FONTDIR",
            os.path.join(os.environ.get("WINDIR", "C:/Windows"), "Fonts"),
        ),
        PYTHONIOENCODING="utf-8",
    )
    started = time.monotonic()
    result = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=JOURNEY_TIMEOUT,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, (
        f"No RESULT (exit {result.returncode}).\n--- stdout\n"
        + result.stdout[-4000:]
        + "\n--- stderr\n"
        + result.stderr[-4000:]
    )
    out = json.loads(lines[-1][len("RESULT ") :])
    out["_seconds"] = round(time.monotonic() - started, 1)
    out["_stderr"] = result.stderr[-4000:]
    return out


class JourneyIncomplete(Exception):
    """The journey stopped before it recorded a value (not an
    AssertionError, so an xfail for a known gap doesn't count a journey
    that crashed early as that gap)."""


def step(out: dict, key: str) -> Any:  # noqa: ANN401
    """A value the journey recorded; a clear failure when the journey
    stopped before it (its error and traceback are shown)."""
    if key not in out:
        raise JourneyIncomplete(
            f"The journey never reached {key!r}.\n"
            f"Error: {out.get('error', '(none)')}\n{out.get('traceback', '')}\n"
            f"--- stderr\n{out.get('_stderr', '')}"
        )
    return out[key]


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _load(name: str) -> Any:  # noqa: ANN401
    spec = importlib.util.spec_from_file_location(name, ROOT / "test" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class FakeVJoyControl:
    """One vJoy axis, button or hat: value, is_pressed and direction."""

    def __init__(self, device: FakeVJoyDevice, kind: str, index: int) -> None:
        self._device = device
        self._kind = kind
        self._index = index

    def _get(self) -> Any:  # noqa: ANN401
        return self._device.state.get((self._kind, self._index))

    def _set(self, value: Any) -> None:  # noqa: ANN401
        self._device.state[(self._kind, self._index)] = value
        self._device.writes.append((self._kind, self._index, value))

    value = property(_get, _set)
    is_pressed = property(_get, _set)
    direction = property(_get, _set)


class FakeVJoyDevice:
    """A vJoy device as the output module uses it: 8 axes, 128 buttons,
    4 hats. Every write is recorded in order."""

    def __init__(self, vjoy_id: int) -> None:
        self.vjoy_id = vjoy_id
        self.state: dict[tuple[str, int], Any] = {}
        self.writes: list[tuple[str, int, Any]] = []
        self.valid = True

    def is_axis_valid(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> bool:
        index = axis_id if axis_id is not None else linear_index
        return index is not None and 1 <= int(index) <= 8

    def is_button_valid(self, index: int) -> bool:
        return 1 <= int(index) <= 128

    def is_hat_valid(self, index: int) -> bool:
        return 1 <= int(index) <= 4

    def axis_id(self, linear_index: int) -> int:
        return int(linear_index)

    def axis(
        self, axis_id: int | None = None, linear_index: int | None = None
    ) -> FakeVJoyControl:
        index = axis_id if axis_id is not None else linear_index
        return FakeVJoyControl(self, "axis", int(index or 0))

    def button(self, index: int) -> FakeVJoyControl:
        return FakeVJoyControl(self, "button", int(index))

    def hat(self, index: int) -> FakeVJoyControl:
        return FakeVJoyControl(self, "hat", int(index))

    def is_owned(self) -> bool:
        return self.valid

    def invalidate(self) -> None:
        self.valid = False

    def pressed(self) -> list[int]:
        return sorted(
            index
            for (kind, index), value in self.state.items()
            if kind == "button" and value
        )


class FakeVJoy:
    """Stands in for vjoy.VJoyProxy behind gremlin.modules.output.

    Like the driver: a device opened by Gremlin is held until reset()
    (Stop), which lets every held device go. ``opened`` lists every device
    ever opened (the last one per vJoy id), so a journey can read what a
    device held when it was let go.
    """

    vjoy_devices: dict[int, FakeVJoyDevice] = {}
    opened: dict[int, list[FakeVJoyDevice]] = {}
    resets: int = 0

    def __getitem__(self, vjoy_id: int) -> FakeVJoyDevice:
        devices = FakeVJoy.vjoy_devices
        if vjoy_id not in devices:
            device = FakeVJoyDevice(vjoy_id)
            devices[vjoy_id] = device
            FakeVJoy.opened.setdefault(vjoy_id, []).append(device)
        return devices[vjoy_id]

    @classmethod
    def reset(cls) -> None:
        for device in cls.vjoy_devices.values():
            device.invalidate()
        cls.vjoy_devices = {}
        cls.resets += 1

    @classmethod
    def held_buttons(cls, vjoy_id: int = 1) -> list[int]:
        """Buttons pressed on the device Gremlin holds now ([] when none)."""
        device = cls.vjoy_devices.get(vjoy_id)
        return device.pressed() if device else []

    @classmethod
    def all_writes(cls, vjoy_id: int = 1) -> list[tuple[str, int, Any]]:
        return [w for d in cls.opened.get(vjoy_id, []) for w in d.writes]


def claim_everything() -> dict:
    return {
        "buttons": list(range(1, 129)),
        "axes": list(range(1, 9)),
        "hats": list(range(1, 5)),
        "keys": [],
        "friendly": {},
    }


class Journey:
    """The program, built off-screen, and what a journey needs to drive it."""

    def __init__(self, before_start: Callable[[Journey], None] | None = None) -> None:
        """before_start runs once the fakes are in, before the program
        starts: files written there are on disk when it starts."""
        # Never the user's own folder: run_journey gives a temporary one.
        home = pathlib.Path(os.environ.get("USERPROFILE", "")).resolve()
        users = pathlib.Path(os.environ.get("SystemDrive", "C:") + "/Users")
        real_home = (users / os.environ.get("USERNAME", "")).resolve()
        if (
            not os.environ.get("USERPROFILE")
            or home == real_home
            or os.environ.get("QT_QPA_PLATFORM") != "offscreen"
        ):
            refused = {"error": "not a test folder or not off-screen"}
            print("RESULT " + json.dumps(refused))
            sys.stdout.flush()
            sys.exit(2)
        sys.path.insert(0, str(ROOT))
        os.chdir(ROOT)
        self.out: dict = {}
        self.fake_hardware = _load("fake_hardware")
        self.dill_fake = self.fake_hardware.install(vjoy_ids=(1,))
        self.fake_input = _load("fake_input")
        # Keys and mouse output stay in this process.
        self.fake_input.install()

        import gremlin.ui.update_model as update_model

        update_model.UpdateModel.startup = lambda self, *a, **k: None

        # The program folder is where the script is: Choose Photo would make
        # qml/images there, in the repository (GL-178). The temporary home
        # stands in for it.
        from gremlin.ui import hardware_profile

        hardware_profile._install_root = lambda: home  # type: ignore[assignment]

        import joystick_gremlin

        assert joystick_gremlin.running_offscreen(), "journeys run off-screen only"
        self.messages: list[tuple] = []
        joystick_gremlin._message_box = (  # type: ignore[assignment]
            lambda *a: self.messages.append(a) or 1
        )
        from gremlin.modules import output

        output._vjoy_proxy = lambda: FakeVJoy  # type: ignore[assignment]
        self.vjoy = FakeVJoy

        from gremlin import signal as gremlin_signal

        self.errors: list[str] = []
        gremlin_signal.signal.showError.connect(
            lambda *a: self.errors.append(" | ".join(str(x) for x in a))
        ) if hasattr(gremlin_signal.signal, "showError") else None

        self.app: Any = None
        if before_start is not None:
            before_start(self)
        self.app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
        self.win = self.app.main_window
        # Run doesn't open the OSC port on the PC's network (another
        # Gremlin-Platforms may hold it).
        from gremlin import osc
        from gremlin.config import Configuration

        if Configuration().exists(osc.OSC_SECTION, osc.OSC_GROUP, "enabled"):
            Configuration().set(osc.OSC_SECTION, osc.OSC_GROUP, "enabled", False)
        from PySide6 import QtTest

        self.QTest = QtTest.QTest

    # --- running the story ---------------------------------------------------

    def run(self, story: Callable[[Journey], None]) -> None:
        """Runs the story; prints RESULT with what it recorded (and the error
        if it stopped), then ends the process (the app's threads would keep
        it alive)."""
        try:
            story(self)
        except BaseException as exc:  # noqa: BLE001
            self.out["error"] = f"{type(exc).__name__}: {exc}"
            self.out["traceback"] = traceback.format_exc()
        try:
            if self.backend.runner.is_running():
                self.backend.activate_gremlin(False)
        except Exception:
            pass
        self.out["_errors"] = self.errors
        self.out["_messages"] = [str(m) for m in self.messages]
        print("RESULT " + json.dumps(self.out, default=str), flush=True)
        sys.stdout.flush()
        os._exit(0)

    def wait_until(
        self, check: Callable[[], object], what: str, timeout: float = 15.0
    ) -> Any:  # noqa: ANN401
        """Processes events until check() is truthy; fails after timeout."""
        deadline = time.monotonic() + timeout
        while True:
            value = check()
            if value:
                return value
            if time.monotonic() > deadline:
                raise TimeoutError(f"Waited {timeout:.0f} s for: {what}")
            self.QTest.qWait(20)

    def await_value(
        self,
        read: Callable[[], Any],
        expected: Any,  # noqa: ANN401
        timeout: float = 5.0,
    ) -> Any:  # noqa: ANN401
        """read() once it gives expected, or what it gives after timeout
        (the test then shows the wrong value instead of a timeout)."""
        deadline = time.monotonic() + timeout
        while True:
            value = read()
            if value == expected or time.monotonic() > deadline:
                return value
            self.QTest.qWait(20)

    def settle(self) -> None:
        """Lets queued events run (posted slots, deleteLater)."""
        from PySide6 import QtCore

        for _ in range(3):
            QtCore.QCoreApplication.processEvents()
            QtCore.QCoreApplication.sendPostedEvents(None, 0)

    # --- the program -----------------------------------------------------------

    @property
    def backend(self) -> Any:  # noqa: ANN401
        import gremlin.ui.backend

        return gremlin.ui.backend.Backend()

    @property
    def profile(self) -> Any:  # noqa: ANN401
        return self.backend.profile

    def ev(self, code: str, target: Any = None) -> Any:  # noqa: ANN401
        """Evaluates QML code in a window's context (the main window by
        default), as the screen's own handlers would run it."""
        from PySide6 import QtQml

        host = target or self.win
        context = QtQml.qmlContext(host)
        assert context is not None, f"no QML context for {host}"
        expr = QtQml.QQmlExpression(context, host, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(f"QML: {code}: {expr.error().toString()}")
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    def window(self, title: str, timeout: float = 15.0) -> Any:  # noqa: ANN401
        """The visible top-level window whose title starts with title."""
        from PySide6 import QtQuick

        def find() -> Any:  # noqa: ANN401
            for w in self.app.topLevelWindows():
                if (
                    isinstance(w, QtQuick.QQuickWindow)
                    and w.title().startswith(title)
                    and w.isVisible()
                ):
                    return w
            return None

        return self.wait_until(find, f"the {title} window", timeout)

    @staticmethod
    def walk(item: Any) -> Iterator[Any]:  # noqa: ANN401
        yield item
        for child in item.childItems():
            yield from Journey.walk(child)

    def item(self, window: Any, name: str) -> Any:  # noqa: ANN401
        """An item by objectName: Repeater rows and popups included."""
        from PySide6 import QtQuick

        for found in self.walk(window.contentItem()):
            if found.objectName() == name:
                return found
        return window.findChild(QtQuick.QQuickItem, name)

    def click(self, button: Any) -> None:  # noqa: ANN401
        """A click on a button item: its clicked signal, so its own
        onClicked runs."""
        assert button is not None, "no button to click"
        self.ev("clicked(); true", button)

    def press_in(self, popup: str, label: str, target: Any = None) -> None:  # noqa: ANN401
        """Clicks the visible button labelled label inside a popup (named by
        its QML id, evaluated in target's context)."""
        found = self.ev(
            "(function() { function find(it) { if (!it) return null;"
            f" if (it.text === {json.dumps(label)} && it.visible"
            " && typeof it.clicked === 'function') return it;"
            " var kids = it.children || [];"
            " for (var i = 0; i < kids.length; i++) { var f = find(kids[i]);"
            " if (f) return f } return null }"
            f" var b = find({popup}.contentItem); if (!b) return false;"
            " b.clicked(); return true })()",
            target,
        )
        assert found, f"no {label!r} button in {popup}"

    # --- hardware --------------------------------------------------------------

    def add_stick(self, name: str, seed: int) -> Any:  # noqa: ANN401
        """Another stick for the fake driver (before the start): a copy of
        the fake "pJoy Pro" with its own id, and name when given (the same
        name makes a twin). Returns its dill.GUID."""
        import dill

        raw = self.fake_hardware.raw_device(is_virtual=False)
        raw.device_guid = dill._GUID(
            Data1=0x5A000000 + seed,
            Data2=seed,
            Data3=seed,
            Data4=(7, 7, 7, 7, 7, 7, 7, seed & 0xFF),
        )
        raw.name = name.encode("utf-8")
        raw.product_id = 0xC000 + seed
        self.dill_fake.devices.append(raw)
        return dill.GUID(raw.device_guid)

    def stick(self, name: str = "pJoy Pro") -> Any:  # noqa: ANN401
        """The connected stick shown with this name (a twin is "<name> (2)")."""
        from gremlin import device_initialization

        return next(
            d for d in device_initialization.physical_devices() if d.name == name
        )

    def press(self, device: Any, button: int, pressed: bool) -> None:  # noqa: ANN401
        """A stick button, as the joystick driver reports it."""
        import dill

        callback = self.dill_fake.input_event_callback
        assert callback is not None, "the event listener is not listening"
        data = dill._JoystickInputData(
            device_guid=device.device_guid.ctypes,
            input_type=2,
            input_index=button,
            value=1 if pressed else 0,
        )
        callback(data)

    def key(self, scan_code: int, pressed: bool, extended: bool = False) -> None:
        """A key on the PC's keyboard, as the keyboard hook reports it (the
        hook itself is off off-screen; its callbacks are what it calls)."""
        from gremlin import windows_event_hook

        event = windows_event_hook.KeyEvent(scan_code, extended, pressed, False)
        for callback in list(windows_event_hook.g_keyboard_callbacks):
            callback(event)

    def write_module(self, slug: str, doc: dict) -> pathlib.Path:
        """A module file, written as Module Setup's Save writes it."""
        if self.app is None:  # before the start: already on disk
            folder = pathlib.Path(
                os.environ["USERPROFILE"], "Gremlin Platforms", "modules"
            )
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{slug}.json"
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            return path
        from gremlin import util
        from gremlin.modules import module_file

        folder = util.modules_dir()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{slug}.json"
        module_file.write_json(path, doc)
        return path

    def input_module(
        self,
        name: str = "pJoy Pro",
        buttons: list[int] | None = None,
        guid: Any = None,  # noqa: ANN401
        slug: str = "",
    ) -> pathlib.Path:
        """The stick's input module, claiming buttons (all when None), bound
        to guid (the fake "pJoy Pro" when None)."""
        import dill
        from gremlin.modules.ids import stored_guid_key
        from gremlin.modules.registry import plain_slug

        if guid is None:
            guid = dill.GUID(self.fake_hardware.raw_guid(False))
        claim = claim_everything()
        if buttons is not None:
            claim["buttons"] = list(buttons)
        return self.write_module(
            slug or plain_slug(name),
            {
                "kind": "control.hardware",
                "device": name,
                "direction": "source",
                "boundGuidLocal": stored_guid_key(guid),
                "claim": claim,
                "nodes": [],
            },
        )

    def vjoy_module(self, vjoy_id: int = 1) -> pathlib.Path:
        """The vJoy output module, claiming every output."""
        return self.write_module(
            f"vjoy_{vjoy_id}",
            {
                "device": f"vJoy {vjoy_id}",
                "direction": "dest",
                "claim": claim_everything(),
            },
        )

    # --- profiles ----------------------------------------------------------------

    def map_button(
        self,
        uid: Any,  # noqa: ANN401
        button: int,
        mode: str,
        vjoy_button: int,
        vjoy: int = 1,
    ) -> Any:  # noqa: ANN401
        """A Map to vJoy action on a stick button, in the open profile."""
        from gremlin import plugin_manager
        from gremlin.types import InputType

        action = plugin_manager.PluginManager().create_instance(
            "Map to vJoy", InputType.JoystickButton
        )
        action.vjoy_device_id = vjoy
        action.vjoy_input_id = vjoy_button
        action.vjoy_input_type = InputType.JoystickButton
        item = self.profile.get_input_item(
            uid, InputType.JoystickButton, button, mode, True
        )
        item.add_item_binding().root_action.insert_action(action, "children")
        return action

    def wires(self, uid: Any) -> dict[str, list]:  # noqa: ANN401
        """A stick's buttons with actions, by mode: {mode: [[button, [what
        each action sends]]]} (vJoy button numbers; other actions by name)."""
        found: dict[str, list] = {}
        for item in sorted(
            self.profile.inputs.get(uid, []), key=lambda i: (i.mode, i.input_id)
        ):
            if not item.action_sequences:
                continue
            sends = []
            for binding in item.action_sequences:
                for action in binding.root_action.get_actions()[0]:
                    sends.append(getattr(action, "vjoy_input_id", action.name))
            found.setdefault(item.mode, []).append([item.input_id, sends])
        return found

    def save_and_reopen(self, name: str) -> tuple[pathlib.Path, str]:
        """Saves the open profile as profiles/<name>.xml (File > Save As),
        opens a new one and then this file again (File > Load Profile)."""
        from PySide6 import QtCore

        from gremlin import util

        path = util.profiles_dir() / f"{name}.xml"
        url = QtCore.QUrl.fromLocalFile(str(path)).toString()
        assert self.backend.saveProfile(url), "the profile was not saved"
        self.backend.newProfile()
        self.backend.loadProfile(url)
        assert pathlib.Path(self.backend.profilePath()) == path, "not loaded again"
        return path, url

    def reopen(self, url: str) -> None:
        """Opens another (new) profile, then this one again."""
        self.backend.newProfile()
        self.backend.loadProfile(url)

    # --- Configuration page ---------------------------------------------------

    def open_configuration(self, slug: str) -> Any:  # noqa: ANN401
        """Opens the Configuration page for a Home card, as a click on the
        card does; returns the page's own BindingCatalogModel."""
        from gremlin.ui.binding_catalog import BindingCatalogModel

        self.ev(f"openConfigurationForCard(_moduleModel.cardMap({json.dumps(slug)}))")
        page = self.wait_until(
            lambda: self.ev("catalogPane()"), f"the Configuration page of {slug}"
        )
        catalog = self.wait_until(
            lambda: page.findChild(BindingCatalogModel), "the page's catalog model"
        )
        self.wait_until(lambda: catalog.rowCount() > 0, "the catalog rows")
        return catalog

    @staticmethod
    def catalog_rows(catalog: Any) -> list[dict]:  # noqa: ANN401
        names = {int(k): bytes(v).decode() for k, v in catalog.roleNames().items()}
        rows = []
        for row in range(catalog.rowCount()):
            index = catalog.index(row, 0)
            rows.append(
                {name: catalog.data(index, role) for role, name in names.items()}
            )
        return rows

    def device_index(self, catalog: Any, kind: str, hw: int) -> int:  # noqa: ANN401
        """The device index of a control's row ("button", 1...)."""
        for row in self.catalog_rows(catalog):
            if row["kind"] == kind and int(row["hwId"]) == hw:
                return int(row["deviceIndex"])
        raise LookupError(f"No catalog row for {kind} {hw}")

    @staticmethod
    def pane_actions(catalog: Any, binding: int = 0) -> list[Any]:  # noqa: ANN401
        """The action editors' models of one binding in the open pane, as
        the pane's ActionNodes get them (root action, then its children)."""
        pane = catalog.paneModel
        assert pane is not None, "no pane open"
        binding_model = pane.data(pane.index(binding, 0), 0x0100 + 1)
        root = binding_model.rootAction
        return [root, *root.getActions("children")]

    def reload_modules(self) -> None:
        """What a Module Setup save sets off: the claims are read again."""
        from gremlin.modules import output
        from gremlin.modules.runtime import InputModuleRuntime

        output.refresh()
        InputModuleRuntime().reload()
