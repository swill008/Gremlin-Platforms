# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware), opens Help and the
Button Map, and prints every Qt message, so test_no_binding_overwrite.py can
check none says "Overwriting binding" (a property set over its own binding).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

SMOKE = Path(__file__).resolve().parent / "one_help_window_smoke.py"
source = SMOKE.read_text(encoding="utf-8")
head = source[: source.index('out: dict = {"errors": []}')]
g: dict = {"__file__": str(SMOKE), "__name__": "no_binding_overwrite"}
sys.argv = [str(SMOKE)]
exec(compile(head, str(SMOKE), "exec"), g)  # noqa: S102  # the shared smoke helpers

ev, wait_until, visible = g["ev"], g["wait_until"], g["visible"]

app = g["joystick_gremlin"].JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))
# The Button Map for the stand-in stick, as from its card (the card that
# showed the warning is only built for a device).
import json  # noqa: E402

import dill  # noqa: E402

stick = next(d for d in g["fake"].devices if bytes(d.name) == b"pJoy Pro")
guid = str(dill.GUID(stick.device_guid).uuid)
card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": guid}
ev(win, f"openButtonMapForCard({json.dumps(card)})")
wait_until(lambda: bool(visible(lambda t: t.startswith("Button Map"))), 8000)
wait_until(lambda: False, 1500)
for text in g["messages"]:
    print("MSG " + text.replace("\n", " "), flush=True)
print("done", flush=True)
os._exit(0)
