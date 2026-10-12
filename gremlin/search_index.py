# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""The Search index (01 S157-S164, D-01-SEARCH-INDEX): one row per action
in every profile in the profiles folder, the open profile (its unsaved
changes, in place of its file's rows) and the Device Library's saved
setups. Rows come from gremlin.usages, so each action's references() says
what it uses; nothing here lists action types or device kinds.

Built on a program thread (gremlin.threads); rows() is an immutable
snapshot, readable while it builds. The plug-in point for more places to
search is register_source(name, lister)."""

from __future__ import annotations

import logging
import threading
import uuid
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from gremlin import clock, threads, usages
from gremlin import references as refs
from gremlin.modules import ids

syslog = logging.getLogger("system")


@dataclass(frozen=True)
class SearchRow:
    """One action of one binding, where it is and what it uses."""

    source: str  # "profile" | "open" | "library"
    source_name: str
    source_path: str
    device_guid: str
    device_name: str
    plugged: bool | None  # None: a Device Library row
    mode: str
    input_type: int
    input_id: object
    input_label: str  # the system's name for the input
    custom_name: str  # the user's name for the input
    action_tag: str
    action_name: str
    text: str  # the binding's text
    targets: tuple[str, ...]  # display text of each target
    target_keys: tuple[tuple, ...]  # gremlin.references target shapes
    role: str
    not_found: bool
    why: str
    used_twice: bool
    binding_index: int
    path: tuple[str, ...]
    kinds: frozenset[str]
    # User-entered text of the action (AbstractActionData.search_texts()).
    notes: tuple[str, ...] = ()


Lister = Callable[[], Iterable[SearchRow]]

# Quick-filter kinds by target kind (first item of a target shape): a new
# target kind adds its line here.
TARGET_KINDS: dict[str, str] = {
    "vjoy": "vjoy",
    "xbox": "xbox",
    "osc-out": "osc",
    "mouse": "mouse",
    "mode": "mode",
}
# Quick-filter kinds by device kind (gremlin.modules.device_class), for the
# input itself and for an input target.
DEVICE_KINDS: dict[str, str] = {"keyboard": "key", "osc": "osc"}

# Roles that belong to the binding, not to one action (gremlin.usages).
_BINDING_ROLES = ("reads-input", "runs-in-mode", "inherited")
_NOTIFY_EVERY_S = 0.25
_OPEN = "open"


def _device_kind(guid: object) -> str:
    from gremlin.modules import device_class

    try:
        return device_class.device_kind(guid)
    except Exception:  # noqa: BLE001 - an id nothing can place
        return ""


def _kinds(device_guid: str, custom: str, keys: Iterable[tuple]) -> frozenset[str]:
    found = {"action"}
    if custom:
        found.add("name")
    own = DEVICE_KINDS.get(_device_kind(device_guid))
    if own:
        found.add(own)
    for key in keys:
        kind = TARGET_KINDS.get(str(key[0]))
        if kind:
            found.add(kind)
        elif key[0] == "input" and len(key) > 1:
            kind = DEVICE_KINDS.get(_device_kind(key[1]))
            if kind:
                found.add(kind)
    return frozenset(found)


def _display(target: tuple, fallback: str) -> str:
    """A target's text: Search's display table when it has one, else the
    Reference's own text."""
    try:
        from gremlin import search_query
    except ImportError:
        return fallback
    show = getattr(search_query, "display", None)
    if show is None:
        return fallback
    try:
        return str(show(target) or fallback)
    except Exception:  # noqa: BLE001 - one target kind with no display
        return fallback


def _input_key(device_guid: str, input_type: int, input_id: object) -> tuple:
    return (ids.guid_key(device_guid), input_type, refs.id_key(input_id))


def _custom_names(profile: Any) -> dict[tuple, str]:  # noqa: ANN401
    names: dict[tuple, str] = {}
    for guid, items in list(profile.inputs.items()):
        for item in items:
            name = str(getattr(item, "action_name", "") or "")
            if name:
                uid = getattr(item, "device_id", None) or guid
                uid = str(getattr(uid, "uuid", uid))
                kind = refs.type_int(item.input_type)
                key = (*_input_key(uid, kind, item.input_id), str(item.mode or ""))
                names[key] = name
    return names


def profile_rows(
    profile: Any,  # noqa: ANN401
    source: str,
    source_name: str,
    source_path: str,
    plugged: Callable[[str, str], bool | None] | None = None,
    device_name: str = "",
) -> list[SearchRow]:
    """Every action of every binding in a profile as rows, "Used twice"
    marked. gremlin.usages yields, per binding, each action's declared
    uses followed by its uses-action, then the binding's reads-input."""
    custom = _custom_names(profile)
    rows: list[SearchRow] = []
    pending: list[usages.Ref] = []
    binding: list[tuple[usages.Usage, list[usages.Ref]]] = []
    known: dict[str, bool | None] = {}
    sends: list[tuple[int, tuple]] = []

    def plugged_of(guid: str, name: str) -> bool | None:
        if plugged is None:
            return None
        if guid not in known:
            try:
                known[guid] = plugged(guid, name)
            except Exception:  # noqa: BLE001 - no device list: not plugged
                known[guid] = False
        return known[guid]

    def emit(text: str) -> None:
        for action, declared in binding:
            name = device_name or action.device_name
            ckey = (
                *_input_key(action.device_guid, action.input_type, action.input_id),
                action.mode,
            )
            cname = custom.get(ckey, "")
            keys = tuple(ref.target for ref in declared)
            first = declared[0].usage if declared else None
            rows.append(
                SearchRow(
                    source=source,
                    source_name=source_name,
                    source_path=source_path,
                    device_guid=action.device_guid,
                    device_name=name,
                    plugged=plugged_of(action.device_guid, name),
                    mode=action.mode,
                    input_type=action.input_type,
                    input_id=action.input_id,
                    input_label=action.input_label,
                    custom_name=cname,
                    action_tag=action.action_tag,
                    action_name=action.path[-1] if action.path else action.action_tag,
                    text=text,
                    targets=tuple(
                        _display(ref.target, ref.usage.text) for ref in declared
                    ),
                    target_keys=keys,
                    role=first.role if first else action.role,
                    not_found=any(ref.usage.not_found for ref in declared),
                    why=next((r.usage.why for r in declared if r.usage.why), ""),
                    used_twice=False,
                    binding_index=action.binding_index,
                    path=action.path,
                    kinds=_kinds(action.device_guid, cname, keys),
                    notes=action.texts,
                )
            )
            sends.extend(
                (len(rows) - 1, ref.target)
                for ref in declared
                if ref.usage.role == "sends-output"
            )
        binding.clear()

    for ref in usages.iter_usages(profile):
        role = ref.usage.role
        if role == "uses-action":
            binding.append((ref.usage, pending))
            pending = []
        elif role == "reads-input":
            if pending:  # the root's own uses, with no action of its own
                binding.append(
                    (replace(ref.usage, role=pending[0].usage.role), pending)
                )
                pending = []
            emit(ref.usage.text)
        elif role not in _BINDING_ROLES:
            pending.append(ref)
    return _mark_used_twice(rows, sends)


def _mark_used_twice(
    rows: list[SearchRow], sends: list[tuple[int, tuple]]
) -> list[SearchRow]:
    """Used twice: the same output in the same mode of the same source
    sent by 2+ different inputs."""
    inputs: dict[tuple, set[tuple]] = {}
    for index, target in sends:
        row = rows[index]
        key = (row.source_path, row.mode, target)
        inputs.setdefault(key, set()).add(
            _input_key(row.device_guid, row.input_type, row.input_id)
        )
    clash = {key for key, found in inputs.items() if len(found) > 1}
    marked = {
        index
        for index, target in sends
        if (rows[index].source_path, rows[index].mode, target) in clash
    }
    return [
        replace(r, used_twice=True) if i in marked else r for i, r in enumerate(rows)
    ]


def mark_used_twice(rows: Iterable[SearchRow]) -> list[SearchRow]:
    """Marks "Used twice" on rows from a registered source: its sends-output
    rows' targets."""
    rows = list(rows)
    sends = [
        (i, key)
        for i, row in enumerate(rows)
        if row.role == "sends-output"
        for key in row.target_keys
    ]
    return _mark_used_twice(rows, sends)


def _default_plugged(guid: str, name: str) -> bool:
    from gremlin.modules import hardware

    return hardware.plugged_in(guid, name)


def _default_folder() -> Path:
    from gremlin import util

    return util.profiles_dir()


def _read_profile(path: Path) -> Any | str:  # noqa: ANN401
    """A profile file read without opening it (as the Device Library does),
    or why it can't be read."""
    from gremlin.library_profiles import read_profile

    return read_profile(path)


def _setup_uid(guid: str, name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(guid).strip().strip("{}"))
    except ValueError:
        return uuid.uuid5(uuid.NAMESPACE_URL, f"gremlin-device:{name}")


def _setup_profile(wires: dict, uid: uuid.UUID) -> Any:  # noqa: ANN401
    """A saved setup's wires as a profile that is never opened, filled
    through the Library's own path (Profile.add_inputs, as a Device Pack
    import does). Its edit note only makes the unsaved check look again."""
    from gremlin.profile import Profile

    made = Profile(bind=False)
    actions = [str(block) for block in wires.get("actions") or []]
    inputs = [
        str(block)
        for mode in wires.get("modes") or []
        if isinstance(mode, dict)
        for block in mode.get("inputs") or []
    ]
    made.add_inputs(uid, inputs, actions, remap=False)
    return made


def library_rows() -> Iterator[SearchRow]:
    """Every Device Library saved setup that holds bindings, as rows."""
    from gremlin import device_library

    for device in device_library.devices():
        for setup in device.get("setups") or []:
            if "bindings" not in (setup.get("holds") or []):
                continue
            pack = device_library._read_pack(Path(setup.get("pack", "")))
            if isinstance(pack, str):
                syslog.info(f"Search: saved setup {setup.get('name')}: {pack}")
                continue
            uid = _setup_uid(device.get("guid", ""), device.get("name", ""))
            made = _setup_profile(pack.get("wires") or {}, uid)
            name = str(setup.get("name") or device.get("name") or "")
            yield from profile_rows(
                made,
                "library",
                name,
                str(setup.get("pack", "")),
                device_name=str(device.get("name") or ""),
            )


class SearchIndex:
    """Rows from every place Search looks; thread-safe snapshot."""

    def __init__(
        self,
        folder: Path | Callable[[], Path] | None = None,
        on_change: Callable[[], None] | None = None,
        plugged: Callable[[str, str], bool | None] | None = None,
        library: bool = True,
    ) -> None:
        self._folder = folder if folder is not None else _default_folder
        self._on_change = on_change
        self._plugged = plugged or _default_plugged
        self._lock = threading.Lock()
        self._sources: dict[str, Lister] = {}
        # Rows by part: "file:<path key>", "open", "source:<name>".
        self._parts: dict[str, list[SearchRow]] = {}
        self._open_key = ""
        self._snapshot: tuple[SearchRow, ...] = ()
        self._state = "ready"
        self._done = 0
        self._total = 0
        self._unreadable: list[tuple[str, str]] = []
        self._generation = 0
        self._idle = threading.Event()
        self._idle.set()
        self._stop = threading.Event()
        if library:
            self.register_source("Device Library", library_rows)

    # --- plug-in point ---------------------------------------------------

    def register_source(self, name: str, lister: Lister) -> None:
        """Adds a place to search: lister() yields SearchRows (on a program
        thread). Read at the next build()."""
        with self._lock:
            self._sources[name] = lister

    def set_on_change(self, callback: Callable[[], None] | None) -> None:
        """callback() after the rows change; it may be called on a program
        thread, so a Qt caller queues it to the main thread."""
        self._on_change = callback

    # --- reading -----------------------------------------------------------

    def rows(self) -> tuple[SearchRow, ...]:
        with self._lock:
            return self._snapshot

    def status(self) -> dict:
        with self._lock:
            return {
                "state": self._state,
                "done": self._done,
                "total": self._total,
                "unreadable": list(self._unreadable),
            }

    def wait(self, timeout: float) -> bool:
        """Waits (bounded) for a build to end; True when it has."""
        return self._idle.wait(timeout)

    # --- building ------------------------------------------------------------

    def build(self, open_profile: Any = _OPEN) -> None:  # noqa: ANN401
        """Rebuilds everything: the open profile here (it belongs to this
        thread), the files and sources on a program thread. open_profile:
        the profile to show as open (default: the program's open one)."""
        if open_profile is _OPEN:
            from gremlin import shared_state

            open_profile = shared_state.current_profile
        self._stop.set()
        with self._lock:
            self._generation += 1
            generation = self._generation
            self._state = "building"
            self._done = 0
            self._total = 0
            self._unreadable = []
            sources = dict(self._sources)
            self._parts = {}
        self._stop = threading.Event()
        self._idle.clear()
        self.rebuild_open(open_profile)
        threads.start(
            "Search index",
            self._run,
            generation,
            sources,
            self._stop,
            stop=self._stop.set,
        )

    def stop(self) -> None:
        """Asks a running build to end."""
        self._stop.set()

    def rebuild_open(self, profile: Any) -> None:  # noqa: ANN401
        """The open profile's rows again (call on the thread that owns it,
        debounced by the caller); None: no open profile."""
        rows: list[SearchRow] = []
        key = ""
        if profile is not None:
            fpath = getattr(profile, "fpath", None)
            key = refs.path_key(fpath) if fpath else ""
            name = Path(str(fpath)).stem if fpath else "Untitled"
            try:
                rows = profile_rows(
                    profile, "open", name, str(fpath or ""), self._plugged
                )
            except Exception:  # noqa: BLE001 - one bad piece hides nothing else
                syslog.exception("Search: the open profile could not be indexed")
        with self._lock:
            self._open_key = key
            self._parts["open"] = rows
            self._assemble()
        self._notify()

    def file_saved(self, path: Path | str) -> threading.Thread | None:
        """A profile file in the folder was written: its rows are read again
        on a program thread (returned, so a caller may join it). A file
        outside the folder is not searched: None."""
        path = Path(path)
        folder = self._folder() if callable(self._folder) else self._folder
        if not Path(refs.path_key(path)).is_relative_to(refs.path_key(folder)):
            return None
        return threads.start("Search index re-read", self._reread, path)

    def _reread(self, path: Path) -> None:
        rows, problem = self._file(path) if path.is_file() else ([], None)
        shown = str(path)
        with self._lock:
            self._parts[f"file:{refs.path_key(path)}"] = rows
            self._unreadable = [u for u in self._unreadable if u[0] != shown]
            if problem is not None:
                self._unreadable.append(problem)
            self._assemble()
        self._notify()

    def _run(
        self, generation: int, sources: dict[str, Lister], stop: threading.Event
    ) -> None:
        try:
            folder = self._folder() if callable(self._folder) else self._folder
            files = sorted(Path(folder).rglob("*.xml")) if Path(folder).is_dir() else []
            with self._lock:
                if generation != self._generation:
                    return
                self._total = len(files) + len(sources)
            last = clock.monotonic()
            for path in files:
                if stop.is_set():
                    return
                self._add(generation, f"file:{refs.path_key(path)}", *self._file(path))
                if clock.monotonic() - last >= _NOTIFY_EVERY_S:
                    last = clock.monotonic()
                    self._notify()
            for name, lister in sources.items():
                if stop.is_set():
                    return
                try:
                    rows = mark_used_twice(lister())
                    problem = None
                except Exception as exc:  # noqa: BLE001 - one source hides nothing else
                    syslog.exception(f"Search: source {name} failed")
                    rows, problem = [], (name, str(exc) or type(exc).__name__)
                self._add(generation, f"source:{name}", rows, problem)
        finally:
            with self._lock:
                if generation == self._generation:
                    self._state = "ready"
                    self._idle.set()
            self._notify()

    def _file(self, path: Path) -> tuple[list[SearchRow], tuple[str, str] | None]:
        read = _read_profile(path)
        if isinstance(read, str):
            return [], (str(path), read)
        try:
            rows = profile_rows(read, "profile", path.stem, str(path), self._plugged)
        except Exception as exc:  # noqa: BLE001 - one bad file hides nothing else
            syslog.exception(f"Search: {path.name} could not be indexed")
            return [], (str(path), str(exc) or type(exc).__name__)
        return rows, None

    def _add(
        self,
        generation: int,
        part: str,
        rows: list[SearchRow],
        problem: tuple[str, str] | None,
    ) -> None:
        with self._lock:
            if generation != self._generation:
                return
            self._parts[part] = rows
            if problem is not None:
                self._unreadable.append(problem)
            self._done += 1
            self._assemble()

    def _assemble(self) -> None:
        """The snapshot from the parts (lock held): the open profile's rows
        stand in for its file's."""
        hidden = f"file:{self._open_key}" if self._open_key else ""
        found: list[SearchRow] = list(self._parts.get("open", []))
        for part in sorted(self._parts):
            if part.startswith("file:") and part != hidden:
                found.extend(self._parts[part])
        for part, rows in self._parts.items():
            if part.startswith("source:"):
                found.extend(rows)
        self._snapshot = tuple(found)

    def _notify(self) -> None:
        callback = self._on_change
        if callback is None:
            return
        try:
            callback()
        except Exception:  # noqa: BLE001 - a listener's error stays its own
            syslog.exception("Search: change listener failed")


# The program's one index (default_index), made on first use.
_default: SearchIndex | None = None
_default_lock = threading.Lock()


def default_index() -> SearchIndex:
    """The program's one SearchIndex, made and built (with the open profile,
    shared_state.current_profile) on the first call; call it on the main
    thread, which owns the open profile."""
    global _default
    with _default_lock:
        made = _default is None
        if _default is None:
            _default = SearchIndex()
        index = _default
    if made:
        index.build()
    return index


def note_saved(path: Path | str) -> None:
    """A profile file was saved (Profile.to_xml, library_profiles
    save_profile): the index, when there is one, reads it again."""
    index = _default
    if index is None:
        return
    try:
        index.file_saved(path)
    except Exception:  # noqa: BLE001 - a save never fails for Search
        syslog.exception("Search: re-reading a saved profile failed")
