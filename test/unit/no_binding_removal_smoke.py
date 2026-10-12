# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Starts the program off-screen (stand-in hardware) and opens the main tool
windows: Help on a topic with program links, the Device Mapping Editor,
Options and the list windows (Device Library, History, Device Pack, the
Logical Device, OSC). Prints every Qt message (MSG ...) and each window
opened (OPENED ...), then "done", so test_no_binding_removal.py can check
none says "Overwriting binding" (a property set over its own binding).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from smoke_exit import smoke_exit

SMOKE = Path(__file__).resolve().parent / "one_help_window_smoke.py"
source = SMOKE.read_text(encoding="utf-8")
head = source[: source.index('out: dict = {"errors": []}')]
g: dict = {"__file__": str(SMOKE), "__name__": "no_binding_removal"}
sys.argv = [str(SMOKE)]
exec(compile(head, str(SMOKE), "exec"), g)  # noqa: S102  # the shared smoke helpers

ev, wait_until, visible = g["ev"], g["wait_until"], g["visible"]
help_windows = g["help_windows"]
QtGui = g["QtGui"]

import dill  # noqa: E402

app = g["joystick_gremlin"].JoystickGremlinApp([sys.argv[0]])
win = app.main_window
win.setProperty("visible", True)
wait_until(lambda: win.isVisible())
wait_until(lambda: bool(ev(win, "_statusLoader.item !== null")))


def titles() -> set[str]:
    return {w.title() for w in QtGui.QGuiApplication.topLevelWindows() if w.isVisible()}


def step(name: str, code: str, ms: int = 800) -> None:
    """Runs code in the main window; an error is printed, the next step runs."""
    before = titles()
    try:
        ev(win, code)
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR {name}: {exc!r}", flush=True)
        return
    wait_until(lambda: False, ms)
    print(f"OPENED {name}: {sorted(titles() - before)}", flush=True)


# The Device Mapping Editor for the stand-in stick, as from its card.
stick = next(d for d in g["fake"].devices if bytes(d.name) == b"pJoy Pro")
guid = str(dill.GUID(stick.device_guid).uuid)
card = {"rawName": "pJoy Pro", "name": "pJoy Pro", "guid": guid}
step("editor", f"openDeviceMappingEditorForCard({json.dumps(card)})", 1500)

# Help (F1) from the editor: a new Help window made on its chapter. Setting
# the chapter while the window is built opens its first topic, whose program
# links (01 S139) are checked then, before the window's own bindings ran:
# a ({}) starting value assigned at that moment logs binding.removal.
editors = visible(lambda t: t.startswith("Device Mapping Editor"))
if editors:
    try:
        ev(editors[0], "openGuide()")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR help: {exc!r}", flush=True)
if wait_until(lambda: bool(help_windows()), 8000):
    hw = help_windows()[0]
    # Then a topic with Open › / Show me › links, its reasons checked again.
    topic = ev(hw, (
        "(function(){for(var i=0;i<_book.length;++i)"
        "if(HelpLinks.programLinks(_book[i].body).length)return _book[i].id;"
        "return ''})()"
    ))
    if topic:
        ev(hw, f"showTopic({json.dumps(topic)})")
    print(f"HELP_TOPIC {topic}", flush=True)
    wait_until(lambda: False, 500)

for command in (
    "help.guide", "tools.options", "tools.deviceLibrary", "tools.history",
    "tools.devicePack", "tools.logical", "tools.oscMonitor", "tools.autoMappingTool",
    "view.deviceBindings", "view.xboxOutput", "view.home",
):
    step(command, f"Commands.trigger({json.dumps(command)})")

wait_until(lambda: False, 1000)
for text in g["messages"]:
    print("MSG " + text.replace("\n", " "), flush=True)
print("done", flush=True)
smoke_exit(0)
