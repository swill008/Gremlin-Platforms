# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The failure message for a smoke program a test ran.

A smoke that ends without its RESULT line (a crash, a hang, a slow CI
runner) only explains itself if the message keeps both ends of its output:
a crash or hang trace starts or ends there. explain() gives the exit code,
the head and tail of each stream and the path of a file holding the full
output (todo 131; seen on 126 where a 2,000-char tail cut the cause off).
It runs only when building a failure message, so passing tests write
nothing.
"""

from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile

HEAD = 2000
TAIL = 4000


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _ends(text: str) -> str:
    if len(text) <= HEAD + TAIL:
        return text
    cut = f"\n[... {len(text) - HEAD - TAIL} chars, see the file ...]\n"
    return text[:HEAD] + cut + text[-TAIL:]


def _name(args: object) -> str:
    """The script a command ran (its first .py argument), else the command."""
    parts = [str(a) for a in args] if isinstance(args, (list, tuple)) else [
        str(args)
    ]
    for part in parts:
        if part.endswith(".py"):
            return pathlib.Path(part).name
    return pathlib.Path(parts[0]).name if parts and parts[0] else "smoke"


def _log_path(name: str) -> pathlib.Path:
    folder = pathlib.Path(tempfile.gettempdir()) / "gremlin-smoke-output"
    folder.mkdir(parents=True, exist_ok=True)
    stem = pathlib.Path(name).stem or "smoke"
    handle, path = tempfile.mkstemp(prefix=f"{stem}-", suffix=".txt", dir=folder)
    os.close(handle)
    return pathlib.Path(path)


def explain(
    done: subprocess.CompletedProcess | subprocess.TimeoutExpired,
    log: pathlib.Path | None = None,
) -> str:
    """Why a smoke run failed: exit code, head and tail of stdout and
    stderr, and the file (log, or a new temp file) with the full output.

    done is the finished run, or the TimeoutExpired raised when it was
    killed."""
    if isinstance(done, subprocess.TimeoutExpired):
        code: object = f"none: killed after {done.timeout} s"
        out, err = _text(done.output), _text(done.stderr)
    else:
        code = done.returncode
        out, err = _text(done.stdout), _text(done.stderr)
    name = _name(done.args)
    try:
        path = log or _log_path(name)
        path.write_text(
            f"exit {code}\n--- stdout ---\n{out}\n--- stderr ---\n{err}",
            encoding="utf-8",
        )
        where = f"full output in {path}"
    except OSError as error:
        where = f"full output not saved ({error})"
    return (
        f"{name} failed; exit {code}; {where}\n--- stdout ---\n{_ends(out)}"
        f"\n--- stderr ---\n{_ends(err)}"
    )
