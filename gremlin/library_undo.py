# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The Device Library's Undo and Redo (10 S53, D-10-UNDO-REDO).

The steps are this session's Library actions, newest last. Most are Tools ›
History entries: Undo puts back the step's "before" (History's own
Restore), Redo its "after". Copy, Swap, Change vJoy Output and Restore also
change the open profile in memory, which History doesn't hold (S33): their
Undo puts the sticks back from the autosaves the action kept
(library_copy.undo_change) and their Redo runs the action again. A new
action clears Redo. An Undo or Redo is in History as usual but is never a
step itself. Older changes stay in Tools › History.
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from gremlin import clock, history

# A step's name comes from its group's or the Library's own entry.
_NAMING_KINDS = (history.GROUP_KIND, "library")


def started() -> float:
    """When an action starts: what History records from then is its step."""
    return clock.now()


def recorded_since(since: float) -> list[dict]:
    """History's entries recorded from since on, newest first."""
    return [e for e in history.entries() if float(e.get("at") or 0) >= since]


def _clean(text: str) -> str:
    return " ".join(str(text or "").split())


def put_back(ids: list[str], which: str, title: str) -> dict:
    """History's Restore of each entry ("before": newest first, "after":
    oldest first), as one History entry."""
    from gremlin.ui import history_model

    order = list(ids) if which == "before" else list(reversed(ids))
    token = ""
    if len(order) > 1:
        token = history.begin_group(f"Put back from History: {title}")
    notes: list[str] = []
    try:
        for entry_id in order:
            out = history_model.restore(entry_id, which)
            if not out.get("ok"):
                return {"ok": False, "error": str(out.get("message") or "")}
            if out.get("message"):
                notes.append(str(out["message"]))
    finally:
        history.end_group(token)
    return {"ok": True, "notes": notes}


class Steps:
    """One session's Undo and Redo steps (the Device Library model's)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._done: list[dict] = []
        self._undone: list[dict] = []

    def note(
        self,
        since: float,
        title: str = "",
        undo: Callable[[], dict] | None = None,
        redo: Callable[[], dict] | None = None,
    ) -> bool:
        """The action that started at since has ended. What History
        recorded since then is one step; undo/redo (Copy, Swap, Change vJoy
        Output, Restore) put it back and do it again instead of History.
        Nothing recorded and no undo: no step. A step clears Redo."""
        found = recorded_since(since)
        if not found and undo is None:
            return False
        if not title and found:
            named = next(
                (e for e in found if e.get("kind") in _NAMING_KINDS), found[0]
            )
            title = str(named.get("title") or "")
        step = {
            "ids": [str(e.get("id")) for e in found],
            "title": _clean(title),
            "undo": undo,
            "redo": redo,
        }
        with self._lock:
            self._done.append(step)
            self._undone.clear()
        return True

    @staticmethod
    def _text(word: str, steps: list[dict]) -> str:
        if not steps:
            return ""
        title = steps[-1]["title"]
        return f"{word} {title}" if title else word

    def undo_text(self) -> str:
        """Edit › Undo: "Undo <title>" ("" when there is nothing)."""
        with self._lock:
            return self._text("Undo", self._done)

    def redo_text(self) -> str:
        """Edit › Redo: "Redo <title>" ("" when there is nothing)."""
        with self._lock:
            return self._text("Redo", self._undone)

    def _run(self, step: dict, which: str) -> dict:
        own = step["undo"] if which == "before" else step["redo"]
        if own is not None:
            out = own()
            return out if isinstance(out, dict) else {"ok": bool(out)}
        if not step["ids"]:
            return {"ok": False, "error": "That change can't be put back."}
        return put_back(step["ids"], which, step["title"])

    def undo(self) -> dict:
        """The newest step's "before"; it moves to Redo."""
        with self._lock:
            step = self._done[-1] if self._done else None
        if step is None:
            return {"ok": False, "error": "There is nothing to undo."}
        out = self._run(step, "before")
        if out.get("ok"):
            with self._lock:
                if self._done and self._done[-1] is step:
                    self._undone.append(self._done.pop())
        return out

    def redo(self) -> dict:
        """The last undone step's "after"; it moves back to Undo."""
        with self._lock:
            step = self._undone[-1] if self._undone else None
        if step is None:
            return {"ok": False, "error": "There is nothing to redo."}
        out = self._run(step, "after")
        if out.get("ok"):
            with self._lock:
                if self._undone and self._undone[-1] is step:
                    self._done.append(self._undone.pop())
        return out
