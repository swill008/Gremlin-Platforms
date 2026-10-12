# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""10 S3, S6 (D-NEXTLIST-1 items 4 and 6): the Device Library's device rows
show a small picture (the module's shown picture, its icon when it has none),
then name / description / "N saved setups" lines with the badge on the right;
the list can be made narrower (about 260) and the divider's place is kept.

The model is checked in-process over the stand-in Library; the window runs
off-screen in its own process (library_rows_smoke.py)."""

from __future__ import annotations

import importlib.util
import json
import os
import pathlib
import sys

import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
import pytest
from pytestqt.qtbot import QtBot

from gremlin.ui import device_library_model as model_mod
from gremlin.ui.device_library_model import DeviceLibraryModel

_HERE = pathlib.Path(__file__).parent
_spec = importlib.util.spec_from_file_location(
    "device_library_LU_fake_smoke", _HERE / "device_library_LU_fake_smoke.py"
)
assert _spec and _spec.loader
fake_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_mod)


class PhotoLibrary(fake_mod.FakeLibrary):
    def __init__(self) -> None:
        super().__init__()
        self.asked: list[str] = []

    def device_photo(self, folder: str) -> str:
        self.asked.append(folder)
        return "C:/pics/photo.png?t=7" if folder == "left-throttle" else ""


def _model(qtbot: QtBot, lib: fake_mod.FakeLibrary) -> DeviceLibraryModel:
    m = DeviceLibraryModel(api=lib.api(), watch_devices=False)
    m.refresh()
    qtbot.waitUntil(lambda: "Library: 48 MB" in m.statusText, timeout=5000)
    return m


def _dev(model: DeviceLibraryModel, key: str) -> dict:
    return next(r for r in model.rows if r["key"] == key)


def test_device_rows_carry_the_module_picture_as_a_url(qtbot: QtBot) -> None:
    lib = PhotoLibrary()
    model = _model(qtbot, lib)
    assert _dev(model, "dev-00000001")["photo"] == "file:///C:/pics/photo.png?t=7"
    assert _dev(model, "dev-00000003")["photo"] == ""
    # No module folder: nothing is asked, no picture.
    assert _dev(model, "dev-00000004")["photo"] == ""
    assert "" not in lib.asked


def test_the_picture_is_read_once_per_refresh(qtbot: QtBot) -> None:
    lib = PhotoLibrary()
    model = _model(qtbot, lib)
    first = lib.asked.count("left-throttle")
    assert first == 1
    model.toggleOpen("dev-00000001")
    model.setSearch("throttle")
    assert lib.asked.count("left-throttle") == first
    model.refresh()
    assert lib.asked.count("left-throttle") == first + 1


def test_a_library_without_device_photo_shows_no_picture(qtbot: QtBot) -> None:
    model = _model(qtbot, fake_mod.FakeLibrary())
    assert all(r.get("photo", "") == "" for r in model.rows if r["kind"] == "device")


def test_image_url_keeps_urls_and_turns_paths_into_file_urls() -> None:
    url = model_mod._image_url
    assert url("") == ""
    assert url("file:///C:/a.png?t=1") == "file:///C:/a.png?t=1"
    assert url("qrc:/x.png") == "qrc:/x.png"
    assert url("C:/a b/p.png") == "file:///C:/a b/p.png"
    assert url("C:/a/p.png?t=5") == "file:///C:/a/p.png?t=5"


def test_the_divider_share_is_kept_and_clamped(
    qtbot: QtBot, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin.ui import window_placement

    kept: dict[str, float] = {}
    monkeypatch.setattr(
        window_placement, "split_ratio", lambda name, default: kept.get(name, default)
    )
    monkeypatch.setattr(
        window_placement, "save_split", lambda name, r: kept.__setitem__(name, r)
    )
    model = _model(qtbot, fake_mod.FakeLibrary())
    assert model.splitRatio == pytest.approx(0.54)
    model.setSplitRatio(0.3)
    assert kept == {"deviceLibrary": pytest.approx(0.3)}
    # A new window (a new model) starts from the kept share.
    assert _model(qtbot, fake_mod.FakeLibrary()).splitRatio == pytest.approx(0.3)
    model.setSplitRatio(0.01)
    assert kept["deviceLibrary"] == pytest.approx(0.15)


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    out = tmp_path_factory.mktemp("dl_rows")
    home = tmp_path_factory.mktemp("home")
    env = {
        **os.environ,
        "QT_QPA_PLATFORM": "offscreen",
        "PYTHONUNBUFFERED": "1",
        "USERPROFILE": str(home),
    }
    proc = proc_tree.run(
        [sys.executable, str(_HERE / "library_rows_smoke.py"), str(out)],
        text=True,
        encoding="utf-8",
        timeout=120,
        cwd=str(_HERE.parents[1]),
        env=env,
    )
    results: dict = {"errors": [], "warnings": []}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            value = json.loads(value)
            try:
                value = json.loads(value)
            except (TypeError, ValueError):
                pass
            results[name] = value
        elif line.startswith("ERROR"):
            results["errors"].append(line)
        elif line.startswith("WARN"):
            results["warnings"].append(line)
    assert "done" in proc.stdout, proc.stdout[-3000:] + proc.stderr[-3000:]
    return results


def test_window_runs_without_errors_or_warnings(run: dict) -> None:
    assert run["errors"] == []
    assert run["warnings"] == []


def test_a_device_with_a_picture_shows_it_in_a_40_frame(run: dict) -> None:
    one = run["rows"]["one"]
    assert one["thumb"]["w"] == 40 and one["thumb"]["h"] == 40
    assert one["thumb"]["picture"] is True and one["thumb"]["glyph"] is False
    assert one["thumb"]["source"].endswith("photo.png?t=123")


def test_a_device_without_a_picture_shows_its_icon_in_the_frame(run: dict) -> None:
    three = run["rows"]["three"]
    assert three["thumb"]["visible"] is True
    assert three["thumb"]["picture"] is False and three["thumb"]["glyph"] is True


def test_saved_setups_sit_under_the_name_and_the_badge_stays_right(run: dict) -> None:
    for key, text in (("one", "3 saved setups"), ("three", "No saved setups")):
        row = run["rows"][key]
        assert row["height"] == 58
        count = row["count"]
        assert count["visible"] is True and count["text"] == text
        assert count["x"] == count["nameX"]
        assert count["y"] > row["name"]
        assert row["badgeX"] > row["width"] / 2


def test_the_list_can_be_narrowed_to_260(run: dict) -> None:
    assert run["min"]["min"] == run["min"]["dp"]


def test_dragging_the_divider_keeps_its_place(run: dict) -> None:
    drag = run["drag"]
    assert drag["pane"] < 450
    assert drag["saved"] == pytest.approx(drag["pane"] / drag["split"], abs=0.01)
