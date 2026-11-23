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
        TextField {
            objectName: "ageField"
            text: "42"
            validator: IntValidator { bottom: 0; top: 99 }
        }
    }
}
"""
# A window that asks before closing, as the dialogs with unsaved changes do.
_ASKS_TITLE = "Asks Panel"
_ASKS_QML = b"""
import QtQuick

Window {
    title: "Asks Panel"
    width: 200
    height: 100
    visible: true
    onClosing: (close) => { close.accepted = false }
}
"""


class _Backend:
    """Stands in for Backend's command_list / run_command_id."""

    def __init__(self) -> None:
        self.ran: list[str] = []
        self.rows = [
            {"id": "tools.panel", "text": "Panel", "group": "Tools", "window": True},
            {"id": "debug.toggle", "text": "Toggle", "group": "Debug", "window": False},
            {"id": "tools.locked", "text": "Locked", "group": "Tools", "window": True},
            {"id": "tools.broken", "text": "Broken", "group": "Tools", "window": True},
        ]

    def command_list(self) -> list[dict]:
        return self.rows

    def run_command_id(self, command_id: str) -> bool:
        if command_id == "tools.locked":
            return False
        if command_id == "tools.broken":
            from gremlin.control_api import CallError

            raise CallError("The command 'tools.broken' failed: oops.", "failed")
        self.ran.append(command_id)
        return True


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
        args: dict | None = None,
    ) -> None:
        self.calls[name] = {
            "handler": handler,
            "main_thread": main_thread,
            "timeout_s": timeout_s,
            "summary": summary,
            "args": {k: v.describe() for k, v in (args or {}).items()},
        }

    def call(self, name: str, **args: Any) -> Any:  # noqa: ANN401
        from gremlin.control_api import CallError

        try:
            return {"ok": self.calls[name]["handler"](args)}
        except CallError as e:
            return {"error": str(e), "code": e.code}


def _child(picture: str) -> dict:  # noqa: PLR0915
    import logging

    sys.path.insert(0, str(_ROOT))
    from PySide6 import QtCore, QtGui, QtQml, QtQuick

    app = QtGui.QGuiApplication(sys.argv[:1])
    from gremlin.ui import control_windows

    logged: list[str] = []
    levels: dict[str, str] = {}
    tracebacks: list[str] = []

    class _Keep(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            logged.append(record.getMessage())
            levels[record.getMessage()] = record.levelname
            if record.exc_info:
                tracebacks.append(record.getMessage())

    system = logging.getLogger("system")
    system.setLevel(logging.INFO)
    system.addHandler(_Keep())

    def pump(ms: int = 50) -> None:
        deadline = QtCore.QDeadlineTimer(ms)
        while not deadline.hasExpired():
            app.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)

    reg = _Registry()
    backend = _Backend()
    control_windows.register_api_calls(reg, backend)
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
    out["press-by-name"] = reg.call("window.press", window=_TITLE, button="applyButton")
    pump()
    out["applied"] = window.property("applied")
    out["press-off"] = reg.call("window.press", window=_TITLE, button="Locked")
    out["type"] = reg.call("window.type", window=_TITLE, field="Name", text="Pilot One")
    out["finished"] = window.property("finished")
    out["type-no-text"] = reg.call("window.type", window=_TITLE, field="Name")
    out["type-refused"] = reg.call(
        "window.type", window=_TITLE, field="ageField", text="abc"
    )
    out["type-out-of-range"] = reg.call(
        "window.type", window=_TITLE, field="ageField", text="250"
    )
    out["type-number"] = reg.call(
        "window.type", window=_TITLE, field="ageField", text="17"
    )
    out["type-clear"] = reg.call("window.type", window=_TITLE, field="Name", text="")
    out["after-clear"] = window.property("finished")
    out["open"] = reg.call("window.open", id="tools.panel")
    out["open-unknown"] = reg.call("window.open", id="tools.nope")
    out["open-no-window"] = reg.call("window.open", id="debug.toggle")
    out["open-locked"] = reg.call("window.open", id="tools.locked")
    out["open-broken"] = reg.call("window.open", id="tools.broken")
    out["ran"] = list(backend.ran)
    backend.rows = []
    out["open-not-ready"] = reg.call("window.open", id="tools.panel")
    out["screenshot-relative"] = reg.call(
        "window.screenshot", window=_TITLE, path="panel.png"
    )
    out["screenshot"] = reg.call("window.screenshot", window=_TITLE, path=picture)
    out["dpr"] = window.devicePixelRatio()
    image = QtGui.QImage(picture)
    out["picture"] = [image.width(), image.height()]
    out["screenshot-jpg"] = reg.call(
        "window.screenshot", window=_TITLE, path=picture[:-4] + ".jpg"
    )
    out["unknown"] = reg.call("window.read", window="No Such Window")
    asks_component = QtQml.QQmlComponent(engine)
    asks_component.setData(_ASKS_QML, QtCore.QUrl())
    asks = asks_component.create()
    pump()
    out["close-asks"] = reg.call("window.close", window=_ASKS_TITLE)
    pump()
    out["asks-visible"] = asks.isVisible()
    # Through the real dispatch (decision 2a): a plain one-line answer and
    # only the one-line "API: ..." log line, no traceback.
    from gremlin import control_api

    control_api.allowed = lambda: True  # this child process only
    control_windows.register_api_calls(control_api, backend)
    out["api-open-old-key"] = control_api.dispatch(
        "window.open", {"command": "tools.panel"}
    )
    out["api-type-no-text"] = control_api.dispatch(
        "window.type", {"window": _TITLE, "field": "Name"}
    )
    out["help-args"] = {
        c["name"]: c["args"]
        for c in control_api.calls()
        if c["name"].startswith("window.")
    }
    out["api-unknown"] = control_api.dispatch(
        "window.read", {"window": "No Such Window"}
    )
    out["api-no-button"] = control_api.dispatch(
        "window.press", {"window": _TITLE, "button": "Nope"}
    )
    out["tracebacks"] = tracebacks
    out["close"] = reg.call("window.close", window=_TITLE)
    pump()
    out["visible-after-close"] = window.isVisible()
    out["logged"] = logged
    out["levels"] = levels
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
    assert [(f["name"], f["placeholder"]) for f in fields] == [
        ("nameField", "Name"),
        ("ageField", ""),
    ]


def test_window_press_clicks_the_button_and_logs_by_api(run: dict) -> None:
    assert run["press"] == {"ok": {"pressed": "Apply"}}
    assert run["press-by-name"] == {"ok": {"pressed": "Apply"}}
    assert run["applied"] == 2
    assert f"Pressed 'Apply' in '{_TITLE}' by API" in run["logged"]


def test_window_press_refuses_a_turned_off_button(run: dict) -> None:
    assert run["press-off"] == {
        "error": f"'Locked' is turned off in '{_TITLE}'.",
        "code": "refused",
    }


def test_window_type_fills_the_field_and_finishes_the_edit(run: dict) -> None:
    assert run["type"] == {"ok": {"text": "Pilot One"}}
    assert run["finished"] == "Pilot One"
    assert f"Typed into 'nameField' in '{_TITLE}' by API" in run["logged"]


def test_window_screenshot_writes_a_png_of_the_window_only(run: dict) -> None:
    path = Path(run["_home"]) / "panel.png"
    assert path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
    dpr = run["dpr"]
    assert run["picture"] == [round(320 * dpr), round(220 * dpr)]
    shot = run["screenshot"]["ok"]
    assert [shot["width"], shot["height"]] == run["picture"]


def test_window_screenshot_refuses_a_path_that_is_not_png(run: dict) -> None:
    assert run["screenshot-jpg"] == {
        "error": "The picture path must end in .png.",
        "code": "bad_args",
    }


def test_an_unknown_window_is_an_error(run: dict) -> None:
    assert run["unknown"] == {
        "error": "No window called 'No Such Window'.",
        "code": "not_found",
    }


def test_window_call_errors_are_one_plain_line_without_a_traceback(
    run: dict,
) -> None:
    """Decision 2a (user 2026-11-23): a window call's error comes back like
    the other calls' ("window.read: No window called ..." on the command
    line, no exception name) and logs only the one-line API line."""
    assert run["api-unknown"] == {
        "ok": False,
        "error": "No window called 'No Such Window'.",
        "code": "not_found",
    }
    assert run["api-no-button"] == {
        "ok": False,
        "error": f"No button 'Nope' in '{_TITLE}'.",
        "code": "not_found",
    }
    assert run["tracebacks"] == []
    assert (
        'API: window.read {"window": "No Such Window"} -> error: '
        "No window called 'No Such Window'."
    ) in run["logged"]


def test_window_close_closes_it(run: dict) -> None:
    assert run["close"] == {"ok": {"closed": _TITLE}}
    assert run["visible-after-close"] is False


def test_window_close_refuses_a_window_that_stays_open(run: dict) -> None:
    """13 S29: a window that asks before closing stays open, and the
    answer says so instead of "closed"."""
    assert run["close-asks"] == {
        "error": f"'{_ASKS_TITLE}' stayed open; it may be asking about unsaved"
        " changes in the program.",
        "code": "refused",
    }
    assert run["asks-visible"] is True
    assert f"Closed window '{_ASKS_TITLE}' by API" not in run["logged"]


def test_window_type_needs_text_and_leaves_the_field_alone(run: dict) -> None:
    """13 S29: no text is an error, not a cleared field; "" clears."""
    assert run["type-no-text"] == {
        "error": "window.type needs text.",
        "code": "bad_args",
    }
    assert run["api-type-no-text"]["code"] == "bad_args"
    assert run["type-clear"] == {"ok": {"text": ""}}
    assert run["after-clear"] == ""


def test_window_type_refuses_text_the_field_turns_away(run: dict) -> None:
    """13 S29: a validator that turns the text away is refused, and the
    field keeps what it had."""
    assert run["type-refused"] == {
        "error": f"'ageField' in '{_TITLE}' doesn't take 'abc'.",
        "code": "refused",
    }
    assert run["type-out-of-range"]["code"] == "refused"
    assert run["type-number"] == {"ok": {"text": "17"}}


def test_window_open_runs_only_a_command_that_opens_a_window(run: dict) -> None:
    """13 S29, S27: the id argument; unknown not_found, can't be used now
    not_ready, a command without a window refused (and not run)."""
    assert run["open"] == {"ok": {"ran": True}}
    assert run["open-unknown"] == {
        "error": "No command called 'tools.nope'.",
        "code": "not_found",
    }
    assert run["open-no-window"] == {
        "error": "'debug.toggle' opens no window; run it with command.run"
        " (gremlin-ctl run-command).",
        "code": "refused",
    }
    assert run["open-locked"] == {
        "error": "'tools.locked' can't be used now.",
        "code": "not_ready",
    }
    # Backend's own errors (a command that throws in QML) pass through.
    assert run["open-broken"] == {
        "error": "The command 'tools.broken' failed: oops.",
        "code": "failed",
    }
    assert run["ran"] == ["tools.panel"]
    assert run["open-not-ready"]["code"] == "not_ready"
    assert run["api-open-old-key"]["code"] == "bad_args"


def test_window_screenshot_refuses_a_short_path(run: dict) -> None:
    assert run["screenshot-relative"] == {
        "error": "Give the full path.",
        "code": "bad_args",
    }


def test_window_calls_declare_their_arguments(run: dict) -> None:
    """13 S26: help lists each window call's arguments."""
    args = run["help-args"]
    assert set(args["window.open"]) == {"id"}
    assert set(args["window.type"]) == {"window", "field", "text"}
    assert set(args["window.screenshot"]) == {"window", "path"}
    assert args["window.list"] == {}
    assert args["window.press"]["button"]["required"] is True


def test_by_api_lines_are_written_at_warning(run: dict) -> None:
    """13 S18: the "... by API" lines show at the default log level."""
    by_api = [m for m in run["logged"] if m.endswith(" by API")]
    assert by_api
    assert {run["levels"][m] for m in by_api} == {"WARNING"}


if __name__ == "__main__":
    main()
