# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Input Tester logs (D-02-INPUT-TESTER addendum 2026-10-10, items 1-3, 7):
tester.log lines and rotation, plain mode in memory, the Logs tab sources
(tail, find, follow, warnings), stale_since, restart, follow input."""

from __future__ import annotations

import datetime
import json
import pathlib
import sys
from dataclasses import dataclass
from typing import Any

sys.path.append(".")


from gremlin.input_tester import compare as cmp
from gremlin.input_tester import log as tester_log
from gremlin.input_tester import logfiles
from gremlin.input_tester import model as model_mod
from gremlin.input_tester.devices import LiveValues, SeenDevice
from gremlin.input_tester.model import InputTesterModel

START = datetime.datetime(2026, 10, 10, 4, 2, 10, 114000)


@dataclass
class FakeSkip:
    path: str
    name: str = ""
    vid: int = 0
    pid: int = 0
    reason: str = ""
    code: int = 0

    @property
    def denied(self) -> bool:
        return self.code == 5


@dataclass
class FakeOpen:
    kind: str
    name: str
    instance: str
    ok: bool
    code: int = 0
    text: str = ""
    left_out: str = ""


DENIED_PATH = r"\\?\hid#vid_231d&pid_0200#a&6b6f223"
OPENS = [
    FakeOpen("directinput", "vJoy Device", "{AAAA}", True, 0, "values read ok"),
    FakeOpen(
        "hid", "VKBsim Gladiator EVO R", DENIED_PATH, False, 5, "access denied (5)"
    ),
    FakeOpen(
        "hid",
        "Keyboard",
        r"\\?\hid#kbd",
        True,
        0,
        "ok",
        "not a game device (usage page 0x0001, usage 0x0006)",
    ),
    FakeOpen(
        "hid",
        "Odd",
        r"\\?\hid#odd",
        False,
        31,
        "error 31: A device attached is not functioning.",
    ),
]
SKIPS = [
    FakeSkip(
        DENIED_PATH, "VKBsim Gladiator EVO R", 0x231D, 0x0200, "access denied (5)", 5
    ),
    FakeSkip(
        r"\\?\hid#kbd",
        "Keyboard",
        1,
        2,
        "not a game device (usage page 0x0001, usage 0x0006)",
        0,
    ),
]


class Devs:
    """Two fake DirectInput sticks whose values a test sets."""

    def __init__(self) -> None:
        self.list = [
            SeenDevice(
                "di:{A}", "directinput", "Stick A", axes=2, buttons=4, axis_ids=[1, 2]
            ),
            SeenDevice(
                "di:{B}", "directinput", "Stick B", axes=2, buttons=4, axis_ids=[1, 2]
            ),
        ]
        self.values = {
            d.key: LiveValues([0.0, 0.0], [False] * 4, []) for d in self.list
        }

    def poll(self, device: SeenDevice) -> LiveValues:
        v = self.values[device.key]
        return LiveValues(list(v.axes), list(v.buttons), list(v.hats))


def make(
    gremlin_dir: str | None = None,
    *,
    devs: Devs | None = None,
    now: list | None = None,
    clock: list | None = None,
    **kw: Any,  # noqa: ANN401
) -> InputTesterModel:
    devs = devs or Devs()
    exe_dir = kw.pop("exe_dir", None) or str(pathlib.Path(gremlin_dir or ".").resolve())
    times = now if now is not None else [START]
    ticks = clock if clock is not None else [0.0]
    kw.setdefault("hid_scan", lambda: ([], list(SKIPS)))
    kw.setdefault("open_results", lambda: list(OPENS))
    return InputTesterModel(
        gremlin_dir,
        snapshot=lambda: list(devs.list),
        poll=devs.poll,
        steam_running=lambda: False,
        clock=lambda: ticks[0],
        now=lambda: times[0],
        start_timers=False,
        exe_dir=exe_dir,
        **kw,
    )


def write_expected(gremlin_dir: pathlib.Path, **extra: object) -> pathlib.Path:
    path = gremlin_dir / "tester" / "expected.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "written": "2026-10-10T04:02:09",
        "hidhide": {
            "present": True,
            "cloak": True,
            "mode": "block",
            "tester_on_list": True,
            "apps": [],
        },
        "sticks": [],
        "vjoy": [],
        "xbox": [],
    }
    data.update(extra)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# tester.log (item 2) ----------------------------------------------------------


def test_tester_log_lines_include_access_denied(qapp, tmp_path) -> None:  # noqa: ANN001
    write_expected(tmp_path)
    make(str(tmp_path))
    text = (tmp_path / "tester" / "tester.log").read_text(encoding="utf-8")
    lines = text.splitlines()
    assert all(line[:12] == "04:02:10.114" and line[12:14] == "  " for line in lines)
    assert "Started · " in lines[0] and "compared with Gremlin" in lines[0]
    assert any(
        "HidHide (from Gremlin): cloak on · Block list · this tester is on the list"
        in line
        for line in lines
    )
    assert any(
        line.endswith("DirectInput vJoy Device · listed · values read ok")
        for line in lines
    )
    assert any(
        f"HID VKBsim Gladiator EVO R {DENIED_PATH} · open → access denied (5): "
        "refused, HidHide is hiding it from this program" in line
        for line in lines
    )
    assert any(
        "Keyboard" in line and "open → ok · left out: not a game device" in line
        for line in lines
    )
    assert any(
        "error 31: A device attached" in line and tester_log.WARN_MARK in line
        for line in lines
    )
    assert any("Result: " in line for line in lines)


def test_open_results_logged_once(qapp, tmp_path) -> None:  # noqa: ANN001
    write_expected(tmp_path)
    model = make(str(tmp_path))
    model.refresh()
    text = (tmp_path / "tester" / "tester.log").read_text(encoding="utf-8")
    assert text.count("VKBsim Gladiator EVO R") == 1


def test_rotation_at_one_megabyte(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "tester" / "tester.log"
    log = tester_log.TesterLog(path, now=lambda: START)
    assert tester_log.MAX_BYTES == 1024 * 1024
    chunk = "x" * 1000
    for _ in range(1100):
        log.add(chunk)
    older = path.with_name("tester.log.1")
    assert older.is_file()
    assert path.stat().st_size <= tester_log.MAX_BYTES
    assert older.stat().st_size <= tester_log.MAX_BYTES
    assert older.stat().st_size > tester_log.MAX_BYTES - 2000
    # Only one older copy.
    assert sorted(p.name for p in path.parent.iterdir()) == [
        "tester.log",
        "tester.log.1",
    ]


def test_plain_mode_writes_no_file(qapp, tmp_path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.chdir(tmp_path)
    model = make(None, exe_dir=str(tmp_path))
    assert not any(tmp_path.rglob("*"))
    assert [s["id"] for s in model.logSources] == ["tester", "dill"]
    assert model.logNote == model_mod.PLAIN_LOG_NOTE
    texts = [x["text"] for x in model.logLines]
    assert any("not opened from Gremlin" in t for t in texts)
    assert any("access denied (5)" in t for t in texts)


# Logs tab sources (item 1) -----------------------------------------------------


def test_sources_and_dill_fallback(tmp_path) -> None:  # noqa: ANN001
    exe_dir, cwd = tmp_path / "exe", tmp_path / "cwd"
    exe_dir.mkdir()
    cwd.mkdir()
    (cwd / "dill_debug.log").write_text("x\n")
    out = logfiles.sources(str(tmp_path), exe_dir, cwd)
    assert [s.id for s in out] == ["tester", "trace", "system", "dill"]
    assert out[1].path == tmp_path / "logs" / "trace.log"
    assert out[3].path == cwd / "dill_debug.log"
    (exe_dir / "dill_debug.log").write_text("y\n")
    assert logfiles.sources(None, exe_dir, cwd)[-1].path == exe_dir / "dill_debug.log"


def test_tail_reads_last_512_kb(tmp_path) -> None:  # noqa: ANN001
    path = tmp_path / "big.log"
    lines = [f"04:00:00.000  line {i:06d} " + "y" * 90 for i in range(8000)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    tail = logfiles.read_tail(path)
    assert tail.truncated and tail.size == path.stat().st_size
    assert tail.lines[-1] == lines[-1]
    assert tail.lines[0] in lines  # no cut first line
    assert sum(len(x) + 1 for x in tail.lines) <= logfiles.TAIL_BYTES
    small = tmp_path / "small.log"
    small.write_text("a\nb\n")
    assert logfiles.read_tail(small).lines == ["a", "b"]
    assert not logfiles.read_tail(tmp_path / "none.log").exists


def test_model_log_view_find_warnings_follow_copy(qapp, tmp_path) -> None:  # noqa: ANN001
    write_expected(tmp_path)
    logs = tmp_path / "logs"
    logs.mkdir()
    trace = logs / "trace.log"
    trace.write_text(
        "04:01:00.000  RAW Stick A Axis 1\n"
        "04:01:01.000  HIDHIDE WARNING game started before change\n"
        "04:01:02.000  OUTPUT vJoy 1 Axis 1\n",
        encoding="utf-8",
    )
    opened: list[str] = []
    model = make(str(tmp_path), open_folder=lambda f: opened.append(f) or True)
    model.logSource = "trace"
    assert [x["text"] for x in model.logLines][0] == "RAW Stick A Axis 1"
    assert model.logLines[0]["time"] == "04:01:00.000"
    model.logFind = "axis"
    assert model.logFindCount == 2 and model.logFindPos == 0
    assert model.findNext() == 2 and model.findNext() == 0
    assert model.findPrevious() == 2
    model.logWarningsOnly = True
    assert [x["text"] for x in model.logLines] == [
        "HIDHIDE WARNING game started before change"
    ]
    assert (
        model.copyLog() == "04:01:01.000  HIDHIDE WARNING game started before change\n"
    )
    model.logWarningsOnly = False
    model.logFind = ""
    # Follow: an appended line shows on the next poll; off: it doesn't.
    with open(trace, "a", encoding="utf-8") as h:
        h.write("04:01:03.000  OUTPUT vJoy 1 Axis 2 longer\n")
    model.poll_log()
    assert model.logLines[-1]["text"] == "OUTPUT vJoy 1 Axis 2 longer"
    model.logFollow = False
    with open(trace, "a", encoding="utf-8") as h:
        h.write("04:01:04.000  later\n")
    model.poll_log()
    assert model.logLines[-1]["text"] != "later"
    model.logFollow = True
    assert model.logLines[-1]["text"] == "later"
    assert model.openLogFolder() and opened == [str(logs)]
    model.logSource = "system"
    assert model.logNote.startswith("File not found")
    # Tester log follows its own new lines.
    model.logSource = "tester"
    before = len(model.logLines)
    model._log.add("extra line")
    assert len(model.logLines) == before + 1


# Restart banner (item 3) -----------------------------------------------------------


def test_stale_since_cases() -> None:
    started = datetime.datetime(2026, 10, 10, 3, 40, 53)
    assert cmp.stale_since(None, started) is None
    assert cmp.stale_since({}, started) is None
    assert cmp.stale_since({"hidhide_changed_at": "bad"}, started) is None
    assert (
        cmp.stale_since({"hidhide_changed_at": "2026-10-10T03:40:00"}, started) is None
    )
    assert (
        cmp.stale_since({"hidhide_changed_at": "2026-10-10T03:40:53"}, started) is None
    )
    assert cmp.stale_since(
        {"hidhide_changed_at": "2026-10-10T03:41:50", "hidhide_change": "program list"},
        started,
    ) == ("program list", "03:41:50")
    assert cmp.stale_since(
        {"hidhide_changed_at": "2026-10-10T03:41:50", "hidhide_change": "whatever"},
        started,
    ) == ("settings", "03:41:50")
    assert (
        cmp.stale_since({"hidhide_changed_at": "2026-10-10T03:41:50"}, started)[0]
        == "settings"
    )


def test_banner_and_restart(qapp, tmp_path, monkeypatch) -> None:  # noqa: ANN001
    path = write_expected(tmp_path)
    started: list[list[str]] = []
    quits: list[int] = []
    model = make(
        str(tmp_path),
        starter=started.append,
        quit_app=lambda: quits.append(1),
        argv=["input_tester.py", "--gremlin-dir", str(tmp_path)],
    )
    assert model.staleBanner == ""
    write_expected(
        tmp_path,
        hidhide_changed_at="2026-10-10T04:05:12",
        hidhide_change="program list",
    )
    import os

    os.utime(path, (1, 1))
    model.check_changes()
    assert model.staleBanner == (
        "HidHide changed after this tester started (program list, 04:05:12). "
        "HidHide only checks devices when they're opened, so what you see may "
        "be out of date."
    )
    log_text = (tmp_path / "tester" / "tester.log").read_text(encoding="utf-8")
    assert (
        "⚠ HidHide changed after this tester started (program list 04:05:12)"
        in log_text
    )
    model.restartTester()
    assert started == [
        [
            sys.executable,
            os.path.abspath("input_tester.py"),
            "--gremlin-dir",
            str(tmp_path),
        ]
    ]
    assert quits == [1]
    # Frozen: the exe itself with the same args.
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    assert model_mod.restart_args(["x.exe", "--gremlin-dir", "D"]) == [
        sys.executable,
        "--gremlin-dir",
        "D",
    ]


def test_restart_module_hooks_and_failed_start(qapp, tmp_path) -> None:  # noqa: ANN001
    calls: list = []
    model_mod.set_starter(lambda args: calls.append(("start", args)))
    model_mod.set_quitter(lambda: calls.append("quit"))
    try:
        make(str(tmp_path), argv=["t.py"]).restartTester()
    finally:
        model_mod.set_starter(None)
        model_mod.set_quitter(None)
    assert calls[-1] == "quit" and calls[0][0] == "start"

    def boom(args: list[str]) -> None:
        raise OSError("nope")

    quits: list[int] = []
    model = make(
        str(tmp_path), starter=boom, quit_app=lambda: quits.append(1), argv=["t.py"]
    )
    model.restartTester()
    assert quits == []
    assert "Restart failed: nope" in (tmp_path / "tester" / "tester.log").read_text(
        encoding="utf-8"
    )


# HID left-out rows (item 6c) ----------------------------------------------------------


def test_hid_skipped_rows(qapp) -> None:  # noqa: ANN001
    rows = make(None).hidSkipped
    assert rows[0]["label"] == "left out: access denied (hidden from this program)"
    assert rows[0]["vid"] == "231D" and rows[0]["denied"] is True
    assert rows[1]["label"].startswith("left out: not a game device")


# Follow input (item 7) ---------------------------------------------------------


def test_follow_input_rules(qapp) -> None:  # noqa: ANN001
    devs = Devs()
    clock = [0.0]
    model = make(None, devs=devs, clock=clock)
    followed: list[str] = []
    model.inputFollowed.connect(followed.append)
    model.selectedKey = "di:{A}"
    model.tick()
    assert model.followInput is True
    # Jitter under 0.05 on B: no switch.
    devs.values["di:{B}"].axes[0] = 0.04
    clock[0] = 1.0
    model.tick()
    assert model.selectedKey == "di:{A}"
    # A real move on B: selects B.
    devs.values["di:{B}"].axes[0] = 0.3
    clock[0] = 2.0
    model.tick()
    assert model.selectedKey == "di:{B}" and followed == ["di:{B}"]
    # Within the 1 s hold, A's button doesn't switch back.
    devs.values["di:{A}"].buttons[0] = True
    clock[0] = 2.5
    model.tick()
    assert model.selectedKey == "di:{B}"
    # After the hold, a new move on A switches.
    devs.values["di:{A}"].buttons[1] = True
    clock[0] = 3.6
    model.tick()
    assert model.selectedKey == "di:{A}"
    # All devices view: nothing changes.
    model.allDevicesShown = True
    devs.values["di:{B}"].buttons[2] = True
    clock[0] = 9.0
    model.tick()
    assert model.selectedKey == "di:{A}"
    # Follow off: nothing changes.
    model.allDevicesShown = False
    model.followInput = False
    devs.values["di:{B}"].buttons[3] = True
    clock[0] = 12.0
    model.tick()
    assert model.selectedKey == "di:{A}"
