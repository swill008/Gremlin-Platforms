# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator

sys.path.append(".")


import pytest

import gremlin.error
import gremlin.types
from gremlin.common import SingletonMetaclass
from gremlin.ui.option import (
    BaseMetaConfigOptionWidget,
    MetaConfigOption,
)


class DummyWidget(BaseMetaConfigOptionWidget):
    def _qml_path(self) -> str:
        return "dummy.qml"


@pytest.fixture
def option() -> Iterator[MetaConfigOption]:
    # A fresh registry for the test; the program's own one (holding every
    # option registered at start-up) is put back after, or later tests
    # found their options gone (seen in random order on CI).
    original = SingletonMetaclass._instances.pop(MetaConfigOption, None)
    yield MetaConfigOption()
    SingletonMetaclass._instances.pop(MetaConfigOption, None)
    if original is not None:
        SingletonMetaclass._instances[MetaConfigOption] = original


def test_basic(option: MetaConfigOption) -> None:
    assert option.count() == 0

    option.register("some", "test", "option 1", "description 1", DummyWidget)
    option.register("some", "test", "option 2", "description 2", DummyWidget)

    assert option.count() == 2

    assert len(option.sections()) == 1
    assert len(option.groups("some")) == 1
    assert len(option.entries("some", "test")) == 2
    assert option.description("some", "test", "option 1") == "description 1"
    assert option.description("some", "test", "option 2") == "description 2"
    assert option.qml_widget("some", "test", "option 1") == DummyWidget
    assert option.qml_widget("some", "test", "option 2") == DummyWidget


def test_empty_entries(option: MetaConfigOption) -> None:
    assert option.count() == 0

    option.register("some", "test", "option 1", "description 1", DummyWidget)

    assert option.count() == 1

    assert len(option.sections()) == 1
    assert len(option.groups("some")) == 1
    assert len(option.entries("some", "test")) == 1
    assert option.entries("no", "such") == []
    assert option.entries("some", "no such") == []


def test_register_duplicate_logs_warning(
    option: MetaConfigOption, caplog: pytest.LogCaptureFixture
) -> None:
    option.register("dup", "grp", "name", "desc", DummyWidget)
    option.register("dup", "grp", "name", "desc", DummyWidget)

    assert caplog.record_tuples == [
        ("system", logging.WARNING, "Option dup.grp.name already registered.")
    ]


def test_retrieve_nonexistent_raises(option: MetaConfigOption) -> None:
    with pytest.raises(gremlin.error.GremlinError):
        option.qml_widget("no", "such", "option")

    option.register("sec", "grp", "name", "desc", DummyWidget)
    with pytest.raises(gremlin.error.GremlinError):
        option.description("sec", "grp", "other")
