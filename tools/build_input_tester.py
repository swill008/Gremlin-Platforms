# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Builds only the Gremlin Input Tester, for running Gremlin from source.

    python tools/build_input_tester.py

Uses joystick_gremlin.spec with GREMLIN_TESTER_ONLY=1, so the tester is built
exactly as in a release, into dist/Gremlin Input Tester/. Tools › Input
Tester… looks for it there when Gremlin runs from source.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
NAME = "Gremlin Input Tester"


def main() -> int:
    if not (ROOT / "input_tester.py").exists():
        print("input_tester.py is missing; nothing to build.", file=sys.stderr)
        return 1
    env = dict(os.environ, GREMLIN_TESTER_ONLY="1")
    result = subprocess.run(
        [
            sys.executable, "-m", "PyInstaller", "-y", "--clean",
            "--distpath", str(ROOT / "dist"),
            # Own work folder: never mixes with the full build's cache.
            "--workpath", str(ROOT / "build" / "input_tester"),
            str(ROOT / "joystick_gremlin.spec"),
        ],
        cwd=ROOT,
        env=env,
    )
    if result.returncode != 0:
        print(f"PyInstaller failed ({result.returncode}).", file=sys.stderr)
        return result.returncode
    exe = ROOT / "dist" / NAME / f"{NAME}.exe"
    if not exe.exists():
        print(f"Build finished but {exe} is missing.", file=sys.stderr)
        return 1
    print(f"Built {exe} ({exe.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
