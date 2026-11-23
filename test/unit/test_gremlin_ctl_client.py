# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin_ctl.client errors against a small fake pipe (S11, S25,
D-13-RESEARCH): a program that stops answering or closes during a call, the
answer's error code, alive checked before version, next-step texts."""

from __future__ import annotations

import json
import os
import secrets
import threading
from collections.abc import Iterator
from multiprocessing.connection import Listener
from pathlib import Path

import pytest

from gremlin_ctl import client

pytestmark = pytest.mark.skipif(os.name != "nt", reason="AF_PIPE is Windows only")


class Pipe:
    """Answers hello, then behaves as `mode` says for every other call:
    "close" closes the pipe, "silent" never answers, "error" answers a coded
    error."""

    def __init__(self, mode: str) -> None:
        self.mode = mode
        self.key = secrets.token_bytes(32)
        self.address = r"\\.\pipe\gremlin-ctl-client-test-" + secrets.token_hex(8)
        self.listener = Listener(self.address, family="AF_PIPE", authkey=self.key)
        self.done = threading.Event()
        threading.Thread(target=self._serve, daemon=True).start()

    def _serve(self) -> None:
        try:
            conn = self.listener.accept()
        except Exception:  # noqa: BLE001 - closed, or a client with the wrong key
            return
        with conn:
            while True:
                try:
                    request = json.loads(conn.recv_bytes().decode("utf-8"))
                except (EOFError, OSError):
                    return
                if request["call"] == "hello":
                    reply = {"ok": True, "result": {"version": 1}}
                elif self.mode == "close":
                    return
                elif self.mode == "silent":
                    self.done.wait(10)
                    return
                else:
                    reply = {
                        "ok": False,
                        "error": "No such thing.",
                        "code": "not_found",
                    }
                conn.send_bytes(json.dumps(reply).encode("utf-8"))

    def write(self, path: Path, **extra: object) -> None:
        data = {"address": self.address, "key": self.key.hex(), "version": 1}
        data.update(extra)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def close(self) -> None:
        self.done.set()
        self.listener.close()


@pytest.fixture
def endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "api" / "endpoint.json"
    monkeypatch.setenv(client.ENDPOINT_ENV, str(path))
    return path


@pytest.fixture
def pipe(request: pytest.FixtureRequest, endpoint: Path) -> Iterator[Pipe]:
    fake = Pipe(request.param)
    fake.write(endpoint)
    yield fake
    fake.close()


@pytest.mark.parametrize("pipe", ["close"], indirect=True)
def test_a_program_that_closes_during_a_call_stopped_answering(pipe: Pipe) -> None:
    with client.connect() as conn, pytest.raises(client.StoppedAnswering) as e:
        conn.call("run.start")
    assert str(e.value) == "The program stopped answering; the call may have run."
    assert not isinstance(e.value, client.NotRunning)


@pytest.mark.parametrize("pipe", ["silent"], indirect=True)
def test_a_silent_program_stopped_answering(pipe: Pipe) -> None:
    with client.connect() as conn:
        conn.call_timeout_s = 0.3
        with pytest.raises(client.StoppedAnswering):
            conn.call("state")


@pytest.mark.parametrize("pipe", ["error"], indirect=True)
def test_a_call_error_carries_the_answers_code(pipe: Pipe) -> None:
    with client.connect() as conn, pytest.raises(client.CallError) as e:
        conn.call("window.read", window="X")
    assert e.value.code == "not_found"
    assert str(e.value) == "No such thing."


def test_a_left_over_file_of_another_version_is_not_running(endpoint: Path) -> None:
    """Alive is checked before the version, so a stale file means 4, not 3."""
    endpoint.parent.mkdir(parents=True)
    endpoint.write_text(
        json.dumps(
            {"address": r"\\.\pipe\none", "key": "00", "version": 2, "pid": 0x7FFFFFF0}
        ),
        encoding="utf-8",
    )
    with pytest.raises(client.NotRunning, match="left over") as e:
        client.connect()
    assert not isinstance(e.value, client.VersionMismatch)


def test_messages_say_what_to_do_next(endpoint: Path) -> None:
    with pytest.raises(client.Off) as e:
        client.connect()
    assert e.value.code == "control_off"
    assert str(e.value).endswith(
        "Start Gremlin-Platforms and turn on Options › General › Control › "
        "Allow control from other programs."
    )
    fake = Pipe("error")
    try:
        fake.write(endpoint, key=secrets.token_bytes(32).hex())
        with pytest.raises(client.NotRunning) as e:
            client.connect()
        assert "off and on again, or restart Gremlin-Platforms." in str(e.value)
    finally:
        fake.close()


def test_version_text_suits_any_client(endpoint: Path) -> None:
    """The MCP server shows it too: no 'use the gremlin-ctl that came with'."""
    fake = Pipe("error")
    try:
        fake.write(endpoint, version=2)
        with pytest.raises(client.VersionMismatch) as e:
            client.connect()
    finally:
        fake.close()
    assert "gremlin-ctl" not in str(e.value)
    assert "Use a client from the same Gremlin-Platforms version." in str(e.value)
