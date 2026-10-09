# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC functional check: real UDP packets on loopback through the real
OscRuntime (python-osc server thread), off-screen, in a temp USERPROFILE.

    python tools/osc_functional_check.py [--json results.json]

Binds and sends on 127.0.0.1 only (never 0.0.0.0). Events are taken from
the signal the runtime emits (EventListener().joystick_event); a stand-in
EventListener carries it so no hardware, hooks or vJoy are touched.
Exit code 0 only when every check passes."""

from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

# -- isolation before anything from gremlin is imported ------------------------

_TMP = Path(tempfile.mkdtemp(prefix="osc_check_"))
(_TMP / "home").mkdir()
os.environ["USERPROFILE"] = str(_TMP / "home")
os.environ["userprofile"] = str(_TMP / "home")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))
sys.path.insert(1, str(_REPO / "test"))
try:  # No real vJoy, whatever gets imported.
    import vjoy_guard  # type: ignore[import-not-found]

    vjoy_guard.install()
except ImportError:
    pass

from PySide6 import QtCore, QtGui  # noqa: E402

APP = QtGui.QGuiApplication.instance() or QtGui.QGuiApplication(sys.argv[:1])

import gremlin.util  # noqa: E402
import gremlin.windows_event_hook  # noqa: E402

gremlin.windows_event_hook.enabled = False
assert str(_TMP) in gremlin.util.userprofile_path(), "USERPROFILE not isolated"

import joystick_gremlin  # noqa: E402

joystick_gremlin.register_config_options()  # options the action plugins read

from pythonosc.osc_message_builder import OscMessageBuilder  # noqa: E402
from pythonosc.udp_client import SimpleUDPClient  # noqa: E402

from gremlin import event_handler, history_modules, shared_state  # noqa: E402
from gremlin import osc_device_file as odf  # noqa: E402
from gremlin.modules import store  # noqa: E402

MODULES = _TMP / "modules"
MODULES.mkdir()
store.folder = lambda: MODULES  # type: ignore[assignment]
store._saved = lambda: None  # type: ignore[assignment]
history_modules.note_write = lambda *a, **k: None  # type: ignore[assignment]


class _Listener(QtCore.QObject):
    """Stand-in EventListener: only the signal the OSC runtime emits."""

    joystick_event = QtCore.Signal(object)
    virtual_event = QtCore.Signal(object)


_LISTENER = _Listener()
event_handler.EventListener = lambda: _LISTENER  # type: ignore[assignment,misc]

from gremlin import osc_bulk  # noqa: E402,F401  (patches the page model)
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime  # noqa: E402
from gremlin.profile import InputItem, Profile  # noqa: E402
from gremlin.types import InputType  # noqa: E402
from gremlin.ui.osc_device_model import OscDeviceManagementModel  # noqa: E402

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton
HOST = "127.0.0.1"
OVERALL_S = 60.0
_T0 = time.monotonic()

# -- helpers ------------------------------------------------------------------

events: list[dict[str, Any]] = []
results: list[dict[str, Any]] = []


def _on_event(event: Any) -> None:  # noqa: ANN401
    if event.device_guid != OSC_DEVICE_UUID:
        return
    events.append({
        "t": time.monotonic(),
        "type": "axis" if event.event_type == AXIS else "button",
        "id": event.identifier,
        "pressed": getattr(event, "is_pressed", None),
        "value": getattr(event, "value", None),
    })


_LISTENER.joystick_event.connect(_on_event)


def pump(seconds: float) -> None:
    end = time.monotonic() + min(seconds, 2.0)
    while time.monotonic() < end:
        APP.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        time.sleep(0.005)


def wait_for(pred: Any, timeout: float = 1.5) -> bool:  # noqa: ANN401
    end = time.monotonic() + min(timeout, 2.0)
    while time.monotonic() < end:
        APP.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        if pred():
            return True
        if time.monotonic() - _T0 > OVERALL_S:
            raise TimeoutError("overall 60 s timeout")
        time.sleep(0.005)
    return bool(pred())


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((HOST, 0))
        return sock.getsockname()[1]


def port_free(port: int) -> bool:
    """True when this process can bind 127.0.0.1:port itself (nobody holds it)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((HOST, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


class Client(SimpleUDPClient):
    """python-osc client whose socket is bound to loopback (not 0.0.0.0)."""

    def __init__(self, port: int) -> None:
        super().__init__(HOST, port)
        self._sock.close()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((HOST, 0))

    def send_args(self, address: str, *args: Any) -> None:  # noqa: ANN401
        builder = OscMessageBuilder(address=address)
        for arg in args:
            builder.add_arg(arg)
        self.send(builder.build())

    def close(self) -> None:
        self._sock.close()


def check(name: str, expected: Any, got: Any, ok: bool | None = None) -> None:  # noqa: ANN401
    passed = (expected == got) if ok is None else ok
    results.append({"check": name, "expected": str(expected), "got": str(got),
                    "result": "PASS" if passed else "FAIL"})


def take(since: int = 0) -> list[dict[str, Any]]:
    return events[since:]


def short(evs: list[dict[str, Any]]) -> list[tuple]:
    out = []
    for e in evs:
        if e["type"] == "axis":
            out.append(("A", e["id"], round(e["value"], 3)))
        else:
            out.append(("B", e["id"], e["pressed"]))
    return out


def profile_with(rows: list[Any]) -> Profile:  # noqa: ANN401
    made = Profile()
    items = []
    for row in rows:
        item = InputItem(made.library)
        item.device_id = OSC_DEVICE_UUID
        item.input_type = row.input_type
        item.input_id = row.input_id
        item.osc_uid = row.uid
        item.mode = made.modes.first_mode
        item.add_item_binding()
        items.append(item)
    if items:
        made.inputs[OSC_DEVICE_UUID] = items
    return made


# -- the checks ---------------------------------------------------------------


def run_checks() -> None:
    port = free_port()
    odf.write_server({
        "enabled": True, "host": HOST, "port": port,
        "autorelease_no_arg": True, "autorelease_delay_ms": 300,
    })
    server = odf.read_server()
    check("server settings written", (HOST, port, 300),
          (server["host"], server["port"], server["autorelease_delay_ms"]))

    rows = OscDevice().rows
    rows.load_dict({"inputs": []})
    btn = rows.create(BUTTON, "/btn")
    trig = rows.create(BUTTON, "/trig", trigger=True, delay_ms=150)
    noval = rows.create(BUTTON, "/noval")
    axis = rows.create(AXIS, "/axis", range_min=0.0, range_max=1.0)
    ax2 = rows.create(AXIS, "/ax2", source=1)
    chg = rows.create(BUTTON, "/chg", mode="change", delay_ms=100)
    scene = rows.create(BUTTON, "/scene", cmd_mode="data", data=["1"], delay_ms=100)
    dual_b = rows.create(BUTTON, "/dual", source=0)
    dual_a = rows.create(AXIS, "/dual", source=1)
    odf.save()

    runtime = OscRuntime()
    client = Client(port)
    try:
        # Profile without OSC inputs: no port.
        shared_state.current_profile = profile_with([])
        runtime.start()
        check("no OSC inputs: no port", "listener None, port free",
              f"listener {'None' if runtime._listener is None else 'open'}, "
              f"port {'free' if port_free(port) else 'held'}",
              runtime._listener is None and port_free(port))
        runtime.stop()

        # Profile with one OSC input: port opens.
        shared_state.current_profile = profile_with([btn])
        runtime.start()
        held = runtime._listener is not None and not port_free(port)
        check("profile with OSC input binds", f"{HOST}:{port} held",
              f"{getattr(runtime._listener, 'host', None)}:"
              f"{getattr(runtime._listener, 'port', None)} "
              f"{'held' if not port_free(port) else 'free'}", held)

        # Button 1/0.
        n = len(events)
        client.send_args("/btn", 1.0)
        wait_for(lambda: len(events) >= n + 1)
        client.send_args("/btn", 0.0)
        wait_for(lambda: len(events) >= n + 2)
        pump(0.1)
        check("button 1/0", [("B", btn.input_id, True), ("B", btn.input_id, False)],
              short(take(n)))

        # Trigger with own delay 150 ms.
        n = len(events)
        client.send_args("/trig", 1.0)
        wait_for(lambda: len(events) >= n + 2, 1.5)
        evs = take(n)
        gap = round((evs[1]["t"] - evs[0]["t"]) * 1000) if len(evs) >= 2 else None
        check("trigger + own delay 150 ms: press/release",
              [("B", trig.input_id, True), ("B", trig.input_id, False)], short(evs))
        check("trigger release after ~150 ms", "130..400 ms", f"{gap} ms",
              gap is not None and 130 <= gap <= 400)

        # No value: default auto-release (server 300 ms).
        n = len(events)
        client.send_args("/noval")
        wait_for(lambda: len(events) >= n + 2, 1.5)
        evs = take(n)
        gap = round((evs[1]["t"] - evs[0]["t"]) * 1000) if len(evs) >= 2 else None
        check("no value: auto-release press/release",
              [("B", noval.input_id, True), ("B", noval.input_id, False)], short(evs))
        check("no value release after server 300 ms", "280..600 ms", f"{gap} ms",
              gap is not None and 280 <= gap <= 600)

        # Axis 0..1.
        n = len(events)
        for v in (0.0, 0.5, 1.0):
            client.send_args("/axis", v)
            k = len(events)
            wait_for(lambda k=k: len(events) > k)
        check("axis 0..1 -> -1, 0, 1",
              [("A", axis.input_id, -1.0), ("A", axis.input_id, 0.0),
               ("A", axis.input_id, 1.0)], short(take(n)))

        # Axis on P2 (source 1).
        n = len(events)
        client.send_args("/ax2", "x", 0.25)
        wait_for(lambda: len(events) > n)
        pump(0.1)
        check("axis on P2: ('x', 0.25) -> -0.5", [("A", ax2.input_id, -0.5)],
              short(take(n)))

        # Change mode: 3, 3, 4 -> two pulses.
        n = len(events)
        client.send_args("/chg", 3)
        wait_for(lambda: len(events) >= n + 2)
        client.send_args("/chg", 3)
        pump(0.3)
        client.send_args("/chg", 4)
        wait_for(lambda: len(events) >= n + 4)
        pump(0.2)
        check("change mode 3,3,4 -> two pulses",
              [("B", chg.input_id, True), ("B", chg.input_id, False)] * 2,
              short(take(n)))

        # Message + data: /scene 1 fires, /scene 2 does not.
        n = len(events)
        client.send_args("/scene", 2)
        pump(0.3)
        got_2 = short(take(n))
        n = len(events)
        client.send_args("/scene", 1)
        wait_for(lambda: len(events) >= n + 2)
        pump(0.1)
        check("data row: /scene 2 ignored", [], got_2)
        check("data row: /scene 1 pulses",
              [("B", scene.input_id, True), ("B", scene.input_id, False)],
              short(take(n)))

        # Two inputs on one address.
        n = len(events)
        client.send_args("/dual", 1.0, 0.5)
        wait_for(lambda: len(events) >= n + 2)
        pump(0.1)
        check("two inputs on /dual (1.0, 0.5)",
              sorted([("B", dual_b.input_id, True), ("A", dual_a.input_id, 0.0)]),
              sorted(short(take(n))))
        k = len(events)
        client.send_args("/dual", 0.0, 0.5)  # release, so Stop finds it free
        wait_for(lambda: len(events) >= k + 2)

        # Unknown address: nothing.
        n = len(events)
        client.send_args("/nothing", 1.0)
        pump(0.3)
        check("unknown address ignored", [], short(take(n)))

        # Port change while running: rebinds.
        new_port = free_port()
        odf.write_server({
            "enabled": True, "host": HOST, "port": new_port,
            "autorelease_no_arg": True, "autorelease_delay_ms": 300,
        })
        pump(0.2)
        check("port change rebinds",
              f"listener on {new_port}, old {port} free",
              f"listener on {getattr(runtime._listener, 'port', None)}, old {port} "
              f"{'free' if port_free(port) else 'held'}",
              getattr(runtime._listener, "port", None) == new_port and port_free(port))
        n = len(events)
        client.send_args("/btn", 1.0)  # old port
        pump(0.4)
        old_got = short(take(n))
        new_client = Client(new_port)
        try:
            n = len(events)
            new_client.send_args("/btn", 1.0)
            wait_for(lambda: len(events) > n)
            new_client.send_args("/btn", 0.0)
            wait_for(lambda: len(events) > n + 1)
            new_got = short(take(n))
        finally:
            new_client.close()
        check("old port gets nothing after rebind", [], old_got)
        check("new port works", [("B", btn.input_id, True), ("B", btn.input_id, False)],
              new_got)
        port = new_port
        client.close()
        client = Client(port)

        # Stop releases every held button once (axis none, nothing after).
        n = len(events)
        client.send_args("/btn", 1.0)  # held: no 0 sent
        client.send_args("/trig", 1.0)  # 150 ms release pending
        client.send_args("/noval")  # 300 ms auto-release pending
        client.send_args("/axis", 0.5)
        wait_for(lambda: len(events) >= n + 4)
        pressed = short(take(n))
        check("before stop: 3 presses + axis",
              sorted([("B", btn.input_id, True), ("B", trig.input_id, True),
                      ("B", noval.input_id, True), ("A", axis.input_id, 0.0)]),
              sorted(pressed))
        n = len(events)
        runtime.stop()
        pump(0.05)
        at_stop = short(take(n))
        check("stop: one release per held button, axis none",
              sorted([("B", btn.input_id, False), ("B", trig.input_id, False),
                      ("B", noval.input_id, False)]),
              sorted(at_stop))
        n = len(events)
        pump(0.7)  # past the 150 ms and 300 ms delays
        check("after stop: no late events", [], short(take(n)))

        # Stop closes the port.
        check("stop closes the port", "listener None, port free",
              f"listener {'None' if runtime._listener is None else 'open'}, "
              f"port {'free' if port_free(port) else 'held'}",
              runtime._listener is None and port_free(port))
        n = len(events)
        client.send_args("/btn", 1.0)
        pump(0.3)
        check("stopped: packets ignored", [], short(take(n)))

        # Listen (no profile running): captures a real packet, then closes.
        model = OscDeviceManagementModel()
        learned: list[tuple] = []
        runtime.learned.connect(lambda a, p: learned.append((a, tuple(p))))
        model.setCaptureSettings({"mode": "button", "cmd_mode": "message"})
        before = len(rows)
        model.listenForInput()
        opened = runtime.is_listening() and not port_free(port)
        client.send_args("/learn/me", 1.0)
        wait_for(lambda: bool(learned))
        pump(0.2)
        check("listen opens the port", True, opened)
        check("listen captures real packet", [("/learn/me", (1.0,))], learned)
        added = OscDevice().find_address("/learn/me") is not None
        check("listen adds the input", True, len(rows) == before + 1 and added)
        check("listen closes port when not running", "not listening, port free",
              f"{'listening' if runtime.is_listening() else 'not listening'}, "
              f"port {'free' if port_free(port) else 'held'}",
              not runtime.is_listening() and runtime._listener is None
              and port_free(port))

        # Bulk capture: several addresses with the chosen settings.
        captured: list[tuple] = []
        model.commandCaptured.connect(lambda a, p: captured.append((a, p)))
        bulk = {"mode": "change", "cmd_mode": "message", "source": 1,
                "trigger": None, "delay_ms": 60}
        osc_bulk.start_bulk(model, bulk)
        bulk_open = runtime.is_listening() and not port_free(port)
        for addr in ("/bulk/a", "/bulk/b", "/bulk/c"):
            k = len(captured)
            client.send_args(addr, 0, 5)
            wait_for(lambda k=k: len(captured) > k)
        pump(0.1)
        model.cancelListen()
        pump(0.1)
        got = {}
        for addr in ("/bulk/a", "/bulk/b", "/bulk/c"):
            row = OscDevice().find_address(addr)
            got[addr] = None if row is None else (
                row.input_type.name, row.mode, row.source, row.delay_ms)
        want = {a: ("JoystickButton", "change", 1, 60)
                for a in ("/bulk/a", "/bulk/b", "/bulk/c")}
        check("bulk opens the port", True, bulk_open)
        check("bulk adds 3 addresses with settings", want, got)
        check("bulk cancel closes the port", True,
              runtime._listener is None and port_free(port))
    finally:
        try:
            runtime.cancel_listen()
            runtime.stop()
        finally:
            client.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="write the results as JSON here")
    args = parser.parse_args()
    start = time.strftime("%H:%M:%S")
    try:
        run_checks()
    except Exception as exc:  # noqa: BLE001 - reported as a failed check
        import traceback

        traceback.print_exc()
        got = f"{type(exc).__name__}: {exc}"
        check("script ran to the end", "no error", got, False)
    end = time.strftime("%H:%M:%S")

    w1 = max(len(r["check"]) for r in results)
    w2 = min(45, max(len(r["expected"]) for r in results))
    print(f"\nOSC functional check {start} - {end} (temp {_TMP})\n")
    print(f"{'check':<{w1}} | {'expected':<{w2}} | got | result")
    print("-" * (w1 + w2 + 20))
    for r in results:
        print(f"{r['check']:<{w1}} | {r['expected']:<{w2}} | "
              f"{r['got']} | {r['result']}")
    failed = [r for r in results if r["result"] != "PASS"]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"start": start, "end": end, "passed": not failed, "results": results},
            indent=2), encoding="utf-8")
    import shutil

    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
