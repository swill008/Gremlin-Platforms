# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Disabling the devices that never go quiet (Screen Saver Mode S21-S27).

Gremlin never runs elevated: Gremlin Device Helper does the disabling and
enabling (S25). Gremlin listens on a private pipe, starts the helper with
Windows' administrator confirmation, and sends it requests. Every step is
written to the journal (S22) BEFORE the request, and after it the real
Windows status is read back (no admin needed) and written. Only ids the
journal lists are ever enabled; a device someone else disabled is never
touched.

All the Windows work runs on one program thread, one job at a time, so a
re-enable always comes after the disable it undoes. Three seams keep tests
away from Windows: the elevation launcher, the pipe listener and the status
reader; the real ones refuse to run under pytest.
"""

from __future__ import annotations

import ctypes
import datetime
import json
import logging
import os
import queue
import secrets
import sys
import threading
from collections.abc import Callable
from typing import Any, Protocol

from gremlin import clock, threads, trace, util
from gremlin import device_helper_protocol as protocol

FOLDER_NAME = "screen saver mode"
JOURNAL_NAME = "devices.json"
KEY_NAME = "helper.key"
HELPER_EXE = "Gremlin Device Helper.exe"
HELPER_SCRIPT = "gremlin_device_helper.py"

ERROR_CANCELLED = 1223
CONNECT_TIMEOUT_S = 60.0
PING_TIMEOUT_S = 10.0
# The helper runs pnputil bounded 30 s per device.
PER_DEVICE_TIMEOUT_S = 30.0
ANSWER_SLACK_S = 10.0

ENABLED, DISABLED, NOT_PRESENT = "enabled", "disabled", "not present"
TO_BE_DISABLED, DISABLE_FAILED = "to be disabled", "disable failed"
TO_BE_ENABLED, ENABLE_FAILED = "to be enabled", "enable failed"
# pnputil's answers that Windows will only act at the next restart (S34).
RESTART_EXIT = "pnputil exit 3010"
PENDING_REBOOT = "pending system reboot"
RESTART_UNDONE = "Windows wanted a restart, undone"

HELPER_NOT_RUNNING_TEXT = "Devices can't be disabled: the helper isn't running"
REFUSED_TEXT = "Administrator rights were refused."
NO_CONNECTION_TEXT = "The helper did not connect in time."
HELPER_ENDED_TEXT = "The helper ended before it connected."

_log = logging.getLogger("system")


class Refused(Exception):
    """The administrator confirmation was declined (Windows error 1223)."""


class RealCallBlocked(RuntimeError):
    """A real Windows call (elevation, pipe, device status) from a test."""


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


def _trace(text: str) -> None:
    """One Screen Saver Mode trace line; never raises."""
    try:
        write = getattr(trace, "screen_saver", None)
        if write is not None:
            write(text)
    except Exception:
        pass


def _now_text() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def folder() -> str:
    return os.path.join(util.data_folder(), FOLDER_NAME)


def journal_path() -> str:
    return os.path.join(folder(), JOURNAL_NAME)


def key_path() -> str:
    return os.path.join(folder(), KEY_NAME)


# The journal (S22) ----------------------------------------------------------


class Journal:
    """devices.json: {id: {"name", "state", "time", "result"}}, the same
    entries the helper checks requests against. Saved whole, atomically:
    a temporary file next to it, then swapped in with os.replace."""

    def __init__(self, path: str | None = None) -> None:
        self.path = path or journal_path()
        self.entries: dict[str, dict[str, str]] = {}

    def load(self) -> Journal:
        try:
            with open(self.path, encoding="utf-8") as fh:
                data = json.load(fh)
        except FileNotFoundError:
            data = {}
        except (OSError, ValueError) as error:
            # Keep the unreadable file for a person to look at.
            bad = self.path + ".bad"
            _log.warning(
                "Screen Saver Mode: device journal unreadable (%s), kept as %s",
                error,
                bad,
            )
            try:
                os.replace(self.path, bad)
            except OSError:
                pass
            data = {}
        self.entries = {
            str(k): {f: str(v.get(f, "")) for f in ("name", "state", "time", "result")}
            for k, v in (data.items() if isinstance(data, dict) else [])
            if isinstance(v, dict)
        }
        return self

    def save(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        temp = self.path + ".tmp"
        with open(temp, "w", encoding="utf-8") as fh:
            json.dump(self.entries, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(temp, self.path)

    def state(self, device_id: str) -> str:
        return self.entries.get(device_id, {}).get("state", "")

    def set(self, device_id: str, name: str, state: str, result: str = "") -> None:
        if state not in protocol.STATES:
            raise ValueError(f"not a journal state: {state!r}")
        old = self.entries.get(device_id, {})
        self.entries[device_id] = {
            "name": name or old.get("name", ""),
            "state": state,
            "time": _now_text(),
            "result": result,
        }

    def not_enabled(self) -> list[str]:
        return [i for i, e in self.entries.items() if e.get("state") != ENABLED]


# The device status (no admin) ----------------------------------------------

StatusReader = Callable[[str], str]


def device_status(device_id: str) -> str:
    """ "enabled" | "disabled" | "not present", read from Windows'
    configuration manager (CM_Locate_DevNodeW, CM_Get_DevNode_Status and
    the ConfigFlags property). A device whose disabled flag is set counts
    as disabled even while it still runs: Windows set the flag but waits
    for a restart to stop it (S34)."""
    if _under_test():
        raise RealCallBlocked("device_disable.device_status called from a test")
    from ctypes import wintypes

    CR_SUCCESS = 0
    DN_HAS_PROBLEM = 0x00000400
    CM_PROB_DISABLED = 22
    CM_DRP_CONFIGFLAGS = 0x0A
    CONFIGFLAG_DISABLED = 0x00000001
    cfg = ctypes.WinDLL("cfgmgr32")
    cfg.CM_Locate_DevNodeW.argtypes = [
        ctypes.POINTER(wintypes.DWORD),
        wintypes.LPCWSTR,
        wintypes.ULONG,
    ]
    cfg.CM_Locate_DevNodeW.restype = wintypes.DWORD
    cfg.CM_Get_DevNode_Status.argtypes = [
        ctypes.POINTER(wintypes.ULONG),
        ctypes.POINTER(wintypes.ULONG),
        wintypes.DWORD,
        wintypes.ULONG,
    ]
    cfg.CM_Get_DevNode_Status.restype = wintypes.DWORD
    cfg.CM_Get_DevNode_Registry_PropertyW.argtypes = [
        wintypes.DWORD,
        wintypes.ULONG,
        ctypes.POINTER(wintypes.ULONG),
        ctypes.c_void_p,
        ctypes.POINTER(wintypes.ULONG),
        wintypes.ULONG,
    ]
    cfg.CM_Get_DevNode_Registry_PropertyW.restype = wintypes.DWORD
    devinst = wintypes.DWORD()
    # CM_LOCATE_DEVNODE_NORMAL finds present devices only.
    if cfg.CM_Locate_DevNodeW(ctypes.byref(devinst), device_id, 0) != CR_SUCCESS:
        return NOT_PRESENT
    status, problem = wintypes.ULONG(), wintypes.ULONG()
    result = cfg.CM_Get_DevNode_Status(
        ctypes.byref(status), ctypes.byref(problem), devinst, 0
    )
    if result != CR_SUCCESS:
        return NOT_PRESENT
    if status.value & DN_HAS_PROBLEM and problem.value == CM_PROB_DISABLED:
        return DISABLED
    flags = wintypes.ULONG()
    size = wintypes.ULONG(ctypes.sizeof(flags))
    result = cfg.CM_Get_DevNode_Registry_PropertyW(
        devinst,
        CM_DRP_CONFIGFLAGS,
        None,
        ctypes.byref(flags),
        ctypes.byref(size),
        0,
    )
    # No ConfigFlags value (CR_NO_SUCH_VALUE) means no flag is set.
    if result == CR_SUCCESS and flags.value & CONFIGFLAG_DISABLED:
        return DISABLED
    return ENABLED


# The seams -----------------------------------------------------------------


class Connection(Protocol):
    def send(self, obj: object) -> None: ...
    def recv(self) -> object: ...
    def poll(self, timeout: float = 0.0) -> bool: ...
    def close(self) -> None: ...


class Listener(Protocol):
    def accept(self) -> Connection: ...
    def close(self) -> None: ...


class Process(Protocol):
    def running(self) -> bool: ...
    def close(self) -> None: ...


Launcher = Callable[[str, str], Process]
ListenerFactory = Callable[[str, bytes], Listener]


def helper_command(pipe: str, journal: str, key: str) -> tuple[str, str]:
    """(file, parameters) of the helper: the exe next to the program when
    frozen, else this Python running gremlin_device_helper.py. pipe is the
    pipe's name after PIPE_PREFIX."""
    args = f'--pipe "{pipe}" --journal "{journal}" --key "{key}" --parent {os.getpid()}'
    if getattr(sys, "frozen", False):
        return os.path.join(os.path.dirname(sys.executable), HELPER_EXE), args
    script = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), HELPER_SCRIPT
    )
    return sys.executable, f'"{script}" {args}'


class _ElevatedProcess:
    def __init__(self, handle: int) -> None:
        self._handle = handle

    def running(self) -> bool:
        if not self._handle:
            return True  # Windows gave no handle; rely on the connection wait
        k32 = ctypes.WinDLL("kernel32")
        k32.WaitForSingleObject.restype = ctypes.c_ulong
        return k32.WaitForSingleObject(ctypes.c_void_p(self._handle), 0) != 0

    def close(self) -> None:
        if self._handle:
            ctypes.WinDLL("kernel32").CloseHandle(ctypes.c_void_p(self._handle))
            self._handle = 0


def _real_launcher(file: str, parameters: str) -> Process:
    """ShellExecuteExW "runas" of the helper, hidden; does not wait."""
    if _under_test():
        raise RealCallBlocked("device_disable elevation called from a test")
    from gremlin.power_requests import SHELLEXECUTEINFOW

    SEE_MASK_NOCLOSEPROCESS = 0x00000040
    SEE_MASK_NO_CONSOLE = 0x00008000
    SW_HIDE = 0
    shell = ctypes.WinDLL("shell32", use_last_error=True)
    shell.ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]
    shell.ShellExecuteExW.restype = ctypes.c_int
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NO_CONSOLE
    info.lpVerb = "runas"
    info.lpFile = file
    info.lpParameters = parameters
    info.lpDirectory = os.path.dirname(file) or None
    info.nShow = SW_HIDE
    if not shell.ShellExecuteExW(ctypes.byref(info)):
        error = ctypes.get_last_error()
        if error == ERROR_CANCELLED:
            raise Refused()
        raise OSError(error, "ShellExecuteExW failed")
    return _ElevatedProcess(info.hProcess or 0)


class _PipeListener:
    """multiprocessing.connection.Listener on a named pipe. close() wakes a
    waiting accept() (it waits without a limit) by connecting to it, without
    the key handshake, and only while accept() waits: once the helper is
    connected nothing would answer a handshake, and quitting hung on it
    (found on the user's PC 2026-11-16)."""

    def __init__(self, address: str, authkey: bytes) -> None:
        if _under_test():
            raise RealCallBlocked("device_disable pipe listener called from a test")
        from multiprocessing.connection import Listener as MpListener

        self._address = address
        self._authkey = authkey
        self._listener = MpListener(address, family="AF_PIPE", authkey=authkey)
        self._closed = False
        self._accepting = False

    def accept(self) -> Connection:
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

                # No authkey: no handshake to wait for; the waiting accept()
                # fails its own handshake and returns.
                Client(self._address, family="AF_PIPE").close()
            except Exception:
                pass
        try:
            self._listener.close()
        except Exception:
            pass


# The disabler --------------------------------------------------------------


class DeviceDisabler:
    """The helper's connection and the disable/enable flows."""

    def __init__(
        self,
        journal_file: str | None = None,
        key_file: str | None = None,
        launcher: Launcher | None = None,
        listener_factory: ListenerFactory | None = None,
        status_reader: StatusReader | None = None,
        connect_timeout_s: float = CONNECT_TIMEOUT_S,
    ) -> None:
        self._journal_file = journal_file
        self._key_file = key_file
        self._launcher = launcher or _real_launcher
        self._listener_factory = listener_factory or _PipeListener
        self._status = status_reader or device_status
        self._connect_timeout_s = connect_timeout_s
        self._lock = threading.RLock()
        self._conn: Connection | None = None
        self._listener: Listener | None = None
        self._process: Process | None = None
        self._starting = False
        self._wanted = False
        self._error = ""
        self._callbacks: list[Callable[[bool, str], None]] = []
        self._jobs: queue.Queue[tuple[str, Callable[[], None]]] = queue.Queue()
        self._queued: set[str] = set()
        self._worker: threading.Thread | None = None
        self._busy = 0
        self._idle = threading.Event()
        self._idle.set()

    # Paths ---------------------------------------------------------------

    def journal(self) -> Journal:
        return Journal(self._journal_file or journal_path()).load()

    def _key(self) -> str:
        return self._key_file or key_path()

    # The helper ------------------------------------------------------------

    def helper_running(self) -> bool:
        with self._lock:
            return self._conn is not None

    def status_text(self) -> str:
        """ "" when fine; the S26 text when the helper should run but isn't."""
        with self._lock:
            if not self._wanted or self._conn is not None or self._starting:
                return ""
            if self._error:
                return f"{HELPER_NOT_RUNNING_TEXT}. {self._error}"
            return HELPER_NOT_RUNNING_TEXT

    def start_helper(self, on_done: Callable[[bool, str], None]) -> None:
        """Starts the helper elevated and waits (on a program thread, up to
        60 s, while the user answers Windows' confirmation) for it to
        connect; on_done(ok, error text) is called from that thread."""
        with self._lock:
            self._wanted = True
            if self._conn is not None:
                running = True
            else:
                running = False
                self._callbacks.append(on_done)
                if self._starting:
                    return
                self._starting = True
                self._error = ""
        if running:
            _call(on_done, True, "")
            return
        threads.start("Device helper start", self._start)

    def _start(self) -> None:
        ok, error = False, ""
        try:
            ok, error = self._connect()
        except Exception as exc:  # never leave _starting set
            _log.exception("Screen Saver Mode: device helper start failed")
            ok, error = False, f"The helper could not start ({exc})."
        with self._lock:
            self._starting = False
            self._error = "" if ok else error
            callbacks, self._callbacks = self._callbacks, []
        if ok:
            _log.info("Screen Saver Mode: device helper running")
            _trace("Device helper: running")
        else:
            _log.warning("Screen Saver Mode: device helper not running: %s", error)
            _trace(f"Device helper: not running, {error}")
        for callback in callbacks:
            _call(callback, ok, error)

    def _connect(self) -> tuple[bool, str]:
        name = secrets.token_hex(16)
        address = protocol.PIPE_PREFIX + name
        authkey = secrets.token_bytes(32)
        key = self._key()
        _write_key(key, authkey)
        listener = self._listener_factory(address, authkey)
        accepted: dict[str, Any] = {}
        got = threading.Event()

        def accept() -> None:
            try:
                accepted["conn"] = listener.accept()
            except Exception as exc:
                accepted["error"] = exc
            got.set()

        threads.start("Device helper accept", accept, stop=listener.close)
        file, parameters = helper_command(
            name, self._journal_file or journal_path(), key
        )
        _trace(f"Device helper: starting {file} {parameters}")
        try:
            process = self._launcher(file, parameters)
        except Refused:
            self._give_up(listener, key)
            return False, REFUSED_TEXT
        except (OSError, ValueError) as exc:
            self._give_up(listener, key)
            return False, f"The helper could not start ({exc})."
        deadline = clock.monotonic() + self._connect_timeout_s
        while not got.wait(0.25):
            if not process.running():
                got.wait(0.5)  # it may have connected just before ending
                if not got.is_set():
                    self._give_up(listener, key, process)
                    return False, HELPER_ENDED_TEXT
                break
            if clock.monotonic() >= deadline:
                self._give_up(listener, key, process)
                return False, NO_CONNECTION_TEXT
        conn = accepted.get("conn")
        if conn is None:
            self._give_up(listener, key, process)
            return False, f"The helper did not connect ({accepted.get('error')})."
        with self._lock:
            self._conn, self._listener, self._process = conn, listener, process
        answer = self._ask(protocol.make_request("ping", []), PING_TIMEOUT_S)
        if answer is None or not answer.get("ok"):
            self._drop()
            return False, "The helper did not answer."
        return True, ""

    def _give_up(
        self, listener: Listener, key: str, process: Process | None = None
    ) -> None:
        try:
            listener.close()
        except Exception:
            pass
        if process is not None:
            try:
                process.close()
            except Exception:
                pass
        try:
            os.remove(key)
        except OSError:
            pass

    def _drop(self) -> None:
        """Forgets the connection (closed or broken)."""
        with self._lock:
            conn, listener, process = self._conn, self._listener, self._process
            self._conn = self._listener = self._process = None
        for thing in (conn, listener, process):
            if thing is not None:
                try:
                    thing.close()
                except Exception:
                    pass

    def stop_helper(self) -> None:
        """Lets running jobs end (bounded), sends "quit" and closes."""
        with self._lock:
            self._wanted = False
            conn = self._conn
        self.wait_idle(5.0)
        if conn is not None:
            try:
                conn.send(protocol.make_request("quit", []))
            except Exception:
                pass
            _trace("Device helper: quit sent")
        self._drop()

    def _ask(self, request: dict, timeout_s: float) -> dict | None:
        """One request and its answer, bounded; None when the helper is gone
        (the connection is dropped then)."""
        with self._lock:
            conn = self._conn
        if conn is None:
            return None
        try:
            conn.send(request)
            if not conn.poll(timeout_s):
                raise TimeoutError("no answer in time")
            answer = conn.recv()
        except (OSError, EOFError, TimeoutError, ValueError) as exc:
            _log.warning(
                "Screen Saver Mode: device helper gone (%s): %s", request["op"], exc
            )
            _trace(f"Device helper: no answer to {request['op']}, {exc}")
            self._drop()
            return None
        return answer if isinstance(answer, dict) else None

    # Jobs: one program thread, one job at a time -------------------------

    def _enqueue(self, name: str, job: Callable[[], None]) -> None:
        with self._lock:
            if name == "enable" and "enable" in self._queued:
                return  # one queued enable covers every pending device
            self._queued.add(name)
            self._busy += 1
            self._idle.clear()
            self._jobs.put((name, job))
            if self._worker is None or not self._worker.is_alive():
                self._worker = threads.start("Device disabler", self._work)

    def _work(self) -> None:
        while True:
            try:
                name, job = self._jobs.get(timeout=1.0)
            except queue.Empty:
                with self._lock:
                    if self._jobs.empty():
                        self._worker = None
                        return
                continue
            with self._lock:
                self._queued.discard(name)
            try:
                job()
            except Exception:
                _log.exception("Screen Saver Mode: device %s failed", name)
            finally:
                with self._lock:
                    self._busy -= 1
                    if self._busy == 0:
                        self._idle.set()

    def wait_idle(self, timeout: float) -> bool:
        """Waits (bounded) until no disable/enable job is queued or running."""
        return self._idle.wait(timeout)

    # Disable (S21) ----------------------------------------------------------

    def disable(self, devices: list[tuple[str, str]]) -> None:
        """Disables (name, id) devices, async; only while the helper runs."""
        devices = list(devices)
        self._enqueue("disable", lambda: self._disable(devices))

    def _disable(self, devices: list[tuple[str, str]]) -> None:
        if not self.helper_running():
            _trace("Disable devices: skipped, the helper isn't running")
            return
        journal = self.journal()
        names: dict[str, str] = {}
        for name, device_id in devices:
            if not protocol.valid_device_id(device_id):
                _log.warning(
                    "Screen Saver Mode: not disabling %s: %r is not a HID device id",
                    name,
                    device_id,
                )
                continue
            if device_id in names:
                continue
            status = self._read(device_id)
            ours = journal.state(device_id) not in ("", ENABLED)
            if status == NOT_PRESENT:
                _trace(f"Disable {name} ({device_id}): skipped, not present")
                continue
            if status == DISABLED:
                if ours:
                    journal.set(device_id, name, DISABLED, "was already disabled")
                    _note(name, device_id, DISABLED, "was already disabled")
                else:
                    # Someone else disabled it: never ours to enable later.
                    _trace(
                        f"Disable {name} ({device_id}): skipped, already "
                        "disabled outside Gremlin"
                    )
                continue
            journal.set(device_id, name, TO_BE_DISABLED)
            _note(name, device_id, TO_BE_DISABLED, "")
            names[device_id] = name
        journal.save()
        if not names:
            return
        timeout = PER_DEVICE_TIMEOUT_S * len(names) + ANSWER_SLACK_S
        answer = self._ask(protocol.make_request("disable", list(names)), timeout)
        results = _results(answer)
        restart = [i for i in names if RESTART_EXIT in results.get(i, "")]
        if restart:
            self._undo_restart(journal, {i: names[i] for i in restart})
        for device_id, name in names.items():
            if device_id in restart:
                continue
            said = results.get(device_id, "no answer from the helper")
            status = self._read(device_id)
            if status == DISABLED:
                journal.set(device_id, name, DISABLED, said)
                _note(name, device_id, DISABLED, said)
            else:
                why = f"{said}; Windows has it {status}"
                journal.set(device_id, name, DISABLE_FAILED, why)
                _note(name, device_id, DISABLE_FAILED, why)
            journal.save()

    def _undo_restart(self, journal: Journal, names: dict[str, str]) -> None:
        """S34: Windows answered the disable with "restart needed" (pnputil
        exit 3010), so the device would stay disabled after the next
        restart; ask at once to enable it again."""
        for device_id, name in names.items():
            journal.set(device_id, name, TO_BE_ENABLED, "Windows wanted a restart")
            _note(name, device_id, TO_BE_ENABLED, "Windows wanted a restart, undoing")
        journal.save()
        timeout = PER_DEVICE_TIMEOUT_S * len(names) + ANSWER_SLACK_S
        answer = self._ask(protocol.make_request("enable", list(names)), timeout)
        results = _results(answer)
        for device_id, name in names.items():
            said = results.get(device_id, "no answer from the helper")
            status = self._read(device_id)
            if said == "done" and status != DISABLED:
                why = RESTART_UNDONE
            elif said == "done":
                why = f"Windows wanted a restart, undo failed: Windows has it {status}"
            else:
                why = f"Windows wanted a restart, undo failed: {said}"
            journal.set(device_id, name, DISABLE_FAILED, why)
            _note(name, device_id, DISABLE_FAILED, why)
        journal.save()

    # Enable (S23, S24) ------------------------------------------------------

    def enable_pending(self) -> None:
        """Enables, async, every journal device not "enabled"; never any
        other device."""
        self._enqueue("enable", self._enable)

    def _enable(self) -> None:
        journal = self.journal()
        pending = journal.not_enabled()
        if not pending:
            return
        if not self.helper_running():
            _trace(f"Enable devices: {len(pending)} waiting, the helper isn't running")
            return
        asked: list[str] = []
        for device_id in pending:
            name = journal.entries[device_id].get("name", "")
            state = journal.state(device_id)
            status = self._read(device_id)
            # A "disable failed" device may still be flagged for a restart
            # while it runs: enable it anyway (S34).
            if status == ENABLED and state != DISABLE_FAILED:
                journal.set(device_id, name, ENABLED, "was already enabled")
                _note(name, device_id, ENABLED, "was already enabled")
            elif status == NOT_PRESENT:
                journal.set(device_id, name, TO_BE_ENABLED, "not present")
                _note(name, device_id, TO_BE_ENABLED, "not present, waits")
            else:
                journal.set(device_id, name, TO_BE_ENABLED)
                _note(name, device_id, TO_BE_ENABLED, "")
                asked.append(device_id)
        journal.save()
        if not asked:
            return
        timeout = PER_DEVICE_TIMEOUT_S * len(asked) + ANSWER_SLACK_S
        answer = self._ask(protocol.make_request("enable", asked), timeout)
        results = _results(answer)
        for device_id in asked:
            name = journal.entries[device_id].get("name", "")
            said = results.get(device_id, "no answer from the helper")
            status = self._read(device_id)
            if PENDING_REBOOT in said.lower():
                # Windows refuses until it restarts: retried at the next start.
                journal.set(device_id, name, TO_BE_ENABLED, said)
                _note(name, device_id, TO_BE_ENABLED, said)
            elif status == ENABLED:
                journal.set(device_id, name, ENABLED, said)
                _note(name, device_id, ENABLED, said)
            elif status == NOT_PRESENT:
                journal.set(device_id, name, TO_BE_ENABLED, f"{said}; not present")
                _note(name, device_id, TO_BE_ENABLED, "not present, waits")
            else:
                why = f"{said}; Windows has it {status}"
                journal.set(device_id, name, ENABLE_FAILED, why)
                _note(name, device_id, ENABLE_FAILED, why)
            journal.save()

    def recover_at_start(self) -> None:
        """S24: when the journal lists a device not "enabled", starts the
        helper, then enables and checks those devices. Async."""
        pending = self.journal().not_enabled()
        if not pending:
            return
        _log.info(
            "Screen Saver Mode: %d device(s) left disabled, recovering", len(pending)
        )
        _trace(f"Recovery at start: {len(pending)} device(s) not enabled")

        def done(ok: bool, _error: str) -> None:
            if ok:
                self.enable_pending()

        self.start_helper(done)

    def on_device_arrival(self) -> None:
        """A device was plugged in: retry the ones still "to be enabled"."""
        journal = self.journal()
        if any(e.get("state") == TO_BE_ENABLED for e in journal.entries.values()):
            self.enable_pending()

    def _read(self, device_id: str) -> str:
        try:
            status = self._status(device_id)
        except RealCallBlocked:
            raise
        except Exception as exc:
            _log.warning(
                "Screen Saver Mode: status of %s unreadable: %s", device_id, exc
            )
            return "unknown"
        return status


def _results(answer: dict | None) -> dict[str, str]:
    if not answer:
        return {}
    results = answer.get("results")
    if not isinstance(results, dict):
        return {}
    return {str(k): str(v) for k, v in results.items()}


def _note(name: str, device_id: str, state: str, result: str) -> None:
    text = f"{name} ({device_id}): {state}" + (f", {result}" if result else "")
    _log.info("Screen Saver Mode: device %s", text)
    _trace(f"Device {text}")


def _call(callback: Callable[[bool, str], None], ok: bool, error: str) -> None:
    try:
        callback(ok, error)
    except Exception:
        _log.exception("Screen Saver Mode: device helper callback failed")


def _write_key(path: str, authkey: bytes) -> None:
    """The authkey's bytes, in a file made fresh (an old one is removed);
    the helper reads it, then deletes it."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        os.remove(path)
    except FileNotFoundError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(authkey)


_manager: DeviceDisabler | None = None
_manager_lock = threading.Lock()


def manager() -> DeviceDisabler:
    """The one instance."""
    global _manager
    with _manager_lock:
        if _manager is None:
            _manager = DeviceDisabler()
        return _manager
