# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Copies a command's output to the agent logs the user watches.

Usage (any shell): <command> 2>&1 | python tools/agent_log.py <AGENT>

Each line goes to the console as usual, to .agent-logs/<AGENT>.log and,
prefixed "[<AGENT>] ", to .agent-logs/all.log. The folder is not in git.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

_FOLDER = Path(__file__).resolve().parent.parent / ".agent-logs"


def main() -> int:
    name = (sys.argv[1] if len(sys.argv) > 1 else "agent").strip() or "agent"
    _FOLDER.mkdir(exist_ok=True)
    stamp = time.strftime("%H:%M:%S")
    with (
        open(_FOLDER / f"{name}.log", "a", encoding="utf-8", errors="replace") as own,
        open(_FOLDER / "all.log", "a", encoding="utf-8", errors="replace") as shared,
    ):
        own.write(f"--- {stamp} ---\n")
        shared.write(f"[{name}] --- {stamp} ---\n")
        own.flush()
        shared.flush()
        # Bytes in, UTF-8 out with "replace": a line that isn't valid UTF-8
        # (a grep of a binary file) must never stop the pipe.
        out = sys.stdout.buffer
        for raw in sys.stdin.buffer:
            line = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")
            out.write(line.encode("utf-8", errors="replace"))
            out.flush()
            own.write(line)
            shared.write(f"[{name}] {line}")
            own.flush()
            shared.flush()
    return 0


if __name__ == "__main__":
    sys.exit(main())
