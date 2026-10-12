# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""One Input Tester at a time (02 S110, D-02-TESTER-ONE-OPEN): an Input
Tester command while the tester this program started is open writes
expected.json again and raises that window instead of starting another;
after it closes a press starts a new one; Restart Input Tester (S118)
always starts a fresh one. Fake starter and raiser: no real process or
window is touched."""

from __future__ import annotations

import json
import pathlib
from collections.abc import Iterator
from types import SimpleNamespace

import pytest

from gremlin import input_tester_link as link
from gremlin.ui import hidhide as hh


class _Proc:
    """A started tester: running until ended."""

    def __init__(self, pid: int) -> None:
        self.pid = pid
        self.ended = False

    def poll(self) -> int | None:
        return 0 if self.ended else None


@pytest.fixture
def env(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SimpleNamespace]:
    exe = tmp_path / "Gremlin Input Tester.exe"
    exe.write_bytes(b"MZ")
    writes: list[int] = []

    def build() -> dict:
        writes.append(1)
        return {"version": 1, "write": len(writes)}

    monkeypatch.setattr(link, "tester_path", lambda: exe)
    monkeypatch.setattr(link, "gremlin_dir", lambda: tmp_path)
    monkeypatch.setattr(link, "build_expected", build)
    monkeypatch.setattr(link, "_start_watch", lambda: None)
    link._reset_for_tests()
    started: list[_Proc] = []
    raised: list[int] = []

    def starter(_exe: str, _args: list[str]) -> _Proc:
        started.append(_Proc(1000 + len(started)))
        return started[-1]

    link.set_starter(starter)
    link.set_raiser(raised.append)
    yield SimpleNamespace(started=started, raised=raised, writes=writes, dir=tmp_path)
    link._reset_for_tests()


def _expected(env: SimpleNamespace) -> dict:
    path = env.dir / "tester" / "expected.json"
    return json.loads(path.read_text("utf-8"))


def test_second_press_raises_the_open_tester(env: SimpleNamespace) -> None:
    assert link.launch() == ""
    assert len(env.started) == 1 and env.raised == []
    assert link.launch() == ""
    assert len(env.started) == 1  # no second tester
    assert env.raised == [1000]
    assert _expected(env)["write"] == 2  # expected.json written again
    # The QML command path (toolbar, Tools › Viewers) is the same owner.
    assert link.InputTesterLink().launch() == ""
    assert len(env.started) == 1 and env.raised == [1000, 1000]


def test_after_the_tester_closes_a_press_starts_a_new_one(
    env: SimpleNamespace,
) -> None:
    link.launch()
    env.started[0].ended = True
    assert link.launch() == ""
    assert len(env.started) == 2 and env.raised == []


def test_restart_always_starts_a_fresh_one(env: SimpleNamespace) -> None:
    link.launch()
    assert link.launch(fresh=True) == ""
    assert len(env.started) == 2 and env.raised == []


def test_hidhide_page_buttons(env: SimpleNamespace) -> None:
    """Input Tester raises the open one; Restart Input Tester starts anew."""
    page = SimpleNamespace(
        _tester_message="x", changed=SimpleNamespace(emit=lambda: None)
    )
    page._launch_tester = lambda fresh: hh.HidHideModel._launch_tester(page, fresh)
    assert hh.HidHideModel.openInputTester(page) == ""  # type: ignore[arg-type]
    assert hh.HidHideModel.openInputTester(page) == ""  # type: ignore[arg-type]
    assert len(env.started) == 1 and env.raised == [1000]
    assert hh.HidHideModel.restartInputTester(page) == ""  # type: ignore[arg-type]
    assert len(env.started) == 2 and env.raised == [1000]


def test_a_raise_failure_is_not_a_message(env: SimpleNamespace) -> None:
    link.launch()

    def boom(_pid: int) -> None:
        raise OSError("no window")

    link.set_raiser(boom)
    assert link.launch() == ""
    assert len(env.started) == 1
