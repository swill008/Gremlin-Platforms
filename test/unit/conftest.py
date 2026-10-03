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
def terminate_event_listener(request: pytest.FixtureRequest) -> None:
    request.addfinalizer(lambda: gremlin.event_handler.EventListener().terminate())


@pytest.fixture(scope="package")
def unit_test_dir(test_root_dir: pathlib.Path) -> pathlib.Path:
    """Returns the path for the directory with unit test files."""
    return test_root_dir / "unit"


@pytest.fixture(scope="package")
def xml_dir(unit_test_dir: pathlib.Path) -> pathlib.Path:
    """Returns the path for the directory with XML files for unit tests."""
    return unit_test_dir / "xml"
