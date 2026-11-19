# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6 import QtCore

from gremlin import input_thread, shared_state, util
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

    def next(self, current: str | None = None, known: set[str] | None = None) -> str:
        """Returns the next mode in the sequence.

        Args:
            current: the mode now active: the result is the one after it (the
                first when it isn't in the sequence). Without it, the
                sequence's own counter is used.
            known: the modes that exist; others (deleted after the action
                named them) are skipped. None or empty: no check.

        Returns:
            Next mode in the sequence, wrapping around at the end.
        """
        if current is not None:
            # From the current mode: the first press goes somewhere, and copies
            # of the same Cycle action in different modes stay in step (each
            # had its own counter).
            if current in self.modes:
                self._current_index = (self.modes.index(current) + 1) % len(self.modes)
            else:
                self._current_index = 0
        else:
            self._current_index = (self._current_index + 1) % len(self.modes)
        if known:
            # A deleted mode is stepped over (the cycle stayed put on it).
            for _ in range(len(self.modes)):
                if self.modes[self._current_index] in known:
                    break
                self._current_index = (self._current_index + 1) % len(self.modes)
        return self.modes[self._current_index]


# The last mode per profile, changed while a profile runs: kept here and
# saved when it stops or the program quits (and at most hourly), not on every
# mode switch during play.
_pending_last: dict[str, str] = {}
_LAST_KEY = ("global", "internal", "last-mode-per-profile")


def _last_mode_of(stored: dict[str, str], fpath: str | Path) -> str | None:
    for key, mode in stored.items():
        if util.same_path(key, fpath):
            return mode
    return None


def _put_last_mode(stored: dict[str, str], fpath: str | Path, mode: str | None) -> None:
    """One entry per file: other spellings of it go."""
    for key in [key for key in stored if util.same_path(key, fpath)]:
        del stored[key]
    if mode:
        stored[str(fpath)] = mode


def _stored_last_modes() -> dict[str, str]:
    stored = dict(Configuration().value(*_LAST_KEY))
    for key, mode in _pending_last.items():
        _put_last_mode(stored, key, mode)
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

    A named startup mode is used as itself. Anything else is Last Active:
    the mode the profile was last on (running or not), when that mode still
    exists; with no such record, the top row of the mode list (04 S52,
    D-04-LAST-ACTIVE).
    """
    mode_names = active_profile.modes.mode_names()
    startup_mode = active_profile.settings.startup_mode
    if startup_mode in mode_names:
        return startup_mode
    if active_profile.fpath is not None:
        last_mode = _last_mode_of(_stored_last_modes(), active_profile.fpath)
        if last_mode in mode_names:
            return last_mode
    return active_profile.modes.top_listed_mode()


def _known_modes() -> set[str]:
    """The running profile's modes; with none running, the open profile's."""
    from gremlin.event_handler import EventHandler

    known = set(getattr(EventHandler(), "known_modes", set()))
    profile = _run_profile()
    if not known and profile is not None:
        known = set(profile.modes.mode_names())
    return known


def _run_profile() -> Profile | None:
    """The profile the mode system works on from the input thread: the
    Run's own copy while one runs (answer 6a), else the open profile."""
    return shared_state.profile_for_runtime()


def _run_fpath() -> Path | None:
    """The file path of _run_profile(), read on the calling thread."""
    profile = _run_profile()
    return None if profile is None else profile.fpath


def _on_input_thread(fn: Callable[..., None], *args: object) -> None:
    """Runs fn on the input thread, where the mode stack is changed; where
    it doesn't run (stopped program, tests), on the caller."""
    if input_thread.is_running() or input_thread.is_inline():
        input_thread.call(fn, *args)
    else:
        fn(*args)


def _run_copy() -> Profile | None:
    """The Run's own copy of the profile, when a Run is on and it is not the
    open profile itself. Read on the input thread, which sets and clears it."""
    copy = shared_state.running_profile
    if copy is None or copy is shared_state.current_profile:
        return None
    return copy


def _rename_in_run_copy(old_name: str, new_name: str) -> None:
    """A rename reaches the Run's copy too: its Change Mode targets (a
    running Cycle holds the list), inputs and Startup Mode, by the rename
    the open profile used (ModeHierarchy.rename_mode, 04 S44)."""
    from gremlin import error

    copy = _run_copy()
    if copy is None or not copy.modes.mode_exists(old_name):
        return
    try:
        copy.modes.rename_mode(old_name, new_name)
    except error.GremlinError as err:
        # The copy differs from the open profile (a mode added or deleted
        # since Run): the open profile has the rename; the next Run gets it.
        logging.getLogger("system").warning(
            f"Mode rename '{old_name}' to '{new_name}' not applied to the "
            f"running profile: {err}"
        )


def _first_mode_without(profile: Profile, name: str) -> str:
    """The profile's first top-level mode once name is deleted (its child
    modes move up a level, 04 S46); the Run's copy still has name."""
    modes = profile.modes
    if not modes.mode_exists(name):
        return modes.first_mode
    dropped = modes.find_mode(name)
    roots = []
    for other in modes.mode_names():
        if other == name:
            continue
        parent = modes.find_mode(other).parent
        if parent is dropped:
            parent = dropped.parent
        if parent is not None and parent.parent is None:
            roots.append(other)
    return min(roots, key=str.casefold) if roots else modes.first_mode


@SingletonDecorator
class ModeManager(QtCore.QObject):
    """Manages the mode change history.

    The stack is changed on the input thread only (Change Mode actions, Run
    start and end, the toolbar pick through input_thread.call). Other threads
    read `current`, a whole Mode published after each change; mode_changed is
    emitted there and reaches Qt receivers on other threads queued.
    """

    mode_changed = QtCore.Signal(str)

    def __init__(self) -> None:
        QtCore.QObject.__init__(self)

        self._stack = [Mode("Invalid", None)]
        # The current mode, published whole: read from the listener, macro
        # and script threads while the main thread changes the stack.
        self._current = self._stack[-1]
        self._config = Configuration()

    @property
    def _mode_stack(self) -> list[Mode]:
        return self._stack

    @_mode_stack.setter
    def _mode_stack(self, stack: list[Mode]) -> None:
        self._stack = stack
        if stack:
            self._current = stack[-1]

    def _publish(self) -> None:
        """The top of the stack becomes the current mode (after an in-place
        change of the stack)."""
        if self._stack:
            self._current = self._stack[-1]

    @property
    def current(self) -> Mode:
        """The current mode; safe to read from any thread."""
        return self._current

    def reset(self) -> str:
        """The open profile's start mode on a fresh stack (profile load).

        Called on main: the start mode is worked out here from the open
        profile and the stack is replaced on the input thread (so it can't
        race a Stop's end_run). Returns the start mode's name, as `current`
        shows it only once the input thread has run it."""
        profile = shared_state.current_profile
        assert profile is not None
        name = resolve_start_mode(profile)
        _on_input_thread(self._set_stack, [Mode(name, None)])
        return name

    def _set_stack(self, stack: list[Mode]) -> None:
        self._mode_stack = stack

    def start_run(self, name: str) -> None:
        """A Run starts in mode name (the toolbar mode) on a fresh stack: no
        mode history or temporary mode of an earlier Run (06 Q3, R3)."""
        self._mode_stack = [Mode(name, None)]
        self._update_mode()

    def end_run(self) -> None:
        """At Stop: temporary modes end with the Run, and the mode history
        with them; the mode under them stays shown (06 Q3, R3)."""
        before = self.current.name
        kept = [mode for mode in self._mode_stack if not mode.is_temporary]
        name = kept[-1].name if kept else before
        self._mode_stack = [Mode(name, None)]
        if name != before:
            self.mode_changed.emit(name)

    def _exists(self, mode: Mode) -> bool:
        return mode in self._mode_stack

    def _store_last_mode(self) -> None:
        """Last Active is the mode last used while running: a toolbar pick
        while stopped doesn't count (GL-149, 04 Q2)."""
        if not _profile_running():
            return
        profile = _run_profile()
        if profile is None or profile.fpath is None:
            return
        last_mode = next(
            (mode for mode in reversed(self._mode_stack) if not mode.is_temporary),
            None,
        )
        if last_mode is None:
            return
        if _last_mode_of(_stored_last_modes(), profile.fpath) != last_mode.name:
            _put_last_mode(_pending_last, profile.fpath, last_mode.name)
            from gremlin import deferred_write

            # Saved on stop or quit; an hour is only a safety net.
            # hold: the input thread has no scheduler, and must not write the
            # settings file itself; the Run's end or quit flushes it.
            deferred_write.schedule("last-mode", flush_last_modes, 3_600_000, hold=True)

    def _rewrite_stored_name(
        self, fpath: Path | None, old_name: str, new_name: str | None
    ) -> None:
        """Rewrites the stored last mode of the profile at fpath. fpath is
        taken by the caller when the change is made, so a profile swap while
        the change waits for the input thread can't redirect it (N2)."""
        if fpath is None:
            return
        config = Configuration()
        stored = _stored_last_modes()
        if _last_mode_of(stored, fpath) != old_name:
            return
        _pending_last.clear()
        _put_last_mode(stored, fpath, new_name)
        config.set(*_LAST_KEY, stored)

    def _update_mode(self) -> None:
        # The running profile refreshes the axes on a mode change (CodeRunner).
        self._store_last_mode()
        self.mode_changed.emit(self.current.name)

    def rename_mode(self, old_name: str, new_name: str) -> None:
        """Keep the running stack and the saved last mode on a renamed mode.

        Callable from any thread: the change runs on the input thread."""
        if old_name == new_name:
            return
        _on_input_thread(self._rename_mode, _run_fpath(), old_name, new_name)

    def _rename_mode(self, fpath: Path | None, old_name: str, new_name: str) -> None:
        current_changed = self.current.name == old_name
        for mode in self._mode_stack:
            if mode.name == old_name:
                mode._name = new_name
            if mode.previous == old_name:
                mode.previous = new_name
        _rename_in_run_copy(old_name, new_name)
        self._rewrite_stored_name(fpath, old_name, new_name)
        if current_changed:
            self._update_mode()
        from gremlin.event_handler import EventHandler

        EventHandler().rename_mode(old_name, new_name)

    def drop_mode(self, name: str) -> None:
        """Remove a deleted mode from the running stack.

        Callable from any thread: the change runs on the input thread."""
        _on_input_thread(self._drop_mode, _run_fpath(), name)

    def _drop_mode(self, fpath: Path | None, name: str) -> None:
        current_changed = self.current.name == name
        self._mode_stack = [mode for mode in self._mode_stack if mode.name != name]
        if len(self._mode_stack) == 0:
            profile = _run_profile()
            assert profile is not None
            fallback = _first_mode_without(profile, name)
            self._mode_stack = [Mode(fallback, None)]
        self._rewrite_stored_name(fpath, name, None)
        if current_changed:
            self._update_mode()
        from gremlin.event_handler import EventHandler

        EventHandler().drop_mode(name)

    def cycle(self, sequence: ModeSequence) -> None:
        if not sequence.modes:  # nothing to cycle through
            return
        target = sequence.next(self.current.name, _known_modes())
        # Only the current mode left to go to (a one-mode Cycle, or the
        # others deleted): stay, rather than stack the mode on itself.
        if target == self.current.name:
            return
        self.switch_to(Mode(target, self.current.name))

    def previous(self) -> None:
        if len(self._mode_stack) < 2:
            return

        # Swap the two top-most elements of the mode stack, built aside and
        # swapped in whole.
        stack = list(self._mode_stack)
        stack[-1], stack[-2] = stack[-2], stack[-1]
        self._mode_stack = stack
        self._update_mode()

    def unwind(self) -> None:
        if len(self._mode_stack) < 2:
            return

        # Remove top mode in stack
        self._mode_stack = self._mode_stack[:-1]
        self._update_mode()

    def switch_to(self, mode: Mode) -> None:
        # A mode the profile no longer has (deleted after an action named
        # it): switching to it left every input with nothing to do. The
        # running profile's modes; with none running, the open profile's.
        known = _known_modes()
        if known and mode.name not in known:
            from gremlin.log_once import log_once

            log_once(
                "system",
                ("unknown mode", mode.name),
                logging.WARNING,
                f"Mode '{mode.name}' is not in the profile: the mode was not changed.",
            )
            return
        # Built aside and swapped in whole: a reader never sees it half done.
        stack = list(self._mode_stack)
        # Detect cycle in the mode stack and resolve it
        if mode in stack:
            resolution_mode = Configuration().value(
                "action", "change-mode", "resolution-mode"
            )
            idx = stack.index(mode)

            if not mode.is_temporary:
                if resolution_mode == "Oldest":
                    stack = stack[:idx]
                elif resolution_mode == "Newest":
                    stack = stack[idx + 1 :]
            # Special handling if the loop is caused by a temporary mode
            else:
                if resolution_mode == "Oldest":
                    stack = stack[:idx]
                if resolution_mode == "Newest":
                    # 1. Find the index corresponding to the first non-temporary
                    #    mode entry in the stack before the idx mode
                    idx2 = idx
                    while idx2 > 0 and stack[idx2].is_temporary:
                        idx2 -= 1
                    assert not stack[idx2].is_temporary
                    # 2. Create new stack that no longer contains the old
                    #    temporary mode instance but retains all previous
                    #    modes until the first non-temporary entry
                    stack = [m for m in stack[idx2:] if m != mode]
                    # 3. Fix inconsistent stack entry transitions
                    for a, b in zip(stack[:-1], stack[1:]):
                        if a.name != b.previous:
                            b.previous = a.name

        self._mode_stack = [*stack, mode]
        self._update_mode()

    def temporary(self, mode: Mode) -> None:
        mode.is_temporary = True
        self.switch_to(mode)


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
