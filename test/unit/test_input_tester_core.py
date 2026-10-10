# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin Input Tester core (D-02-INPUT-TESTER, contract items 2-8):
compare() verdicts, matching, Steam line, result.json, the model on the fake
joystick driver, and the no-settings guard."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import textwrap
from collections.abc import Callable, Sequence

sys.path.append(".")

import pytest

import dill
from gremlin.input_tester import compare as cmp
from gremlin.input_tester import devices, result
from gremlin.input_tester import model as model_mod
from gremlin.input_tester.devices import SeenDevice
from gremlin.input_tester.model import InputTesterModel

REPO = pathlib.Path(__file__).resolve().parents[2]

STICK_GUID = "{11111111-2222-3333-4444-555555555555}"
VJOY_GUID = "{AAAAAAAA-0000-0000-0000-000000000003}"


def di(name: str, vid: int, pid: int, guid: str) -> SeenDevice:
    return SeenDevice(
        key=f"di:{guid}",
        kind="directinput",
        name=name,
        vid=vid,
        pid=pid,
        guid=guid,
        axes=2,
        buttons=4,
        hats=1,
        axis_ids=[1, 2],
    )


def pad(n: int) -> SeenDevice:
    return SeenDevice(
        key=f"xi:{n}",
        kind="xinput",
        name=f"Xbox pad {n}",
        pad=n,
        axes=6,
        buttons=10,
        hats=1,
    )


def expected(
    sticks: Sequence[dict] = (),
    vjoy: Sequence[dict] = (),
    xbox: Sequence[dict] = (),
    mode: str = "block",
    on_list: bool = True,
    apps: Sequence[str] = (),
) -> dict:
    return {
        "version": 1,
        "written": "2026-10-10T03:14:22",
        "tester_path": "C:\\Gremlin\\Gremlin Input Tester.exe",
        "hidhide": {
            "present": True,
            "cloak": True,
            "mode": mode,
            "tester_on_list": on_list,
            "apps": list(apps),
        },
        "sticks": list(sticks),
        "vjoy": list(vjoy),
        "xbox": list(xbox),
    }


def stick(
    expect: str,
    guid: str = STICK_GUID,
    name: str = "VKBsim Gladiator EVO R",
    vid: int = 0x231D,
    pid: int = 0x0200,
) -> dict:
    return {
        "name": "Right stick",
        "windows_name": name,
        "vid": vid,
        "pid": pid,
        "guid": guid,
        "instance_ids": [],
        "feeds": ["vJoy 3"],
        "expect": expect,
    }


def by_name(verdict: cmp.Verdict) -> dict[str, cmp.Row]:
    return {r.name: r for r in verdict.rows}


# compare() verdicts ------------------------------------------------------------


def test_hidden_and_not_seen_is_ok() -> None:
    v = cmp.compare(expected([stick("hidden")]), [], False)
    row = by_name(v)["Right stick"]
    assert (row.verdict, row.seen, row.tag) == ("ok", False, "hidden")
    assert v.verdict == "pass"


def test_hidden_but_visible_fails() -> None:
    seen = [di("VKBsim Gladiator EVO R", 0x231D, 0x0200, STICK_GUID)]
    v = cmp.compare(expected([stick("hidden")]), seen, False)
    row = by_name(v)["Right stick"]
    assert (row.verdict, row.tag) == ("bad", "VISIBLE · should be hidden")
    assert v.verdict == "fail"
    assert v.summary.startswith("1 stick visible that should be hidden")


def test_visible_and_seen_passes() -> None:
    seen = [di("VKBsim Gladiator EVO R", 0x231D, 0x0200, STICK_GUID)]
    v = cmp.compare(expected([stick("visible")]), seen, False)
    assert by_name(v)["Right stick"].verdict == "ok"
    assert v.verdict == "pass"
    assert v.summary == "1 visible"


def test_expected_visible_not_seen_is_missing() -> None:
    v = cmp.compare(
        expected(
            vjoy=[
                {
                    "id": 3,
                    "guid": VJOY_GUID,
                    "fed_by": ["Right stick"],
                    "used": True,
                    "expect": "visible",
                }
            ]
        ),
        [],
        False,
    )
    row = by_name(v)["vJoy Device 3"]
    assert (row.verdict, row.tag) == ("missing", "missing")
    assert v.verdict == "fail"
    assert "1 vJoy device missing" in v.summary


def test_unknown_device_is_not_a_fail() -> None:
    seen = [
        di(
            "Virtual Desktop Gamepad",
            0x045E,
            0x028E,
            "{BBBBBBBB-0000-0000-0000-000000000001}",
        )
    ]
    v = cmp.compare(expected(), seen, False)
    row = by_name(v)["Virtual Desktop Gamepad"]
    assert (row.kind, row.verdict, row.tag) == (
        "other",
        "unknown",
        "not known to Gremlin",
    )
    assert row.section == cmp.SECTION_OTHER
    assert v.verdict == "pass"


def test_xbox_pad_matched_by_number() -> None:
    v = cmp.compare(
        expected(
            xbox=[
                {"pad": 1, "on": True, "expect": "visible"},
                {"pad": 2, "on": True, "expect": "visible"},
            ]
        ),
        [pad(1)],
        False,
    )
    rows = by_name(v)
    assert rows["Xbox pad 1"].verdict == "ok"
    assert rows["Xbox pad 2"].verdict == "missing"


def test_xbox_pad_with_no_expect_has_no_verdict() -> None:
    v = cmp.compare(expected(xbox=[{"pad": 2, "on": False, "expect": ""}]), [], False)
    row = by_name(v)["Xbox pad 2"]
    assert (row.verdict, row.tag) == ("", "")
    assert v.verdict == "pass"


def test_steam_on_list_by_volume_path() -> None:
    apps = [r"\Device\HarddiskVolume4\Program Files (x86)\Steam\STEAM.EXE"]
    v = cmp.compare(expected(apps=apps), [], True)
    assert v.steam == {"running": True, "on_list": True}
    assert v.steam_warning == ""


def test_vjoy_not_used_tag() -> None:
    seen = [di("vJoy Device", 0x1234, 0xBEAD, VJOY_GUID)]
    v = cmp.compare(
        expected(
            vjoy=[
                {
                    "id": 4,
                    "guid": VJOY_GUID,
                    "fed_by": [],
                    "used": False,
                    "expect": "visible",
                }
            ]
        ),
        seen,
        False,
    )
    assert by_name(v)["vJoy Device 4"].tag == "visible · not used by Gremlin"


# Matching (item 4) --------------------------------------------------------------


def test_matches_by_guid_first() -> None:
    # Same VID/PID + name twice: the GUID picks the right one.
    other_guid = "{22222222-0000-0000-0000-000000000000}"
    seen = [
        di("VKBsim Gladiator EVO R", 0x231D, 0x0200, other_guid),
        di("VKBsim Gladiator EVO R", 0x231D, 0x0200, STICK_GUID.lower()),
    ]
    v = cmp.compare(expected([stick("visible")]), seen, False)
    row = by_name(v)["Right stick"]
    assert row.key == f"di:{STICK_GUID.lower()}"
    # The other one is not part of Gremlin's setup.
    assert [r.verdict for r in v.rows if r.kind == "other"] == ["unknown"]


def test_matches_by_vid_pid_and_name_when_guid_differs() -> None:
    seen = [
        di(
            "vkbsim   GLADIATOR evo r",
            0x231D,
            0x0200,
            "{33333333-0000-0000-0000-000000000000}",
        )
    ]
    v = cmp.compare(expected([stick("hidden")]), seen, False)
    assert by_name(v)["Right stick"].verdict == "bad"


def test_same_vid_pid_other_name_does_not_match() -> None:
    seen = [
        di(
            "VKBsim Gladiator EVO L",
            0x231D,
            0x0200,
            "{33333333-0000-0000-0000-000000000000}",
        )
    ]
    v = cmp.compare(expected([stick("hidden")]), seen, False)
    assert by_name(v)["Right stick"].verdict == "ok"
    assert by_name(v)["VKBsim Gladiator EVO L"].verdict == "unknown"


def test_expect_comes_from_the_file() -> None:
    seen = [di("VKBsim Gladiator EVO R", 0x231D, 0x0200, STICK_GUID)]
    file_hidden = cmp.compare(
        expected([stick("hidden")], mode="allow", on_list=True), seen, False
    )
    file_visible = cmp.compare(
        expected([stick("visible")], mode="block", on_list=True), seen, False
    )
    assert by_name(file_hidden)["Right stick"].verdict == "bad"
    assert by_name(file_visible)["Right stick"].verdict == "ok"


def test_load_expected_reads_file_and_rejects_bad(tmp_path: pathlib.Path) -> None:
    good = tmp_path / "expected.json"
    good.write_text(json.dumps(expected([stick("hidden")])), encoding="utf-8")
    assert cmp.load_expected(good)["sticks"][0]["expect"] == "hidden"
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert cmp.load_expected(bad) is None
    assert cmp.load_expected(tmp_path / "none.json") is None


# Context and Steam (items 3, 7) -------------------------------------------------


def test_context_line_block_list() -> None:
    line = cmp.context_line(expected())
    assert line == (
        "Compared with Gremlin's devices (updated 03:14:22). This program is on "
        "HidHide's Block list, so hidden sticks must not show here."
    )


@pytest.mark.parametrize(
    "mode, apps, running, warn",
    [
        ("block", [], True, True),
        ("block", ["C:\\Steam\\steam.exe"], True, False),
        ("allow", [], True, False),
        ("allow", ["C:\\Program Files (x86)\\Steam\\Steam.exe"], True, True),
        ("block", [], False, False),
    ],
)
def test_steam_line(mode: str, apps: list, running: bool, warn: bool) -> None:
    v = cmp.compare(expected(mode=mode, apps=apps), [], running)
    assert (v.steam_warning == cmp.STEAM_LINE) is warn
    assert v.steam == {"running": running, "on_list": bool(apps)}
    assert v.verdict == "pass"  # never a fail


def test_plain_mode_without_file() -> None:
    seen = [di("pJoy Pro", 0x5678, 0xFACE, STICK_GUID), pad(1)]
    v = cmp.compare(None, seen, True)
    assert v.verdict == "none"
    assert v.context == cmp.PLAIN_LINE
    assert v.steam_warning == ""
    assert all(r.verdict == "" and r.tag == "" for r in v.rows)
    assert [r.section for r in v.rows] == [cmp.SECTION_PLAIN_DI, cmp.SECTION_XBOX]


# result.json (item 6) -----------------------------------------------------------


def test_result_json_atomic_with_contract_schema(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = [di("VKBsim Gladiator EVO R", 0x231D, 0x0200, STICK_GUID)]
    v = cmp.compare(expected([stick("hidden")]), seen, True)
    replaced: list[tuple[str, str]] = []
    real_replace = os.replace

    def spy(src: str, dst: str) -> None:
        replaced.append((str(src), str(dst)))
        real_replace(src, dst)

    monkeypatch.setattr(result.os, "replace", spy)
    path = result.write_result(tmp_path / "tester", v)
    assert path == tmp_path / "tester" / "result.json"
    # Written to a temp file in the same folder, then swapped in.
    assert len(replaced) == 1 and pathlib.Path(replaced[0][0]).parent == path.parent
    assert [p.name for p in path.parent.iterdir()] == ["result.json"]
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"version", "written", "verdict", "summary", "rows", "steam"}
    assert data["version"] == 1 and data["verdict"] == "fail"
    assert data["rows"] == [
        {
            "kind": "stick",
            "name": "Right stick",
            "expect": "hidden",
            "seen": True,
            "verdict": "bad",
        }
    ]
    assert data["steam"] == {"running": True, "on_list": False}


# Model on the fake joystick driver ------------------------------------------------


@pytest.fixture
def no_xinput(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(devices, "xinput_state", lambda n: None)


def make_model(
    gremlin_dir: str | None = None,
    steam_on: bool = False,
    clock: Callable[[], float] | None = None,
) -> InputTesterModel:
    times = clock or (lambda: 0.0)
    return InputTesterModel(
        gremlin_dir,
        hid_list=lambda: [],
        steam_running=lambda: steam_on,
        clock=times,
        start_timers=False,
    )


def test_model_rows_from_fake_dill(qapp, no_xinput) -> None:  # noqa: ANN001
    model = make_model()
    names = [r["name"] for r in model.rows]
    assert names == ["pJoy Pro", "vJoy Device"]
    assert model.compareMode is False
    assert model.verdict == "none" and model.verdictText == ""
    # From source HidHide sees python.exe: the path and the line say so.
    assert model.exePath == sys.executable
    assert model.contextLine == f"{cmp.PLAIN_LINE} {model_mod.SOURCE_NOTE}"
    assert model.selectedKey  # something live is selected
    assert model.selected["axisCount"] == 6 and model.selected["buttonCount"] == 64


def test_model_live_values_and_activity(qapp, no_xinput, monkeypatch) -> None:  # noqa: ANN001
    fake = dill.DILL._dll
    now = [0.0]
    model = make_model(clock=lambda: now[0])
    pjoy = next(r["key"] for r in model.rows if r["name"] == "pJoy Pro")
    model.selectedKey = pjoy
    assert [a["label"] for a in model.axes] == ["X", "Y", "Z", "Rz", "S1", "S2"]
    assert model.axes[0]["value"] == 0.0
    assert model.hats == [-1, -1]
    assert model.activity[pjoy] is False

    monkeypatch.setattr(
        fake, "get_axis", lambda guid, i: 32767 if i == 1 else 0, raising=False
    )
    monkeypatch.setattr(fake, "get_button", lambda guid, i: i == 2, raising=False)
    monkeypatch.setattr(
        fake, "get_hat", lambda guid, i: 9000 if i == 1 else -1, raising=False
    )
    now[0] = 1.0
    model.tick()
    assert model.axes[0]["value"] == pytest.approx(1.0)
    assert model.buttons[1] is True and model.buttons[0] is False
    assert model.hats == [90, -1]
    assert model.activity[pjoy] is True
    entry = next(d for d in model.allDevices if d["key"] == pjoy)
    assert entry["axes"][0] == pytest.approx(1.0)

    now[0] = 2.0  # no change since: the dot stops
    model.tick()
    assert model.activity[pjoy] is False


def test_model_compares_and_writes_result(
    qapp, no_xinput, tmp_path, monkeypatch  # noqa: ANN001
) -> None:
    # Never the real clipboard (the user's, and it crashed under full load).
    copied: list[str] = []
    monkeypatch.setattr(model_mod, "_set_clipboard", copied.append)
    pjoy_guid = devices.normalise_guid(
        str(dill.GUID(dill.DILL._dll.devices[0].device_guid))
    )
    (tmp_path / "tester").mkdir()
    (tmp_path / "tester" / "expected.json").write_text(
        json.dumps(
            expected(
                [
                    stick(
                        "hidden",
                        guid=pjoy_guid,
                        name="pJoy Pro",
                        vid=0x5678,
                        pid=0xFACE,
                    )
                ]
            )
        ),
        encoding="utf-8",
    )
    model = make_model(str(tmp_path), steam_on=True)
    assert model.compareMode is True
    assert model.verdict == "fail" and model.verdictText == "✗ Fail"
    row = next(r for r in model.rows if r["name"] == "Right stick")
    assert row["sub"] == "pJoy Pro · feeds vJoy 3"
    assert (row["icon"], row["tagStyle"], row["tag"]) == (
        "✗",
        "bad",
        "VISIBLE · should be hidden",
    )
    assert model.steamWarning == cmp.STEAM_LINE
    data = json.loads((tmp_path / "tester" / "result.json").read_text(encoding="utf-8"))
    assert data["verdict"] == "fail"

    text = model.resultText()
    assert text.startswith("Gremlin Input Tester: ✗ Fail\n")
    assert "✗ Right stick — VISIBLE · should be hidden" in text
    assert "? vJoy Device — not known to Gremlin" in text
    assert model.copyResult() == text
    assert copied == [text]


def test_model_rereads_expected_on_change(qapp, no_xinput, tmp_path) -> None:  # noqa: ANN001
    model = make_model(str(tmp_path))
    assert model.compareMode is False
    (tmp_path / "tester").mkdir(exist_ok=True)
    (tmp_path / "tester" / "expected.json").write_text(
        json.dumps(expected()), encoding="utf-8"
    )
    model.check_changes()
    assert model.compareMode is True
    assert model.verdict == "pass"


@pytest.mark.parametrize("gremlin_dir", [None, "", ".", "tester-home"])
def test_plain_mode_writes_nothing(
    qapp: object,
    no_xinput: None,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    gremlin_dir: str | None,
) -> None:
    """No --gremlin-dir (or not a full path to a folder): plain tester,
    no file anywhere."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "tester-home").mkdir()
    model = make_model(gremlin_dir)
    model.tick()
    model.check_changes()
    model.refresh()
    assert model.compareMode is False and model.verdict == "none"
    assert [p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*")] == [
        "tester-home"
    ]


def test_full_dir_without_expected_writes_only_result(
    qapp: object, no_xinput: None, tmp_path: pathlib.Path
) -> None:
    make_model(str(tmp_path)).check_changes()
    files = [
        p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob("*") if p.is_file()
    ]
    assert files == ["tester/result.json"]
    assert (
        json.loads((tmp_path / "tester" / "result.json").read_text("utf-8"))["verdict"]
        == "none"
    )


# Guard: never reads the user's settings ------------------------------------------


def test_tester_never_imports_gremlin_config(tmp_path: pathlib.Path) -> None:
    code = textwrap.dedent(
        """
        import sys
        sys.path.insert(0, sys.argv[1])
        import input_tester
        import gremlin.input_tester
        from gremlin.input_tester import compare, devices, model, result, steam
        bad = sorted(m for m in sys.modules
                     if m == "gremlin.config" or m.startswith("gremlin.config.")
                     or m in ("gremlin.util", "joystick_gremlin"))
        print("LOADED", bad)
        """
    )
    env = dict(os.environ, USERPROFILE=str(tmp_path), QT_QPA_PLATFORM="offscreen")
    out = subprocess.run(
        [sys.executable, "-c", code, str(REPO)],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert "LOADED []" in out.stdout, out.stderr[-1500:]
    assert not (tmp_path / "Gremlin Platforms").exists()


def test_frozen_exe_path_and_no_source_note(
    qapp: object, no_xinput: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\G\Gremlin Input Tester.exe")
    model = make_model()
    assert model.exePath == r"C:\G\Gremlin Input Tester.exe"
    assert model.contextLine == cmp.PLAIN_LINE
    assert model_mod.SOURCE_NOTE not in model.resultText()
