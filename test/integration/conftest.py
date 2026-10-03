# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

sys.path.append(".")

import json
import logging
import pathlib
import shutil
import tempfile
from collections.abc import Iterator
from typing import Generator

import pytest
from PySide6 import QtCore

import dill
import gremlin.config
import gremlin.device_initialization
import gremlin.error
import gremlin.event_handler
import gremlin.logical_device
import gremlin.profile
import gremlin.ui.backend
import gremlin.util
import joystick_gremlin
from action_plugins import map_to_vjoy
from gremlin.modules.ids import stored_guid_key
from vjoy import vjoy

pytest.register_assert_rewrite("test.integration.app_tester")
from test.integration import app_tester  # noqa: E402

# +-------------------------------------------------------------------------
# | Common fixtures, override in modules as needed.
# +-------------------------------------------------------------------------


@pytest.fixture(scope="module")
def vjoy_di_device(
    vjoy_di_devices_or_skip: list[dill.DeviceSummary],
) -> dill.DeviceSummary:
    """Returns the DirectInput (vJoy) device to be used for this module."""
    assert vjoy_di_devices_or_skip
    for vjoy_device in vjoy_di_devices_or_skip:
        if (
            vjoy_device.axis_count >= 4
            and vjoy_device.button_count >= 4
            and vjoy_device.hat_count >= 2
        ):
            return vjoy_device
    pytest.skip("No vJoy device suitable for testing found")


@pytest.fixture(scope="module")
def vjoy_control_device_id(vjoy_ids_or_skip: list[int]) -> int:
    """Returns the vJoy control device to be used for this test."""
    assert vjoy_ids_or_skip
    for vjoy_id in vjoy_ids_or_skip:
        # TODO: Actually match them in case of multiple vJoy devices.
        return vjoy_id
    pytest.skip("No vJoy control device suitable for testing found")


@pytest.fixture(scope="module")
def edited_profile(
    profile_from_file: gremlin.profile.Profile,
    vjoy_di_device: dill.DeviceSummary,
    vjoy_control_device_id: int,
) -> gremlin.profile.Profile:
    """Replaces input/output devices in the profile."""
    # Replace the (only) input device.
    assert len(profile_from_file.inputs) == 1
    _, input_items = profile_from_file.inputs.popitem()
    profile_from_file.inputs[vjoy_di_device.device_guid.uuid] = input_items
    for input_item in input_items:
        input_item.device_id = vjoy_di_device.device_guid.uuid

    # Replace the output device(s) with the single vJoy control device.
    for action in profile_from_file.library.actions_by_type(map_to_vjoy.MapToVjoyData):
        action.vjoy_device_id = vjoy_control_device_id

    return profile_from_file


def _claim_everything() -> dict:
    return {
        "buttons": list(range(1, 129)),
        "axes": list(range(1, 9)),
        "hats": list(range(1, 5)),
        "keys": [],
        "friendly": {},
    }


@pytest.fixture(scope="module")
def device_modules(
    vjoy_di_device: dill.DeviceSummary, vjoy_control_device_id: int
) -> Iterator[None]:
    """Writes the modules the test vJoy device needs to pass the layer rule.

    The same vJoy device is the test input (read back through DirectInput) and
    the output. The input module is bound to its DirectInput GUID; the output
    module is found by its "vJoy N" name and left unbound, so the gate does not
    treat the device as an output and drop its input events.
    """
    folder = gremlin.util.modules_dir()
    folder.mkdir(parents=True, exist_ok=True)
    files = {
        folder / "integration_test_input.json": {
            "device": "Integration Test Input",
            "direction": "source",
            "boundGuidLocal": stored_guid_key(vjoy_di_device.device_guid),
            "claim": _claim_everything(),
        },
        folder / f"vjoy_{vjoy_control_device_id}.json": {
            "device": f"vJoy {vjoy_control_device_id}",
            "direction": "dest",
            "claim": _claim_everything(),
        },
    }
    for path, doc in files.items():
        path.write_text(json.dumps(doc), encoding="utf-8")
    yield
    for path in files:
        path.unlink(missing_ok=True)


# +-------------------------------------------------------------------------
# | Common fixtures, typically there should be no need to override.
# +-------------------------------------------------------------------------


@pytest.fixture(scope="module")
def profile_path(profile_name: str) -> pathlib.Path:
    """Returns profile path. Requires test modules to define profile_name fixture."""
    return pathlib.Path(__file__).parent / "xml" / profile_name


@pytest.fixture(scope="module")
def profile_from_file(
    profile_path: pathlib.Path,
) -> gremlin.profile.Profile:
    """Returns a Gremlin profile for testing the current module.

    This implementation mutates the profile specified by 'profile_path', with
    inputs and outputs swapped with "real" devices. Alternatively, you can
    override this fixture in test modules to use a generated profile.

    (Where "real" means actual vJoy devices on this system.)
    """
    gremlin.logical_device.LogicalDevice().reset()
    profile = gremlin.profile.Profile()
    profile.from_xml(profile_path)
    return profile


@pytest.fixture(scope="module")
def edited_profile_path(edited_profile: gremlin.profile.Profile) -> Iterator[str]:
    with tempfile.NamedTemporaryFile(delete_on_close=False) as f:
        f.close()
        edited_profile.to_xml(f.name)
        yield f.name


@pytest.fixture(scope="module", params=None)
def vjoy_control_device(vjoy_control_device_id: int) -> Iterator[vjoy.VJoy]:
    vjoy_control = vjoy.VJoyProxy()[vjoy_control_device_id]
    try:
        yield vjoy_control
    finally:
        vjoy_control.invalidate()
        vjoy.VJoyProxy.reset()


def _gremlin_platforms_open() -> bool:
    """True while Gremlin-Platforms runs on this PC (the installed program or
    joystick_gremlin.py from source)."""
    import subprocess

    try:
        found = subprocess.run(
            [
                "powershell", "-NoProfile", "-Command",
                "Get-CimInstance Win32_Process | Where-Object {"
                " $_.Name -eq 'gremlin_platforms.exe' -or "
                "$_.Name -eq 'joystick_gremlin.exe' -or "
                "(($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and "
                "$_.CommandLine -match 'joystick_gremlin\\.py')"
                "} | ForEach-Object { $_.ProcessId }",
            ],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000,
        )
    except Exception:
        return False
    return any(line.strip().isdigit() for line in found.stdout.splitlines())


@pytest.fixture(scope="package", autouse=True)
def _not_while_gremlin_is_open() -> None:
    """These tests write to a real vJoy device: not while Gremlin-Platforms is
    open, where the program (and any game) would see those inputs."""
    if _gremlin_platforms_open():
        pytest.skip(
            "Gremlin-Platforms is open: close it to run the integration tests "
            "(they drive a real vJoy device)."
        )


@pytest.fixture(scope="package")
def vjoy_di_devices_or_skip() -> list[dill.DeviceSummary]:
    """Returns list of DirectInput vJoy device summaries, else skips dependent tests."""
    vjoy_devices = gremlin.device_initialization.vjoy_devices()
    if len(vjoy_devices) == 0:
        pytest.skip("No vJoy input devices found")
    return vjoy_devices


@pytest.fixture(scope="package")
def vjoy_ids_or_skip() -> list[int]:
    """Returns list of vJoy device IDs if any, else skips dependent tests.

    We return IDs instead of the control devices to not acquire vJoy devices a
    test might not actually use.
    """
    # TODO: Share this functionality with input_devices.py
    vjoy_ids = []
    vjoy_proxy = vjoy.VJoyProxy()
    for i in range(1, 17):
        if vjoy.device_exists(i):
            try:
                vjoy_proxy[i]
            except gremlin.error.VJoyError:
                logging.warning("vJoy device %d cannot be acquired", i)
            else:
                vjoy_ids.append(i)
    vjoy_proxy.reset()
    if len(vjoy_ids):
        return vjoy_ids
    pytest.skip("No usable vJoy control devices found")


# Do not use directly, see app_tester fixture instead.
@pytest.fixture(scope="module", autouse=True)
def _activate_gremlin(edited_profile_path: str, device_modules: None) -> Iterator[None]:
    """Activates Gremlin."""
    del device_modules
    assert gremlin.event_handler.EventListener()._running
    backend = gremlin.ui.backend.Backend()
    backend.loadProfile(edited_profile_path)
    backend.activate_gremlin(True)
    backend.minimize()
    yield
    backend.activate_gremlin(False)


@pytest.fixture(scope="package", autouse=True)
def _own_process() -> None:
    """Fails clearly when run in the same process as the unit tests.

    A unit test makes a plain QCoreApplication while being collected, so
    pytest-qt never creates JoystickGremlinApp and the Backend has no engine.
    """
    app = QtCore.QCoreApplication.instance()
    if app is not None and not isinstance(app, joystick_gremlin.JoystickGremlinApp):
        pytest.fail(
            "Run the integration tests in their own pytest process "
            "(pytest test/integration), not together with test/unit.",
            pytrace=False,
        )


@pytest.fixture(scope="package", autouse=True)
def _bundled_user_scripts() -> None:
    """Copies the bundled user scripts into the scripts folder.

    Relative script paths in a profile resolve against the user's scripts
    folder, which is an empty temporary folder in tests.
    """
    source = pathlib.Path(__file__).parents[2] / "user_scripts"
    target = gremlin.util.scripts_dir()
    target.mkdir(parents=True, exist_ok=True)
    for script in source.glob("*.py"):
        shutil.copy(script, target / script.name)


@pytest.fixture(scope="module", autouse=True)
def tear_down() -> Iterator[None]:
    """Performs package-level teardown for integration tests."""
    yield
    vjoy.VJoyProxy.reset()


@pytest.fixture(scope="session", autouse=True)
def _terminate_event_listener_and_monitor(
    request: pytest.FixtureRequest,
) -> None:
    """Terminates session-wide singletons once, after the entire run."""

    # EventListener/Backend set up their DILL callback and process-monitor
    # thread once per session with nothing to restart them; must not
    # terminate them mid-session, only here.
    def _finalize() -> None:
        gremlin.event_handler.EventListener().terminate()
        gremlin.ui.backend.Backend().process_monitor.stop()

    request.addfinalizer(_finalize)


# +-------------------------------------------------------------------------
# | Fixture used for assertions in integration tests.
# +-------------------------------------------------------------------------


@pytest.fixture
def tester(
    qapp: joystick_gremlin.JoystickGremlinApp,
) -> Generator[app_tester.GremlinAppTester]:
    gremlin_app = app_tester.GremlinAppTester(qapp)
    cfg = gremlin.config.Configuration()
    cfg.set("global", "general", "refresh-axis-on-mode-change", False)
    cfg.set("global", "general", "refresh-axis-on-activation", False)
    yield gremlin_app
