# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import sys

import pytest
from PySide6 import QtCore

from gremlin import shared_state
from gremlin.profile import Profile
from gremlin.signal import signal
from gremlin.ui.profile import ModeHierarchyModel


def test_closed_manage_modes_model_ignores_later_profile_changes(
    qapp: QtCore.QCoreApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Closing Manage Modes deletes this model; a later profileChanged (Auto
    # Mapper, profile load) used to fail with "Signal source has been deleted".
    errors: list[str] = []
    monkeypatch.setattr(
        sys, "excepthook", lambda kind, value, trace: errors.append(str(value))
    )
    old = shared_state.current_profile
    shared_state.current_profile = Profile()
    try:
        model = ModeHierarchyModel()
        model.deleteLater()
        QtCore.QCoreApplication.sendPostedEvents(
            None, QtCore.QEvent.Type.DeferredDelete
        )
        signal.profileChanged.emit()
        qapp.processEvents()
        assert errors == []
    finally:
        shared_state.current_profile = old


def test_mode_names_refuse_blank_and_look_alikes(qapp: QtCore.QCoreApplication) -> None:
    old = shared_state.current_profile
    shared_state.current_profile = Profile()
    try:
        model = ModeHierarchyModel()
        model.newMode("Test Mode")
        assert model.nameTaken("", "")
        assert model.nameTaken("   ", "")
        assert model.nameTaken("test mode", "")
        assert model.nameTaken("Test   Mode", "")
        assert not model.nameTaken("Flight", "")
        # Renaming a mode may change the capitals of its own name.
        assert not model.nameTaken("TEST MODE", "Test Mode")
        model.newMode("test mode")
        assert sum(n.casefold() == "test mode" for n in model.modeStringList()) == 1
        model.deleteLater()
    finally:
        shared_state.current_profile = old
