# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin Device Helper and its protocol (Screen Saver Mode S21-S25).

Nothing here runs pnputil, elevates or starts the helper: the serve loop gets
a fake connection, a fake runner and a fake parent check.
"""

from __future__ import annotations

import ast
import json
import pathlib
import subprocess

import pytest

import gremlin_device_helper as helper
from gremlin import device_helper_protocol as protocol

_ROOT = pathlib.Path(__file__).resolve().parents[2]

PAD = "HID\\VID_231D&PID_0200&MI_00\\7&1A2B3C4D&0&0000"
MIC = "HID\\VID_352F&PID_0100&MI_03&COL01\\8&2B&0&0000"
OTHER = "HID\\VID_046D&PID_C52B\\9&3C&0&0000"


# Protocol -------------------------------------------------------------------


@pytest.mark.parametrize("text", [PAD, MIC, "HID\\X"])
def test_valid_ids(text: str) -> None:
    assert protocol.valid_device_id(text)


@pytest.mark.parametrize(
    "text",
    [
        "",
        "HID\\",
        "USB\\VID_231D&PID_0200\\1",
        "hid\\VID_231D",
        'HID\\VID_1" /enable-device "USB\\X',
        "HID\\VID\n1",
        "HID\\VID\x001",
        "HID\\" + "A" * 300,
        None,
        42,
    ],
)
def test_bad_ids(text: object) -> None:
    assert not protocol.valid_device_id(text)  # type: ignore[arg-type]


def test_states_and_prefix() -> None:
    assert protocol.STATES == (
        "to be disabled",
        "disabled",
        "disable failed",
        "to be enabled",
        "enabled",
        "enable failed",
    )
    assert protocol.PIPE_PREFIX == "\\\\.\\pipe\\gremlin-device-helper-"


def test_make_request() -> None:
    assert protocol.make_request("disable", [PAD]) == {"op": "disable", "ids": [PAD]}
    assert protocol.make_request("ping", []) == {"op": "ping", "ids": []}
    with pytest.raises(ValueError):
        protocol.make_request("format", [PAD])


def _journal(**states: str) -> dict:
    ids = {"pad": PAD, "mic": MIC, "other": OTHER}
    return {ids[k]: {"name": k, "state": v} for k, v in states.items()}


def test_check_disable_only_to_be_disabled() -> None:
    journal = _journal(pad="to be disabled", mic="to be enabled")
    allowed, refused = protocol.check_request(
        protocol.make_request("disable", [PAD, MIC, OTHER, "USB\\X"]), journal
    )
    assert allowed == [PAD]
    assert set(refused) == {MIC, OTHER, "USB\\X"}
    assert refused[MIC].startswith("refused: ") and "to be enabled" in refused[MIC]
    assert refused[OTHER] == "refused: not in the journal"
    assert "HID" in refused["USB\\X"]


def test_check_enable_only_to_be_enabled() -> None:
    journal = _journal(pad="to be enabled", mic="disabled", other="enabled")
    allowed, refused = protocol.check_request(
        protocol.make_request("enable", [PAD, MIC, OTHER]), journal
    )
    assert allowed == [PAD]
    assert set(refused) == {MIC, OTHER}


def test_check_unknown_op_and_no_device_ops() -> None:
    journal = _journal(pad="to be disabled")
    allowed, refused = protocol.check_request({"op": "wipe", "ids": [PAD]}, journal)
    assert allowed == [] and refused == {PAD: "refused: unknown operation"}
    allowed, refused = protocol.check_request({"op": "ping", "ids": [PAD]}, journal)
    assert allowed == [] and PAD in refused
    assert protocol.check_request({"op": "quit", "ids": []}, journal) == ([], {})


def test_check_bad_shapes_never_raise() -> None:
    journal = _journal(pad="to be disabled")
    assert protocol.check_request("disable", journal) == ([], {})  # type: ignore[arg-type]
    assert protocol.check_request({"op": "disable", "ids": PAD}, journal) == ([], {})
    allowed, refused = protocol.check_request({"op": "disable", "ids": [7]}, journal)
    assert allowed == [] and list(refused) == ["7"]
    assert protocol.check_request({"op": "disable", "ids": [PAD]}, [])[0] == []  # type: ignore[arg-type]
    # A duplicate is handled once.
    allowed, _ = protocol.check_request({"op": "disable", "ids": [PAD, PAD]}, journal)
    assert allowed == [PAD]


def test_protocol_imports_nothing_from_the_program() -> None:
    tree = ast.parse(
        (_ROOT / "gremlin" / "device_helper_protocol.py").read_text("utf-8")
    )
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module == "__future__"
        assert not isinstance(node, ast.Import)


def test_helper_imports_only_the_protocol_from_the_program() -> None:
    tree = ast.parse((_ROOT / "gremlin_device_helper.py").read_text("utf-8"))
    program = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and node.module.startswith("gremlin")
        ):
            program.add((node.module, tuple(a.name for a in node.names)))
        if isinstance(node, ast.Import):
            assert not any(
                a.name.startswith(("gremlin", "PySide6")) for a in node.names
            )
    assert program == {("gremlin", ("device_helper_protocol",))}


# Serve loop ------------------------------------------------------------------


class FakeConn:
    """Hands out queued requests; then None (nothing waiting) or EOFError."""

    def __init__(self, requests: list[object], close_after: bool = True) -> None:
        self.requests = list(requests)
        self.sent: list[dict] = []
        self.close_after = close_after
        self.polls = 0
        self.closed = False

    def poll(self, timeout: float) -> bool:
        self.polls += 1
        if self.requests:
            return True
        if self.close_after:
            raise EOFError
        return False

    def recv(self) -> object:
        item = self.requests.pop(0)
        if isinstance(item, BaseException):
            raise item
        return item

    def send(self, obj: dict) -> None:
        self.sent.append(obj)

    def close(self) -> None:
        self.closed = True


class FakeRunner:
    def __init__(self, results: dict[str, object] | None = None) -> None:
        self.calls: list[tuple[str, str]] = []
        self.results = results or {}

    def __call__(self, op: str, device_id: str) -> str:
        self.calls.append((op, device_id))
        result = self.results.get(device_id, "done")
        if isinstance(result, BaseException):
            raise result
        return result  # type: ignore[return-value]


@pytest.fixture
def no_real_pnputil(monkeypatch: pytest.MonkeyPatch) -> list:
    """Fails the test if anything reaches subprocess."""
    calls: list = []

    def blocked(*args: object, **kwargs: object) -> None:
        calls.append(args)
        raise AssertionError("subprocess was called")

    monkeypatch.setattr(subprocess, "run", blocked)
    monkeypatch.setattr(subprocess, "Popen", blocked)
    return calls


def _write_journal(tmp_path: pathlib.Path, entries: dict) -> pathlib.Path:
    folder = tmp_path / "screen saver mode"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "devices.json"
    path.write_text(json.dumps(entries), encoding="utf-8")
    return path


def test_serve_disable_results_per_id(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(
        tmp_path, _journal(pad="to be disabled", mic="to be disabled", other="enabled")
    )
    runner = FakeRunner({MIC: "error: pnputil exit 5: Access is denied."})
    conn = FakeConn([protocol.make_request("disable", [PAD, MIC, OTHER])])
    reason = helper.serve(conn, journal, runner, lambda: True, poll_s=0)
    assert reason == "closed"
    assert runner.calls == [("disable", PAD), ("disable", MIC)]
    (response,) = conn.sent
    assert response["ok"] is False
    assert response["results"][PAD] == "done"
    assert response["results"][MIC] == "error: pnputil exit 5: Access is denied."
    assert response["results"][OTHER].startswith("refused: ")
    assert no_real_pnputil == []


def test_serve_all_done_is_ok(tmp_path: pathlib.Path, no_real_pnputil: list) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be enabled"))
    runner = FakeRunner()
    conn = FakeConn([protocol.make_request("enable", [PAD])])
    helper.serve(conn, journal, runner, lambda: True, poll_s=0)
    assert runner.calls == [("enable", PAD)]
    assert conn.sent == [{"ok": True, "results": {PAD: "done"}}]


def test_serve_reads_the_journal_at_each_request(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    # Gremlin writes "to be disabled" just before it asks.
    journal = _write_journal(tmp_path, _journal(pad="enabled"))
    runner = FakeRunner()

    class Rewrite(FakeConn):
        def recv(self) -> object:
            item = super().recv()
            if len(self.requests) == 0:
                _write_journal(tmp_path, _journal(pad="to be disabled"))
            return item

    conn = Rewrite(
        [
            protocol.make_request("disable", [PAD]),
            protocol.make_request("disable", [PAD]),
        ]
    )
    helper.serve(conn, journal, runner, lambda: True, poll_s=0)
    assert conn.sent[0]["results"][PAD].startswith("refused: ")
    assert conn.sent[1]["results"][PAD] == "done"
    assert runner.calls == [("disable", PAD)]


def test_serve_runner_exception_and_timeout_are_errors(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(
        tmp_path, _journal(pad="to be disabled", mic="to be disabled")
    )
    runner = FakeRunner(
        {PAD: RuntimeError("boom"), MIC: "error: pnputil took over 30 s"}
    )
    conn = FakeConn([protocol.make_request("disable", [PAD, MIC])])
    helper.serve(conn, journal, runner, lambda: True, poll_s=0)
    results = conn.sent[0]["results"]
    assert results == {PAD: "error: boom", MIC: "error: pnputil took over 30 s"}


def test_serve_odd_runner_text_is_an_error(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be disabled"))
    conn = FakeConn([protocol.make_request("disable", [PAD])])
    helper.serve(conn, journal, FakeRunner({PAD: "maybe"}), lambda: True, poll_s=0)
    assert conn.sent[0]["results"][PAD] == "error: maybe"
    assert conn.sent[0]["ok"] is False


def test_serve_bad_requests_never_crash(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be disabled"))
    runner = FakeRunner()
    conn = FakeConn(
        [
            "disable everything",
            {"op": "disable", "ids": PAD},
            {"op": "wipe", "ids": [PAD]},
            ValueError("unpickling failed"),
            protocol.make_request("ping", []),
        ]
    )
    reason = helper.serve(conn, journal, runner, lambda: True, poll_s=0)
    assert reason == "closed"
    assert runner.calls == []
    assert [r["ok"] for r in conn.sent] == [False, False, False, False, True]
    assert conn.sent[2]["results"] == {PAD: "refused: unknown operation"}


def test_serve_missing_or_broken_journal_allows_nothing(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    runner = FakeRunner()
    conn = FakeConn([protocol.make_request("disable", [PAD])])
    helper.serve(conn, tmp_path / "none.json", runner, lambda: True, poll_s=0)
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    conn2 = FakeConn([protocol.make_request("enable", [PAD])])
    helper.serve(conn2, broken, runner, lambda: True, poll_s=0)
    assert runner.calls == []
    assert conn.sent[0]["results"][PAD] == "refused: not in the journal"
    assert conn2.sent[0]["results"][PAD] == "refused: not in the journal"


def test_journal_with_a_devices_key(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "j.json"
    path.write_text(
        json.dumps({"devices": {PAD: {"state": "to be disabled"}}}), "utf-8"
    )
    assert helper.load_journal(path) == {PAD: {"state": "to be disabled"}}


def test_quit_ends_the_loop(tmp_path: pathlib.Path, no_real_pnputil: list) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be disabled"))
    runner = FakeRunner()
    conn = FakeConn(
        [protocol.make_request("quit", []), protocol.make_request("disable", [PAD])],
        close_after=False,
    )
    assert helper.serve(conn, journal, runner, lambda: True, poll_s=0) == "quit"
    assert conn.sent == [{"ok": True, "results": {}}]
    assert runner.calls == []


def test_parent_gone_ends_the_loop(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be disabled"))
    checks = iter([True, True, True, False])
    conn = FakeConn([], close_after=False)
    reason = helper.serve(conn, journal, FakeRunner(), lambda: next(checks), poll_s=0)
    assert reason == "parent gone"
    assert conn.polls == 3


def test_parent_checked_about_once_a_second() -> None:
    assert 0.5 <= helper.POLL_S <= 1.5
    assert helper.PNPUTIL_TIMEOUT_S == 30


# main: key file, connection, log ---------------------------------------------


def _args(
    tmp_path: pathlib.Path, journal: pathlib.Path, key: pathlib.Path
) -> list[str]:
    return [
        "--pipe",
        "abc123",
        "--journal",
        str(journal),
        "--key",
        str(key),
        "--parent",
        "4242",
    ]


def test_main_reads_then_deletes_the_key(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be disabled"))
    key = tmp_path / "screen saver mode" / "helper.key"
    key.write_bytes(b"\x01secret\xff")
    seen: list = []
    conn = FakeConn(
        [protocol.make_request("disable", [PAD]), protocol.make_request("quit", [])]
    )
    runner = FakeRunner()

    def connect(pipe: str, authkey: bytes) -> FakeConn:
        seen.append((pipe, authkey, key.exists()))
        return conn

    code = helper.main(
        _args(tmp_path, journal, key),
        connect=connect,
        runner=runner,
        parent_alive=lambda: True,
    )
    assert code == 0
    assert seen == [("abc123", b"\x01secret\xff", False)]
    assert not key.exists()
    assert conn.closed
    assert runner.calls == [("disable", PAD)]
    log_file = tmp_path / "logs" / "device_helper.log"
    text = log_file.read_text("utf-8")
    assert PAD in text and "Ended: quit" in text


def test_main_empty_or_missing_key_does_not_connect(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, {})
    key = tmp_path / "helper.key"
    key.write_bytes(b"")

    def connect(pipe: str, authkey: bytes) -> None:
        raise AssertionError("connected")

    assert helper.main(_args(tmp_path, journal, key), connect=connect) == 2
    assert not key.exists()
    assert helper.main(_args(tmp_path, journal, key), connect=connect) == 2


def test_main_connect_failure_is_an_exit_code(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, {})
    key = tmp_path / "helper.key"
    key.write_bytes(b"k")

    def connect(pipe: str, authkey: bytes) -> None:
        raise ConnectionRefusedError("no pipe")

    assert helper.main(_args(tmp_path, journal, key), connect=connect) == 3


def test_log_path_is_under_the_data_folder(tmp_path: pathlib.Path) -> None:
    journal = tmp_path / "data" / "screen saver mode" / "devices.json"
    assert (
        helper.log_path(journal)
        == (tmp_path / "data" / "logs" / "device_helper.log").resolve()
    )


# The real runner never runs under test ---------------------------------------


def test_real_runner_refuses_under_pytest(no_real_pnputil: list) -> None:
    with pytest.raises(helper.RealRunnerBlocked):
        helper.real_runner("disable", PAD)
    assert no_real_pnputil == []


def test_main_defaults_to_the_real_runner_which_refuses(
    tmp_path: pathlib.Path, no_real_pnputil: list
) -> None:
    journal = _write_journal(tmp_path, _journal(pad="to be disabled"))
    key = tmp_path / "helper.key"
    key.write_bytes(b"k")
    conn = FakeConn([protocol.make_request("disable", [PAD])])
    with pytest.raises(helper.RealRunnerBlocked):
        helper.main(
            _args(tmp_path, journal, key),
            connect=lambda p, k: conn,
            parent_alive=lambda: True,
        )
    assert no_real_pnputil == []


def test_real_runner_command_line(monkeypatch: pytest.MonkeyPatch) -> None:
    # The command it would run, checked with subprocess faked and the test
    # guard lifted only for this call.
    seen: dict = {}

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        seen["command"] = command
        seen.update(kwargs)
        return subprocess.CompletedProcess(command, 0, b"", b"")

    monkeypatch.setattr(helper, "_under_test", lambda: False)
    monkeypatch.setattr(helper.os, "name", "nt")
    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setenv("SystemRoot", "C:\\Windows")
    assert helper.real_runner("disable", PAD) == "done"
    assert seen["command"][1:] == ["/disable-device", PAD]
    assert seen["command"][0].lower().endswith("system32\\pnputil.exe")
    assert seen["shell"] is False and seen["timeout"] == 30

    def timed_out(command: list[str], **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(command, 30)

    monkeypatch.setattr(subprocess, "run", timed_out)
    assert helper.real_runner("enable", PAD) == "error: pnputil took over 30 s"

    def failed(command: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(command, 5, b"Access is denied.\r\n", b"")

    monkeypatch.setattr(subprocess, "run", failed)
    assert (
        helper.real_runner("enable", PAD) == "error: pnputil exit 5: Access is denied."
    )


# Packaging ---------------------------------------------------------------------


def _spec_calls(func: str) -> list[ast.Call]:
    tree = ast.parse((_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8"))
    return [
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Name)
        and n.func.id == func
    ]


def _kw(call: ast.Call, name: str) -> ast.expr:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    raise AssertionError(name)


def test_spec_builds_the_helper_exe_with_admin_rights() -> None:
    helpers = [
        c
        for c in _spec_calls("EXE")
        if isinstance(_kw(c, "name"), ast.Name) and _kw(c, "name").id == "helper_name"
    ]
    assert len(helpers) == 1
    (call,) = helpers
    assert ast.literal_eval(_kw(call, "uac_admin")) is True
    assert ast.literal_eval(_kw(call, "console")) is False
    assert ast.literal_eval(_kw(call, "exclude_binaries")) is True
    spec = (_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8")
    assert 'helper_name = "Gremlin Device Helper"' in spec
    scripts = [ast.literal_eval(c.args[0]) for c in _spec_calls("Analysis")]
    assert ["gremlin_device_helper.py"] in scripts


def test_helper_shares_the_main_folder_and_tester_only_build_skips_it() -> None:
    collects = _spec_calls("COLLECT")
    main = [
        c
        for c in collects
        if isinstance(_kw(c, "name"), ast.Constant)
        and _kw(c, "name").value == "gremlin_platforms"
    ]
    (main_collect,) = main
    names = [a.id for a in main_collect.args if isinstance(a, ast.Name)]
    assert {"exe", "tester_exe", "helper_exe"} <= set(names)
    tester = [c for c in collects if isinstance(_kw(c, "name"), ast.Name)]
    (tester_collect,) = tester
    assert not any(
        isinstance(a, ast.Name) and a.id.startswith("helper")
        for a in tester_collect.args
    )
    # The helper's Analysis sits in the full-build branch, not the tester-only one.
    tree = ast.parse((_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8"))
    (branch,) = [
        n
        for n in tree.body
        if isinstance(n, ast.If)
        and isinstance(n.test, ast.Name)
        and n.test.id == "tester_only"
    ]
    assert "gremlin_device_helper.py" not in ast.unparse(ast.Module(branch.body, []))
    assert "gremlin_device_helper.py" in ast.unparse(ast.Module(branch.orelse, []))


def test_release_checks_the_helper_was_built() -> None:
    workflow = (_ROOT / ".github" / "workflows" / "release-exe.yml").read_text("utf-8")
    line = next(x for x in workflow.splitlines() if "foreach ($exe in" in x)
    for exe in (
        "gremlin_platforms.exe",
        "Gremlin Input Tester.exe",
        "Gremlin Device Helper.exe",
    ):
        assert f'"{exe}"' in line
