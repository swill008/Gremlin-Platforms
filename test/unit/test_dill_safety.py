# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The real dill.dll never loads in tests.

`import dill` loads nothing; the library loads on first use. Programs the
tests start get a guard (test/hang_trace/sitecustomize.py) that refuses the
real load, so a child that forgets test/fake_hardware fails loudly instead
of reading the PC's own devices.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from typing import Any

REPO = pathlib.Path(__file__).resolve().parents[2]

# Records every ctypes load; imports dill the way the program does.
_IMPORT_ONLY = r"""
import ctypes, os, sys
loads = []
sys.addaudithook(
    lambda event, args: loads.append(str(args[0])) if event == "ctypes.dlopen" else None
)
import dill
hits = [p for p in loads if os.path.basename(p).lower() == "dill.dll"]
print("LOADS", len(hits), dill._di_listener_dll is None)
"""

_CHILD = r"""
import sys
from typing import Any
if sys.argv[1] == "fake":
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", "test/fake_hardware.py"
    )
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake_hardware.install()
import gremlin.ui.module_model  # noqa: F401  (reaches dill through the modules)
import dill
print("COUNT", dill.DILL.get_device_count())
"""


def _child(code: str, *args: str, guarded: bool) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    hang_trace = str(REPO / "test" / "hang_trace")
    paths = [str(REPO)]
    if guarded:
        paths.insert(0, hang_trace)
        env.setdefault("GREMLIN_TEST_HANG_LIMIT", "50")
    else:
        env.pop("GREMLIN_TEST_HANG_LIMIT", None)
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["QT_QPA_PLATFORM"] = "offscreen"
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.run(
        [sys.executable, "-c", code, *args],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_importing_dill_loads_no_library() -> None:
    done = _child(_IMPORT_ONLY, guarded=False)
    assert done.returncode == 0, done.stderr
    assert "LOADS 0 True" in done.stdout, done.stdout + done.stderr


def test_a_child_without_the_fake_hits_the_guard() -> None:
    done = _child(_CHILD, "real", guarded=True)
    assert done.returncode != 0, done.stdout
    assert "tests must use test/fake_hardware" in done.stderr, done.stderr
    assert "COUNT" not in done.stdout


def test_a_child_with_the_fake_lists_the_fake_devices() -> None:
    done = _child(_CHILD, "fake", guarded=True)
    assert done.returncode == 0, done.stderr
    assert "COUNT 2" in done.stdout, done.stdout + done.stderr


def test_this_process_uses_the_fake_and_never_loaded_the_real_library() -> None:
    import dill
    from test import fake_hardware  # pyright: ignore[reportAttributeAccessIssue]

    fake: Any = dill.DILL._dll
    assert isinstance(fake, fake_hardware.FakeDill)
    assert dill._di_listener_dll is None
    assert dill.DILL.get_device_count() == len(fake.devices)
