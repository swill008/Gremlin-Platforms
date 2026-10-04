# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Runs the test folders one after another, so you can watch it.

    python test/run_tests.py [folder ...]      (default: all three)

Every line shows the time since the start and how many tests of the folder
are done. When a test prints nothing for a while it says which test is
still running. A folder that runs longer than LIMIT_S is stopped. The
same output goes to a log file (its path is shown at the start and end).

The folders run in separate pytest runs: test/unit can't share a process
with the two that need the Gremlin app (test/conftest.py refuses that).
"""

from __future__ import annotations

import os
import pathlib
import queue
import re
import subprocess
import sys
import tempfile
import threading
import time

FOLDERS = ["test/unit", "test/action_interaction", "test/integration"]
LIMIT_S = 600
QUIET_S = 15  # say which test is running after this long without output

_ROOT = pathlib.Path(__file__).parents[1]
_COUNT = re.compile(r"\[\s*(\d+)/(\d+)\]\s*$")
_SUMMARY = re.compile(r"=+ (.* in [\d.]+s.*) =+$")


def _clock(start: float) -> str:
    seconds = int(time.monotonic() - start)
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _end(process: subprocess.Popen) -> None:
    """Ends pytest and anything it started."""
    subprocess.run(
        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
        capture_output=True, check=False,
    )


def run_folder(folder: str, start: float, log) -> tuple[str, str, float]:  # noqa: ANN001
    def say(text: str) -> None:
        line = f"[{_clock(start)}] {text}"
        print(line, flush=True)
        log.write(line + "\n")
        log.flush()

    say(f"=== {folder}: starting (stopped after {LIMIT_S // 60} min)")
    began = time.monotonic()
    process = subprocess.Popen(
        [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider",
         "-o", "console_output_style=count", folder],
        cwd=_ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace",
        env=dict(os.environ, PYTHONUNBUFFERED="1"),
    )
    lines: queue.Queue[str | None] = queue.Queue()

    def read() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            lines.put(line.rstrip("\n"))
        lines.put(None)

    threading.Thread(target=read, daemon=True).start()
    done = total = 0
    current = ""
    summary = "no summary (see the log)"
    last_output = time.monotonic()
    last_note = 0.0
    while True:
        try:
            line = lines.get(timeout=1.0)
        except queue.Empty:
            now = time.monotonic()
            if now - began > LIMIT_S:
                say(f"!!! {folder}: over {LIMIT_S // 60} min, stopping it")
                _end(process)
                summary = f"STOPPED after {LIMIT_S // 60} min"
                break
            if now - last_output > QUIET_S and now - last_note > QUIET_S:
                last_note = now
                say(f"... {done}/{total or '?'} done; still in "
                    f"{current or 'start-up'} ({int(now - last_output)} s)")
            continue
        if line is None:
            break
        last_output = time.monotonic()
        if m := _COUNT.search(line):
            done, total = int(m.group(1)), int(m.group(2))
        if "::" in line and not line.startswith(" "):
            current = line.split(" ")[0]
        if m := _SUMMARY.search(line):
            summary = m.group(1)
        say(f"{done}/{total or '?'}  {line}")
    process.wait()
    took = time.monotonic() - began
    say(f"=== {folder}: {summary} ({took:.0f} s)")
    return folder, summary, took


def main() -> int:
    folders = sys.argv[1:] or FOLDERS
    log_path = pathlib.Path(tempfile.gettempdir()) / "gremlin-test-run.log"
    start = time.monotonic()
    results = []
    with log_path.open("w", encoding="utf-8") as log:
        print(f"Log: {log_path}", flush=True)
        for folder in folders:
            results.append(run_folder(folder, start, log))
        lines = ["", f"=== All done in {_clock(start)}"]
        lines += [f"  {f}: {s} ({t:.0f} s)" for f, s, t in results]
        lines.append(f"Log: {log_path}")
        for line in lines:
            print(line, flush=True)
            log.write(line + "\n")
    ok = all(" failed" not in s and "STOPPED" not in s and " error" not in s
             for _, s, _ in results)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
