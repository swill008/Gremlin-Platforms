# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Leaving a page with an open action pane is answered by the shared
ActionPane (to-do 91, Method B item 1; 05 Q8, 06 Q6): requestLeave()
resolves at once when the pane is clean, asks when it has unsaved edits,
and resolves after Save or Discard (Cancel stops the leave). Main's
helpers reach a page's pane through `page.actionPane`, or the page itself
when it has none (Output View).

The test runs the real program off-screen (stand-in hardware) in its own
process with a fresh user folder: this file run as a script creates an
ActionPane on a stand-in layout inside the main window and drives it.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    import proc_tree  # pyright: ignore[reportMissingImports]  (test/)
    import smoke_report  # pyright: ignore[reportMissingImports]  (test/)
    home = tmp_path_factory.mktemp("home")
    (home / "Gremlin Platforms").mkdir(parents=True)
    env = dict(
        os.environ, USERPROFILE=str(home), QT_QPA_PLATFORM="offscreen",
        GREMLIN_OFFLINE="1", PYTHONIOENCODING="utf-8",
        TEMP=str(home), TMP=str(home),
    )
    result = proc_tree.run(
        [sys.executable, str(pathlib.Path(__file__).resolve())],
        cwd=_ROOT, env=env, text=True,
        encoding="utf-8", errors="replace", timeout=180,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.startswith("RESULT ")]
    assert lines, smoke_report.explain(result)
    out = json.loads(lines[-1][len("RESULT "):])
    assert "error" not in out, out
    return out


def test_clean_pane_resolves_at_once(run: dict) -> None:
    assert run["clean"] == {"resolved": 1, "cancelled": 0, "asked": False}


def test_unsaved_pane_asks_first(run: dict) -> None:
    assert run["dirty_asked"] is True
    assert run["dirty_before_answer"] == {"resolved": 0, "cancelled": 0}


def test_save_resolves_and_writes(run: dict) -> None:
    assert run["save"] == {"resolved": 1, "cancelled": 0, "committed": 1,
                           "open": False}


def test_discard_resolves_and_drops(run: dict) -> None:
    assert run["discard"] == {"resolved": 1, "cancelled": 0, "discarded": 1,
                              "open": False}


def test_cancel_stops_the_leave(run: dict) -> None:
    assert run["cancel"] == {"resolved": 0, "cancelled": 1, "open": True}


def test_pane_answers_main_close_and_save(run: dict) -> None:
    assert run["pane_calls"] == {"changes": True, "saved": True,
                                 "after_save": False, "closed": False}


def test_main_reaches_the_pane_of_either_page_shape(run: dict) -> None:
    assert run["main_new_shape"] == "pane"
    assert run["main_old_shape"] == "page"
    assert run["main_none"] is None


def _smoke() -> None:  # noqa: C901
    import importlib.util

    sys.path.insert(0, str(_ROOT))
    spec = importlib.util.spec_from_file_location(
        "fake_hardware", _ROOT / "test" / "fake_hardware.py"
    )
    assert spec is not None and spec.loader is not None
    fake_hardware = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fake_hardware)
    fake_hardware.install()

    import gremlin.ui.update_model as um

    um.UpdateModel.startup = lambda self, *a, **k: None

    from PySide6 import QtCore, QtQml

    import joystick_gremlin
    from gremlin import clock

    def wait_until(cond, limit_ms: int = 10000) -> bool:  # noqa: ANN001
        end = clock.monotonic() + limit_ms / 1000.0
        qapp = QtCore.QCoreApplication.instance()
        while True:
            if cond():
                return True
            if clock.monotonic() > end:
                return False
            qapp.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 20)
            clock.sleep(0.005)

    def ev(obj: QtCore.QObject, code: str) -> object:
        expr = QtQml.QQmlExpression(QtQml.qmlContext(obj), obj, code)
        value = expr.evaluate()
        if expr.hasError():
            raise RuntimeError(expr.error().toString() + " :: " + code[:200])
        value = value[0] if isinstance(value, tuple) else value
        return value.toVariant() if hasattr(value, "toVariant") else value

    out: dict = {}
    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    win = app.main_window
    win.setProperty("visible", True)
    wait_until(lambda: win.isVisible())
    try:
        # A stand-in layout (the model's pane draft calls) and a pane on it,
        # driven in one expression (QML objects take no new properties).
        res = ev(win, """(function() {
            var c = Qt.createComponent("ActionPane.qml")
            if (c.status !== Component.Ready)
                throw new Error(c.errorString())
            var lay = {
                paneModel: null, dirty: false, committed: 0, discarded: 0,
                paneDirty: function() { return lay.dirty },
                commitPane: function() { lay.committed++; lay.dirty = false; return 0 },
                discardPane: function() { lay.discarded++; lay.dirty = false },
                endPane: function() {},
                beginPane: function(k, s) {},
                beginNewAction: function(k) {}
            }
            var p = c.createObject(_root.contentItem, { layout: lay })
            var dlg = null
            for (var i = 0; i < p.data.length; ++i) {
                var o = p.data[i]
                if (o && typeof o.saveChosen === "function"
                        && typeof o.ask === "function")
                    dlg = o
            }
            if (!dlg)
                throw new Error("no unsaved-changes dialog in ActionPane")
            var n = { resolved: 0, cancelled: 0 }
            p.leaveResolved.connect(function() { n.resolved++ })
            p.leaveCancelled.connect(function() { n.cancelled++ })
            function counts() {
                return { resolved: n.resolved, cancelled: n.cancelled }
            }
            function reset() {
                n.resolved = 0; n.cancelled = 0; dlg.visible = false
                p.openAt("k", 0, "T"); lay.dirty = true
            }
            var r = {}
            p.openAt("k", 0, "T")
            p.requestLeave()
            r.clean = counts(); r.clean.asked = dlg.visible

            reset()
            p.requestLeave()
            r.dirty_asked = dlg.visible
            r.dirty_before_answer = counts()
            dlg.saveChosen()
            r.save = counts(); r.save.committed = lay.committed; r.save.open = p.open

            reset()
            p.requestLeave(); dlg.discardChosen()
            r.discard = counts()
            r.discard.discarded = lay.discarded
            r.discard.open = p.open

            reset()
            p.requestLeave(); dlg.cancelled()
            r.cancel = counts(); r.cancel.open = p.open

            dlg.visible = false
            var q = { changes: p.paneHasChanges(), saved: p.savePane() }
            q.after_save = p.paneHasChanges()
            p.closeActionPane()
            q.closed = p.open
            r.pane_calls = q
            return JSON.stringify(r)
        })()""")
        out.update(json.loads(res))

        # Main's helper: a page with actionPane, one without, none.
        out["main_new_shape"] = ev(
            win, "_root._paneOf({ actionPane: { name: 'pane' }, name: 'page' }).name")
        out["main_old_shape"] = ev(win, "_root._paneOf({ name: 'page' }).name")
        out["main_none"] = ev(win, "_root._paneOf(null)")
    except Exception as exc:  # noqa: BLE001
        out["error"] = repr(exc)
    print("RESULT " + json.dumps(out), flush=True)
    os._exit(0)


if __name__ == "__main__":
    _smoke()
