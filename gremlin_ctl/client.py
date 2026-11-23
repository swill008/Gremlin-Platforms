# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Client for the Gremlin-Platforms control pipe (claude/plans/control-api-contract.md).

While "Allow control from other programs" is on, the program writes
%USERPROFILE%/Gremlin Platforms/api/endpoint.json with the pipe address and
key. A request is UTF-8 JSON {"call", "args"}; the answer is {"ok": true,
"result"} or {"ok": false, "error"}. One call at a time per connection.

    with connect() as client:
        print(client.call("state"))
"""

from __future__ import annotations

import ctypes
import json
import os
import threading
from multiprocessing.connection import Client as _PipeClient
from multiprocessing.connection import Connection
from pathlib import Path
from typing import Any

PROTOCOL_VERSION = 1
USER_DATA_FOLDER = "Gremlin Platforms"
# Points the client at another endpoint.json (tests, a second user folder).
ENDPOINT_ENV = "GREMLIN_CTL_ENDPOINT"

# The program answers within 10 s (30 s for long calls) or replies with an
# error; this only covers a program that stopped answering altogether.
DEFAULT_CALL_TIMEOUT_S = 40.0

NOT_RUNNING_TEXT = "Gremlin-Platforms isn't running"
OFF_TEXT = (
    "Gremlin-Platforms isn't running, or control from other programs is off "
    "in Options › General"
)


class GremlinCtlError(Exception):
    """Base of every error this module raises."""


class NotRunning(GremlinCtlError):
    """The program isn't running or its pipe is gone."""


class Off(NotRunning):
    """No endpoint file: the program isn't running or the switch is off."""


class VersionMismatch(GremlinCtlError):
    """The program speaks another protocol version."""


class CallError(GremlinCtlError):
    """The program refused or failed the call; the text is its error."""


def endpoint_path() -> Path:
    """Where the program writes endpoint.json."""
    override = os.environ.get(ENDPOINT_ENV)
    if override:
        return Path(override)
    home = os.environ.get("USERPROFILE") or str(Path.home())
    return Path(home) / USER_DATA_FOLDER / "api" / "endpoint.json"


def read_endpoint(path: Path | None = None) -> dict[str, Any]:
    """The endpoint file's contents; Off when it is missing or unreadable."""
    path = path or endpoint_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise Off(OFF_TEXT) from None
    except (OSError, ValueError) as e:
        raise Off(f"{OFF_TEXT} (endpoint file unreadable: {e})") from None
    if not isinstance(data, dict) or not data.get("address") or not data.get("key"):
        raise Off(f"{OFF_TEXT} (endpoint file incomplete)")
    return data


def _process_alive(pid: int) -> bool:
    """False only when the process is known to be gone (Windows)."""
    if os.name != "nt" or pid <= 0:
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    query_limited = 0x1000
    still_active = 259
    handle = kernel32.OpenProcess(query_limited, False, pid)
    if not handle:
        # 5 = access denied: the process exists.
        return ctypes.get_last_error() == 5
    try:
        code = ctypes.c_ulong()
        if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True
        return code.value == still_active
    finally:
        kernel32.CloseHandle(handle)


def _open_pipe(address: str, key: bytes, timeout_s: float) -> Connection:
    """Connects and authenticates within timeout_s (the handshake itself has
    no time limit, so it runs on a thread)."""
    box: dict[str, Any] = {}

    def work() -> None:
        try:
            box["conn"] = _PipeClient(address, family="AF_PIPE", authkey=key)
        except BaseException as e:  # noqa: BLE001 - handed back to the caller
            box["error"] = e

    thread = threading.Thread(target=work, name="gremlin-ctl-connect", daemon=True)
    thread.start()
    thread.join(timeout_s)
    if thread.is_alive():
        raise NotRunning(f"{NOT_RUNNING_TEXT} (no answer within {timeout_s:g} s)")
    error = box.get("error")
    if error is not None:
        if isinstance(error, (FileNotFoundError, ConnectionError, EOFError)):
            raise NotRunning(NOT_RUNNING_TEXT) from None
        if type(error).__name__ == "AuthenticationError":
            raise NotRunning(
                f"{NOT_RUNNING_TEXT} (the pipe refused the key; the endpoint "
                "file is out of date)"
            ) from None
        if isinstance(error, OSError):
            raise NotRunning(f"{NOT_RUNNING_TEXT} ({error})") from None
        raise error
    return box["conn"]


class Client:
    """One connection to the program. Use connect() to make one."""

    def __init__(
        self, conn: Connection, *, call_timeout_s: float = DEFAULT_CALL_TIMEOUT_S
    ) -> None:
        self._conn: Connection | None = conn
        self._lock = threading.Lock()
        self.call_timeout_s = call_timeout_s
        self.program_version = ""

    def call(self, name: str, **args: Any) -> Any:  # noqa: ANN401
        """Makes one call; returns its result or raises CallError/NotRunning."""
        with self._lock:
            conn = self._conn
            if conn is None:
                raise NotRunning(f"{NOT_RUNNING_TEXT} (connection closed)")
            request = json.dumps({"call": name, "args": args}).encode("utf-8")
            try:
                conn.send_bytes(request)
                if not conn.poll(self.call_timeout_s):
                    self._drop()
                    raise NotRunning(
                        f"{NOT_RUNNING_TEXT} (no answer to {name} within "
                        f"{self.call_timeout_s:g} s)"
                    )
                raw = conn.recv_bytes()
            except (OSError, EOFError):
                self._drop()
                raise NotRunning(NOT_RUNNING_TEXT) from None
        try:
            reply = json.loads(raw.decode("utf-8"))
        except ValueError as e:
            raise CallError(f"unreadable answer to {name}: {e}") from None
        if not isinstance(reply, dict) or "ok" not in reply:
            raise CallError(f"unreadable answer to {name}")
        if not reply["ok"]:
            raise CallError(str(reply.get("error") or "unknown error"))
        return reply.get("result")

    def _drop(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.close()
            except OSError:
                pass

    def close(self) -> None:
        with self._lock:
            self._drop()

    def __enter__(self) -> Client:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def connect(timeout_s: float = 5.0, *, endpoint: Path | str | None = None) -> Client:
    """Connects to the running program and checks its protocol version.

    Raises Off (no endpoint file), NotRunning (pipe gone or silent) or
    VersionMismatch.
    """
    path = Path(endpoint) if endpoint is not None else endpoint_path()
    info = read_endpoint(path)
    file_version = info.get("version")
    if file_version is not None and file_version != PROTOCOL_VERSION:
        raise VersionMismatch(_mismatch_text(file_version))
    pid = info.get("pid")
    if isinstance(pid, int) and not _process_alive(pid):
        raise NotRunning(f"{NOT_RUNNING_TEXT} (its endpoint file is left over)")
    try:
        key = bytes.fromhex(str(info["key"]))
    except ValueError:
        raise Off(f"{OFF_TEXT} (endpoint key unreadable)") from None
    client = Client(_open_pipe(str(info["address"]), key, timeout_s))
    try:
        hello = client.call("hello")
    except BaseException:
        client.close()
        raise
    version = hello.get("version") if isinstance(hello, dict) else None
    if version != PROTOCOL_VERSION:
        client.close()
        raise VersionMismatch(_mismatch_text(version))
    client.program_version = str(hello.get("program_version", ""))
    return client


def _mismatch_text(version: object) -> str:
    return (
        f"Gremlin-Platforms speaks control protocol {version}; this gremlin-ctl "
        f"speaks {PROTOCOL_VERSION}. Use the gremlin-ctl that came with the program."
    )
