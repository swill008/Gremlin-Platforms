# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""04 S94 (Q14) off-screen in the real program: started as joystick_gremlin.py
starts it (fake hardware, a stand-in home folder) after a "crash" left a
recovery copy of the last profile. Real mouse clicks answer the offer.
Prints "RESULT name json" per check and "done".
test_profile_recovery.py runs it.

    python test/unit/profile_recovery_smoke.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import traceback
from collections.abc import Callable
from pathlib import Path

_HOME = Path(os.environ.get("USERPROFILE", "")).resolve()
_REAL_HOME = (
    Path(os.environ.get("SystemDrive", "C:") + "/Users")
    / os.environ.get("USERNAME", "")
).resolve()
if not os.environ.get("USERPROFILE") or _HOME == _REAL_HOME:
    raise SystemExit("Run with a stand-in USERPROFILE (test_profile_recovery.py).")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
_spec = importlib.util.spec_from_file_location(
    "fake_hardware", ROOT / "test" / "fake_hardware.py"
)
assert _spec and _spec.loader
fake_hardware = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fake_hardware)
fake_hardware.install()

import gremlin.ui.update_model as um  # noqa: E402

um.UpdateModel.startup = lambda self, *a, **k: None

from PySide6 import QtCore, QtQml, QtTest  # noqa: E402

from gremlin import clock, profile_recovery  # noqa: E402
from gremlin.config import Configuration  # noqa: E402
from gremlin.profile import Profile  # noqa: E402

# A copy every half second instead of every minute.
profile_recovery.INTERVAL_SECONDS = 0.5

import joystick_gremlin  # noqa: E402

LIMIT = 15.0
Left = QtCore.Qt.MouseButton.LeftButton
NoMod = QtCore.Qt.KeyboardModifier.NoModifier


def result(name: str, value: object) -> None:
    print(f"RESULT {name} {json.dumps(value)}", flush=True)


def wait_for(cond: Callable[[], object], limit: float = LIMIT) -> object:
    end = clock.monotonic() + limit
    while True:
        value = cond()
        if value or clock.monotonic() > end:
            return value
        QtTest.QTest.qWait(25)


def ev(root: QtCore.QObject, code: str) -> object:
    expr = QtQml.QQmlExpression(QtQml.qmlContext(root), root, code)
    value = expr.evaluate()
    if expr.hasError():
        raise RuntimeError(f"{code[:80]}: {expr.error().toString()}")
    value = value[0] if isinstance(value, tuple) else value
    return value.toVariant() if hasattr(value, "toVariant") else value


# The centre of the visible button labelled LABEL in the offer, in the
# window's coordinates ("" when there is none).
_FIND = (
    "(function() { function find(it) { if (!it) return null;"
    " if (it.text === LABEL && it.visible && typeof it.clicked === 'function')"
    " return it; var kids = it.children || [];"
    " for (var i = 0; i < kids.length; i++) { var f = find(kids[i]);"
    " if (f) return f } return null }"
    " var b = find(_profileRecoveryGate.contentItem); if (!b) return '';"
    " var p = b.mapToItem(null, b.width / 2, b.height / 2);"
    " return Math.round(p.x) + ',' + Math.round(p.y) })()"
)


def press(
    app: joystick_gremlin.JoystickGremlinApp, root: QtCore.QObject, label: str
) -> bool:
    """A real mouse click on the offer's button."""
    where = str(ev(root, _FIND.replace("LABEL", json.dumps(label))) or "")
    if not where:
        return False
    x, y = (int(v) for v in where.split(","))
    point = QtCore.QPoint(x, y)
    QtTest.QTest.mouseClick(root, Left, NoMod, point)  # type: ignore[arg-type]
    return bool(wait_for(lambda: not ev(root, "_profileRecoveryGate.opened"), 5))


def offer(root: QtCore.QObject) -> dict:
    return {
        "open": bool(ev(root, "_profileRecoveryGate.opened")),
        "title": ev(root, "_profileRecoveryGate.titleText"),
        "text": ev(root, "_profileRecoveryGate.messageText"),
        "buttons": [
            ev(root, "_profileRecoveryGate.confirmText"),
            ev(root, "_profileRecoveryGate.discardText"),
            ev(root, "_profileRecoveryGate.cancelText"),
        ],
    }


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    folder = _HOME / "profiles-here"
    folder.mkdir(exist_ok=True)
    path = folder / "Flight.xml"
    joystick_gremlin.register_config_options()
    saved = Profile()
    saved.mark_clean()
    saved.to_xml(path)
    Configuration().set("global", "internal", "last-profile", str(path))
    # The crash: a copy of Flight with a mode the file doesn't have.
    crashed = Profile()
    crashed.from_xml(path)
    crashed.modes.add_mode("Recovered")
    keeper = profile_recovery.ProfileRecovery()
    copy = keeper.file_for(path)
    keeper._write(copy, path, crashed._xml_text())
    result("copy-before-start", copy.is_file())

    app = joystick_gremlin.JoystickGremlinApp([sys.argv[0]])
    try:
        root = wait_for(lambda: app.engine.rootObjects())[0]  # type: ignore[index]
        backend = app.backend
        steps(app, root, backend, path, copy)
    except Exception:  # noqa: BLE001
        print("ERROR " + traceback.format_exc().replace("\n", " | "), flush=True)
    print("done", flush=True)
    os._exit(0)


def starred(root: QtCore.QObject) -> str:
    """The window title once it shows the unsaved "*", else ""."""
    title = str(root.property("title"))
    return title if title.startswith("* ") else ""


def has_mode(backend: object, name: str) -> bool:
    return bool(backend.profile.modes.mode_exists(name))  # type: ignore[attr-defined]


def steps(app, root, backend, path: Path, copy: Path) -> None:  # noqa: ANN001
    # 1. At start the last profile opens and its copy is offered.
    wait_for(lambda: ev(root, "_profileRecoveryGate.opened"))
    result("start-offer", offer(root))
    result("restore-clicked", press(app, root, "Restore"))
    wait_for(lambda: has_mode(backend, "Recovered"), 5)
    result("restored", {
        "mode": has_mode(backend, "Recovered"),
        "unsaved": backend.profileContainsUnsavedChanges,
        "path": backend.profilePath(),
        "title": wait_for(lambda: starred(root), 5),
    })

    # 2. An edit: the copy has it within the interval.
    backend.profile.modes.add_mode("Later")
    backend.profile.note_edit()
    kept = wait_for(
        lambda: copy.is_file() and "Later" in copy.read_text(encoding="utf-8"), 5
    )
    result("edit-kept", bool(kept))

    # 3. Save removes it.
    result("save-ok", backend.saveProfile(path.as_uri()))
    result("after-save", copy.is_file())
    QtTest.QTest.qWait(1200)
    result("clean-no-copy", copy.is_file())

    # 4. An edit, then New after Discard: the copy goes.
    backend.profile.modes.add_mode("Dropped")
    backend.profile.note_edit()
    result("edit-again-kept", bool(wait_for(lambda: copy.is_file(), 5)))
    backend.newProfile()
    result("after-new", copy.is_file())

    # 5. Opening a profile with a crash's copy: Not now keeps it.
    crashed = Profile()
    crashed.from_xml(path)
    crashed.modes.add_mode("Again")
    keeper = profile_recovery.ProfileRecovery()
    keeper._write(copy, path, crashed._xml_text())
    backend.loadProfile(path.as_uri())
    wait_for(lambda: ev(root, "_profileRecoveryGate.opened"), 5)
    result("open-offer", offer(root))
    result("notnow-clicked", press(app, root, "Not now"))
    QtTest.QTest.qWait(1200)
    result("after-notnow", {
        "copy": copy.is_file(),
        "mode": has_mode(backend, "Again"),
        "unsaved": backend.profileContainsUnsavedChanges,
    })

    # 6. Opening it again: offered again; Discard deletes it.
    backend.loadRecentProfile(str(path))
    wait_for(lambda: ev(root, "_profileRecoveryGate.opened"), 5)
    result("again-offer", offer(root)["open"])
    result("discard-clicked", press(app, root, "Discard"))
    QtTest.QTest.qWait(300)
    result("after-discard", {
        "copy": copy.is_file(),
        "mode": has_mode(backend, "Again"),
        "unsaved": backend.profileContainsUnsavedChanges,
    })

    # 7. A clean close removes this session's copy.
    backend.profile.modes.add_mode("Closing")
    backend.profile.note_edit()
    result("closing-kept", bool(wait_for(lambda: copy.is_file(), 5)))
    QtCore.QTimer.singleShot(0, app.quit)
    QtCore.QTimer.singleShot(5000, app.quit)
    app.exec()
    result("after-close", copy.is_file())


if __name__ == "__main__":
    main()
