"""Gremlin's real Screen Saver Mode (listener, timers, keep-off) next to a
small Qt window; measures the longest main-thread gap while the displays
are kept off. Power off after 5 s (typed wait), screen saver timer off.
Keyboard or mouse input ends the keep-off; the test ends 25 s after the
power-off. Run with a temp USERPROFILE.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.getcwd())

from PySide6 import QtCore, QtGui, QtQuick  # noqa: E402

app = QtGui.QGuiApplication(sys.argv)
view = QtQuick.QQuickView()
view.setSource(
    QtCore.QUrl(
        "data:text/plain,"
        + "import QtQuick\nRectangle { width: 200; height: 60; color: 'black' }"
    )
)
view.show()

from gremlin import screen_saver_mode as ssm  # noqa: E402

mode = ssm.manager()
state = {
    "last": time.monotonic(),
    "worst": 0.0,
    "fired_at": None,
    "start": time.monotonic(),
}


def stamp() -> str:
    return time.strftime("%H:%M:%S")


def beat() -> None:
    now = time.monotonic()
    gap = now - state["last"]
    state["last"] = now
    st = mode.status()
    if st.off_fired and state["fired_at"] is None:
        state["fired_at"] = now
        print(stamp(), "power off fired; measuring", flush=True)
    if state["fired_at"] is not None:
        state["worst"] = max(state["worst"], gap)
        if now - state["fired_at"] > 25 or (
            not st.keeping_off and now - state["fired_at"] > 3
        ):
            print(
                stamp(),
                f"longest main-thread gap: {state['worst']:.2f} s; "
                f"wakes {st.wakes}; keeping off {st.keeping_off}",
                flush=True,
            )
            mode.shutdown()
            app.quit()
    elif now - state["start"] > 40:
        print(stamp(), "power off never fired:", st, flush=True)
        mode.shutdown()
        app.quit()


t = QtCore.QTimer()
t.setInterval(100)
t.timeout.connect(beat)
t.start()
mode.apply(
    ssm.Settings(True, screen_saver_on=False, power_off_on=True, power_off_wait_s=5)
)
print(stamp(), "Screen Saver Mode on: power off in 5 s; hands off", flush=True)
app.exec()
