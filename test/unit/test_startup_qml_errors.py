# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The start-up QML error list stops at the end of start-up (R-QMLWARN,
memory probe 2026-11-24).

joystick_gremlin collects the engine's QML warnings while Main.qml loads,
to name them if the main window fails (01 S15). It used to stay connected
for the whole run, so every warning from every window opened later was
kept (about three per round of the seven windows below). Now the collector
is disconnected once Main.qml has loaded.

Also: opening and closing those seven windows gives no QML warnings. The
one found: closing Calibration called destroy() on its ModelFactory models
(C++ owned since memory fix stage 1), which threw, so the rest of its
onClosing, resuming input highlighting, never ran.

A journey (test/journeys/_harness.py): the real program off-screen with a
temporary USERPROFILE, fake hardware and the fake vJoy.

Spec: none (no behaviour change).
"""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import Journey, pump, run_journey, step  # noqa: E402

WINDOWS = [
    "DialogOptions.qml", "DialogInputViewer.qml", "DialogManageModes.qml",
    "DialogDeviceInformation.qml", "DialogCalibration.qml", "DialogLiveLog.qml",
    "DialogDeviceMappingEditor.qml",
]  # fmt: skip
ROUNDS = 3


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _before(j: Journey) -> None:
    j.input_module()
    j.vjoy_module()


def story(j: Journey) -> None:
    from gremlin import shared_state

    engine = j.app.engine
    signal = "2warnings(QList<QQmlError>)"
    # Receivers before this story adds its own: the start-up collector only.
    j.out["receiversAfterStart"] = engine.receivers(signal)

    seen: list[str] = []
    engine.warnings.connect(lambda ws: seen.extend(w.toString() for w in ws))
    per_window: dict[str, list[str]] = {}
    for _ in range(ROUNDS):
        for qml in WINDOWS:
            before = len(seen)
            j.ev(f'Helpers.createComponent("{qml}")')
            pump(300)
            j.ev(f'Helpers.windowOf("{qml}").close()')
            pump(200)
            per_window.setdefault(qml, []).extend(seen[before:])
            if qml == "DialogCalibration.qml":
                held = j.await_value(
                    lambda: "calibration" in shared_state._highlight_holders, False
                )
                still_open = bool(j.ev(f'Helpers.windowOf("{qml}") !== null'))
                j.out.setdefault("calibrationHolds", []).append(
                    {"held": held, "open": still_open} if held else False
                )
    j.settle()
    j.out["receiversAfterWindows"] = engine.receivers(signal) - 1
    j.out["warnings"] = per_window


def main() -> None:
    Journey(_before).run(story)


if __name__ == "__main__":
    main()


# +-------------------------------------------------------------------------
# | Pytest side


def test_startup_collector_stops_and_windows_give_no_warnings(
    tmp_path: pathlib.Path,
) -> None:
    out = run_journey(pathlib.Path(__file__), tmp_path)
    assert "error" not in out, (out.get("error"), out.get("traceback"))
    # Nothing keeps collecting after start-up, so the list can't grow.
    assert step(out, "receiversAfterStart") == 0
    assert step(out, "receiversAfterWindows") == 0
    assert step(out, "calibrationHolds") == [False] * ROUNDS
    warned = {k: v for k, v in step(out, "warnings").items() if v}
    assert warned == {}, warned
