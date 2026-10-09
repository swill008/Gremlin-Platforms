# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Keeps tests away from the real vJoy driver (to-do 44).

vjoy/vjoy_interface.py loads vJoyInterface.dll when it is imported. Under
install() that load gets the stand-in vJoy below instead: a vJoy that is not
installed, as on CI (no devices, nothing can be acquired or set). Any other
attempt to load vJoyInterface.dll (ctypes.CDLL, WinDLL, a second loader)
raises VJoyGuardError naming the test, and the test fails at teardown even
when the program caught the error. Backstop: after each test, and at the
start of the session, the real library must not be loaded in the process.

The real vJoy only with GREMLIN_REAL_VJOY=1 (python test/run_tests.py
--real-vjoy).

Installed by test/conftest.py (before anything imports vjoy) and, for the
programs the tests start, by test/hang_trace/sitecustomize.py. Imports only
the standard library: no pytest, no gremlin.
"""

from __future__ import annotations

import ctypes
import os
import sys
from collections.abc import Callable
from typing import Any

REAL_VJOY_ENV = "GREMLIN_REAL_VJOY"
DLL_NAME = "vjoyinterface.dll"
# The program's one loading point; its load gets the stand-in.
LOADER_MODULE = "vjoy.vjoy_interface"


class VJoyGuardError(RuntimeError):
    """A test tried to load the real vJoy library. Not an OSError, so the
    program's "dll failed to load" handling doesn't swallow it."""


def real_vjoy_allowed() -> bool:
    return os.environ.get(REAL_VJOY_ENV) == "1"


def current_test() -> str:
    """The running test (pytest sets PYTEST_CURRENT_TEST in the test process,
    and the programs a test starts inherit it)."""
    name = os.environ.get("PYTEST_CURRENT_TEST", "")
    if name.endswith((" (setup)", " (call)", " (teardown)")):
        name = name.rsplit(" ", 1)[0]
    return name or "the test run (no test running yet)"


def _is_vjoy_dll(name: object) -> bool:
    if name is None:
        return False
    try:
        return os.path.basename(os.fspath(name)).lower() == DLL_NAME  # type: ignore[arg-type]
    except TypeError:
        return False


def _message(path: object, where: str) -> str:
    return (
        f"{current_test()} tried to load the real vJoy library ({path}) "
        f"from {where}. Tests use the stand-in vJoy; the real one only with "
        f"{REAL_VJOY_ENV}=1 (python test/run_tests.py --real-vjoy)."
    )


# | Stand-in vJoyInterface.dll


class _Fn:
    """One stand-in DLL function: settable argtypes/restype like a ctypes
    function, and not a descriptor, so it is the same on the class and as
    an attribute."""

    def __init__(self, name: str, result: Callable[..., Any]) -> None:
        self.__name__ = name
        self.argtypes: list[Any] | None = None
        self.restype: Any = None
        self._result = result
        self.calls = 0

    def __call__(self, *args: Any) -> Any:  # noqa: ANN401
        self.calls += 1
        return self._result(*args)


# vJoy not installed: what the real library answers without the driver.
_VJD_STAT_MISS = 3
_ANSWERS: dict[str, Callable[..., Any]] = {
    "GetvJoyVersion": lambda: 0,
    "vJoyEnabled": lambda: False,
    "GetvJoyProductString": lambda: None,
    "GetvJoyManufacturerString": lambda: None,
    "GetvJoySerialNumberString": lambda: None,
    "GetVJDButtonNumber": lambda vjoy_id: 0,
    "GetVJDDiscPovNumber": lambda vjoy_id: 0,
    "GetVJDContPovNumber": lambda vjoy_id: 0,
    "GetVJDAxisExist": lambda vjoy_id, axis: 0,
    "GetVJDAxisMax": lambda vjoy_id, axis, out: False,
    "GetVJDAxisMin": lambda vjoy_id, axis, out: False,
    "GetOwnerPid": lambda vjoy_id: 0,
    "AcquireVJD": lambda vjoy_id: False,
    "RelinquishVJD": lambda vjoy_id: None,
    "UpdateVJD": lambda vjoy_id, data: False,
    "GetVJDStatus": lambda vjoy_id: _VJD_STAT_MISS,
    "ResetVJD": lambda vjoy_id: False,
    "ResetAll": lambda: None,
    "ResetButtons": lambda vjoy_id: False,
    "ResetPovs": lambda vjoy_id: False,
    "SetAxis": lambda value, vjoy_id, axis: False,
    "SetBtn": lambda value, vjoy_id, button: False,
    "SetDiscPov": lambda value, vjoy_id, hat: False,
    "SetContPov": lambda value, vjoy_id, hat: False,
}


class StandInVJoyDll:
    """Stands in for vJoyInterface.dll: every function vjoy/ uses, no driver."""

    is_stand_in = True

    def __init__(self, path: object = None) -> None:
        self._name = str(path)
        for name, answer in _ANSWERS.items():
            setattr(self, name, _Fn(name, answer))

    def __repr__(self) -> str:
        return f"<stand-in vJoy for {self._name}>"


# | Guard

_installed = False
_blocked: list[str] = []  # load attempts stopped since the last check
_reported = False
_original_load: Callable[..., Any] | None = None
_original_cdll_init: Callable[..., Any] | None = None


def _caller(depth: int) -> tuple[str, str]:
    """(module name, "file:line") of the frame `depth` levels up."""
    frame = sys._getframe(depth + 1)
    return (
        str(frame.f_globals.get("__name__", "")),
        f"{frame.f_code.co_filename}:{frame.f_lineno}",
    )


def _block(path: object, where: str) -> VJoyGuardError:
    message = _message(path, where)
    _blocked.append(message)
    return VJoyGuardError(message)


def _guarded_load(name: object, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
    """ctypes.cdll.LoadLibrary under the guard."""
    assert _original_load is not None
    if _is_vjoy_dll(name) and not real_vjoy_allowed():
        module, where = _caller(1)
        if module == LOADER_MODULE:
            return StandInVJoyDll(name)
        raise _block(name, where)
    return _original_load(name, *args, **kwargs)


def _guarded_cdll_init(
    self: ctypes.CDLL, name: object, *args: Any, **kwargs: Any  # noqa: ANN401
) -> None:
    """ctypes.CDLL (and WinDLL, OleDLL, PyDLL) under the guard: every other
    way to load the library."""
    assert _original_cdll_init is not None
    if _is_vjoy_dll(name) and not real_vjoy_allowed():
        raise _block(name, _caller(1)[1])
    _original_cdll_init(self, name, *args, **kwargs)


def install() -> None:
    """Puts the guard in place in this process (once; does nothing more when
    called again). With GREMLIN_REAL_VJOY=1 every load goes through."""
    global _installed, _original_load, _original_cdll_init
    if _installed:
        return
    _installed = True
    _original_load = ctypes.cdll.LoadLibrary
    _original_cdll_init = ctypes.CDLL.__init__
    ctypes.cdll.LoadLibrary = _guarded_load  # type: ignore[method-assign]
    ctypes.CDLL.__init__ = _guarded_cdll_init  # type: ignore[method-assign]


def real_vjoy_loaded() -> bool:
    """True when the real vJoyInterface.dll is loaded in this process."""
    if sys.platform != "win32":
        return False
    get_handle = ctypes.windll.kernel32.GetModuleHandleW
    get_handle.argtypes = [ctypes.c_wchar_p]
    get_handle.restype = ctypes.c_void_p
    return bool(get_handle("vJoyInterface.dll"))


def problems() -> list[str]:
    """What touched the real vJoy since the last call (empty when nothing or
    when GREMLIN_REAL_VJOY=1). Each problem is reported once."""
    global _reported
    found = list(_blocked)
    _blocked.clear()
    if real_vjoy_allowed():
        return []
    if not _reported and real_vjoy_loaded():
        _reported = True
        found.append(
            f"the real vJoy library (vJoyInterface.dll) is loaded in this test "
            f"process, first seen after {current_test()}. Tests use the stand-in "
            f"vJoy; the real one only with {REAL_VJOY_ENV}=1."
        )
    return found


# | pytest hooks (registered by test/conftest.py: pluginmanager.register(vjoy_guard)).
# | Marked by hand: this module doesn't import pytest (programs load it too).

_LAST = {
    "wrapper": False, "hookwrapper": False, "optionalhook": False,
    "tryfirst": False, "trylast": True, "specname": None,
}


def pytest_sessionstart(session: Any) -> None:  # noqa: ANN401
    found = problems()
    if found:
        import pytest

        pytest.exit("vJoy guard: " + " ".join(found), returncode=4)


def pytest_runtest_teardown(item: Any, nextitem: Any) -> None:  # noqa: ANN401
    """After the test's own teardown: fails it when it touched the real vJoy,
    and stops the run when the real library got loaded."""
    del nextitem
    found = problems()
    if not found:
        return
    if real_vjoy_loaded() and not real_vjoy_allowed():
        item.session.shouldstop = "vJoy guard: the real vJoy library got loaded"
    import pytest

    pytest.fail(f"vJoy guard ({item.nodeid}): " + " ".join(found), pytrace=False)


pytest_runtest_teardown.pytest_impl = _LAST  # type: ignore[attr-defined]
