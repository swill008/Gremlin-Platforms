# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""tester.log: the tester's own log (D-02-INPUT-TESTER addendum 2026-10-10, item 2).

Lines are "HH:MM:SS.mmm  <text>", kept in a ring for the Logs tab. With a
valid --gremlin-dir they also go to <gremlin-dir>\\tester\\tester.log: 1 MB,
then it becomes tester.log.1 (one older copy) and a new file starts. Plain
mode keeps the lines in memory only.
"""

from __future__ import annotations

import datetime
import os
from collections import deque
from collections.abc import Callable
from pathlib import Path

FILE_NAME = "tester.log"
MAX_BYTES = 1024 * 1024
RING_LINES = 5000
WARN_MARK = "⚠ "


def stamp(now: datetime.datetime) -> str:
    return now.strftime("%H:%M:%S.") + f"{now.microsecond // 1000:03d}"


def log_path(gremlin_dir: str | os.PathLike) -> Path:
    return Path(gremlin_dir) / "tester" / FILE_NAME


class TesterLog:
    """Ring of the last RING_LINES lines plus the optional rotating file."""

    def __init__(
        self,
        path: str | os.PathLike | None = None,
        *,
        max_bytes: int = MAX_BYTES,
        ring: int = RING_LINES,
        now: Callable[[], datetime.datetime] = datetime.datetime.now,
    ) -> None:
        self._path = Path(path) if path is not None else None
        self._max_bytes = max_bytes
        self._now = now
        self._lines: deque[str] = deque(maxlen=ring)
        self.version = 0  # bumped on every line, for followers
        self.listeners: list[Callable[[], None]] = []

    @property
    def path(self) -> Path | None:
        return self._path

    def lines(self) -> list[str]:
        return list(self._lines)

    def add(self, text: str, warn: bool = False) -> str:
        """Adds one line (each embedded newline starts a new line)."""
        when = stamp(self._now())
        prefix = WARN_MARK if warn else ""
        written = []
        for part in str(text).splitlines() or [""]:
            line = f"{when}  {prefix}{part}"
            self._lines.append(line)
            written.append(line)
        self._write("".join(line + "\n" for line in written))
        self.version += 1
        for listener in list(self.listeners):
            listener()
        return written[-1]

    def warn(self, text: str) -> str:
        return self.add(text, warn=True)

    def _write(self, text: str) -> None:
        if self._path is None:
            return
        data = text.encode("utf-8")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            try:
                size = self._path.stat().st_size
            except OSError:
                size = 0
            if size and size + len(data) > self._max_bytes:
                os.replace(self._path, self._path.with_name(self._path.name + ".1"))
            with open(self._path, "ab") as handle:
                handle.write(data)
        except OSError:
            # A file we can't write stays a window-only log.
            self._path = None
