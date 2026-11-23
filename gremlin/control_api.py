# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Control from other programs: the gremlin-ctl command line, the MCP
server and scripts read and control the program through a private named
pipe (claude/plans/control-api.md, control-api-contract.md).

Only while Options › General › "Allow control from other programs" is on
(off at first; only the user changes it, never a call). The pipe has a new
random name and a 32-byte key each time it opens, the same method as the
device helper (gremlin/device_disable.py); both are written to
<user folder>/api/endpoint.json, which goes when the pipe closes.

One JSON request per message, {"call", "args"}; the answer is {"ok": true,
"result"} or {"ok": false, "error", "code"} (CODES). Calls come from
register(), each declaring its arguments (Arg), checked before it runs: the
ones here, and the window and menu command ones registered at attach_ui().
One limit covers the wait for a busy API and the call; a call that needs
the window runs on the main thread, and one that hasn't started by then
never runs (threads.main_call_wait); the program carries on. Nothing in the
program waits on a client: each connection has its own thread, every wait
on it is bounded, and a client that stops answering is dropped.

Every call writes one system log line "API: <call> <args> -> ok|error",
except the version handshake (hello).
Profile saves and Options changes made here go into Tools › History
marked "(by API)" where History's group path can mark them (see
_by_api).
"""

from __future__ import annotations

import dataclasses
import json
import logging
import math
import os
import secrets
import sys
import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from gremlin import clock, threads

PROTOCOL_VERSION = 1
PIPE_PREFIX = "\\\\.\\pipe\\gremlin-platforms-api-"
SWITCH_KEY = ("global", "control", "allow-other-programs")
SWITCH_DESCRIPTION = (
    "Lets the gremlin-ctl command line and other programs on this PC read "
    "and control Gremlin-Platforms."
)
OFF_TEXT = "Control from other programs is off in Options › General."
SWITCH_REFUSED_TEXT = "Only the user can change this setting, in Options › General."
ENDPOINT_FOLDER = "api"
ENDPOINT_NAME = "endpoint.json"

# Limits: a request's size, the key handshake, an idle connection, the
# connections served at once, and the wait for another call to finish.
MAX_REQUEST_BYTES = 1024 * 1024
HANDSHAKE_S = 5.0
IDLE_S = 120.0
MAX_CONNECTIONS = 4
POLL_S = 0.5
DEFAULT_TIMEOUT_S = 10.0
LONG_TIMEOUT_S = 30.0
LOG_LINES_MAX = 2000
# run.start / run.stop: the longest wait for the Run's answer.
RUN_WAIT_S = DEFAULT_TIMEOUT_S

_log = logging.getLogger("system")


# The answer's error code (S25): clients read it, not the text.
CODES = (
    "bad_args",
    "unknown_call",
    "not_found",
    "not_ready",
    "refused",
    "busy",
    "timeout",
    "too_large",
    "failed",
)


class CallError(Exception):
    """A call that can't be done; its text is the answer's error, code one
    of CODES (an unknown one counts as "failed")."""

    def __init__(self, text: str, code: str = "failed") -> None:
        super().__init__(text)
        self.code = code if code in CODES else "failed"


def _error(text: str, code: str) -> dict:
    return {"ok": False, "error": text, "code": code}


def _error_answer(name: str, error: BaseException, limit: float = 0.0) -> dict:
    """Every exception to its answer, in one place: CallError keeps its
    code, a main-thread time-out is "timeout", anything else is a fault
    ("failed", traceback logged)."""
    if isinstance(error, CallError):
        return _error(str(error), error.code)
    if isinstance(error, TimeoutError):
        if getattr(error, "started", False):
            text = f"{name} took over {limit:g} s; it may still finish."
        else:
            text = f"{name} took over {limit:g} s and was not done."
        return _error(text, "timeout")
    _log.error(f"API: {name} failed", exc_info=error)
    return _error(f"{type(error).__name__}: {error}", "failed")


# --- the switch ---------------------------------------------------------------


def register_options() -> None:
    """The Options switch (before the start-up purge)."""
    from gremlin.config import Configuration
    from gremlin.types import PropertyType

    Configuration().register(
        *SWITCH_KEY, PropertyType.Bool, False, SWITCH_DESCRIPTION, {}, True
    )


def allowed() -> bool:
    """The switch is on (False when it can't be read)."""
    try:
        from gremlin.config import Configuration

        return bool(Configuration().value(*SWITCH_KEY))
    except Exception:
        return False


# --- the call registry ---------------------------------------------------------


ARG_TYPES = ("str", "int", "float", "bool", "object", "list", "any")
_TYPE_WORDS = {
    "str": "text",
    "int": "a whole number",
    "float": "a number",
    "bool": "true or false",
    "object": "an object",
    "list": "a list",
    "any": "any value",
}


@dataclass(frozen=True)
class Arg:
    """One argument a call takes (S26): its type (ARG_TYPES), whether it
    must be given, its help line, and limits checked before the handler.
    A required "str" refuses "" unless allow_empty (e.g. text that clears
    a field)."""

    type: str
    required: bool = False
    help: str = ""
    min: float | None = None
    max: float | None = None
    choices: tuple | None = None
    allow_empty: bool = False

    def __post_init__(self) -> None:
        if self.type not in ARG_TYPES:
            raise ValueError(f"Arg type {self.type!r} isn't one of {ARG_TYPES}")
        if self.choices is not None:
            object.__setattr__(self, "choices", tuple(self.choices))

    def describe(self) -> dict:
        return {
            "type": self.type,
            "required": self.required,
            "help": self.help,
            "min": self.min,
            "max": self.max,
            "choices": list(self.choices) if self.choices is not None else None,
        }


@dataclass(frozen=True)
class _Call:
    handler: Callable[[dict], Any]
    main_thread: bool
    timeout_s: float
    summary: str
    args: dict[str, Arg] = dataclasses.field(default_factory=dict)


_calls: dict[str, _Call] = {}
_calls_lock = threading.Lock()
# One call at a time (a second waits for the first, within its own limit).
_busy = threading.Lock()


def register(
    name: str,
    handler: Callable[[dict], Any],
    *,
    main_thread: bool = False,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    summary: str = "",
    args: dict[str, Arg] | None = None,
) -> None:
    """Adds a call (the owning module registers its own; a second one with
    the same name replaces the first). args declares every argument it
    takes (None: none); dispatch refuses others before handler(args) runs.
    The handler returns a JSON-able result or raises CallError."""
    declared = dict(args or {})
    for key, arg in declared.items():
        if not isinstance(arg, Arg):
            raise TypeError(f"{name}: argument {key!r} isn't an Arg")
    with _calls_lock:
        _calls[str(name)] = _Call(
            handler, bool(main_thread), float(timeout_s), summary, declared
        )


def calls() -> list[dict]:
    """Every call: [{"name", "summary", "args": {name: {...}}}], by name."""
    with _calls_lock:
        items = sorted(_calls.items())
    return [
        {
            "name": name,
            "summary": call.summary,
            "args": {key: arg.describe() for key, arg in call.args.items()},
        }
        for name, call in items
    ]


def _takes(name: str, declared: dict[str, Arg]) -> str:
    if not declared:
        return f"{name} takes no arguments"
    return f"it takes: {', '.join(declared)}"


def _type_ok(kind: str, value: Any) -> bool:  # noqa: ANN401 - any argument
    if kind == "any":
        return True
    if kind == "bool":
        return isinstance(value, bool)
    if isinstance(value, bool):
        return False
    if kind == "int":
        return isinstance(value, int) or (
            isinstance(value, float) and math.isfinite(value) and value.is_integer()
        )
    if kind == "float":
        return isinstance(value, (int, float)) and math.isfinite(value)
    expected = {"str": str, "object": dict, "list": list}[kind]
    return isinstance(value, expected)


def _checked_args(name: str, declared: dict[str, Arg], args: dict) -> dict:
    """args as the call declared them (S26); CallError "bad_args" when one
    is unknown, missing, of the wrong type or out of range. A null value
    counts as not given."""
    unknown = [key for key in args if key not in declared]
    if unknown:
        if not declared:
            raise CallError(
                f"{name} takes no arguments ('{unknown[0]}' given).", "bad_args"
            )
        raise CallError(
            f"{name} has no argument '{unknown[0]}' ({_takes(name, declared)}).",
            "bad_args",
        )
    result = {}
    for key, arg in declared.items():
        value = args.get(key)
        empty = arg.type == "str" and value == "" and not arg.allow_empty
        if value is None or (empty and arg.required):
            if arg.required:
                raise CallError(
                    f"{name} needs {key} ({_takes(name, declared)}).", "bad_args"
                )
            continue
        if not _type_ok(arg.type, value):
            raise CallError(f"{name}: '{key}' is {_TYPE_WORDS[arg.type]}.", "bad_args")
        if arg.type in ("int", "float"):
            number = int(value) if arg.type == "int" else float(value)
            low, high = arg.min, arg.max
            if (low is not None and number < low) or (
                high is not None and number > high
            ):
                raise CallError(f"{name}: '{key}' is {_range_text(arg)}.", "bad_args")
            value = number
        if arg.choices is not None and value not in arg.choices:
            raise CallError(
                f"{name}: '{key}' is one of: {', '.join(map(str, arg.choices))}.",
                "bad_args",
            )
        result[key] = value
    return result


def _range_text(arg: Arg) -> str:
    def shown(number: float) -> str:
        return f"{number:g}"

    if arg.min is not None and arg.max is not None:
        return f"{shown(arg.min)} to {shown(arg.max)}"
    if arg.min is not None:
        return f"at least {shown(arg.min)}"
    return f"at most {shown(arg.max)}"  # type: ignore[arg-type]


def _short(args: dict) -> str:
    """The call's arguments for its log line, with the space before them
    ("" for none, so "API: state -> ok" has single spaces)."""
    if not args:
        return ""
    try:
        text = json.dumps(args, ensure_ascii=False, default=str)
    except Exception:
        text = repr(args)
    return " " + (text if len(text) <= 120 else text[:117] + "...")


def _json_safe(value: Any) -> Any:  # noqa: ANN401 - any result
    return json.loads(json.dumps(value, default=str))


def dispatch(call: str, args: dict | None = None) -> dict:
    """Runs one call; returns the answer {"ok": true, "result"} or {"ok":
    false, "error", "code"}. Never raises. With the switch off nothing
    runs."""
    args = {} if args is None else args
    name = str(call)
    reply: dict
    if not allowed():
        reply = _error(OFF_TEXT, "refused")
    elif not isinstance(args, dict):
        reply = _error("The request's args is an object.", "bad_args")
    else:
        with _calls_lock:
            entry = _calls.get(name)
        if entry is None:
            reply = _error(
                f"No call '{name}' (the call 'help' lists them).", "unknown_call"
            )
        else:
            reply = _run(name, entry, args)
    # The client's version handshake before every call isn't logged (S8).
    if reply["ok"] and name != "hello":
        _log.warning(f"API: {name}{_short(args)} -> ok")
    elif not reply["ok"]:
        _log.warning(f"API: {name}{_short(args)} -> error: {reply['error']}")
    return reply


# The deadline of the call this thread runs (one limit for the busy wait
# and the call, S9/S28); handlers that wait read it through time_left().
_local = threading.local()


def time_left(default: float = DEFAULT_TIMEOUT_S) -> float:
    """Seconds left before the running call's limit (default outside one)."""
    deadline = getattr(_local, "deadline", None)
    if deadline is None:
        return default
    return max(0.0, deadline - clock.monotonic())


def _run(name: str, entry: _Call, args: dict) -> dict:
    deadline = clock.monotonic() + entry.timeout_s
    try:
        checked = _checked_args(name, entry.args, args)
    except CallError as error:
        return _error_answer(name, error)
    if not _busy.acquire(timeout=entry.timeout_s):
        return _error("Busy with another call; try again.", "busy")
    _local.deadline = deadline
    try:
        if entry.main_thread:
            result = threads.main_call_wait(
                entry.handler, checked, timeout=max(0.0, deadline - clock.monotonic())
            )
        else:
            result = entry.handler(checked)
        return {"ok": True, "result": _json_safe(result)}
    except Exception as error:
        return _error_answer(name, error, entry.timeout_s)
    finally:
        _local.deadline = None
        _busy.release()


def handle_bytes(data: bytes) -> bytes:
    """One request message to its answer message (UTF-8 JSON both)."""
    if len(data) > MAX_REQUEST_BYTES:
        reply: dict = _too_large()
    else:
        try:
            request = json.loads(bytes(data).decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            reply = _error("The request isn't JSON.", "bad_args")
        else:
            if not isinstance(request, dict) or not isinstance(
                request.get("call"), str
            ):
                reply = _error('A request is {"call": name, "args": {}}.', "bad_args")
            else:
                reply = dispatch(request["call"], request.get("args"))
    return json.dumps(reply, ensure_ascii=False).encode("utf-8")


def _too_large() -> dict:
    _log.warning("API: a request over 1 MB was refused")
    return _error("The request is over 1 MB.", "too_large")


# --- the pipe -------------------------------------------------------------------


class Listener(Protocol):
    def accept(self) -> Any: ...  # noqa: ANN401 - a Connection

    def close(self) -> None: ...


ListenerFactory = Callable[[str], Listener]
# (connection, key) -> True when the client proved it has the key.
Handshake = Callable[[Any, bytes], bool]


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


class RealPipeBlocked(RuntimeError):
    """A real named pipe opened from a test (pass a listener_factory)."""


class _PipeListener:
    """A named pipe listener without a handshake of its own: the key check
    runs on the connection's thread with time limits (_handshake), so a
    client that connects and says nothing never holds up the next one.
    close() wakes a waiting accept() by connecting to it."""

    def __init__(self, address: str) -> None:
        if _under_test():
            raise RealPipeBlocked("control API pipe opened from a test")
        from multiprocessing.connection import Listener as MpListener

        self._address = address
        self._listener = MpListener(address, family="AF_PIPE")
        self._closed = False
        self._accepting = False

    def accept(self) -> Any:  # noqa: ANN401 - a Connection
        self._accepting = True
        try:
            conn = self._listener.accept()
        finally:
            self._accepting = False
        if self._closed:
            conn.close()
            raise OSError("listener closed")
        return conn

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._accepting:
            try:
                from multiprocessing.connection import Client

                Client(self._address, family="AF_PIPE").close()
            except Exception:
                pass
        try:
            self._listener.close()
        except Exception:
            pass


class _Bounded:
    """A connection whose every read waits at most limit seconds."""

    def __init__(self, conn: Any, limit: float) -> None:  # noqa: ANN401
        self._conn = conn
        self._limit = limit

    def send_bytes(self, data: bytes) -> None:
        self._conn.send_bytes(data)

    def recv_bytes(self, maxlength: int | None = None) -> bytes:
        if not self._conn.poll(self._limit):
            raise TimeoutError("no answer in the handshake")
        return self._conn.recv_bytes(maxlength)


def _handshake(conn: Any, key: bytes) -> bool:  # noqa: ANN401
    """The key check multiprocessing's Listener(authkey=key) does, both
    ways, each read bounded (a Client(authkey=key) passes it)."""
    from multiprocessing.connection import answer_challenge, deliver_challenge

    bounded = _Bounded(conn, HANDSHAKE_S)
    try:
        deliver_challenge(bounded, key)  # type: ignore[arg-type]
        answer_challenge(bounded, key)  # type: ignore[arg-type]
        return True
    except Exception as error:
        _log.warning(f"API: a connection was refused ({type(error).__name__})")
        return False


def endpoint_path() -> Path:
    """<user folder>/api/endpoint.json: the fixed Gremlin Platforms folder in
    the user's profile (where configuration.json is), so gremlin-ctl finds
    it without reading the settings."""
    from gremlin import util

    return Path(util.userprofile_path()) / ENDPOINT_FOLDER / ENDPOINT_NAME


def _write_endpoint(address: str, key: bytes) -> None:
    path = endpoint_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(
        {
            "address": address,
            "key": key.hex(),
            "version": PROTOCOL_VERSION,
            "pid": os.getpid(),
        }
    )
    temp = path.with_name(path.name + ".tmp")
    try:
        temp.unlink()
    except FileNotFoundError:
        pass
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(text)
    os.replace(temp, path)


def _remove_endpoint() -> None:
    try:
        endpoint_path().unlink()
    except FileNotFoundError:
        pass
    except OSError:
        _log.warning("API: endpoint.json could not be removed", exc_info=True)


class _Server:
    """One open pipe: its accept thread and the connections it serves."""

    def __init__(self, factory: ListenerFactory, handshake: Handshake) -> None:
        self.address = PIPE_PREFIX + secrets.token_hex(16)
        self.key = secrets.token_bytes(32)
        self._handshake = handshake
        self._listener = factory(self.address)
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._conns: set[Any] = set()

    def start(self) -> None:
        threads.start("Control API", self._accept_loop, stop=self.close)

    def _accept_loop(self) -> None:
        while not self._stop.is_set():
            try:
                conn = self._listener.accept()
            except Exception:
                if not self._stop.is_set():
                    _log.warning("API: the pipe stopped listening", exc_info=True)
                return
            if self._stop.is_set():
                _close(conn)
                return
            with self._lock:
                full = len(self._conns) >= MAX_CONNECTIONS
                if not full:
                    self._conns.add(conn)
            if full:
                _log.warning("API: a connection was refused (too many at once)")
                _close(conn)
                continue
            threads.start(
                "Control API connection",
                self._serve,
                conn,
                stop=lambda c=conn: _close(c),
            )

    def _serve(self, conn: Any) -> None:  # noqa: ANN401
        try:
            if not self._handshake(conn, self.key):
                return
            idle_from = clock.monotonic()
            while not self._stop.is_set():
                if not conn.poll(POLL_S):
                    if clock.monotonic() - idle_from > IDLE_S:
                        return
                    continue
                # No maxlength: past it multiprocessing closes the pipe
                # unanswered; handle_bytes answers "too_large" instead (S9).
                data = conn.recv_bytes()
                if self._stop.is_set():
                    return
                conn.send_bytes(handle_bytes(data))
                idle_from = clock.monotonic()
        except (EOFError, OSError, TimeoutError):
            pass  # the client went away or stopped answering
        except Exception:
            _log.exception("API: a connection failed")
        finally:
            with self._lock:
                self._conns.discard(conn)
            _close(conn)

    def close(self) -> None:
        """Asks everything to end; returns at once."""
        self._stop.set()
        try:
            self._listener.close()
        except Exception:
            pass
        with self._lock:
            conns = list(self._conns)
        for conn in conns:
            _close(conn)


def _close(conn: Any) -> None:  # noqa: ANN401
    try:
        conn.close()
    except Exception:
        pass


_state_lock = threading.RLock()
_server: _Server | None = None
_started = False
_watching = False
_factory: ListenerFactory | None = None
_handshake_fn: Handshake | None = None


def start(
    listener_factory: ListenerFactory | None = None,
    handshake: Handshake | None = None,
) -> None:
    """At program start: the pipe opens while the switch is on, and follows
    it (Options, History Restore) until stop()."""
    global _started, _watching, _factory, _handshake_fn
    with _state_lock:
        _started = True
        _factory = listener_factory
        _handshake_fn = handshake
        if not _watching:
            try:
                from gremlin.signal import signal

                signal.configChanged.connect(apply)
                _watching = True
            except Exception:
                _log.exception("API: the switch can't be followed")
    apply()


def apply() -> None:
    """Opens or closes the pipe to match the switch."""
    with _state_lock:
        want = _started and allowed()
        if want and _server is None:
            _open()
        elif not want and _server is not None:
            _close_server()
        elif not want:
            _remove_endpoint()  # one left by a program that ended badly


def _open() -> None:
    global _server
    try:
        server = _Server(_factory or _PipeListener, _handshake_fn or _handshake)
    except Exception:
        _log.exception("API: the pipe could not open")
        return
    try:
        _write_endpoint(server.address, server.key)
    except Exception:
        _log.exception("API: endpoint.json could not be written")
        server.close()
        return
    _server = server
    server.start()
    _log.warning("API: control from other programs is on (pipe open)")


def _close_server() -> None:
    global _server
    server, _server = _server, None
    if server is not None:
        server.close()
        _log.warning("API: control from other programs is off (pipe closed)")
    _remove_endpoint()


def stop() -> None:
    """At quit: the pipe closes and endpoint.json goes."""
    global _started, _watching
    with _state_lock:
        _started = False
        if _watching:
            try:
                from gremlin.signal import signal

                signal.configChanged.disconnect(apply)
            except Exception:
                pass
            _watching = False
        _close_server()


def running() -> bool:
    """The pipe is open."""
    with _state_lock:
        return _server is not None


def address() -> str:
    """The open pipe's address ("" when closed)."""
    with _state_lock:
        return _server.address if _server is not None else ""


def attach_ui() -> None:
    """Once the window exists: the calls of the menu command bridge
    (Backend.register_api_calls) and of the windows
    (gremlin.ui.control_windows.register_api_calls) join. Either missing
    is logged; the rest still works."""
    me = sys.modules[__name__]
    instance = None
    try:
        from gremlin.ui import backend

        instance = getattr(backend.Backend, "instance", None)
        hook = getattr(instance, "register_api_calls", None)
        if hook is None:
            hook = getattr(backend, "register_api_calls", None)
        if hook is None:
            _log.warning("API: the menu command calls are not there")
        else:
            hook(me)
    except Exception:
        _log.exception("API: the menu command calls could not join")
    try:
        from gremlin.ui import control_windows

        control_windows.register_api_calls(me, backend=instance)
    except Exception:
        _log.exception("API: the window calls could not join")


# --- History: marked "by API" ------------------------------------------------------


BY_API = "(by API)"


def _by_api(title: str, area: str, work: Callable[[], Any]) -> Any:  # noqa: ANN401
    """Runs work inside a History group titled title + " (by API)" with
    {"by": "api"} on the entry, so the change it records shows in Tools ›
    History as made by the API (one change: its own entry, retitled)."""
    from gremlin import history

    token = history.begin_group(f"{title} {BY_API}", area=area, extra={"by": "api"})
    try:
        return work()
    finally:
        history.end_group(token)


# --- the calls owned here ------------------------------------------------------------


def _backend() -> Any:  # noqa: ANN401 - gremlin.ui.backend.Backend
    from gremlin.ui import backend

    instance = backend.Backend.instance
    if instance is None:
        raise CallError("The program's window isn't ready yet.", "not_ready")
    return instance


def _hello(_args: dict) -> dict:
    from gremlin import util

    return {"version": PROTOCOL_VERSION, "program_version": util.get_code_version()}


def _help(_args: dict) -> list[dict]:
    return calls()


def _run_state(backend: Any) -> str:  # noqa: ANN401
    if backend.gremlinStarting:
        return "starting"
    return "running" if backend.gremlinActive else "stopped"


def _guarded(read: Callable[[], Any]) -> Any:  # noqa: ANN401
    try:
        return read()
    except Exception:
        _log.exception("API: a state value could not be read")
        return None


def _screen_saver_state() -> dict | None:
    """Screen Saver Mode's status, when its module is loaded (nothing is
    started to answer)."""
    module = sys.modules.get("gremlin.screen_saver_mode")
    if module is None:
        return None
    status = module.manager().status()
    return dataclasses.asdict(status)


def _state(_args: dict) -> dict:
    from gremlin import health, trace, util

    backend = _backend()
    return {
        "version": util.get_code_version(),
        "api_version": PROTOCOL_VERSION,
        "profile": _guarded(backend.profilePath),
        "profile_name": _guarded(lambda: backend.windowTitle),
        "unsaved": _guarded(lambda: bool(backend.profileContainsUnsavedChanges)),
        "run": _guarded(lambda: _run_state(backend)),
        "mode": _guarded(lambda: backend.currentMode),
        "tracing": trace.enabled(),
        "health": _guarded(health.broken_count),
        "screen_saver_mode": _guarded(_screen_saver_state),
    }


def _device_id(value: object) -> str:
    """A device id in the Library's form (store.guid_text of a uuid: lower
    case, dashes, no braces), whether DILL's upper-case GUID text or a
    stored one ("" for none; text that isn't a GUID as it is)."""
    from gremlin.modules import store

    text = store.guid_text(value)
    try:
        return str(uuid.UUID(text)) if text else ""
    except ValueError:
        return text


def _devices(_args: dict) -> list[dict]:
    """The devices plugged in now, then the other hardware the program knows
    (the open profile's, saved module files: store.known_devices()), each
    once with plugged_in (S3, S21). Known rows without a device id and the
    built-in devices (Keyboard, OSC, Logical Device, vJoy and Xbox outputs:
    device_class) are not devices here. An unplugged one's counts are None."""
    from gremlin import device_initialization
    from gremlin.modules import device_class, store

    found = []
    plugged: set[str] = set()
    for dev in device_initialization.joystick_devices():
        try:
            guid = _device_id(dev.device_guid)
            row = {
                "name": dev.name,
                "label": dev.name,
                "guid": guid,
                "virtual": bool(dev.is_virtual),
                "vjoy_id": dev.vjoy_id if dev.is_virtual else None,
                "axes": dev.axis_count,
                "buttons": dev.button_count,
                "hats": dev.hat_count,
                "plugged_in": True,
            }
            plugged.add(store.stored_guid_key(guid))
        except Exception:
            # One device that can't be read is left out, not the answer.
            _log.exception("API: a plugged-in device could not be read")
            continue
        found.append(row)
    try:
        known = store.known_devices()
    except Exception:
        _log.exception("API: the known devices could not be read")
        known = []
    for row in known:
        try:
            guid = _device_id(row.get("guid"))
            key = store.stored_guid_key(guid)
            if row.get("connected") or not key or key in plugged:
                continue
            name = str(row.get("name") or "")
            if not device_class.can("library_device", guid, name):
                continue
        except Exception:
            _log.exception("API: a known device could not be read")
            continue
        plugged.add(key)
        found.append(
            {
                "name": row.get("name") or "",
                "label": row.get("label") or row.get("name") or "",
                "guid": guid,
                "virtual": None,
                "vjoy_id": None,
                "axes": None,
                "buttons": None,
                "hats": None,
                "plugged_in": False,
            }
        )
    return found


class _RunWaiter:
    """One Run or Stop answer: set on the main thread by Backend's
    runStartHandled / runStopHandled (its state already updated)."""

    def __init__(self) -> None:
        self.done = threading.Event()
        self.ok = True
        self.error = ""

    def started(self, ok: bool, error: str) -> None:
        self.ok = bool(ok)
        self.error = str(error or "")
        self.done.set()

    def stopped(self) -> None:
        self.done.set()


def _run_send(backend: Any, run: bool) -> tuple[bool, str]:  # noqa: ANN401
    """On the main thread: asks for the Run (True) or Stop. Returns (done,
    state): done when nothing is left to wait for (already in the wanted
    state, or inline, where the Run finished on this thread)."""
    from gremlin import input_thread

    state = _run_state(backend)
    if state == ("running" if run else "stopped"):
        return True, state
    if not (run and state == "starting"):
        # A Run already on its way isn't asked for again: its answer follows.
        backend.activate_gremlin(run)
    if not input_thread.is_running() or input_thread.is_inline():
        return True, _run_state(backend)
    return False, state


RUN_HEADING = "Could not run the profile"


def _run_last_error(backend: Any) -> str:  # noqa: ANN401
    runner = getattr(backend, "runner", None)
    return str(getattr(runner, "last_error", "") or "")


def _run_failed(reason: str) -> CallError:
    """A Run that didn't start, under the heading the program shows
    (code_runner's error box): "Could not run the profile: <reason>."."""
    reason = str(reason or "").strip()
    if reason.startswith(RUN_HEADING):
        text = reason
    elif reason:
        text = f"{RUN_HEADING}: {reason}"
    else:
        text = f"{RUN_HEADING}."
    if not text.endswith("."):
        text += "."
    return CallError(text, "failed")


def _run_late(run: bool) -> CallError:
    word = "start" if run else "stop"
    return CallError(f"The Run didn't {word} within {RUN_WAIT_S:g} s.", "timeout")


def _run_set(run: bool) -> dict:
    """run.start / run.stop on the listener thread: the request goes to the
    main thread, the wait for its answer stays here (D-13-RUN-WAIT)."""
    from PySide6 import QtCore

    backend = _backend()
    # One limit for the busy wait and the Run's answer (S9, S24).
    limit = min(float(RUN_WAIT_S), time_left(RUN_WAIT_S))
    deadline = clock.monotonic() + limit
    waiter = _RunWaiter()
    # Armed before the request, so the answer can't come first; direct: the
    # slot only sets an Event, on the thread that emits (the main thread).
    answered = backend.runStartHandled if run else backend.runStopHandled
    slot = waiter.started if run else waiter.stopped
    answered.connect(slot, QtCore.Qt.ConnectionType.DirectConnection)
    try:
        try:
            done, state = threads.main_call_wait(_run_send, backend, run, timeout=limit)
        except TimeoutError:
            raise _run_late(run) from None
        if done:
            if run and state != "running":
                raise _run_failed(_run_last_error(backend))
            return {"run": state}
        if not waiter.done.wait(max(0.0, deadline - clock.monotonic())):
            raise _run_late(run)
        if run and not waiter.ok:
            raise _run_failed(waiter.error)
        return {"run": "running" if run else "stopped"}
    finally:
        try:
            answered.disconnect(slot)
        except (RuntimeError, TypeError):
            pass


def _run_start(_args: dict) -> dict:
    return _run_set(True)


def _run_stop(_args: dict) -> dict:
    return _run_set(False)


def _problem(backend: Any, name: str) -> str:  # noqa: ANN401
    """Backend's reason for the last load or save failing ("" if none)."""
    try:
        return str(getattr(backend, name, lambda: "")() or "").strip().rstrip(".")
    except Exception:
        _log.exception(f"API: {name} could not be read")
        return ""


def _profile_load(args: dict) -> dict:
    from gremlin import util

    path = args["path"]
    if not os.path.isabs(path):
        raise CallError("Give the full path.", "bad_args")
    path = os.path.normpath(path)
    if not os.path.isfile(path):
        raise CallError(f"No profile file '{path}'.", "not_found")
    backend = _backend()
    if backend.profileContainsUnsavedChanges:
        raise CallError(
            "The open profile has unsaved changes, so save or discard them in "
            "the program first.",
            "not_ready",
        )
    before = str(backend.profilePath() or "")
    backend.loadProfile(path)
    now = str(backend.profilePath() or "")
    if not util.same_path(now, path):
        reason = _problem(backend, "last_load_problem")
        text = f"The profile '{path}' didn't open"
        if reason:
            text += f": {reason}"
        if before and util.same_path(now, before):
            text += f"; '{before}' is still open."
        elif now:
            text += f"; '{now}' is open instead."
        else:
            text += "; a new, empty profile is open instead."
        raise CallError(text, "failed")
    return {"profile": path}


def _profile_save(_args: dict) -> dict:
    backend = _backend()
    path = backend.profilePath()
    if not path:
        raise CallError(
            "The open profile has no file yet, so save it in the program first "
            "(File › Save As).",
            "not_ready",
        )
    # Not grouped in History: a profile save is several entries (each
    # input, the whole-profile copy), which a group would fold into one;
    # made_by marks each of them "(by API)" instead (decision 3a).
    from gremlin import history

    with history.made_by("api"):
        saved = backend.saveProfile(path)
    if not saved:
        reason = _problem(backend, "last_save_problem") or _problem(
            backend, "saveProblem"
        )
        raise CallError(
            f"The profile was not saved: {reason}."
            if reason
            else "The profile was not saved.",
            "failed",
        )
    return {"profile": path, "saved": True}


def _parse_key(args: dict) -> tuple[str, str, str]:
    key = args["key"]
    parts = tuple(key.split("/"))
    if len(parts) != 3 or not all(parts):
        raise CallError(
            'A setting key is "section/group/name" (options.list lists them).',
            "bad_args",
        )
    if parts not in _option_keys():
        raise CallError(
            f"No Options setting '{key}' (options.list lists them).", "not_found"
        )
    return parts  # type: ignore[return-value]


def _option_keys() -> dict[tuple[str, str, str], tuple[str, str]]:
    """The settings Options shows that are stored settings: key ->
    (sidebar section, group title)."""
    from gremlin.config import Configuration
    from gremlin.ui import option

    cfg = Configuration()
    found = {}
    for section, groups in option.main_layout():
        for group, keys in groups:
            for key in keys:
                if cfg.exists(*key):
                    found[key] = (section, group)
    return found


def _describe(key: tuple[str, str, str], where: tuple[str, str]) -> dict:
    from gremlin.config import Configuration
    from gremlin.types import PropertyType
    from gremlin.ui import option

    cfg = Configuration()
    data_type = cfg.data_type(*key)
    item = {
        "key": "/".join(key),
        "title": option.entry_title(key[2], "/".join(key)),
        "section": where[0],
        "group": where[1],
        "type": PropertyType.to_string(data_type),
        "value": option.shown_setting(key),
        "description": cfg.description(*key),
    }
    props = cfg.properties(*key) or {}
    if data_type == PropertyType.Selection:
        item["choices"] = [
            option.shown_choice(key, v) for v in props.get("valid_options", [])
        ]
    for limit in ("min", "max"):
        if limit in props:
            item[limit] = props[limit]
    return item


def _options_list(_args: dict) -> list[dict]:
    return [_describe(key, where) for key, where in _option_keys().items()]


def _option_get(args: dict) -> dict:
    key = _parse_key(args)
    return _describe(key, _option_keys()[key])


_TRUE = {"true", "on", "yes", "1"}
_FALSE = {"false", "off", "no", "0"}


def _converted(key: tuple[str, str, str], value: Any) -> Any:  # noqa: ANN401
    """value (often text from the command line) as the setting's type;
    CallError "bad_args" naming the setting when it isn't one."""
    from gremlin.config import Configuration
    from gremlin.types import PropertyType
    from gremlin.ui import option

    cfg = Configuration()
    data_type = cfg.data_type(*key)
    props = cfg.properties(*key) or {}
    title = option.entry_title(key[2], "/".join(key))

    def refuse(what: str) -> CallError:
        return CallError(f"'{title}' is {what}.", "bad_args")

    if data_type == PropertyType.Bool:
        if isinstance(value, bool):
            return value
        text = str(value).strip().lower() if isinstance(value, (str, int)) else ""
        if text in _TRUE:
            return True
        if text in _FALSE:
            return False
        raise refuse("on or off: true or false")
    if data_type in (PropertyType.Int, PropertyType.Float):
        whole = data_type == PropertyType.Int
        word = "a whole number" if whole else "a number"
        try:
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValueError
            number = float(value.strip()) if isinstance(value, str) else float(value)
        except ValueError:
            raise refuse(word) from None
        if not math.isfinite(number) or (whole and not number.is_integer()):
            raise refuse(word)
        result = int(number) if whole else number
        low, high = props.get("min"), props.get("max")
        if (low is not None and result < low) or (high is not None and result > high):
            if low is not None and high is not None:
                raise refuse(f"from {low} to {high}")
            raise refuse(f"at least {low}" if low is not None else f"at most {high}")
        return result
    if data_type == PropertyType.Selection:
        if not isinstance(value, str):
            raise refuse("text")
        choices = [option.shown_choice(key, v) for v in props.get("valid_options", [])]
        if choices and value not in choices:
            raise refuse("one of: " + ", ".join(map(str, choices)))
        return value
    if data_type in (PropertyType.String, PropertyType.Path):
        if not isinstance(value, str):
            raise refuse("text")
        return value
    raise CallError(f"'{title}' is changed in Options only.", "refused")


def _option_set(args: dict) -> dict:
    from gremlin.config import settings_history_title
    from gremlin.ui import option

    key = _parse_key(args)
    if key == SWITCH_KEY:
        raise CallError(SWITCH_REFUSED_TEXT, "refused")
    value = _converted(key, args["value"])
    title = settings_history_title(["/".join(key)])
    done = _by_api(title, "settings", lambda: option.change_setting(key, value))
    if not done:
        raise CallError("The setting was not changed (Windows kept its own).", "failed")
    return _describe(key, _option_keys()[key])


def _trace_categories() -> dict[str, tuple[Callable[[], bool], Callable[[bool], None]]]:
    """The Trace tab's rows that aren't devices, as trace.categories() lists
    them: name -> (ticked, set)."""
    from gremlin import trace

    return {c.name: (c.ticked, c.set) for c in trace.categories()}


def _trace_switch(args: dict, on: bool) -> dict:
    from gremlin import trace

    category = args.get("category") or ""
    if not category:
        trace.set_enabled(on)
    else:
        found = _trace_categories()
        if category not in found:
            raise CallError(
                f"No trace category '{category}' (one of: " + ", ".join(found) + ").",
                "bad_args",
            )
        found[category][1](on)
    return _trace_status({})


def _trace_on(args: dict) -> dict:
    return _trace_switch(args, True)


def _trace_off(args: dict) -> dict:
    return _trace_switch(args, False)


def _trace_status(_args: dict) -> dict:
    from gremlin import trace

    return {
        "tracing": trace.enabled(),
        "categories": {
            name: bool(ticked()) for name, (ticked, _s) in _trace_categories().items()
        },
        "file": str(trace.file_path()),
    }


def _tail(path: Path, count: int) -> list[str]:
    """The last count lines of a text file (only its end is read)."""
    if not path.is_file():
        return []
    size = path.stat().st_size
    chunk = min(size, max(64 * 1024, count * 400))
    with open(path, "rb") as fh:
        fh.seek(size - chunk)
        text = fh.read().decode("utf-8", errors="replace")
    lines = text.splitlines()
    if chunk < size:
        lines = lines[1:]  # the first may be cut
    return lines[-count:] if count else []


def _log_lines(args: dict) -> dict:
    from gremlin import trace, util

    # which and lines are checked by their Arg (choices, 1 to LOG_LINES_MAX).
    which = args.get("which", "system")
    count = args.get("lines", 50)
    if which == "system":
        path = Path(util.logs_dir()) / "system.log"
    else:
        path = Path(trace.file_path())
    return {"file": str(path), "lines": _tail(path, count)}


def _register_own() -> None:
    register("hello", _hello, summary="The API and program versions.")
    register("help", _help, summary="Every call with its arguments.")
    register(
        "state",
        _state,
        main_thread=True,
        summary="Version, profile, Run state, mode, tracing, Health count, "
        "Screen Saver Mode.",
    )
    register(
        "devices", _devices, main_thread=True, summary="Devices, plugged in or not."
    )
    # Off the main thread: only the request goes there; the answer is
    # waited for here (RUN_WAIT_S).
    register("run.start", _run_start, summary="Runs the open profile.")
    register("run.stop", _run_stop, summary="Stops the Run.")
    register(
        "profile.load",
        _profile_load,
        main_thread=True,
        timeout_s=LONG_TIMEOUT_S,
        summary="Opens a profile file {path}.",
        args={"path": Arg("str", required=True, help="The profile file's full path.")},
    )
    register(
        "profile.save",
        _profile_save,
        main_thread=True,
        timeout_s=LONG_TIMEOUT_S,
        summary="Saves the open profile to its file.",
    )
    key = Arg(
        "str",
        required=True,
        help='The setting\'s key "section/group/name" (options.list lists them).',
    )
    register(
        "option.get",
        _option_get,
        main_thread=True,
        summary="Reads one Options setting {key}.",
        args={"key": key},
    )
    register(
        "option.set",
        _option_set,
        main_thread=True,
        summary="Changes an Options setting {key, value}.",
        args={
            "key": key,
            "value": Arg("any", required=True, help="The new value."),
        },
    )
    register(
        "options.list",
        _options_list,
        main_thread=True,
        summary="Lists every Options setting.",
    )
    category = Arg(
        "str", help="One category (trace.status lists them); none: all of tracing."
    )
    register(
        "trace.on",
        _trace_on,
        main_thread=True,
        summary="Turns tracing on, or one category {category}.",
        args={"category": category},
    )
    register(
        "trace.off",
        _trace_off,
        main_thread=True,
        summary="Turns tracing off, or one category {category}.",
        args={"category": category},
    )
    register(
        "trace.status",
        _trace_status,
        main_thread=True,
        summary="Tracing and its categories.",
    )
    register(
        "log",
        _log_lines,
        summary="The last lines of a log {which, lines}.",
        args={
            "which": Arg(
                "str", help="The system or trace log.", choices=("system", "trace")
            ),
            "lines": Arg(
                "int",
                help="How many lines (50 if not given).",
                min=1,
                max=LOG_LINES_MAX,
            ),
        },
    )


_register_own()
