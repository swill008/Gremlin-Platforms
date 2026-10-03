# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import os
import subprocess
from typing import NoReturn

import pytest

import joystick_gremlin as jg


@pytest.mark.parametrize("name", ["gremlin_platforms.exe", "joystick_gremlin.exe"])
def test_installed_and_older_exe_count_as_gremlin(
    monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setattr(jg, "_process_image_name", lambda pid: name)
    assert jg._is_gremlin_process(1234, set())


def test_other_programs_do_not_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jg, "_process_image_name", lambda pid: "notepad.exe")
    assert not jg._is_gremlin_process(1234, {1234})


def test_python_counts_only_when_running_gremlin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(jg, "_process_image_name", lambda pid: "python.exe")
    assert jg._is_gremlin_process(1234, {1234})
    assert not jg._is_gremlin_process(1234, {99})


def test_process_query_asks_for_both_exe_names(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def fake_run(args: list[str], **kwargs: object) -> subprocess.CompletedProcess:
        seen.append(args[-1])
        return subprocess.CompletedProcess(args, 0, stdout="101\n\n202\n", stderr="")

    monkeypatch.setattr(jg.subprocess, "run", fake_run)
    assert jg._command_line_process_ids() == {101, 202}
    query = seen[0]
    assert "$_.Name -eq 'gremlin_platforms.exe'" in query
    assert "$_.Name -eq 'joystick_gremlin.exe'" in query
    assert "joystick_gremlin\\.py" in query


def test_starting_copy_never_finds_itself(monkeypatch: pytest.MonkeyPatch) -> None:
    me, parent, other = os.getpid(), 500, 700
    monkeypatch.setattr(jg, "_this_process_tree", lambda: {me, parent})
    # The exe query matches this copy and its launcher too.
    monkeypatch.setattr(jg, "_command_line_process_ids", lambda: {me, parent, other})
    monkeypatch.setattr(jg, "_window_process_ids", lambda: {other})
    monkeypatch.setattr(jg, "_lock_owner_pid", lambda: me)
    assert jg._other_gremlin_pids() == [other]


def test_alone_finds_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    me = os.getpid()
    monkeypatch.setattr(jg, "_this_process_tree", lambda: {me})
    monkeypatch.setattr(jg, "_command_line_process_ids", lambda: {me})
    monkeypatch.setattr(jg, "_window_process_ids", lambda: set())
    monkeypatch.setattr(jg, "_lock_owner_pid", lambda: None)
    assert jg._other_gremlin_pids() == []


class _AppStarted(BaseException):
    """The fake app's "start-up reached" signal: not an error, so main()'s
    could-not-start handling (which catches Exception) lets it through."""



def _fake_app(*args: object, **kwargs: object) -> NoReturn:
    raise _AppStarted


def _stub_main(
    monkeypatch: pytest.MonkeyPatch, choice: str, locks: list, windows: list[str]
) -> dict[str, list]:
    calls: dict[str, list] = {"prompt": [], "terminate": []}
    monkeypatch.setattr(jg, "acquire_instance_lock", lambda: locks.pop(0))
    monkeypatch.setattr(jg, "_gremlin_window_titles", lambda: windows)
    monkeypatch.setattr(jg, "_other_gremlin_pids", lambda: [700])

    def prompt(lock_held: bool, wins: list[str], pids: list[int]) -> str:
        calls["prompt"].append((lock_held, wins, pids))
        return choice

    monkeypatch.setattr(jg, "_confirm_second_instance", prompt)
    monkeypatch.setattr(
        jg, "_terminate_other_gremlin", lambda pids: calls["terminate"].append(pids)
    )
    monkeypatch.setattr(jg, "JoystickGremlinApp", _fake_app)
    return calls


def test_main_cancel_does_not_start(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_main(monkeypatch, "quit", [None], [])
    assert jg.main() == 0
    assert calls["prompt"] == [(True, [], [700])]
    assert calls["terminate"] == []


def test_main_close_others_closes_then_takes_the_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    locks = [None, "lock"]
    calls = _stub_main(monkeypatch, "close_others", locks, ["Gremlin-Platforms R1"])
    with pytest.raises(_AppStarted):
        jg.main()
    assert calls["terminate"] == [[700]]
    assert locks == []


def test_main_continue_starts_without_closing(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_main(monkeypatch, "continue", [None], [])
    with pytest.raises(_AppStarted):
        jg.main()
    assert calls["terminate"] == []


def test_main_alone_does_not_ask(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = _stub_main(monkeypatch, "quit", ["lock"], [])
    with pytest.raises(_AppStarted):
        jg.main()
    assert calls["prompt"] == []
