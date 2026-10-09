# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""test/vjoy_guard.py: tests never reach the real vJoy driver (to-do 44).

Each case is a child pytest run in its own folder (only its own files
collected, no cache), with the guard installed the way test/conftest.py does
it. No case loads the real vJoyInterface.dll: the library the child tests
"load" is a path that doesn't exist, and with GREMLIN_REAL_VJOY=1 the loader
underneath the guard is a fake.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
GUARD = ROOT / "test" / "vjoy_guard.py"

CONFTEST = """
import ctypes, importlib.util, os, sys

sys.path.insert(0, {root!r})
CALLS = []
if os.environ.get("GREMLIN_REAL_VJOY") == "1":
    # The "real" loader under the guard: never the driver, even here.
    def _fake_load(name, *args, **kwargs):
        CALLS.append(str(name))
        return sys.modules["vjoy_guard"].StandInVJoyDll(name)
    ctypes.cdll.LoadLibrary = _fake_load

spec = importlib.util.spec_from_file_location("vjoy_guard", {guard!r})
vjoy_guard = importlib.util.module_from_spec(spec)
sys.modules["vjoy_guard"] = vjoy_guard
spec.loader.exec_module(vjoy_guard)
vjoy_guard.install()


def pytest_configure(config):
    config.pluginmanager.register(vjoy_guard, "vjoy_guard")
"""

TESTS = """
import ctypes, os
import pytest

DLL = os.path.join(os.path.dirname(__file__), "nowhere", "vJoyInterface.dll")


def test_load_directly():
    ctypes.cdll.LoadLibrary(DLL)


def test_load_and_swallow_the_error():
    try:
        ctypes.CDLL(DLL)
    except Exception:
        pass


def test_other_libraries_load():
    ctypes.CDLL("kernel32")


def test_program_import_gets_the_stand_in():
    from vjoy import vjoy_interface

    dll = vjoy_interface.VJoyInterface.vjoy_dll
    if os.environ.get("GREMLIN_REAL_VJOY") != "1":
        assert getattr(dll, "is_stand_in", False)
        assert not vjoy_interface.VJoyInterface.vJoyEnabled()
        assert not vjoy_interface.VJoyInterface.AcquireVJD(1)


def test_zz_real_library_found_loaded():
    import vjoy_guard

    # Left in place: the guard looks after the test's own teardown.
    vjoy_guard.real_vjoy_loaded = lambda: True
"""


def _run(tmp_path: pathlib.Path, real: bool) -> str:
    folder = tmp_path / "child"
    folder.mkdir()
    (folder / "conftest.py").write_text(
        CONFTEST.format(root=str(ROOT), guard=str(GUARD)), encoding="utf-8"
    )
    (folder / "test_child.py").write_text(textwrap.dedent(TESTS), encoding="utf-8")
    (folder / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("PYTHONPATH", "GREMLIN_TEST_HANG_LIMIT", "PYTEST_CURRENT_TEST",
                     "GREMLIN_REAL_VJOY")
    }
    if real:
        env["GREMLIN_REAL_VJOY"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "-rA", "-q",
         "-c", str(folder / "pytest.ini"), "--rootdir", str(folder), str(folder)],
        cwd=folder, env=env, capture_output=True, text=True, timeout=120,
    )
    return result.stdout + result.stderr


def test_a_test_that_loads_the_real_vjoy_fails_naming_itself(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, real=False)
    assert "FAILED test_child.py::test_load_directly" in out, out
    assert "test_child.py::test_load_directly tried to load the real vJoy" in out, out
    # Caught by the program: still fails, at teardown.
    assert "ERROR test_child.py::test_load_and_swallow_the_error" in out, out
    assert "test_child.py::test_load_and_swallow_the_error tried to load" in out, out
    assert "PASSED test_child.py::test_other_libraries_load" in out, out
    # The program's own loading point gets the stand-in.
    assert "PASSED test_child.py::test_program_import_gets_the_stand_in" in out, out
    # Backstop: the real library loaded in the process fails the test.
    assert "ERROR test_child.py::test_zz_real_library_found_loaded" in out, out
    assert "is loaded in this test process" in out, out


def test_with_gremlin_real_vjoy_the_real_vjoy_is_allowed(
    tmp_path: pathlib.Path,
) -> None:
    out = _run(tmp_path, real=True)
    assert "5 passed" in out, out
    assert "vJoy guard" not in out, out
