"""AUD-LINT-01: the second-copy check reads who holds gremlin.lock. It
called QLockFile.lockInfo, which PySide6 doesn't have (getLockInfo), so the
error was swallowed and the owner was never found."""

import os
import pathlib

import pytest
from PySide6 import QtCore

import gremlin.util
import joystick_gremlin


def test_the_lock_owner_is_found(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(gremlin.util, "data_folder", lambda: str(tmp_path))
    held = QtCore.QLockFile(os.path.join(str(tmp_path), "gremlin.lock"))
    assert held.tryLock(0)
    try:
        assert joystick_gremlin._lock_owner_pid() == os.getpid()
    finally:
        held.unlock()
