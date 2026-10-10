# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Logs tab's sources (D-02-INPUT-TESTER addendum 2026-10-10, item 1).

Read only: the tester log, Gremlin's trace.log and system.log from
<gremlin-dir>\\logs, and dill_debug.log from the tester's own folder (the
working folder when it isn't there). Files over TAIL_BYTES show their last
TAIL_BYTES; Follow polls by modification time and size.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from gremlin.input_tester import log as tester_log

TAIL_BYTES = 512 * 1024
FOLLOW_S = 0.5

TESTER, TRACE, SYSTEM, DILL = "tester", "trace", "system", "dill"
LABELS = {
    TESTER: "Tester log (tester.log)",
    TRACE: "Gremlin trace.log",
    SYSTEM: "Gremlin system.log",
    DILL: "DirectInput reader (dill_debug.log)",
}
DILL_FILE = "dill_debug.log"

_TIME = re.compile(
    r"^(?:\d{4}-\d{2}-\d{2}[ T])?(\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?)\s+(.*)$"
)
_WARN = re.compile(
    r"\b(WARNING|WARN|ERROR|CRITICAL|Traceback)\b|⚠|access denied|"
    r"\berror\b|\bfailed\b|\binvalid\b",
    re.IGNORECASE,
)


@dataclass
class LogSource:
    id: str
    label: str
    path: Path | None  # None: the tester log kept in memory (plain mode)

    @property
    def exists(self) -> bool:
        return self.path is None or self.path.is_file()


def sources(
    gremlin_dir: str | os.PathLike | None,
    exe_dir: str | os.PathLike,
    cwd: str | os.PathLike | None = None,
) -> list[LogSource]:
    """The Log picker's choices, in order. Plain mode: tester + dill only."""
    out = [
        LogSource(
            TESTER,
            LABELS[TESTER],
            tester_log.log_path(gremlin_dir) if gremlin_dir else None,
        )
    ]
    if gremlin_dir:
        logs = Path(gremlin_dir) / "logs"
        out.append(LogSource(TRACE, LABELS[TRACE], logs / "trace.log"))
        out.append(LogSource(SYSTEM, LABELS[SYSTEM], logs / "system.log"))
    dill_path = Path(exe_dir) / DILL_FILE
    if not dill_path.is_file() and cwd is not None:
        other = Path(cwd) / DILL_FILE
        if other.is_file():
            dill_path = other
    out.append(LogSource(DILL, LABELS[DILL], dill_path))
    return out


@dataclass
class Tail:
    lines: list[str]
    size: int  # whole file, bytes
    truncated: bool  # only the last TAIL_BYTES were read
    exists: bool


def read_tail(path: str | os.PathLike, limit: int = TAIL_BYTES) -> Tail:
    """The file's last `limit` bytes as lines (a cut first line is dropped)."""
    try:
        with open(path, "rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - limit)
            handle.seek(max(0, start - 1))
            before = handle.read(1) if start > 0 else b"\n"
            data = handle.read(size - start)
    except OSError:
        return Tail([], 0, False, False)
    lines = data.decode("utf-8", errors="replace").splitlines()
    if before != b"\n" and lines:
        lines = lines[1:]  # part of a line was cut
    return Tail(lines, size, start > 0, True)


def file_state(path: str | os.PathLike | None) -> tuple[float, int] | None:
    """(mtime, size) for Follow, None when missing."""
    if path is None:
        return None
    try:
        stat = os.stat(path)
    except OSError:
        return None
    return (stat.st_mtime, stat.st_size)


class Follower:
    """Says when a file changed since the last check (mtime or size)."""

    def __init__(self, path: str | os.PathLike | None) -> None:
        self.path = path
        self._state = file_state(path)

    def changed(self) -> bool:
        state = file_state(self.path)
        if state != self._state:
            self._state = state
            return True
        return False


def split_line(line: str) -> tuple[str, str]:
    """(time "HH:MM:SS.mmm" or "", rest)."""
    match = _TIME.match(line)
    if match is None:
        return "", line
    return match.group(1), match.group(2)


def is_warning(line: str) -> bool:
    return bool(_WARN.search(line))


def find(lines: list[str], text: str) -> list[int]:
    """Indexes of the lines containing `text` (case-insensitive)."""
    if not text:
        return []
    wanted = text.casefold()
    return [i for i, line in enumerate(lines) if wanted in line.casefold()]


def size_text(size: int) -> str:
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    if size >= 1024:
        return f"{round(size / 1024)} KB"
    return f"{size} bytes"
