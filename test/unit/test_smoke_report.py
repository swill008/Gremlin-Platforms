# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""A smoke that dies mid-way explains itself (todo 131): the failure
message from smoke_report.explain names the exit code, keeps the head and
tail of each stream, and the full output is saved to a file."""

from __future__ import annotations

import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import smoke_report  # pyright: ignore[reportMissingImports]  (test/)

_FAKE = """
import os, sys
print("HEAD-OUT first line", flush=True)
for n in range(3000):
    print(f"filler line {n:05d} " + "x" * 20, flush=True)
print("TAIL-OUT last line", flush=True)
sys.stderr.write("HEAD-ERR\\n" + "e" * 9000 + "\\nTAIL-ERR died in settle()\\n")
sys.stderr.flush()
os._exit(3)
print("RESULT {}")
"""


def test_a_smoke_that_dies_midway_explains_itself(tmp_path: pathlib.Path) -> None:
    fake = tmp_path / "dies_smoke.py"
    fake.write_text(_FAKE, encoding="utf-8")
    done = proc_tree.run([sys.executable, str(fake)], text=True, timeout=60)
    assert "RESULT " not in done.stdout

    log = tmp_path / "out.txt"
    message = smoke_report.explain(done, log)

    assert "dies_smoke.py failed; exit 3" in message
    for mark in ("HEAD-OUT", "TAIL-OUT", "HEAD-ERR", "TAIL-ERR died in settle()"):
        assert mark in message
    assert "filler line 01500" not in message  # the middle is cut ...
    assert f"full output in {log}" in message
    full = log.read_text(encoding="utf-8")
    assert full.startswith("exit 3\n")
    assert "filler line 01500" in full  # ... but kept in the file
    assert len(message) < len(full)

    # Without a path it saves to a new temp file and names it.
    named = smoke_report.explain(done)
    path = pathlib.Path(named.split("full output in ", 1)[1].split("\n", 1)[0])
    try:
        assert path.read_text(encoding="utf-8") == full
    finally:
        path.unlink()
