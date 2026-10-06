# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every gremlin module loads on its own, in a fresh process.

A circular import only shows when a module of the loop is loaded first, so
it can hide behind the order other code happens to import things in: 1.0.18
did not start for that reason. Loading each module alone finds every loop.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys
from collections import deque

_ROOT = pathlib.Path(__file__).parents[2]


def _modules() -> list[str]:
    names = []
    for path in sorted((_ROOT / "gremlin").rglob("*.py")):
        parts = list(path.relative_to(_ROOT).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        names.append(".".join(parts))
    return names


def test_each_gremlin_module_loads_on_its_own(tmp_path: pathlib.Path) -> None:
    env = dict(os.environ)
    env["USERPROFILE"] = str(tmp_path)
    env["QT_QPA_PLATFORM"] = "offscreen"

    def start(name: str) -> tuple[str, subprocess.Popen]:
        return name, subprocess.Popen(
            [sys.executable, "-c", f"import {name}"],
            cwd=_ROOT,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        )

    def finish(name: str, proc: subprocess.Popen) -> str | None:
        # Waited for here, on the main thread: the test's hang watch counts
        # waiting on a program as progress (waiting on a thread pool looked
        # like a stall on CI's slower 4-core machine).
        try:
            _, err = proc.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            return f"{name}: did not load within 120 s"
        if proc.returncode == 0:
            return None
        lines = [line for line in err.splitlines() if line.strip()]
        return f"{name}: {' / '.join(lines[-2:])}"

    at_once = max(2, (os.cpu_count() or 4) // 2)
    running: deque[tuple[str, subprocess.Popen]] = deque()
    failures = []
    for name in _modules():
        if len(running) >= at_once:
            failures.append(finish(*running.popleft()))
        running.append(start(name))
    while running:
        failures.append(finish(*running.popleft()))
    failures = [f for f in failures if f]
    assert not failures, "\n".join(failures)
