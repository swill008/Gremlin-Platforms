# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin_ctl client and CLI against a small fake control pipe in this process
(claude/plans/control-api-contract.md): connect, calls, errors, exit codes."""

from __future__ import annotations

import io
import json
import os
import secrets
import sys
import threading
from collections.abc import Callable, Iterator
from multiprocessing.connection import Listener
from pathlib import Path
from typing import Any

import pytest

from gremlin_ctl import cli, client

pytestmark = pytest.mark.skipif(os.name != "nt", reason="AF_PIPE is Windows only")


class FakeProgram:
    """Answers control calls on a named pipe like the program does."""

    def __init__(self, handler: Callable[[str, dict], Any], version: int = 1) -> None:
        self.key = secrets.token_bytes(32)
        self.address = r"\\.\pipe\gremlin-ctl-test-" + secrets.token_hex(8)
        self.listener = Listener(self.address, family="AF_PIPE", authkey=self.key)
        self.handler = handler
        self.version = version
        self.requests: list[dict] = []
        self.thread = threading.Thread(target=self._serve, daemon=True)
        self.thread.start()

    def _serve(self) -> None:
        while True:
            try:
                conn = self.listener.accept()
            except OSError:
                return
            except Exception:  # noqa: BLE001 - a client with the wrong key
                continue
            with conn:
                while True:
                    try:
                        raw = conn.recv_bytes()
                    except (EOFError, OSError):
                        break
                    request = json.loads(raw.decode("utf-8"))
                    self.requests.append(request)
                    if request["call"] == "hello":
                        reply = {
                            "ok": True,
                            "result": {
                                "version": self.version,
                                "program_version": "9.9",
                            },
                        }
                    else:
                        try:
                            result = self.handler(request["call"], request["args"])
                            reply = {"ok": True, "result": result}
                        except Exception as e:  # noqa: BLE001
                            reply = {"ok": False, "error": str(e)}
                    conn.send_bytes(json.dumps(reply).encode("utf-8"))

    def write_endpoint(self, path: Path, **extra: Any) -> None:  # noqa: ANN401
        data = {
            "address": self.address,
            "key": self.key.hex(),
            "version": 1,
            "pid": os.getpid(),
        }
        data.update(extra)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def close(self) -> None:
        self.listener.close()


def _answers(call: str, args: dict) -> Any:  # noqa: ANN401
    if call == "state":
        return {"profile": "Test.xml", "running": True, "tracing": False}
    if call == "commands":
        return [{"id": "open-options", "text": "Options", "group": "Tools"}]
    if call == "fail":
        raise RuntimeError("Option key unknown")
    return {"call": call, "args": args}


@pytest.fixture
def endpoint(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "Gremlin Platforms" / "api" / "endpoint.json"
    monkeypatch.setenv(client.ENDPOINT_ENV, str(path))
    return path


@pytest.fixture
def program(endpoint: Path) -> Iterator[FakeProgram]:
    fake = FakeProgram(_answers)
    fake.write_endpoint(endpoint)
    yield fake
    fake.close()


def _run(*argv: str) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = cli.main(list(argv), out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_endpoint_defaults_to_user_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(client.ENDPOINT_ENV, raising=False)
    monkeypatch.setenv("USERPROFILE", r"C:\Users\someone")
    assert client.endpoint_path() == Path(
        r"C:\Users\someone\Gremlin Platforms\api\endpoint.json"
    )


def test_client_imports_no_qt_and_no_gremlin() -> None:
    source = "".join(
        p.read_text(encoding="utf-8") for p in Path(client.__file__).parent.glob("*.py")
    )
    assert "PySide6" not in source
    assert "import gremlin\n" not in source and "from gremlin " not in source
    assert "from gremlin." not in source and "import gremlin." not in source


def test_connect_hello_and_call(program: FakeProgram) -> None:
    with client.connect() as conn:
        assert conn.program_version == "9.9"
        assert conn.call("state")["profile"] == "Test.xml"
        assert conn.call("echo", a=1) == {"call": "echo", "args": {"a": 1}}
    assert program.requests[0] == {"call": "hello", "args": {}}


def test_call_error_carries_program_text(program: FakeProgram) -> None:
    with client.connect() as conn, pytest.raises(client.CallError, match="unknown"):
        conn.call("fail")


def test_no_endpoint_is_off(endpoint: Path) -> None:
    with pytest.raises(client.Off, match="Options › General"):
        client.connect()
    code, _, err = _run("state")
    assert code == cli.EXIT_NOT_RUNNING
    assert "control from other programs is off" in err


def test_pipe_gone_is_not_running(program: FakeProgram, endpoint: Path) -> None:
    program.write_endpoint(
        endpoint, address=r"\\.\pipe\gremlin-ctl-test-" + secrets.token_hex(8)
    )
    code, _, err = _run("state")
    assert code == cli.EXIT_NOT_RUNNING
    assert "isn't running" in err


def test_left_over_endpoint_is_not_running(endpoint: Path) -> None:
    # A pid that cannot exist: the program that wrote the file is gone.
    endpoint.parent.mkdir(parents=True)
    endpoint.write_text(
        json.dumps(
            {
                "address": r"\\.\pipe\gremlin-ctl-none",
                "key": "00",
                "version": 1,
                "pid": 0x7FFFFFF0,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(client.NotRunning, match="left over"):
        client.connect()


def test_version_mismatch_exit_3(endpoint: Path) -> None:
    fake = FakeProgram(_answers, version=2)
    fake.write_endpoint(endpoint)
    try:
        code, _, err = _run("state")
    finally:
        fake.close()
    assert code == cli.EXIT_VERSION
    assert "protocol 2" in err


def test_wrong_key_is_not_running(program: FakeProgram, endpoint: Path) -> None:
    program.write_endpoint(endpoint, key=secrets.token_bytes(32).hex())
    with pytest.raises(client.NotRunning, match="refused the key"):
        client.connect()


@pytest.mark.parametrize(
    ("argv", "call", "args"),
    [
        (["state"], "state", {}),
        (["devices"], "devices", {}),
        (["run", "start"], "run.start", {}),
        (["run", "stop"], "run.stop", {}),
        (["profile", "save"], "profile.save", {}),
        (["commands"], "commands", {}),
        (["run-command", "open-options"], "command.run", {"id": "open-options"}),
        (
            ["option", "get", "global/control/x"],
            "option.get",
            {"key": "global/control/x"},
        ),
        (
            ["option", "set", "a/b/c", "true"],
            "option.set",
            {"key": "a/b/c", "value": True},
        ),
        (
            ["option", "set", "a/b/c", "hello"],
            "option.set",
            {"key": "a/b/c", "value": "hello"},
        ),
        (["options"], "options.list", {}),
        (["options", "list"], "options.list", {}),
        (["trace", "on"], "trace.on", {}),
        (["trace", "off", "output"], "trace.off", {"category": "output"}),
        (["trace", "status"], "trace.status", {}),
        (["log"], "log", {"which": "system", "lines": 50}),
        (["log", "trace", "-n", "5"], "log", {"which": "trace", "lines": 5}),
        (["windows"], "window.list", {}),
        (
            ["window", "open", "open-options"],
            "window.open",
            {"command": "open-options"},
        ),
        (["window", "close", "Options"], "window.close", {"window": "Options"}),
        (["window", "read", "Options"], "window.read", {"window": "Options"}),
        (
            ["window", "press", "Options", "OK"],
            "window.press",
            {"window": "Options", "button": "OK"},
        ),
        (
            ["window", "type", "Options", "Name", "abc"],
            "window.type",
            {"window": "Options", "field": "Name", "text": "abc"},
        ),
        (["call", "x.y", '{"n": 2}'], "x.y", {"n": 2}),
    ],
)
def test_cli_commands_make_their_call(
    program: FakeProgram, argv: list[str], call: str, args: dict
) -> None:
    code, _, err = _run(*argv)
    assert code == cli.EXIT_OK, err
    assert program.requests[-1] == {"call": call, "args": args}


def test_paths_are_made_absolute(
    program: FakeProgram, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    assert _run("profile", "load", "p.xml")[0] == cli.EXIT_OK
    assert program.requests[-1]["args"] == {"path": str(tmp_path / "p.xml")}
    assert _run("window", "screenshot", "Options", "s.png")[0] == cli.EXIT_OK
    assert program.requests[-1]["args"]["path"] == str(tmp_path / "s.png")


def test_readable_and_json_output(program: FakeProgram) -> None:
    code, out, _ = _run("state")
    assert code == 0
    assert "profile: Test.xml" in out and "running: yes" in out
    code, out, _ = _run("--json", "state")
    assert json.loads(out)["running"] is True
    code, out, _ = _run("commands")
    assert "open-options  Options  (Tools)" in out


def test_call_error_exit_1(program: FakeProgram) -> None:
    code, _, err = _run("call", "fail")
    assert code == cli.EXIT_CALL_ERROR
    assert "fail: Option key unknown" in err


def test_usage_errors_exit_1(program: FakeProgram) -> None:
    assert _run("window", "press", "Options")[0] == cli.EXIT_CALL_ERROR
    assert _run("profile", "load")[0] == cli.EXIT_CALL_ERROR
    assert _run("option", "set", "a/b/c")[0] == cli.EXIT_CALL_ERROR
    assert not program.requests  # nothing was sent


def test_help_works_without_the_program(endpoint: Path) -> None:
    code, out, _ = _run("help")
    assert code == cli.EXIT_OK
    assert "gremlin-ctl" in out and "needs the program" in out


def test_main_module_runs(
    program: FakeProgram, monkeypatch: pytest.MonkeyPatch
) -> None:
    import runpy

    monkeypatch.setattr(sys, "argv", ["gremlin-ctl", "--json", "state"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("gremlin_ctl", run_name="__main__")
    assert stop.value.code == 0
