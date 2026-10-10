# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""History keeps the order of what is queued when flush() (at quit, close())
runs beside the writer thread (AUD-THREADS-06, GL-187): the writer never
holds an item it has taken while flush() writes later ones first."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from gremlin import history


@pytest.fixture
def store(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    folder = tmp_path / "history"
    monkeypatch.setattr(history, "folder", lambda: folder)
    monkeypatch.setattr(history, "_pruned", True)
    yield folder
    history.flush()


def _wait(done: object, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while not done() and time.monotonic() < deadline:  # type: ignore[operator]
        time.sleep(0.01)


def test_flush_beside_the_writer_keeps_the_order(store: Path) -> None:
    order: list[str] = []
    # flush() is mid-item (holding the handle lock) when two more are queued
    # and the writer wakes for them.
    history._handle_lock.acquire()
    try:
        history.later(lambda: order.append("first"))
        history.later(lambda: order.append("second"))
        # Give the writer time to wake (it used to take "first" here and wait).
        _wait(lambda: history._queue.qsize() < 2, 0.5)
        history.flush()
    finally:
        history._handle_lock.release()
    _wait(lambda: history._writer is None, 5)
    assert order == ["first", "second"]
