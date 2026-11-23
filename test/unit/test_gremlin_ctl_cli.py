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
                            reply = {
                                "ok": False,
                                "error": str(e),
                                "code": getattr(e, "code", "failed"),
                            }
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
    if call == "missing":
        error = LookupError("No window called 'X'.")
        error.code = "not_found"  # type: ignore[attr-defined]
        raise error
    if call == "devices":
        return [
            {
                "name": " VKBSim NXT  SEM ",
                "label": " VKBSim NXT  SEM ",
                "guid": "{AB}",
                "virtual": False,
                "vjoy_id": None,
                "axes": 6,
                "buttons": 32,
                "hats": 1,
                "plugged_in": True,
            },
            {
                "name": "vJoy Device",
                "label": "vJoy Device",
                "guid": "{CD}",
                "virtual": True,
                "vjoy_id": 2,
                "axes": None,
                "buttons": None,
                "hats": None,
                "plugged_in": False,
            },
        ]
    if call == "shape":
        return {"idle_s": 19.73366420000093, "whole": 2.0, "problem": "", "x": {}}
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
            {"id": "open-options"},
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


def test_bad_arguments_exit_2(program: FakeProgram) -> None:
    """S11: a missing or bad argument found before any call is exit 2, with
    the command's usage and "gremlin-ctl: error:" on stderr."""
    for argv in (
        ["window", "press", "Options"],
        ["profile", "load"],
        ["option", "set", "a/b/c"],
        ["call", "x.y", "{not json"],
        ["call", "x.y", "[1]"],  # JSON, but not an object
        ["call", "x.y", "5"],
        ["call", "x.y", "null"],
        ["trace", "status", "output"],  # status takes no category
        ["--timeout", "0", "state"],
        ["--timeout", "-1", "state"],
        ["log", "-n", "0"],
        ["log", "-n", "2001"],
        ["log", "-n", "-5"],
    ):
        code, out, err = _run(*argv)
        assert code == cli.EXIT_USAGE == 2, argv
        assert "usage: gremlin-ctl" in err and "gremlin-ctl: error:" in err, argv
        assert out == "", argv
    assert _run("log", "-n", "2000")[0] == cli.EXIT_OK
    assert program.requests[-1]["args"]["lines"] == 2000
    assert all(r["call"] in ("hello", "log") for r in program.requests)


def test_call_args_that_are_not_an_object_say_so(program: FakeProgram) -> None:
    code, _, err = _run("call", "x.y", "[1]")
    assert code == cli.EXIT_USAGE
    assert "must be a JSON object" in err and "Traceback" not in err


@pytest.mark.parametrize(
    "argv",
    [
        ["status"],  # unknown command (found live 2026-11-23)
        ["--bogus", "state"],  # unknown option
        ["state", "--bogus"],  # unknown option after the command
        ["run"],  # missing argument
        ["run", "go"],  # bad choice
        ["log", "-n", "many"],  # bad number
        ["--timeout", "soon", "state"],  # bad number
    ],
)
def test_a_mistyped_command_exits_2(program: FakeProgram, argv: list[str]) -> None:
    """S11, D-13-RESEARCH 3a: exit 2 with the usage text on stderr."""
    code, out, err = _run(*argv)
    assert code == cli.EXIT_USAGE == 2
    assert "usage: gremlin-ctl" in err and "error:" in err
    assert out == ""
    assert not program.requests


def test_exit_4_means_not_running(endpoint: Path) -> None:
    """S11: 4 is not running / control off only."""
    code, _, err = _run("state")
    assert code == cli.EXIT_NOT_RUNNING == 4
    assert "Allow control from other programs" in err  # the next step
    assert _run("status")[0] == cli.EXIT_USAGE  # typed wrong beats not running


def test_exit_code_numbers_and_epilog() -> None:
    assert (
        cli.EXIT_OK,
        cli.EXIT_CALL_ERROR,
        cli.EXIT_USAGE,
        cli.EXIT_VERSION,
        cli.EXIT_NOT_RUNNING,
    ) == (0, 1, 2, 3, 4)
    out = io.StringIO()
    cli._build_parser().print_help(out)
    text = " ".join(out.getvalue().split())
    assert "2 command typed wrong" in text and "4 not running or control off" in text


def test_help_flag_exits_0(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--help"]) == cli.EXIT_OK
    assert cli.main(["run", "--help"]) == cli.EXIT_OK
    assert "usage: gremlin-ctl" in capsys.readouterr().out


def test_help_works_without_the_program(endpoint: Path) -> None:
    """S11: help lists the commands from gremlin-ctl itself, exit 0, with or
    without --json, and never connects."""

    def no_connect() -> client.Client:
        raise AssertionError("help must not connect")

    out, err = io.StringIO(), io.StringIO()
    assert cli.main(["help"], out=out, err=err, connect=no_connect) == cli.EXIT_OK
    assert "window" in out.getvalue() and err.getvalue() == ""
    out = io.StringIO()
    assert cli.main(["--json", "help"], out=out, connect=no_connect) == cli.EXIT_OK
    rows = json.loads(out.getvalue())
    names = [row["command"] for row in rows]
    assert {"state", "devices", "window", "call", "help"} <= set(names)
    assert all(row["help"] for row in rows)


def test_json_errors_go_to_stdout_as_json(program: FakeProgram, endpoint: Path) -> None:
    """S11, S25: with --json an error is {"ok", "code", "error", "exit"} on
    stdout and the readable line on stderr."""
    code, out, err = _run("--json", "call", "missing")
    assert code == cli.EXIT_CALL_ERROR
    assert json.loads(out) == {
        "ok": False,
        "code": "not_found",
        "error": "No window called 'X'.",
        "exit": 1,
    }
    assert "missing: No window called 'X'." in err
    code, out, err = _run("--json", "status")
    assert code == cli.EXIT_USAGE
    assert json.loads(out)["code"] == "bad_args" and json.loads(out)["exit"] == 2
    assert "usage: gremlin-ctl" in err
    endpoint.unlink()
    code, out, err = _run("state", "--json")
    assert code == cli.EXIT_NOT_RUNNING
    assert json.loads(out)["exit"] == 4 and json.loads(out)["code"] == "control_off"
    assert "isn't running" in err


def test_ctrl_c_during_a_call_is_a_clean_exit_1() -> None:
    class Interrupted:
        call_timeout_s = 0.0

        def __enter__(self) -> Interrupted:
            return self

        def __exit__(self, *exc: object) -> None:
            pass

        def call(self, name: str, **args: Any) -> Any:  # noqa: ANN401
            raise KeyboardInterrupt

    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["state"], out=out, err=err, connect=Interrupted)  # type: ignore[arg-type]
    assert code == cli.EXIT_CALL_ERROR
    assert "Stopped." in err.getvalue() and "Traceback" not in err.getvalue()


def test_stopped_answering_exits_1() -> None:
    class Silent:
        call_timeout_s = 0.0

        def __enter__(self) -> Silent:
            return self

        def __exit__(self, *exc: object) -> None:
            pass

        def call(self, name: str, **args: Any) -> Any:  # noqa: ANN401
            raise client.StoppedAnswering()

    out, err = io.StringIO(), io.StringIO()
    code = cli.main(["run-command", "x"], out=out, err=err, connect=Silent)  # type: ignore[arg-type]
    assert code == cli.EXIT_CALL_ERROR
    assert "The program stopped answering; the call may have run." in err.getvalue()


def test_readable_text_rounds_floats_and_shows_empty(program: FakeProgram) -> None:
    code, out, _ = _run("call", "shape")
    assert code == cli.EXIT_OK
    lines = out.splitlines()
    assert "idle_s: 19.73" in lines and "whole: 2" in lines
    assert "problem: -" in lines and "x: -" in lines
    assert cli.format_result([]) == ["none"]


def test_devices_read_one_block_per_device(program: FakeProgram) -> None:
    code, out, _ = _run("devices")
    assert code == cli.EXIT_OK
    assert out.splitlines() == [
        "VKBSim NXT  SEM  [plugged in]",
        "  id {AB}  axes 6  buttons 32  hats 1",
        "vJoy Device  [not plugged in]",
        "  id {CD}  vJoy 2",
    ]


def test_main_module_runs(
    program: FakeProgram, monkeypatch: pytest.MonkeyPatch
) -> None:
    import runpy

    monkeypatch.setattr(sys, "argv", ["gremlin-ctl", "--json", "state"])
    with pytest.raises(SystemExit) as stop:
        runpy.run_module("gremlin_ctl", run_name="__main__")
    assert stop.value.code == 0


def test_devices_help_says_plugged_in_or_not(endpoint: Path) -> None:
    """S21: devices lists the known devices that aren't plugged in too."""
    code, out, _ = _run("help")
    assert code == cli.EXIT_OK
    line = next(row for row in out.splitlines() if row.strip().startswith("devices"))
    assert "devices, plugged in or not" in line
