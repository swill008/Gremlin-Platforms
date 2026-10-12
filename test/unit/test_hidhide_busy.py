# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""D-02-HIDHIDE-BUSY (02 S67, gap HH-INUSE-1): when HidHide's control
device refuses access (Windows error 5: HidHide's own window is open), the
Hardware Hide page says HidHide is in use, not that it is not installed;
the controls that need the driver stay unavailable.

The model part fakes the control device below the public calls
(test_trace_hidhide's fixture). The page part runs this file as a script:
the real program off-screen with a fake control device that answers
error 5. The real HidHide driver is never opened."""

from __future__ import annotations

import json
import os
import pathlib
import sys
from collections.abc import Iterator

import pytest

if __name__ != "__main__":
    import shiboken6

    from test.unit.test_trace_hidhide import (  # noqa: F401 - fixture
        _HidHide,
        hidhide,
    )

_HERE = pathlib.Path(__file__).parent
BUSY = "HidHide is in use by another program (its window is open)."
MISSING = "HidHide is not installed"


# --- the model ------------------------------------------------------------------


def test_window_open_makes_the_model_busy_not_missing(hidhide: _HidHide) -> None:
    from gremlin.ui import hidhide as hh

    hidhide.busy = True
    page = hh.HidHideModel()
    try:
        assert page.property("installed") is False
        assert page.property("inUse") is True
    finally:
        shiboken6.delete(page)


def test_closing_the_window_clears_busy(hidhide: _HidHide) -> None:
    from gremlin.ui import hidhide as hh

    hidhide.busy = True
    page = hh.HidHideModel()
    try:
        hidhide.busy = False
        page.reload()
        assert page.property("installed") is True
        assert page.property("inUse") is False
    finally:
        shiboken6.delete(page)


def test_not_installed_is_not_busy(
    hidhide: _HidHide, monkeypatch: pytest.MonkeyPatch
) -> None:
    from gremlin import hidhide_driver as drv
    from gremlin.ui import hidhide as hh

    monkeypatch.setattr(drv, "_open_control", lambda: drv._opened(None, 2))
    page = hh.HidHideModel()
    try:
        assert page.property("installed") is False
        assert page.property("inUse") is False
    finally:
        shiboken6.delete(page)


# --- the page, in the real program ---------------------------------------------


@pytest.fixture(scope="module")
def page(tmp_path_factory: pytest.TempPathFactory) -> Iterator[dict]:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
    home_dir = tmp_path_factory.mktemp("hh_busy_home")
    (home_dir / "Gremlin Platforms").mkdir()
    proc = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__))],
        text=True, encoding="utf-8", timeout=150,
        cwd=str(_HERE.parents[1]),
        env={
            **os.environ, "USERPROFILE": str(home_dir),
            "QT_QPA_PLATFORM": "offscreen", "PYTHONUNBUFFERED": "1",
        },
    )
    results: dict = {}
    for line in proc.stdout.splitlines():
        if line.startswith("RESULT "):
            _tag, name, value = line.split(" ", 2)
            results[name] = json.loads(value)
    assert "done" in proc.stdout, smoke_report.explain(proc)
    assert results.get("open") is True, smoke_report.explain(proc)
    yield results


def test_page_says_in_use_not_missing(page: dict) -> None:
    texts = page["texts"]
    assert BUSY in texts
    assert MISSING not in texts
    assert not any(t.startswith("Install HidHide from") for t in texts)


def test_driver_buttons_stay_unavailable(page: dict) -> None:
    assert page["cloakEnabled"] is False


# --- the script (run by the fixture above) --------------------------------------


def _main() -> None:
    import importlib.util
    import time

    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    root = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", root / "test" / "fake_hardware.py"
    )
    assert spec and spec.loader
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake_hardware.install()

    import gremlin.ui.update_model as um

    um.UpdateModel.startup = lambda self, *a, **k: None

    import shiboken6
    from PySide6 import QtCore, QtQuick, QtTest

    from gremlin import hidhide_driver, process_paths

    # HidHide's control device, held by HidHide's own window: every open
    # fails with access denied (5). Never the real driver.
    hidhide_driver._open_control = lambda: hidhide_driver._opened(None, 5)
    hidhide_driver._close = lambda handle: None
    hidhide_driver.list_hid_devices = lambda gaming_only=False: []
    process_paths.running_programs = lambda *_a: []
    process_paths.running_images = lambda: []

    import joystick_gremlin

    def result(name: str, value: object) -> None:
        print(f"RESULT {name} {json.dumps(value)}", flush=True)

    def wait_until(check, timeout: float = 10.0):  # noqa: ANN001, ANN202
        deadline = time.monotonic() + timeout
        while True:
            value = check()
            if value or time.monotonic() > deadline:
                return value
            QtTest.QTest.qWait(20)

    def items(item: QtQuick.QQuickItem) -> list:
        found = [item]
        for c in item.childItems():
            found += items(c)
        return found

    sys.stdout.reconfigure(encoding="utf-8")
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    root_obj = wait_until(lambda: app.engine.rootObjects())[0]
    item = next(
        (o for o in root_obj.findChildren(QtCore.QObject)
         if "ThemedMenuItem" in o.metaObject().className()
         and o.property("command") == "tools.hidhide"),
        None,
    )
    win = None
    if item is not None:
        QtCore.QMetaObject.invokeMethod(item, "triggered")
        win = wait_until(lambda: next(
            (w for w in app.topLevelWindows()
             if isinstance(w, QtQuick.QQuickWindow) and w.isVisible()
             and w.title() == "HidHide"),
            None,
        ))
    result("open", win is not None)
    if win is None:
        print("done", flush=True)
        os._exit(0)
    win = shiboken6.wrapInstance(shiboken6.getCppPointer(win)[0], QtQuick.QQuickWindow)
    QtTest.QTest.qWait(300)
    everything = items(win.contentItem())
    texts = [
        str(i.property("text")) for i in everything
        if i.isVisible() and i.property("text") is not None
    ]
    result("texts", texts)
    cloak = [i for i in everything if i.objectName() == "hidHideCloakSwitch"]
    result("cloakEnabled", bool(cloak and cloak[0].isEnabled()))
    print("done", flush=True)
    os._exit(0)  # threads started by the app would keep it alive


if __name__ == "__main__":
    _main()
