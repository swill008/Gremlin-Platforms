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

    original = SingletonMetaclass._instances.get(gremlin.config.Configuration)
    yield
    if original is not None:
        SingletonMetaclass._instances[gremlin.config.Configuration] = original


@pytest.fixture(autouse=True)
def _no_settings_notice_left() -> Iterator[None]:
    """A test that reads a damaged settings file must not leave the
    'Settings Reset' notice for a later test that builds the app."""
    yield
    gremlin.config._damaged_copy = ""


@pytest.fixture(scope="package", autouse=True)
def register_config_options() -> None:
    joystick_gremlin.register_config_options()


@pytest.fixture(scope="package", autouse=True)
def joystick_init() -> None:
    # The fake driver (installed above) lists the two fake devices and vJoy 1.
    dill.DILL.init()
    gremlin.device_initialization.joystick_devices_initialization()


@pytest.fixture(scope="package", autouse=True)
def event_listener() -> Iterator[gremlin.event_handler.EventListener]:
    """The shared event listener, started before the first test and stopped
    after the last: its threads belong to the package, not to whichever
    test happens to use it first (that depends on the order, which differs
    when the tests run in parts). Tests turn the Windows hooks off, so
    starting it touches nothing on the PC."""
    listener = gremlin.event_handler.EventListener()
    yield listener
    listener.terminate()


@pytest.fixture(scope="package")
def unit_test_dir(test_root_dir: pathlib.Path) -> pathlib.Path:
    """Returns the path for the directory with unit test files."""
    return test_root_dir / "unit"


@pytest.fixture(scope="package")
def xml_dir(unit_test_dir: pathlib.Path) -> pathlib.Path:
    """Returns the path for the directory with XML files for unit tests."""
    return unit_test_dir / "xml"
