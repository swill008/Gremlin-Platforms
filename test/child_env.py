# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The environment for a Python program a test starts.

test/conftest.py puts test/hang_trace on PYTHONPATH; its sitecustomize.py
gives every child the guards (real dill refused, stand-in vJoy, stack dump
when it stalls). A child env that sets PYTHONPATH to just the repository
drops them, so tests build it here: extra folders go in front, the rest is
kept. test/unit/test_child_env_keeps_guards.py checks every test does.
"""

from __future__ import annotations

import os
import pathlib

HANG_TRACE = str(pathlib.Path(__file__).resolve().parent / "hang_trace")


def python_path(*folders: str | os.PathLike[str]) -> str:
    """PYTHONPATH with folders in front of this process's own, which keeps
    test/hang_trace (added if missing)."""
    parts = [str(f) for f in folders]
    parts += [p for p in os.environ.get("PYTHONPATH", "").split(os.pathsep) if p]
    if HANG_TRACE not in parts:
        parts.append(HANG_TRACE)
    return os.pathsep.join(parts)


def child_env(*folders: str | os.PathLike[str], **values: str) -> dict[str, str]:
    """os.environ plus values, with folders added to PYTHONPATH."""
    env = dict(os.environ)
    env.update(values)
    env["PYTHONPATH"] = python_path(*folders)
    return env
