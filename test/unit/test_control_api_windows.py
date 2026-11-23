# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""The control API's window calls (claude/plans/control-api-contract.md,
"Calls owned by WINDOWS"): window.list / read / press / type / screenshot /
close on a real QML window, through the handlers control_windows registers.

QML needs a QGuiApplication, and many test files make a bare
QCoreApplication when they load, so the window runs in a child process
(this file, run as a script, through test/proc_tree.py) on the offscreen
platform: never on the user's screen. The calls run on that process's main
thread, as the API runs them. The child prints one RESULT line; the tests
here check it.
"""

from __future__ import annotations

import json
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_TITLE = "API Test Panel"
_QML = b"""
import QtQuick
import QtQuick.Controls.Basic
import QtQuick.Layouts

Window {
    id: root
    title: "API Test Panel"
    width: 320
    height: 220
    visible: true
    property int applied: 0
    property string finished: ""

    ColumnLayout {
        anchors.fill: parent
        Text { text: "Hello there" }
        Button {
            objectName: "applyButton"
            text: "Apply"
            onClicked: root.applied += 1
        }
        Button { text: "Locked"; enabled: false }
        CheckBox { text: "Loud"; checked: true }
        TextField {
            objectName: "nameField"
            placeholderText: "Name"
            onEditingFinished: root.finished = text
        }
    }
}
"""


# +-------------------------------------------------------------------------
# | The child process


class _Registry:
    """Stands in for gremlin/control_api.py's register(): keeps the handlers."""

    def __init__(self) -> None:
        self.calls: dict[str, dict[str, Any]] = {}

    def register(
        self,
        name: str,
        handler: Callable[[dict], Any],
        *,
        main_thread: bool = False,
        timeout_s: float = 10.0,
        summary: str = "",
    ) -> None:
        self.calls[name] = {
            "handler": handler,
            "main_thread": main_thread,
            "timeout_s": timeout_s,
            "summary": summary,
        }

    def call(self, name: str, **args: Any) -> Any:  # noqa: ANN401
        try:
            return {"ok": self.calls[name]["handler"](args)}
        except ValueError as e:
            return {"error": str(e)}


def _child(picture: str) -> dict:  # noqa: PLR0915
    import logging

    sys.path.insert(0, str(_ROOT))
    from PySide6 import QtCore, QtGui, QtQml, QtQuick

    app = QtGui.QGuiApplication(sys.argv[:1])
    from gremlin.ui import control_windows

    logged: list[str] = []

    class _Keep(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logged.append(record.getMessage())

    system = logging.getLogger("system")
    system.setLevel(logging.INFO)
    system.addHandler(_Keep())

    def pump(ms: int = 50) -> None:
        deadline = QtCore.QDeadlineTimer(ms)
        while not deadline.hasExpired():
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)

    reg = _Registry()
    control_windows.register_api_calls(reg)
    out: dict[str, Any] = {
        "platform": QtGui.QGuiApplication.platformName(),
        "registered": {
            name: {k: v for k, v in entry.items() if k != "handler"}
            for name, entry in reg.calls.items()
        },
    }
    engine = QtQml.QQmlEngine()
    component = QtQml.QQmlComponent(engine)
    component.setData(_QML, QtCore.QUrl())
    window = component.create()
    if not isinstance(window, QtQuick.QQuickWindow):
        out["load-error"] = component.errorString()
        return out
    pump()
    out["list"] = reg.call("window.list")
    out["read"] = reg.call("window.read", window="api test panel")  # any case
    out["press"] = reg.call("window.press", window=_TITLE, button="Apply")
    pump()
    out["press-by-name"] = reg.call(
        "window.press", window=_TITLE, button="applyButton"
    )
    pump()
    out["applied"] = window.property("applied")
    out["press-off"] = reg.call("window.press", window=_TITLE, button="Locked")
    out["type"] = reg.call(
        "window.type", window=_TITLE, field="Name", text="Pilot One"
    )
    out["finished"] = window.property("finished")
    out["screenshot"] = reg.call("window.screenshot", window=_TITLE, path=picture)
    out["dpr"] = window.devicePixelRatio()
    image = QtGui.QImage(picture)
    out["picture"] = [image.width(), image.height()]
    out["screenshot-jpg"] = reg.call(
        "window.screenshot", window=_TITLE, path=picture[:-4] + ".jpg"
    )
    out["unknown"] = reg.call("window.read", window="No Such Window")
    out["close"] = reg.call("window.close", window=_TITLE)
    pump()
    out["visible-after-close"] = window.isVisible()
    out["logged"] = logged
    window.deleteLater()
    pump()
    return out


def main() -> None:
    try:
        out = _child(sys.argv[1])
    except BaseException as e:  # noqa: BLE001
        import traceback

        out = {"error": f"{type(e).__name__}: {e}", "tb": traceback.format_exc()}
    print("RESULT " + json.dumps(out, default=str), flush=True)
    os._exit(0)  # Qt's threads never hold the process


# +-------------------------------------------------------------------------
# | The pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)

    home = tmp_path_factory.mktemp("control-windows")
    env = dict(os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen")
    done = proc_tree.run(
        [sys.executable, __file__, str(home / "panel.png")],
        cwd=_ROOT,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    lines = [ln for ln in done.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, (done.returncode, done.stdout[-2000:], done.stderr[-4000:])
    out = json.loads(lines[-1][len("RESULT ") :])
    assert "error" not in out, out.get("tb")
    assert "load-error" not in out, out["load-error"]
    out["_home"] = str(home)
    return out


def test_the_window_is_off_screen(run: dict) -> None:
    assert run["platform"] == "offscreen"


def test_every_window_call_is_registered_on_the_main_thread(run: dict) -> None:
    names = {
        "window.list",
        "window.open",
        "window.close",
        "window.read",
        "window.screenshot",
        "window.press",
        "window.type",
    }
    reg = run["registered"]
    assert names <= set(reg)
    for name in names:
        assert reg[name]["main_thread"] is True, name
        assert reg[name]["summary"], name
    assert reg["window.screenshot"]["timeout_s"] == 30.0


def test_window_list_names_the_window(run: dict) -> None:
    assert {"title": _TITLE, "visible": True} in run["list"]["ok"]


def test_window_read_lists_text_buttons_checks_and_fields(run: dict) -> None:
    result = run["read"]["ok"]
    assert result["title"] == _TITLE
    items = result["items"]
    assert {
        "kind": "text",
        "name": "",
        "text": "Hello there",
        "enabled": True,
    } in items
    by_text = {(i["kind"], i["text"]): i for i in items}
    assert by_text[("button", "Apply")]["name"] == "applyButton"
    assert by_text[("button", "Apply")]["enabled"] is True
    assert by_text[("button", "Locked")]["enabled"] is False
    assert by_text[("check", "Loud")]["checked"] is True
    fields = [i for i in items if i["kind"] == "field"]
    assert [(f["name"], f["placeholder"]) for f in fields] == [("nameField", "Name")]


def test_window_press_clicks_the_button_and_logs_by_api(run: dict) -> None:
    assert run["press"] == {"ok": {"pressed": "Apply"}}
    assert run["press-by-name"] == {"ok": {"pressed": "Apply"}}
    assert run["applied"] == 2
    assert f"Pressed 'Apply' in {_TITLE} by API" in run["logged"]


def test_window_press_refuses_a_turned_off_button(run: dict) -> None:
    assert "turned off" in run["press-off"]["error"]


def test_window_type_fills_the_field_and_finishes_the_edit(run: dict) -> None:
    assert run["type"] == {"ok": {"text": "Pilot One"}}
    assert run["finished"] == "Pilot One"
    assert f"Typed into 'nameField' in {_TITLE} by API" in run["logged"]


def test_window_screenshot_writes_a_png_of_the_window_only(run: dict) -> None:
    path = Path(run["_home"]) / "panel.png"
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    dpr = run["dpr"]
    assert run["picture"] == [round(320 * dpr), round(220 * dpr)]
    shot = run["screenshot"]["ok"]
    assert [shot["width"], shot["height"]] == run["picture"]


def test_window_screenshot_refuses_a_path_that_is_not_png(run: dict) -> None:
    assert ".png" in run["screenshot-jpg"]["error"]


def test_an_unknown_window_is_an_error(run: dict) -> None:
    assert "No window called" in run["unknown"]["error"]


def test_window_close_closes_it(run: dict) -> None:
    assert run["close"] == {"ok": {"closed": _TITLE}}
    assert run["visible-after-close"] is False


if __name__ == "__main__":
    main()
