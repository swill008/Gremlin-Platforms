# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Screen Saver Mode S21-S27: the journal and the disable/enable flows
(gremlin/device_disable.py). Every Windows seam is faked: no device is
disabled or enabled, nothing is elevated, no helper starts."""

from __future__ import annotations

import json
import os
import threading
from collections.abc import Iterator
from pathlib import Path
from typing import IO, Any

import pytest

from gremlin import device_disable as dd
from gremlin import device_helper_protocol as protocol

KB = "HID\\VID_046D&PID_C52B&MI_00\\7&1A2B3C4D&0&0000"
PAD = "HID\\VID_045E&PID_0B13\\8&2222&0&0000"
WHEEL = "HID\\VID_346E&PID_0006\\9&3333&0&0000"
OTHER = "HID\\VID_1234&PID_5678\\1&4444&0&0000"


class FakeConn:
    """The helper's side: applies allowed requests to the fake Windows
    status, recording the journal file as it was when each request came."""

    def __init__(self, windows: FakeWindows, journal_file: str) -> None:
        self.windows = windows
        self.journal_file = journal_file
        self.requests: list[dict] = []
        self.journal_at_request: list[dict] = []
        self.answer: dict | None = None
        self.fail_ids: set[str] = set()
        self.closed = False
        self.silent = False

    def send(self, req: dict) -> None:
        if self.closed:
            raise OSError("closed")
        self.requests.append(req)
        try:
            with open(self.journal_file, encoding="utf-8") as fh:
                journal = json.load(fh)
        except FileNotFoundError:
            journal = {}
        self.journal_at_request.append(journal)
        if self.silent:
            self.answer = None
            return
        allowed, results = protocol.check_request(req, journal)
        for device_id in allowed:
            if device_id in self.fail_ids:
                results[device_id] = "error: pnputil exit code 1"
                continue
            self.windows.status[device_id] = (
                dd.DISABLED if req["op"] == "disable" else dd.ENABLED
            )
            results[device_id] = "done"
        self.answer = {"ok": True, "results": results}

    def poll(self, timeout: float = 0.0) -> bool:
        return self.answer is not None

    def recv(self) -> dict:
        answer, self.answer = self.answer, None
        assert answer is not None
        return answer

    def close(self) -> None:
        self.closed = True


class FakeListener:
    def __init__(self, conn: FakeConn | None) -> None:
        self.conn = conn
        self.closed = threading.Event()

    def accept(self) -> FakeConn:
        if self.conn is None:
            self.closed.wait(5)
            raise OSError("listener closed")
        return self.conn

    def close(self) -> None:
        self.closed.set()


class FakeProcess:
    def __init__(self) -> None:
        self.alive = True

    def running(self) -> bool:
        return self.alive

    def close(self) -> None:
        pass


class FakeWindows:
    def __init__(self) -> None:
        self.status: dict[str, str] = {}
        self.parents: dict[str, str] = {}
        self.parent_calls: list[str] = []
        self.launches: list[tuple[str, str]] = []
        self.refuse = False
        self.connect = True
        self.conn: FakeConn | None = None
        self.listener: FakeListener | None = None
        self.listener_address = ""

    def read(self, device_id: str) -> str:
        return self.status.get(device_id, dd.NOT_PRESENT)

    def parent(self, device_id: str) -> str:
        self.parent_calls.append(device_id)
        found = self.parents.get(device_id, "")
        if isinstance(found, Exception):
            raise found
        return found

    def launch(self, file: str, parameters: str) -> FakeProcess:
        self.launches.append((file, parameters))
        if self.refuse:
            raise dd.Refused()
        return FakeProcess()

    def listen(self, address: str, authkey: bytes) -> FakeListener:
        assert address.startswith(protocol.PIPE_PREFIX)
        self.listener_address = address
        assert len(authkey) >= 16
        self.listener = FakeListener(self.conn if self.connect else None)
        return self.listener


Env = tuple[dd.DeviceDisabler, FakeWindows, str]


@pytest.fixture
def env(tmp_path: Path) -> Iterator[Env]:
    windows = FakeWindows()
    journal_file = str(tmp_path / "screen saver mode" / "devices.json")
    windows.conn = FakeConn(windows, journal_file)
    disabler = dd.DeviceDisabler(
        journal_file=journal_file,
        key_file=str(tmp_path / "screen saver mode" / "helper.key"),
        launcher=windows.launch,
        listener_factory=windows.listen,
        status_reader=windows.read,
        parent_lookup=windows.parent,
        connect_timeout_s=1.0,
    )
    yield disabler, windows, journal_file
    disabler.stop_helper()


def _start(disabler: dd.DeviceDisabler) -> tuple[bool, str]:
    got: list[tuple[bool, str]] = []
    done = threading.Event()

    def on_done(ok: bool, error: str) -> None:
        got.append((ok, error))
        done.set()

    disabler.start_helper(on_done)
    assert done.wait(10), "start_helper never called on_done"
    return got[0]


def _journal(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _settle(disabler: dd.DeviceDisabler) -> None:
    assert disabler.wait_idle(10)


# The helper ----------------------------------------------------------------


def test_start_helper_connects_and_pings(env: Env) -> None:
    disabler, windows, _ = env
    assert _start(disabler) == (True, "")
    assert disabler.helper_running()
    assert disabler.status_text() == ""
    assert windows.conn.requests == [protocol.make_request("ping", [])]
    file, params = windows.launches[0]
    for arg in ("--pipe", "--journal", "--key", "--parent"):
        assert arg in params
    assert file and params


def test_key_file_holds_the_authkey(env: Env, tmp_path: Path) -> None:
    disabler, windows, _ = env
    seen: list[bytes] = []
    real_listen = windows.listen

    def listen(address: str, authkey: bytes) -> FakeListener:
        seen.append(authkey)
        return real_listen(address, authkey)

    disabler._listener_factory = listen
    _start(disabler)
    assert (tmp_path / "screen saver mode" / "helper.key").read_bytes() == seen[0]
    pipe_arg = windows.launches[0][1].split("--pipe ")[1].split()[0].strip('"')
    assert protocol.PIPE_PREFIX + pipe_arg == windows.listener_address


def test_refused_reports_false_and_status_text(env: Env) -> None:
    disabler, windows, _ = env
    windows.refuse = True
    ok, error = _start(disabler)
    assert not ok
    assert "refused" in error
    assert not disabler.helper_running()
    text = disabler.status_text()
    assert text.startswith(dd.HELPER_NOT_RUNNING_TEXT)
    assert "refused" in text
    assert windows.listener.closed.is_set()


def test_no_connection_times_out(env: Env) -> None:
    disabler, windows, _ = env
    windows.connect = False
    ok, error = _start(disabler)
    assert not ok and error == dd.NO_CONNECTION_TEXT
    assert disabler.status_text().startswith(dd.HELPER_NOT_RUNNING_TEXT)


def test_status_text_empty_when_not_wanted(env: Env) -> None:
    disabler, windows, _ = env
    assert disabler.status_text() == ""
    windows.refuse = True
    _start(disabler)
    disabler.stop_helper()
    assert disabler.status_text() == ""


def test_stop_helper_sends_quit(env: Env) -> None:
    disabler, windows, _ = env
    _start(disabler)
    disabler.stop_helper()
    assert windows.conn.requests[-1] == protocol.make_request("quit", [])
    assert not disabler.helper_running()


# Disable -------------------------------------------------------------------


def test_disable_journal_written_before_the_request(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status.update({KB: dd.ENABLED, PAD: dd.ENABLED})
    _start(disabler)
    disabler.disable([("Keyboard", KB), ("Pad", PAD)])
    _settle(disabler)
    req = windows.conn.requests[-1]
    assert req == protocol.make_request("disable", [KB, PAD])
    at_request = windows.conn.journal_at_request[-1]
    assert at_request[KB]["state"] == "to be disabled"
    assert at_request[PAD]["state"] == "to be disabled"
    assert at_request[KB]["name"] == "Keyboard"
    after = _journal(journal_file)
    assert after[KB]["state"] == "disabled"
    assert after[PAD]["state"] == "disabled"
    assert after[KB]["time"]


def test_disable_failure_and_partial(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status.update({KB: dd.ENABLED, PAD: dd.ENABLED})
    windows.conn.fail_ids = {PAD}
    _start(disabler)
    disabler.disable([("Keyboard", KB), ("Pad", PAD)])
    _settle(disabler)
    after = _journal(journal_file)
    assert after[KB]["state"] == "disabled"
    assert after[PAD]["state"] == "disable failed"
    assert "pnputil" in after[PAD]["result"]
    assert "enabled" in after[PAD]["result"]


def test_disable_state_comes_from_windows_not_the_helper(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status[KB] = dd.ENABLED
    _start(disabler)
    real_send = windows.conn.send

    def lying_send(req: dict) -> None:
        real_send(req)
        if req["op"] == "disable":
            windows.status[KB] = dd.ENABLED  # "done" but Windows says no

    windows.conn.send = lying_send
    disabler.disable([("Keyboard", KB)])
    _settle(disabler)
    assert _journal(journal_file)[KB]["state"] == "disable failed"


def test_disable_skips_device_disabled_outside_gremlin(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status.update({KB: dd.ENABLED, OTHER: dd.DISABLED})
    _start(disabler)
    disabler.disable([("Keyboard", KB), ("Other", OTHER)])
    _settle(disabler)
    assert OTHER not in _journal(journal_file)
    assert OTHER not in windows.conn.requests[-1]["ids"]


def test_disable_skips_bad_ids_and_absent_devices(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status[KB] = dd.ENABLED
    _start(disabler)
    disabler.disable([("Bad", 'USB\\X" & del'), ("Gone", WHEEL), ("Keyboard", KB)])
    _settle(disabler)
    assert set(_journal(journal_file)) == {KB}
    assert windows.conn.requests[-1]["ids"] == [KB]


def test_disable_does_nothing_without_the_helper(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status[KB] = dd.ENABLED
    disabler.disable([("Keyboard", KB)])
    _settle(disabler)
    assert not os.path.exists(journal_file)
    assert windows.status[KB] == dd.ENABLED


def test_helper_gone_mid_request_marks_failed_and_drops(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.status[KB] = dd.ENABLED
    _start(disabler)
    windows.conn.silent = True
    disabler.disable([("Keyboard", KB)])
    _settle(disabler)
    assert _journal(journal_file)[KB]["state"] == "disable failed"
    assert not disabler.helper_running()


# Enable --------------------------------------------------------------------


def _disabled(
    disabler: dd.DeviceDisabler, windows: FakeWindows, *devices: tuple[str, str]
) -> None:
    for _name, device_id in devices:
        windows.status[device_id] = dd.ENABLED
    _start(disabler)
    disabler.disable(list(devices))
    _settle(disabler)


def test_enable_only_journal_ids(env: Env) -> None:
    disabler, windows, journal_file = env
    _disabled(disabler, windows, ("Keyboard", KB), ("Pad", PAD))
    windows.status[OTHER] = dd.DISABLED  # the user's own
    disabler.enable_pending()
    _settle(disabler)
    req = windows.conn.requests[-1]
    assert req["op"] == "enable"
    assert sorted(req["ids"]) == sorted([KB, PAD])
    for sent in windows.conn.requests:
        assert OTHER not in sent["ids"]
    at_request = windows.conn.journal_at_request[-1]
    assert at_request[KB]["state"] == "to be enabled"
    after = _journal(journal_file)
    assert after[KB]["state"] == after[PAD]["state"] == "enabled"
    assert windows.status[OTHER] == dd.DISABLED


def test_enable_skips_already_enabled_entries(env: Env) -> None:
    disabler, windows, _ = env
    _disabled(disabler, windows, ("Keyboard", KB))
    disabler.enable_pending()
    _settle(disabler)
    count = len(windows.conn.requests)
    disabler.enable_pending()
    _settle(disabler)
    assert len(windows.conn.requests) == count


def test_not_present_stays_pending_and_arrival_retries(env: Env) -> None:
    disabler, windows, journal_file = env
    _disabled(disabler, windows, ("Keyboard", KB), ("Wheel", WHEEL))
    windows.status[WHEEL] = dd.NOT_PRESENT  # unplugged while off
    disabler.enable_pending()
    _settle(disabler)
    after = _journal(journal_file)
    assert after[KB]["state"] == "enabled"
    assert after[WHEEL]["state"] == "to be enabled"
    assert WHEEL not in windows.conn.requests[-1]["ids"]
    windows.status[WHEEL] = dd.DISABLED  # plugged in again
    disabler.on_device_arrival()
    _settle(disabler)
    assert windows.conn.requests[-1] == protocol.make_request("enable", [WHEEL])
    assert _journal(journal_file)[WHEEL]["state"] == "enabled"


def test_arrival_does_nothing_when_nothing_pending(env: Env) -> None:
    disabler, windows, _ = env
    _disabled(disabler, windows, ("Keyboard", KB))
    disabler.enable_pending()
    _settle(disabler)
    count = len(windows.conn.requests)
    disabler.on_device_arrival()
    _settle(disabler)
    assert len(windows.conn.requests) == count


def test_enable_failure_is_recorded_and_retried(env: Env) -> None:
    disabler, windows, journal_file = env
    _disabled(disabler, windows, ("Keyboard", KB))
    windows.conn.fail_ids = {KB}
    disabler.enable_pending()
    _settle(disabler)
    assert _journal(journal_file)[KB]["state"] == "enable failed"
    windows.conn.fail_ids = set()
    disabler.enable_pending()
    _settle(disabler)
    assert _journal(journal_file)[KB]["state"] == "enabled"


# Recovery at start (S24) -----------------------------------------------------


def _write(journal_file: str, entries: dict) -> None:
    os.makedirs(os.path.dirname(journal_file), exist_ok=True)
    with open(journal_file, "w", encoding="utf-8") as fh:
        json.dump(entries, fh)


def _entry(name: str, state: str) -> dict:
    return {"name": name, "state": state, "time": "", "result": ""}


def test_recover_at_start_enables_everything_not_enabled(env: Env) -> None:
    disabler, windows, journal_file = env
    _write(
        journal_file,
        {
            KB: _entry("Keyboard", "to be disabled"),
            PAD: _entry("Pad", "disabled"),
            WHEEL: _entry("Wheel", "enabled"),
        },
    )
    windows.status.update({KB: dd.DISABLED, PAD: dd.DISABLED, WHEEL: dd.ENABLED})
    windows.status[OTHER] = dd.DISABLED
    disabler.recover_at_start()
    for _ in range(100):
        if disabler.helper_running() and windows.conn.requests[-1]["op"] == "enable":
            break
        threading.Event().wait(0.05)
    _settle(disabler)
    assert windows.launches
    enables = [r for r in windows.conn.requests if r["op"] == "enable"]
    assert len(enables) == 1
    assert sorted(enables[0]["ids"]) == sorted([KB, PAD])
    after = _journal(journal_file)
    assert all(e["state"] == "enabled" for e in after.values())
    assert windows.status[OTHER] == dd.DISABLED


def test_recover_at_start_does_nothing_when_all_enabled(env: Env) -> None:
    disabler, windows, journal_file = env
    _write(journal_file, {KB: _entry("Keyboard", "enabled")})
    disabler.recover_at_start()
    _settle(disabler)
    assert windows.launches == []


def test_recover_refused_leaves_journal_and_says_so(env: Env) -> None:
    disabler, windows, journal_file = env
    _write(journal_file, {KB: _entry("Keyboard", "disabled")})
    windows.refuse = True
    disabler.recover_at_start()
    for _ in range(100):
        if disabler.status_text():
            break
        threading.Event().wait(0.05)
    assert "refused" in disabler.status_text()
    assert _journal(journal_file)[KB]["state"] == "disabled"


# The journal ---------------------------------------------------------------


def test_journal_states_are_the_protocol_states(tmp_path: Path) -> None:
    journal = dd.Journal(str(tmp_path / "j.json"))
    with pytest.raises(ValueError):
        journal.set(KB, "Keyboard", "off")
    for state in protocol.STATES:
        journal.set(KB, "Keyboard", state)
        journal.save()
        assert dd.Journal(journal.path).load().state(KB) == state


def test_atomic_save_survives_crash_mid_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = str(tmp_path / "j.json")
    journal = dd.Journal(path)
    journal.set(KB, "Keyboard", "disabled")
    journal.save()

    def broken_dump(obj: object, fh: IO[str], **kwargs: object) -> None:
        fh.write('{"half": ')
        raise OSError("power cut")

    monkeypatch.setattr(dd.json, "dump", broken_dump)
    journal.set(KB, "Keyboard", "to be enabled")
    with pytest.raises(OSError):
        journal.save()
    monkeypatch.undo()
    assert dd.Journal(path).load().state(KB) == "disabled"


def test_atomic_save_survives_crash_before_replace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = str(tmp_path / "j.json")
    journal = dd.Journal(path)
    journal.set(KB, "Keyboard", "disabled")
    journal.save()

    def no_replace(src: str, dst: str) -> None:
        raise OSError("crash")

    monkeypatch.setattr(dd.os, "replace", no_replace)
    journal.set(KB, "Keyboard", "to be enabled")
    with pytest.raises(OSError):
        journal.save()
    monkeypatch.undo()
    assert dd.Journal(path).load().state(KB) == "disabled"


def test_unreadable_journal_is_kept_aside(tmp_path: Path) -> None:
    path = tmp_path / "j.json"
    path.write_text("{not json", encoding="utf-8")
    assert dd.Journal(str(path)).load().entries == {}
    assert (tmp_path / "j.json.bad").exists()


# Nothing real ----------------------------------------------------------------


def test_real_seams_refuse_under_pytest() -> None:
    with pytest.raises(dd.RealCallBlocked):
        dd.device_status(KB)
    with pytest.raises(dd.RealCallBlocked):
        dd.physical_parent(KB)
    with pytest.raises(dd.RealCallBlocked):
        dd._real_launcher("x.exe", "")
    with pytest.raises(dd.RealCallBlocked):
        dd._PipeListener(protocol.PIPE_PREFIX + "test", b"k" * 32)


def test_manager_is_one_instance_with_real_seams() -> None:
    one = dd.manager()
    assert one is dd.manager()
    assert one._launcher is dd._real_launcher
    assert one._status is dd.device_status
    assert one._parent is dd.physical_parent
    assert one._listener_factory is dd._PipeListener


def test_helper_command_from_source_runs_the_script() -> None:
    file, params = dd.helper_command("ab", "J", "K")
    assert file == dd.sys.executable
    assert dd.HELPER_SCRIPT in params
    assert f"--parent {os.getpid()}" in params


def test_helper_command_frozen_uses_the_exe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(dd.sys, "frozen", True, raising=False)
    file, params = dd.helper_command("ab", "J", "K")
    assert os.path.basename(file) == dd.HELPER_EXE
    assert dd.HELPER_SCRIPT not in params


# ----- the real pipe listener's close (found on the user's PC 2026-11-16)


class _MpListener:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


def _pipe_listener(accepting: bool) -> tuple[Any, _MpListener]:
    """A _PipeListener without a real pipe (its constructor refuses tests)."""
    listener = object.__new__(dd._PipeListener)
    inner = _MpListener()
    listener._address = protocol.PIPE_PREFIX + "test"
    listener._authkey = b"k" * 32
    listener._listener = inner
    listener._closed = False
    listener._accepting = accepting
    return listener, inner


def test_close_after_the_helper_connected_does_not_wait(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Quitting with the helper connected hung: close() connected to its own
    pipe and waited for a key handshake nobody answers."""
    import multiprocessing.connection as mpc

    calls: list[object] = []
    never = threading.Event()

    def client(*args: object, **kwargs: object) -> None:
        calls.append(kwargs.get("authkey"))
        never.wait(5)  # the handshake that never comes
        raise OSError("no answer")

    monkeypatch.setattr(mpc, "Client", client)
    listener, inner = _pipe_listener(accepting=False)
    done = threading.Event()
    worker = threading.Thread(target=lambda: (listener.close(), done.set()))
    worker.start()
    finished = done.wait(2)
    never.set()
    worker.join(6)
    assert finished, "close() waited on its own pipe"
    assert calls == [] and inner.closed


def test_close_while_waiting_wakes_accept_without_a_handshake(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import multiprocessing.connection as mpc

    calls: list[object] = []

    class _Conn:
        def close(self) -> None:
            pass

    def client(*args: object, **kwargs: object) -> _Conn:
        calls.append(kwargs.get("authkey"))
        return _Conn()

    monkeypatch.setattr(mpc, "Client", client)
    listener, inner = _pipe_listener(accepting=True)
    listener.close()
    assert calls == [None] and inner.closed


# The physical device (S21, D-12-SSM-PARENT-AND-IN-USE) ----------------------

STEAM_USB = "USB\\VID_28DE&PID_1205\\ABC123"
STEAM_MOUSE = "HID\\VID_28DE&PID_1205&MI_00&COL01\\7&AA&0&0000"
STEAM_KB = "HID\\VID_28DE&PID_1205&MI_00&COL02\\7&AA&0&0001"
BT_PAD = "BTHENUM\\{00001124-0000-1000-8000-00805F9B34FB}_VID&0002045E\\9&BB"


def test_disable_uses_the_physical_usb_device(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.parents[KB] = "usb\\vid_046d&pid_c52b\\5&1"
    usb = "USB\\VID_046D&PID_C52B\\5&1"
    windows.status[usb] = dd.ENABLED
    _start(disabler)
    disabler.disable([("Keyboard", KB)])
    _settle(disabler)
    assert windows.conn.requests[-1]["ids"] == [usb]
    entries = _journal(journal_file)
    assert set(entries) == {usb}
    assert entries[usb]["name"] == "Keyboard"
    assert entries[usb]["state"] == dd.DISABLED


def test_parts_of_one_device_become_one_entry(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.parents[STEAM_MOUSE] = STEAM_USB
    windows.parents[STEAM_KB] = STEAM_USB
    windows.status[STEAM_USB] = dd.ENABLED
    _start(disabler)
    disabler.disable([("Steam mouse", STEAM_MOUSE), ("Steam keyboard", STEAM_KB)])
    _settle(disabler)
    assert windows.conn.requests[-1]["ids"] == [STEAM_USB]
    entries = _journal(journal_file)
    assert list(entries) == [STEAM_USB]
    assert entries[STEAM_USB]["name"] == "Steam mouse"


@pytest.mark.parametrize(
    "parent", ["", BT_PAD, 'USB\\X" /enable-device', OSError("cfgmgr32 failed")]
)
def test_unknown_or_non_usb_parent_disables_the_part(env: Env, parent: object) -> None:
    disabler, windows, journal_file = env
    windows.parents[PAD] = parent  # type: ignore[assignment]
    windows.status[PAD] = dd.ENABLED
    windows.status[BT_PAD] = dd.ENABLED
    _start(disabler)
    disabler.disable([("Pad", PAD)])
    _settle(disabler)
    assert windows.parent_calls == [PAD]
    assert windows.conn.requests[-1]["ids"] == [PAD]
    assert set(_journal(journal_file)) == {PAD}


def test_protected_parent_disables_only_the_part(env: Env) -> None:
    disabler, windows, journal_file = env
    windows.parents[STEAM_MOUSE] = STEAM_USB
    windows.parents[STEAM_KB] = STEAM_USB
    windows.status[STEAM_MOUSE] = dd.ENABLED
    windows.status[STEAM_KB] = dd.ENABLED
    windows.status[STEAM_USB] = dd.ENABLED
    disabler.set_protected([STEAM_USB.lower()])
    _start(disabler)
    disabler.disable([("Steam mouse", STEAM_MOUSE), ("Steam keyboard", STEAM_KB)])
    _settle(disabler)
    assert windows.conn.requests[-1]["ids"] == [STEAM_MOUSE, STEAM_KB]
    assert STEAM_USB not in _journal(journal_file)
    # Unticked again: the physical device is disabled next time.
    disabler.set_protected([])
    windows.status[STEAM_MOUSE] = dd.ENABLED
    windows.status[STEAM_KB] = dd.ENABLED
    disabler.enable_pending()
    _settle(disabler)
    disabler.disable([("Steam mouse", STEAM_MOUSE)])
    _settle(disabler)
    assert windows.conn.requests[-1]["ids"] == [STEAM_USB]


def test_parent_journal_round_trip_and_old_hid_entries(env: Env) -> None:
    disabler, windows, journal_file = env
    _write(journal_file, {KB: _entry("Old keyboard", dd.DISABLED)})
    windows.status[KB] = dd.DISABLED
    windows.parents[STEAM_MOUSE] = STEAM_USB
    windows.status[STEAM_USB] = dd.ENABLED
    _start(disabler)
    disabler.disable([("Steam mouse", STEAM_MOUSE)])
    _settle(disabler)
    assert _journal(journal_file)[STEAM_USB]["state"] == dd.DISABLED
    disabler.enable_pending()
    _settle(disabler)
    assert set(windows.conn.requests[-1]["ids"]) == {KB, STEAM_USB}
    entries = _journal(journal_file)
    assert entries[STEAM_USB]["state"] == dd.ENABLED
    assert entries[KB]["state"] == dd.ENABLED
