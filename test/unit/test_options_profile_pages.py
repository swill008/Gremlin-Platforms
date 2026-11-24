# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 S96, D-04-OPTIONS-PROFILE: Options' "This profile" pages (Startup and
macros, vJoy, Scripts): the sidebar group, the strip with the open profile's
name, showPage, Search options, loaded only while shown, and their settings
changing the open profile.

The real program off-screen in its own process (the journey harness).
"""

from __future__ import annotations

import pathlib
import shutil
import sys
from typing import Any

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
    step,
)

PAGES = {
    "startup-macros": "startupModeBox",
    "vjoy": "vjoyInitialValue:1:X Axis",
    "scripts": "scriptAddButton",
}


# +-------------------------------------------------------------------------
# | Child process


def story(j: Journey) -> None:  # noqa: PLR0915
    from PySide6 import QtCore

    from gremlin import util
    from gremlin.profile import Profile

    out = j.out
    j.ev('Commands.trigger("tools.options")')
    window = j.window("Options")

    def named(name: str) -> Any:  # noqa: ANN401
        return next(
            (it for it in j.walk(window.contentItem()) if it.objectName() == name),
            None,
        )

    def shown(name: str) -> bool:
        it = named(name)
        return it is not None and bool(it.isVisible())

    def search(text: str) -> None:
        named("optionsSearch").setProperty("text", text)
        j.settle()

    def state() -> dict:
        return {
            "title": window.property("sectionTitle"),
            "strip": shown("optionsProfileStrip"),
            "loaded": [i for i, name in PAGES.items() if named(name) is not None],
            "shown": [i for i, name in PAGES.items() if shown(name)],
            "current": [
                it.property("text")
                for it in j.walk(window.contentItem())
                if it.property("current") is True and it.property("text") is not None
                and it.property("hoverEnabled")
                and it.metaObject().className().startswith("ConfigSectionButton")
            ],
        }

    j.settle()
    out["open"] = state()
    heading = named("optionsProfileHeading")
    out["heading"] = heading.property("text")
    out["sidebar"] = [
        it.property("text")
        for it in j.walk(window.contentItem())
        if it.metaObject().className().startswith("ConfigSectionButton")
    ]
    history = named("optionsHistory")
    last = named("optionsSection:scripts")

    def y(item: Any) -> float:  # noqa: ANN401
        return item.mapToScene(QtCore.QPointF(0, 0)).y()

    window.setHeight(window.minimumHeight())
    j.settle()
    out["fits"] = y(last) + last.height() <= y(history)

    # Each page from its sidebar row, then a section again.
    for page in PAGES:
        j.click(named("optionsSection:" + page))
        j.settle()
        out["page-" + page] = state()
    j.click(named("optionsSection:vjoy"))
    j.settle()
    out["axes"] = sorted(
        it.objectName() for it in j.walk(window.contentItem())
        if it.objectName().startswith("vjoyInitialValue:1:")
    )
    # Setting the section (a sidebar click on the first) leaves the page.
    j.click(next(
        it for it in j.walk(window.contentItem())
        if it.metaObject().className().startswith("ConfigSectionButton")
    ))
    j.settle()
    out["section-again"] = state()

    # showPage, and an unknown id.
    out["show"] = [j.ev(f'showPage("{p}")', window) for p in (*PAGES, "nothing")]
    j.settle()
    out["after-show"] = state()
    search("zzzz")
    out["show-while-searching"] = j.ev('showPage("vjoy")', window)
    j.settle()
    out["search-cleared"] = named("optionsSearch").property("text")
    out["after-search-show"] = state()

    # The strip follows the open profile.
    name = named("optionsProfileName")
    out["note"] = named("optionsProfileSavedNote").property("text")
    before = str(name.property("text"))
    out["name-is-title"] = before == j.backend.property("windowTitle")
    other = pathlib.Path(util.userprofile_path()) / "Second Profile.xml"
    Profile().to_xml(str(other))
    j.backend.loadProfile(QtCore.QUrl.fromLocalFile(str(other)).toString())
    j.settle()
    out["name-after"] = str(name.property("text"))
    out["name-before"] = before
    # The new profile's settings are the ones changed.
    j.ev('showPage("startup-macros")', window)
    j.settle()
    box = named("startupModeBox")
    labels = [j.ev(f"textAt({i})", box) for i in range(box.property("count"))]
    pick = labels.index("Default")
    j.ev(f"currentIndex = {pick}; activated({pick})", box)
    out["startup"] = j.profile.settings.startup_mode

    # Search: rows on the pages, filtered and counted.
    def count() -> str:
        it = named("searchCount")
        return str(it.property("text")) if it.isVisible() else ""

    search("X Axis")
    out["search-axis"] = {
        "count": count(),
        "strip": shown("optionsProfileStrip"),
        "axes": [
            it.objectName() for it in j.walk(window.contentItem())
            if it.objectName().startswith("vjoyInitialValue:1:") and it.isVisible()
        ],
        "startup": shown("startupModeBox"),
    }
    search("Startup Mode")
    out["search-startup"] = {
        "count": count(), "startup": shown("startupModeBox"),
        "delay": shown("macroDefaultDelayBox"),
    }
    search("zzzz")
    out["search-none"] = count()
    search("")
    out["after-search"] = state()

    # Scripts: empty, then one added; the search finds it and its variables.
    j.ev('showPage("scripts")', window)
    j.settle()
    out["empty"] = [shown("scriptsEmpty"), shown("scriptAddButton")]
    folder = pathlib.Path(util.scripts_dir())
    folder.mkdir(parents=True, exist_ok=True)
    url = ""
    for file in ("vars_all_types.py", "periodic_counter.py"):
        shutil.copy(_ROOT / "test" / "fixtures" / "scripts" / file, folder / file)
        url = QtCore.QUrl.fromLocalFile(str(folder / file)).toString()
        j.ev("scriptListModel", named("scriptManager")).addScript(url)
    rows = lambda: [  # noqa: E731
        it for it in j.walk(window.contentItem())
        if it.objectName().startswith("scriptRow:")
    ]
    j.wait_until(
        lambda: len(rows()) == 2
        and not any(s.starting for s in j.profile.scripts.scripts),
        "the script rows",
    )
    j.settle()
    pane = named("scriptsListPane")
    manager = named("scriptManager")
    out["panes"] = [
        shown("scriptVariablesPane"),
        abs(pane.height() - manager.height()) < 1,
        manager.height() < window.height(),
        # The page itself doesn't scroll; the panes do.
        j.ev("_page.contentItem.contentHeight <= _page.contentItem.height + 1", window),
    ]
    row = next(r for r in rows() if "vars_all" in str(r.property("path")))
    j.click(next(it for it in j.walk(row) if it.objectName() == "scriptConfigure"))
    j.settle()
    search("vars_all_types")
    out["search-script"] = {
        "count": count(),
        "rows": [pathlib.Path(str(r.property("path"))).name
                 for r in rows() if r.isVisible()],
        "add": shown("scriptAddButton"),
        "variables": sum(
            1 for it in j.walk(window.contentItem())
            if it.objectName() == "scriptVariableName" and it.isVisible()),
    }
    search("")
    j.settle()
    out["rows-again"] = sum(1 for r in rows() if r.isVisible())

    # Help's setting links leave the page.
    out["reveal"] = j.ev('revealSetting("minimize to tray")', window)
    j.settle()
    out["after-reveal"] = state()


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | The tests


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("options_profile"))


def test_the_sidebar_has_the_profile_group_below_folders(run: dict) -> None:
    assert step(run, "heading") == "This profile"
    names = step(run, "sidebar")
    assert names[names.index("Folders"):] == [
        "Folders", "Startup and macros", "vJoy", "Scripts"]
    assert step(run, "fits") is True, "the rows reach History at the least height"


def test_program_pages_have_no_strip_and_load_no_profile_page(run: dict) -> None:
    for key in ("open", "section-again"):
        assert step(run, key) == {
            "title": "General", "strip": False, "loaded": [], "shown": [],
            "current": ["General"]}


@pytest.mark.parametrize(("page", "title"), [
    ("startup-macros", "Startup and macros"), ("vjoy", "vJoy"), ("scripts", "Scripts")])
def test_each_page_shows_alone_with_its_strip(
    run: dict, page: str, title: str
) -> None:
    assert step(run, "page-" + page) == {
        "title": title, "strip": True, "loaded": [page], "shown": [page],
        "current": [title]}


def test_the_vjoy_page_keeps_every_axis_box(run: dict) -> None:
    assert "vjoyInitialValue:1:X Axis" in step(run, "axes")


def test_show_page(run: dict) -> None:
    assert step(run, "show") == [True, True, True, False]
    assert step(run, "after-show")["shown"] == ["scripts"]
    assert step(run, "show-while-searching") is True
    assert step(run, "search-cleared") == ""
    assert step(run, "after-search-show")["shown"] == ["vjoy"]


def test_the_strip_and_settings_follow_the_open_profile(run: dict) -> None:
    assert step(run, "note") == "Saved with the profile (Save Profile)"
    assert step(run, "name-is-title") is True
    assert step(run, "name-after") != step(run, "name-before")
    assert "Second Profile" in step(run, "name-after")
    assert step(run, "startup") == "Default"


def test_search_finds_and_counts_rows_on_the_pages(run: dict) -> None:
    assert step(run, "search-axis") == {
        "count": "1 found", "strip": False, "startup": False,
        "axes": ["vjoyInitialValue:1:X Axis"]}
    found = step(run, "search-startup")
    assert found["startup"] is True
    assert found["delay"] is False
    assert found["count"].endswith(" found")
    assert step(run, "search-none") == "Nothing matches"
    assert step(run, "after-search")["loaded"] == ["startup-macros"]


def test_scripts_page(run: dict) -> None:
    assert step(run, "empty") == [True, True]
    assert step(run, "panes") == [True, True, True, True]
    found = step(run, "search-script")
    assert found["rows"] == ["vars_all_types.py"]
    assert found["add"] is False
    # The picked script's variables stay with its row and count.
    assert found["variables"] > 1
    assert found["count"] == f"{found['variables'] + 1} found"
    assert step(run, "rows-again") == 2


def test_a_help_setting_link_leaves_the_profile_page(run: dict) -> None:
    assert step(run, "reveal") is True
    assert step(run, "after-reveal")["strip"] is False
    assert step(run, "after-reveal")["shown"] == []


if __name__ == "__main__":
    main()
