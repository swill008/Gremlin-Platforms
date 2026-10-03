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
from concurrent.futures import ThreadPoolExecutor

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

    def load(name: str) -> str | None:
        result = subprocess.run(
            [sys.executable, "-c", f"import {name}"],
            cwd=_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode == 0:
            return None
        lines = [line for line in result.stderr.splitlines() if line.strip()]
        return f"{name}: {' / '.join(lines[-2:])}"

    with ThreadPoolExecutor(max_workers=max(2, (os.cpu_count() or 4) // 2)) as pool:
        failures = [f for f in pool.map(load, _modules()) if f]
    assert not failures, "\n".join(failures)
