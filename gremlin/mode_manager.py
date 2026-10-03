# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6 import QtCore

from gremlin import shared_state
from gremlin.common import SingletonDecorator
from gremlin.config import Configuration
from gremlin.types import PropertyType

if TYPE_CHECKING:
    from gremlin.profile import Profile


class Mode:
    """Simple containiner holding a mode's name and its identifier."""

    def __init__(
        self, name: str, previous: str | None, is_temporary: bool = False
    ) -> None:
        """Creates a new Mode instance.

        Args:
            name: name of the mode
            previous: name of the previous mode
            is_temporary: True if the mode is temporary, False otherwise
        """
        self._name = name
        self._previous = previous
        self._is_temporary = is_temporary

    @property
    def name(self) -> str:
        return self._name

    @property
    def previous(self) -> str | None:
        return self._previous

    @previous.setter
    def previous(self, value: str | None) -> None:
        self._previous = value

    @property
    def is_temporary(self) -> bool:
        return self._is_temporary

    @is_temporary.setter
    def is_temporary(self, value: bool) -> None:
        self._is_temporary = value

    def __eq__(self, other: Mode) -> bool:
        return (
            self.name == other.name
            and self.previous == other.previous
            and self.is_temporary == other.is_temporary
        )


class ModeSequence:
    def __init__(self, modes: list[str]) -> None:
        """Creates a new ModeSequence instance.

        Args:
            modes: List of mode names making up the sequence.
        """
        self.modes = modes
        self._current_index = -1

    def next(self) -> str:
        """Returns the next mode in the sequence.

        Returns:
            Next mode in the sequence, wrapping around at the end.
        """
        # next_index = self._current_index % len(self.modes)
        self._current_index = (self._current_index + 1) % len(self.modes)
        return self.modes[self._current_index]


# The last mode per profile, changed while a profile runs: kept here and
# saved when it stops or the program quits (and at most hourly), not on every
# mode switch during play.
_pending_last: dict[str, str] = {}
_LAST_KEY = ("global", "internal", "last-mode-per-profile")


def _stored_last_modes() -> dict[str, str]:
    stored = dict(Configuration().value(*_LAST_KEY))
    stored.update(_pending_last)
    return stored


def flush_last_modes() -> None:
    """Save the last modes kept in memory (profile stop, quit)."""
    if not _pending_last:
        return
    stored = _stored_last_modes()
    _pending_last.clear()
    Configuration().set(*_LAST_KEY, stored)


def _profile_running() -> bool:
    from gremlin.event_handler import EventListener

    listener = EventListener.instance
    return bool(listener is not None and listener.gremlin_active)


def resolve_start_mode(active_profile: Profile) -> str:
    """Returns the mode a profile is put in when it is loaded.

    A named startup mode is used as itself. Last Active uses the mode this
    profile was running the last time it was on, when that mode still exists.
    Use Heuristic uses the alphabetically first mode that has no parent.
    """
    mode_names = active_profile.modes.mode_names()
    startup_mode = active_profile.settings.startup_mode
    if startup_mode in mode_names:
        return startup_mode
    if startup_mode == "Last Active" and active_profile.fpath is not None:
        last_mode = _stored_last_modes().get(str(active_profile.fpath))
        if last_mode in mode_names:
            return last_mode
    return active_profile.modes.first_mode


@SingletonDecorator
class ModeManager(QtCore.QObject):
    """Manages the mode change history."""

    mode_changed = QtCore.Signal(str)

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)

        self._mode_stack = [Mode("Invalid", None)]
        self._config = Configuration()

    @property
    def current(self) -> Mode:
        return self._mode_stack[-1]

    def reset(self) -> None:
        self._mode_stack = [
            Mode(resolve_start_mode(shared_state.current_profile), None)
        ]

    def _exists(self, mode: Mode) -> bool:
        return mode in self._mode_stack

    def _store_last_mode(self) -> None:
        profile = shared_state.current_profile
        if profile is None or profile.fpath is None:
            return
        last_mode = next(
            (mode for mode in reversed(self._mode_stack) if not mode.is_temporary),
            None,
        )
        if last_mode is None:
            return
        key = str(profile.fpath)
        if _profile_running():
            if _stored_last_modes().get(key) != last_mode.name:
                _pending_last[key] = last_mode.name
                from gremlin import deferred_write

                # Saved on stop or quit; an hour is only a safety net.
                deferred_write.schedule("last-mode", flush_last_modes, 3_600_000)
            return
        config = Configuration()
        stored = _stored_last_modes()
        _pending_last.clear()
        stored[key] = last_mode.name
        config.set(*_LAST_KEY, stored)

    def _rewrite_stored_name(self, old_name: str, new_name: str | None) -> None:
        profile = shared_state.current_profile
        if profile is None or profile.fpath is None:
            return
        config = Configuration()
        stored = _stored_last_modes()
        _pending_last.clear()
        key = str(profile.fpath)
        if stored.get(key) != old_name:
            return
        if new_name:
            stored[key] = new_name
        else:
            stored.pop(key, None)
        config.set("global", "internal", "last-mode-per-profile", stored)

    def _update_mode(self) -> None:
        # The running profile refreshes the axes on a mode change (CodeRunner).
        self._store_last_mode()
        self.mode_changed.emit(self.current.name)

    def rename_mode(self, old_name: str, new_name: str) -> None:
        """Keep the running stack and the saved last mode on a renamed mode."""
        if old_name == new_name:
            return
        current_changed = self.current.name == old_name
        for mode in self._mode_stack:
            if mode.name == old_name:
                mode._name = new_name
            if mode.previous == old_name:
                mode.previous = new_name
        self._rewrite_stored_name(old_name, new_name)
        if current_changed:
            self._update_mode()
        from gremlin.event_handler import EventHandler

        EventHandler().rename_mode(old_name, new_name)

    def drop_mode(self, name: str) -> None:
        """Remove a deleted mode from the running stack."""
        current_changed = self.current.name == name
        self._mode_stack = [mode for mode in self._mode_stack if mode.name != name]
        if len(self._mode_stack) == 0:
            fallback = shared_state.current_profile.modes.first_mode
            self._mode_stack = [Mode(fallback, None)]
        self._rewrite_stored_name(name, None)
        if current_changed:
            self._update_mode()
        from gremlin.event_handler import EventHandler

        EventHandler().drop_mode(name)

    def cycle(self, sequence: ModeSequence) -> None:
        self.switch_to(Mode(sequence.next(), self.current.name))

    def previous(self) -> None:
        if len(self._mode_stack) < 2:
            return

        # Swap the two top-most elements of the mode stack
        self._mode_stack[-1], self._mode_stack[-2] = (
            self._mode_stack[-2],
            self._mode_stack[-1],
        )
        self._update_mode()

    def unwind(self) -> None:
        if len(self._mode_stack) < 2:
            return

        # Remove top mode in stack
        self._mode_stack.pop()
        self._update_mode()

    def switch_to(self, mode: Mode) -> None:
        # Detect cycle in the mode stack and resolve it
        if self._exists(mode):
            resolution_mode = Configuration().value(
                "action", "change-mode", "resolution-mode"
            )
            idx = self._mode_stack.index(mode)

            if not mode.is_temporary:
                if resolution_mode == "Oldest":
                    self._mode_stack = self._mode_stack[:idx]
                elif resolution_mode == "Newest":
                    self._mode_stack = self._mode_stack[idx + 1 :]
            # Special handling if the loop is caused by a temporary mode
            else:
                if resolution_mode == "Oldest":
                    self._mode_stack = self._mode_stack[:idx]
                if resolution_mode == "Newest":
                    # 1. Find the index corresponding to the first non-temporary
                    #    mode entry in the stack before the idx mode
                    idx2 = idx
                    while idx2 > 0 and self._mode_stack[idx2].is_temporary:
                        idx2 -= 1
                    assert not self._mode_stack[idx2].is_temporary
                    # 2. Create new stack that no longer contains the old
                    #    temporary mode instance but retains all previous
                    #    modes until the first non-temporary entry
                    self._mode_stack = [m for m in self._mode_stack[idx2:] if m != mode]
                    # 3. Fix inconsistent stack entry transitions
                    for a, b in zip(self._mode_stack[:-1], self._mode_stack[1:]):
                        if a.name != b.previous:
                            b.previous = a.name

        self._mode_stack.append(mode)
        self._update_mode()

    def temporary(self, mode: Mode) -> None:
        mode.is_temporary = True
        self.switch_to(mode)

    def leave_temporary(self, mode: Mode) -> None:
        mode.is_temporary = True
        if self._mode_stack[-1] == mode:
            self.unwind()
        self._mode_stack = [m for m in self._mode_stack if m != mode]


Configuration().register(
    "action",
    "change-mode",
    "resolution-mode",
    PropertyType.Selection,
    "Oldest",
    "Defines which mode is switched to in the case that a cyclical mode "
    'traversal is detected. "Oldest" switches to the oldest mode in '
    'the cycle while "newest" finds the most recent common mode and '
    "switches to that one.",
    {"valid_options": ["Oldest", "Newest"]},
    True,
)
