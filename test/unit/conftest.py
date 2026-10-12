# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

import pathlib
from collections.abc import Iterator

import pytest

import dill
import gremlin.config
import gremlin.device_initialization
import gremlin.event_handler

# Import creates required user profile directory.
import joystick_gremlin
from test import fake_hardware

# The fake joystick driver and vJoy from the start: the unit tests never
# read the real joysticks or vJoy (same results on every PC, and no clash
# with a Gremlin-Platforms open on this one).
fake_hardware.install(vjoy_ids=(1,))


def get_fake_device_raw_guid(is_virtual: bool) -> dill._GUID:
    """Returns "raw" _GUID for a fake device. Rarely used directly."""
    return fake_hardware.raw_guid(is_virtual)


def get_fake_device_guid(is_virtual: bool) -> dill.GUID:
    """Returns dill.GUID for a fake device. Typically .uuid is used."""
    return dill.GUID(get_fake_device_raw_guid(is_virtual))


def _make_fake_device(is_virtual: bool) -> dill.DeviceSummary:
    """Creates a repeatable, faked DeviceSummary."""
    return dill.DeviceSummary(fake_hardware.raw_device(is_virtual))


@pytest.fixture(autouse=True)
def _settings_kept() -> Iterator[None]:
    """A test that makes its own Configuration (a fresh settings file) must
    not leave it behind: the program's settings, registered when modules
    load (Tempo's duration...), would be missing for every later test in the
    same run. Which tests follow depends on how the runner splits them."""
    from gremlin.common import SingletonMetaclass
    from gremlin.ui.option import MetaConfigOption

    # The Options registry the same way: options are registered when modules
    # load (the Device Mapping Editor's library entry...), so a test that makes a fresh
    # one must not leave it behind either.
    # The class itself, taken now: a test may monkeypatch the module's name
    # with a fake (test_final_05 S7) and the undo can come after this one.
    cfg_cls = gremlin.config.Configuration
    kept = {
        cls: SingletonMetaclass._instances.get(cls)
        for cls in (cfg_cls, MetaConfigOption)
    }
    yield
    used = SingletonMetaclass._instances.get(cfg_cls)
    original = kept[cfg_cls]
    if original is not None and used is not None and used is not original:
        # A module first imported during the test registered its settings
        # into the test's own Configuration (output.cant_send_action_texts
        # imports the Macro plugin, 2026-10-11): the import won't run again,
        # so hand them to the kept one or they are missing for the rest of
        # the run.
        with used._lock:  # noqa: SLF001
            fresh = {
                key: dict(entry)
                for key, entry in used._data.items()  # noqa: SLF001
                if entry.get("is_registered")
            }
        with original._lock:  # noqa: SLF001
            for key, entry in fresh.items():
                original._data.setdefault(key, entry)  # noqa: SLF001
    for cls, original in kept.items():
        if original is not None:
            SingletonMetaclass._instances[cls] = original


@pytest.fixture(autouse=True)
def _logical_device_kept() -> Iterator[None]:
    """The Logical Device is one shared layout now (D-04-LD-FILE): no profile
    load resets it, so a test that adds controls must not leave them for a
    later test in the same process."""
    from gremlin.logical_device import LogicalDevice

    rows = LogicalDevice()
    kept, dirty = rows.to_dict(), rows.dirty
    yield
    rows = LogicalDevice()
    if rows.to_dict() != kept or rows.dirty != dirty:
        rows.load_dict(kept)
        if dirty:
            rows._changed()  # noqa: SLF001 - put the unsaved mark back


@pytest.fixture(autouse=True)
def _osc_rows_kept() -> Iterator[None]:
    """OSC's address list is shared too (D-09-OSC-FILE): a test that adds or
    changes OSC inputs must not leave them, or their unsaved mark, behind."""
    from gremlin.osc import OscDevice

    rows = OscDevice().rows
    kept, dirty = rows.to_dict(), rows.dirty
    yield
    rows = OscDevice().rows
    if rows.to_dict() != kept or rows.dirty != dirty:
        rows.load_dict(kept)
        if dirty:
            rows._changed()  # noqa: SLF001 - put the unsaved mark back


@pytest.fixture(autouse=True)
def _no_real_clipboard(monkeypatch: pytest.MonkeyPatch) -> Iterator[list[str]]:
    """The Input Tester's Copy buttons never reach the real clipboard in a
    test: it is the user's, and under a full run it crashed the part
    (access violation in setText, twice on 2026-10-10)."""
    from gremlin.input_tester import model

    copied: list[str] = []
    monkeypatch.setattr(model, "_set_clipboard", copied.append)
    yield copied


@pytest.fixture(autouse=True)
def _trace_off_after() -> Iterator[None]:
    """Tracing is program-wide (D-01-TRACE): a test that turns it on must not
    leave it on, its ticks or its notice for the next test. The change hooks
    stay, so the watchers keep listening."""
    yield
    from gremlin import trace

    if trace.enabled():
        trace.set_enabled(False)
    with trace._LOCK:  # noqa: SLF001
        trace._ticks = None  # noqa: SLF001 - ticks reread from the next test's settings
        trace._oos.clear()  # noqa: SLF001
    trace.clear_notice()


@pytest.fixture(autouse=True)
def _home_models_quiet() -> Iterator[None]:
    """A Home card list a test makes stays connected to the program-wide
    signals (its lambda on inputItemChanged keeps it alive), so a later
    profileChanged ran its 200 ms reload inside whichever test came next:
    one that stands in for the device list failed on a stand-in without a
    vendor id (seed 179731, unit-2). Models made by a module-scoped fixture
    are set up before this and kept."""
    import warnings

    from PySide6 import QtCore

    from gremlin import event_handler, signal
    from gremlin.modules.runtime import InputModuleRuntime
    from gremlin.ui import module_model

    cls = module_model.ModuleListModel
    made: list[module_model.ModuleListModel] = []
    real_init = cls.__init__

    def init(
        self: module_model.ModuleListModel, *args: object, **kwargs: object
    ) -> None:
        real_init(self, *args, **kwargs)
        made.append(self)

    cls.__init__ = init  # type: ignore[method-assign]
    try:
        yield
    finally:
        cls.__init__ = real_init  # type: ignore[method-assign]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # already disconnected
            for model in made:
                try:
                    for timer in model.findChildren(QtCore.QTimer):
                        timer.stop()
                        timer.timeout.disconnect()
                    listener = event_handler.EventListener()
                    for sig, slot in (
                        (listener.device_change_event, model._schedule_reload),
                        (InputModuleRuntime().event, model._on_joy),
                        (signal.signal.profileChanged, model._schedule_reload),
                        (signal.signal.configChanged, model._schedule_refresh),
                        (signal.signal.configChanged, model._follow_card_sizes),
                        (signal.signal.logicalDeviceReloaded, model._logical_reloaded),
                        (signal.signal.cantSendChanged, model._follow_cant_send),
                        (signal.signal.bindingsChanged, model._follow_bindings),
                        (signal.signal.deviceNamesChanged, model._follow_names),
                        (signal.signal.moduleFilesChanged, model._follow_module_files),
                    ):
                        try:
                            sig.disconnect(slot)
                        except (RuntimeError, TypeError):
                            pass
                except RuntimeError:  # deleted by the test
                    pass


@pytest.fixture(autouse=True)
def _backends_stop_ticking() -> Iterator[None]:
    """A Backend a test makes (Backend.klass, not the shared instance) stays
    alive after it, and its 60 s recovery timer (04 S94) then serialised a
    stale profile inside whichever test came next. A full run died with an
    access violation in processEvents exactly when such Backends were due
    their first tick (seed 869523, unit-4, CRASH-G2). The timer stops when
    the test that made it ends."""
    from gremlin.ui import backend

    cls = backend.Backend.klass
    made: list[object] = []
    real_init = cls.__init__

    def init(self: object, *args: object, **kwargs: object) -> None:
        made.append(self)
        real_init(self, *args, **kwargs)  # type: ignore[arg-type]

    cls.__init__ = init  # type: ignore[method-assign]
    try:
        yield
    finally:
        cls.__init__ = real_init  # type: ignore[method-assign]
        for be in made:
            timer = getattr(be, "_recovery_timer", None)
            try:
                if timer is not None:
                    timer.stop()
            except RuntimeError:  # deleted by the test
                pass


@pytest.fixture(autouse=True)
def _layout_models_quiet() -> Iterator[None]:
    """A page model (ControlLayoutModel) a test makes outlives it when it is
    only deleteLater'd (no event loop runs the deletion), and it still
    follows the program-wide notices: cantSendChanged then rebuilt nine
    leftover Device Bindings page models on a later test's stand-in profile
    (seed 53633, unit-4, test_osc_run). Models a QML page holds (they have
    a parent) are left to that page; models made by a module-scoped
    fixture are set up before this and kept."""
    import warnings

    import shiboken6

    from gremlin import signal
    from gremlin.ui import control_layout

    cls = control_layout.ControlLayoutModel
    made: list[control_layout.ControlLayoutModel] = []
    real_init = cls.__init__

    def init(
        self: control_layout.ControlLayoutModel, *args: object, **kwargs: object
    ) -> None:
        real_init(self, *args, **kwargs)
        made.append(self)

    cls.__init__ = init  # type: ignore[method-assign]
    try:
        yield
    finally:
        cls.__init__ = real_init  # type: ignore[method-assign]
        sig = signal.signal
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)  # already disconnected
            for model in made:
                if not shiboken6.isValid(model) or model.parent() is not None:
                    continue
                for notice, name in (
                    (sig.profileChanged, "_on_profile"),
                    (sig.modeRenamed, "_on_mode_renamed"),
                    (sig.modeDeleted, "_on_mode_deleted"),
                    (sig.cantSendChanged, "_on_cant_send"),
                    (sig.inputItemChanged, "_on_input_changed"),
                    (sig.configChanged, "reload"),
                    (sig.logicalDeviceModified, "_on_external"),
                    (sig.logicalDeviceReloaded, "_on_reloaded"),
                ):
                    slot = getattr(model, name, None)
                    if slot is None:
                        continue
                    try:
                        notice.disconnect(slot)
                    except (RuntimeError, TypeError):
                        pass


@pytest.fixture(autouse=True)
def _no_settings_notice_left() -> Iterator[None]:
    """A test that reads a damaged settings file must not leave the
    'Settings Reset' notice for a later test that builds the app."""
    yield
    gremlin.config._damaged_copy = ""


@pytest.fixture(scope="package", autouse=True)
def register_config_options() -> None:
    """The program's settings, registered first as at start (items 31, 47):
    the fixtures below read them (twin device names), and pytest doesn't
    set up autouse fixtures in the order they are written."""
    joystick_gremlin.register_config_options()


@pytest.fixture(scope="package", autouse=True)
def joystick_init(register_config_options: None) -> None:
    # The program's settings come first, as at start: device names read the
    # twin names, and an unregistered one only logs a GremlinError (item 31).
    assert gremlin.config.Configuration().exists(
        *gremlin.device_initialization.TWIN_SETTING
    ), "device start-up before the program's settings were registered"
    # The fake driver (installed above) lists the two fake devices and vJoy 1.
    dill.DILL.init()
    gremlin.device_initialization.joystick_devices_initialization()


@pytest.fixture(scope="package", autouse=True)
def event_listener(
    register_config_options: None,
) -> Iterator[gremlin.event_handler.EventListener]:
    """The shared event listener, started before the first test and stopped
    after the last: its threads belong to the package, not to whichever
    test happens to use it first (that depends on the order, which differs
    when the tests run in parts). Tests turn the Windows hooks off, so
    starting it touches nothing on the PC."""
    listener = gremlin.event_handler.EventListener()
    _PACKAGE_LISTENER[:] = [listener]
    yield listener
    _PACKAGE_LISTENER.clear()
    listener.terminate()


# The package's EventListener (event_listener below), for the item 30 check.
_PACKAGE_LISTENER: list[gremlin.event_handler.EventListener] = []


def _runtime_listener_problem(
    package_listener: gremlin.event_handler.EventListener,
) -> str | None:
    """Why the input-module runtime may no longer hear the devices, or None.

    The runtime connects to the EventListener once, when it is made; a test
    that puts another listener in place leaves it deaf (item 30)."""
    from PySide6 import QtCore

    from gremlin.modules import runtime

    # A test may stand a fake in for either class; its undo has run by now.
    if getattr(runtime.InputModuleRuntime, "instance", None) is None:
        return None
    current = getattr(gremlin.event_handler.EventListener, "instance", None)
    if current is not package_listener:
        return "the EventListener was replaced"
    heard = current.receivers(QtCore.SIGNAL("joystick_event(PyObject)"))
    if heard < 1:
        return "nothing listens to the EventListener's joystick events"
    return None


@pytest.hookimpl(wrapper=True)
def pytest_runtest_teardown(item: pytest.Item) -> Iterator[None]:
    """Names the test that leaves the runtime cut off from the devices
    (item 30). After the test's own fixtures are undone: a test may patch
    the listener while it runs."""
    result = yield
    if _PACKAGE_LISTENER:
        problem = _runtime_listener_problem(_PACKAGE_LISTENER[0])
        assert problem is None, f"{item.nodeid} left it: {problem} (item 30)"
    return result


@pytest.fixture(scope="package")
def unit_test_dir(test_root_dir: pathlib.Path) -> pathlib.Path:
    """Returns the path for the directory with unit test files."""
    return test_root_dir / "unit"


@pytest.fixture
def xml_dir(unit_test_dir: pathlib.Path, tmp_path: pathlib.Path) -> pathlib.Path:
    """A fresh copy of the unit tests' XML folder for each test. A test that
    loads a profile and something later saves it (the profile remembers its
    path) writes into the copy, never into the repo's test data (a full run
    once rewrote xml/profile_auto_mapping_tool.xml)."""
    import shutil

    copy = tmp_path / "xml"
    shutil.copytree(unit_test_dir / "xml", copy)
    return copy


@pytest.fixture(autouse=True)
def _no_held_layouts_left() -> Iterator[None]:
    """A layout held for File › Save (CS1, AD4: a new key is one) must not
    reach the next test, where it would make the profile look unsaved."""
    yield
    from gremlin.modules import store

    if store.has_pending():
        store.discard_pending()
