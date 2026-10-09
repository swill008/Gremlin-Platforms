# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""OSC functional check: real UDP packets on loopback through the real
OscRuntime (python-osc server thread), off-screen, in a temp USERPROFILE.

    python tools/osc_functional_check.py [--json results.json]

Binds and sends on 127.0.0.1 only (never 0.0.0.0). Events are taken from
the signal the runtime emits (EventListener().joystick_event); a stand-in
EventListener carries it so no hardware, hooks or vJoy are touched.
Part 2 adds a phone stand-in (a UDP socket on 127.0.0.1, registered as a
target) for Send OSC, reply, the output switch, feedback (change, rate
limit, mode change, sync), the encoder and the Monitor's traffic/hold_open.
Part 3 sends packets exactly as Companion's Generic OSC module builds them
(integer, float, string, no-argument, T/F booleans, several values); part 4
sends to a stand-in Companion API (custom variable, key text, key colour).
Exit code 0 only when no check fails (skipped checks are listed)."""

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
_LISTENER.gremlin_active = False  # type: ignore[attr-defined]


def _listener_singleton() -> _Listener:
    return _LISTENER


_listener_singleton.instance = _LISTENER  # type: ignore[attr-defined]  (ModeManager reads it)
event_handler.EventListener = _listener_singleton  # type: ignore[assignment,misc]

from gremlin import osc_bulk  # noqa: E402,F401  (patches the page model)
from gremlin.osc import OSC_DEVICE_UUID, OscDevice, OscRuntime  # noqa: E402
from gremlin.profile import InputItem, Profile  # noqa: E402
from gremlin.types import InputType  # noqa: E402
from gremlin.ui.osc_device_model import OscDeviceManagementModel  # noqa: E402

AXIS = InputType.JoystickAxis
BUTTON = InputType.JoystickButton
HOST = "127.0.0.1"
OVERALL_S = 150.0
_T0 = time.monotonic()

# -- helpers ------------------------------------------------------------------

events: list[dict[str, Any]] = []
results: list[dict[str, Any]] = []
# Open phone stand-ins, read on every pump so arrival times are true.
_PHONES: list[Any] = []


def _drain_phones() -> None:
    for phone in list(_PHONES):
        phone.drain()


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
        _drain_phones()
        time.sleep(0.005)


def wait_for(pred: Any, timeout: float = 1.5) -> bool:  # noqa: ANN401
    end = time.monotonic() + min(timeout, 2.0)
    while time.monotonic() < end:
        APP.processEvents(QtCore.QEventLoop.ProcessEventsFlag.AllEvents, 10)
        _drain_phones()
        if pred():
            return True
        if time.monotonic() - _T0 > OVERALL_S:
            raise TimeoutError(f"overall {OVERALL_S:.0f} s timeout")
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


# -- part 2: output, feedback, encoder, monitor (D-09-OSC-*) --------------------


def _parse(data: bytes) -> dict[str, Any]:
    from pythonosc.osc_message import OscMessage
    from pythonosc.parsing import osc_types

    msg = OscMessage(data)
    _, idx = osc_types.get_string(data, 0)
    tags, _ = osc_types.get_string(data, idx)
    return {"t": time.monotonic(), "address": msg.address,
            "args": list(msg.params), "types": tags.lstrip(",")}


class Phone:
    """A phone stand-in: an OSC receiver on 127.0.0.1 that also sends from
    its own socket (so "reply" comes back to it)."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((HOST, 0))
        self.sock.setblocking(False)
        self.port: int = self.sock.getsockname()[1]
        self.got: list[dict[str, Any]] = []
        _PHONES.append(self)

    def drain(self) -> None:
        while True:
            try:
                data, _ = self.sock.recvfrom(65536)
            except BlockingIOError:
                return
            except ConnectionResetError:  # Windows: an earlier ICMP reply
                continue
            except OSError:
                return
            self.got.append(_parse(data))

    def send_args(self, port: int, address: str, *args: Any) -> None:  # noqa: ANN401
        builder = OscMessageBuilder(address=address)
        for arg in args:
            builder.add_arg(arg)
        self.sock.sendto(builder.build().dgram, (HOST, port))

    def since(self, n: int, address: str | None = None) -> list[dict[str, Any]]:
        self.drain()
        return [m for m in self.got[n:] if address is None or m["address"] == address]

    def wait(self, n: int, count: int, address: str | None = None,
             timeout: float = 1.5) -> list[dict[str, Any]]:
        wait_for(lambda: len(self.since(n, address)) >= count, timeout)
        return self.since(n, address)

    def quiet(self, n: int, seconds: float = 0.3) -> list[dict[str, Any]]:
        pump(seconds)
        return self.since(n)

    def close(self) -> None:
        if self in _PHONES:
            _PHONES.remove(self)
        self.sock.close()


def msgs(found: list[dict[str, Any]]) -> list[tuple]:
    out = []
    for m in found:
        args = [round(a, 3) if isinstance(a, float) else a for a in m["args"]]
        out.append((m["address"], args, m["types"]))
    return out


def run_checks2() -> None:
    from action_plugins.send_osc import SendOscData, SendOscFunctor
    from gremlin import osc_feedback, osc_output, osc_traffic, run_scope
    from gremlin.base_classes import Value
    from gremlin.event_handler import Event
    from gremlin.mode_manager import Mode, ModeManager
    from gremlin.osc import input_name

    port = free_port()
    srv: dict[str, Any] = {
        "enabled": True, "host": HOST, "port": port,
        "autorelease_no_arg": True, "autorelease_delay_ms": 300,
        "output_enabled": True, "reply_to_sender": True,
        "feedback_enabled": True, "resend_run": True, "resend_mode": True,
        "resend_profile": True, "sync_enabled": True,
        "sync_address": "/gremlin/sync", "feedback_rate": 10,
    }

    def set_server(**changes: Any) -> None:  # noqa: ANN401
        srv.update(changes)
        odf.write_server(dict(srv))
        pump(0.05)

    set_server()
    rows = OscDevice().rows
    rows.load_dict({"inputs": []})
    fbtn = rows.create(BUTTON, "/fbtn")
    fax = rows.create(AXIS, "/fax", range_min=0.0, range_max=1.0)
    enc = rows.create(AXIS, "/enc", mode="encoder", enc_output="axis", enc_step=0.1)
    encp = rows.create(BUTTON, "/encp", mode="encoder", enc_output="pulse_cw",
                       delay_ms=60)
    encn = rows.create(BUTTON, "/encn", mode="encoder", enc_output="pulse_ccw",
                       delay_ms=60)
    syncrow = rows.create(BUTTON, "/gremlin/sync")  # sync must never reach it
    odf.save()

    phone, phone2 = Phone(), Phone()
    phone_id = odf.new_id()
    odf.write_targets([{"id": phone_id, "name": "Phone", "host": HOST,
                        "port": phone.port}])
    odf.write_feedback([
        {"id": "fbmode", "source": {"kind": "mode"}, "target": phone_id,
         "address": "/fb/mode", "type": "auto"},
        {"id": "fbbtn", "source": {"kind": "osc_input", "input": fbtn.uid},
         "target": phone_id, "address": "/fb/btn", "min": 0, "max": 1,
         "type": "int"},
        {"id": "fbax", "source": {"kind": "osc_input", "input": fax.uid},
         "target": phone_id, "address": "/fb/ax", "min": 0, "max": 1,
         "type": "float"},
    ])
    check("targets + feedback written",
          (phone_id, 3), (odf.read_targets()[0]["id"], len(odf.read_feedback())))

    profile = profile_with([fbtn, fax, enc, encp, encn, syncrow])
    profile.modes.add_mode("Flight")
    first = profile.modes.first_mode
    shared_state.current_profile = profile

    runtime = OscRuntime()
    client = Client(port)
    osc_traffic.clear()
    osc_output.reset()
    event = Event(BUTTON, 1, OSC_DEVICE_UUID, first, is_pressed=True)

    def action(target: str, address: str, values: list[dict]) -> SendOscFunctor:
        data = SendOscData(BUTTON)
        data.target, data.address, data.values = target, address, values
        return SendOscFunctor(data)

    def fixed(value: str, kind: str) -> dict:
        return {"source": "fixed", "value": value, "type": kind}

    send_go = action(phone_id, "/out/go", [
        fixed("7", "int"), fixed("1.5", "float"), fixed("hi", "text"),
        fixed("true", "bool"), {"source": "input", "value": "", "type": "auto"},
    ])
    reply = action("reply", "/out/reply", [fixed("ok", "text")])
    full_set = ["/fb/ax", "/fb/btn", "/fb/mode"]
    running = False
    try:
        # A Run as CodeRunner does it: begin, mode, OSC, feedback; Stop stages.
        n = len(phone.got)
        run_scope.begin()
        running = True
        run_scope.on_stop(run_scope.Stage.CUT_INPUT, "OSC feedback",
                          lambda: osc_feedback.stop())
        run_scope.on_stop(run_scope.Stage.CUT_INPUT, "OSC releases",
                          lambda: runtime.release_held())
        run_scope.on_stop(run_scope.Stage.CANCEL, "OSC", lambda: runtime.stop())
        ModeManager().start_run(first)
        runtime.start()
        osc_feedback.start(None)
        got = phone.wait(n, 3)
        check("run start: full resend to the phone",
              sorted([("/fb/ax", [0.5], "f"), ("/fb/btn", [0], "i"),
                      ("/fb/mode", [first], "s")]), sorted(msgs(got)))

        # (1) Send OSC to a target: values and types.
        n = len(phone.got)
        send_go(event, Value(True))
        got = phone.wait(n, 1, "/out/go")
        check("Send OSC: phone gets address/values/types",
              [("/out/go", [7, 1.5, "hi", True, 1.0], "ifsTf")], msgs(got))
        n = len(phone.got)
        send_go(event, Value(False))
        check("Send OSC on press only: release sends nothing", [],
              msgs(phone.quiet(n)))

        # Auto type: the type last received on that address.
        phone.send_args(port, "/out/auto", 3)
        wait_for(lambda: osc_output.received_type("/out/auto", 0) is not None)
        n = len(phone.got)
        action(phone_id, "/out/auto",
               [{"source": "input", "value": "", "type": "auto"}])(event, Value(True))
        check("Send OSC Auto: int after an int came in",
              [("/out/auto", [1], "i")], msgs(phone.wait(n, 1, "/out/auto")))

        # "reply": to the sender of the last incoming packet.
        phone2.send_args(port, "/hello", 1)
        wait_for(lambda: osc_output.last_sender() == (HOST, phone2.port))
        n1, n2 = len(phone.got), len(phone2.got)
        reply(event, Value(True))
        got2 = phone2.wait(n2, 1, "/out/reply")
        check("reply goes to the last sender (phone 2)",
              ([("/out/reply", ["ok"], "s")], []),
              (msgs(got2), msgs(phone.since(n1, "/out/reply"))))
        phone.send_args(port, "/hello", 1)
        wait_for(lambda: osc_output.last_sender() == (HOST, phone.port))
        n1, n2 = len(phone.got), len(phone2.got)
        reply(event, Value(True))
        got1 = phone.wait(n1, 1, "/out/reply")
        check("reply follows a new sender (phone)",
              ([("/out/reply", ["ok"], "s")], []),
              (msgs(got1), msgs(phone2.since(n2, "/out/reply"))))
        set_server(reply_to_sender=False)
        n = len(phone.got)
        reply(event, Value(True))
        check("Reply to sender off: reply sends nothing", [],
              msgs(phone.quiet(n)))
        set_server(reply_to_sender=True)

        # (2) Feedback on change.
        n = len(phone.got)
        client.send_args("/fbtn", 1.0)
        on = phone.wait(n, 1, "/fb/btn")
        n = len(phone.got)
        client.send_args("/fbtn", 0.0)
        off = phone.wait(n, 1, "/fb/btn")
        check("feedback: OSC input echo on change",
              [("/fb/btn", [1], "i"), ("/fb/btn", [0], "i")], msgs(on + off))

        # Output master switch off: no Send OSC, no feedback.
        set_server(output_enabled=False)
        n = len(phone.got)
        send_go(event, Value(True))
        client.send_args("/fbtn", 1.0)
        pump(0.2)
        client.send_args("/fbtn", 0.0)
        check("output off: nothing (Send OSC + feedback)", [],
              msgs(phone.quiet(n, 0.4)))
        set_server(output_enabled=True)
        n = len(phone.got)
        send_go(event, Value(True))
        check("output back on: Send OSC sends again", 1,
              len(phone.wait(n, 1, "/out/go")))

        # Rate limit (10/s per address): 21 changes 20 ms apart (~420 ms)
        # coalesce to a few sends; the latest value wins.
        pump(0.2)
        n = len(phone.got)
        for i in range(21):
            client.send_args("/fax", i / 20)
            pump(0.02)
        wait_for(lambda: bool(phone.since(n, "/fb/ax"))
                 and phone.since(n, "/fb/ax")[-1]["args"] == [1.0], 1.5)
        pump(0.3)
        got = phone.since(n, "/fb/ax")
        gaps = [round((b["t"] - a["t"]) * 1000) for a, b in zip(got, got[1:])]
        check("rate limit: 21 changes in ~420 ms coalesce, last value 1.0",
              "3..7 msgs, last [1.0]",
              f"{len(got)} msgs {[m['args'] for m in got]}",
              3 <= len(got) <= 7 and bool(got) and got[-1]["args"] == [1.0])
        check("rate limit: >= ~100 ms between sends", ">= 85 ms", f"{gaps} ms",
              all(g >= 85 for g in gaps))

        # Mode change: the mode row and a full resend.
        pump(0.15)
        n = len(phone.got)
        ModeManager().switch_to(Mode("Flight", first))
        got = phone.wait(n, 3)
        pump(0.2)
        got = phone.since(n)
        check("mode change: phone gets mode name + full set",
              (["Flight"], full_set),
              ([m["args"][0] for m in got if m["address"] == "/fb/mode"][:1],
               sorted({m["address"] for m in got})))

        # Sync: phone asks, gets the full set; no input sees it.
        pump(0.15)
        n, k = len(phone.got), len(events)
        phone.send_args(port, "/gremlin/sync")
        got = phone.wait(n, 3)
        pump(0.2)
        check("sync: phone gets the full set", full_set,
              sorted(m["address"] for m in phone.since(n)))
        check("sync never reaches inputs (row on /gremlin/sync)", [],
              short(take(k)))

        # (3) Encoder axis: auto format, step 0.1, accumulates, clamps.
        def enc_send(address: str, value: Any, want: int = 1) -> list:  # noqa: ANN401
            k = len(events)
            client.send_args(address, value)
            wait_for(lambda: len(events) >= k + want)
            return short(take(k))

        got = []
        for v in (1, 1, 0):
            got += enc_send("/enc", v)
        check("encoder auto=direction: 1,1,0 -> 0.1,0.2,0.1",
              [("A", enc.input_id, 0.1), ("A", enc.input_id, 0.2),
               ("A", enc.input_id, 0.1)], got)
        check("encoder: -2 switches to signed -> -0.1",
              [("A", enc.input_id, -0.1)], enc_send("/enc", -2))
        k = len(events)
        client.send_args("/enc", 0)
        pump(0.3)
        check("encoder signed after a negative: 0 is no turn", [], short(take(k)))
        check("encoder signed: 1 -> 0.0", [("A", enc.input_id, 0.0)],
              enc_send("/enc", 1))
        check("encoder clamps: 30 -> 1.0", [("A", enc.input_id, 1.0)],
              enc_send("/enc", 30))

        # Encoder pulses: press/release pairs per tick in that direction.
        pair_p = [("B", encp.input_id, True), ("B", encp.input_id, False)]
        pair_n = [("B", encn.input_id, True), ("B", encn.input_id, False)]
        k = len(events)
        client.send_args("/encp", 0)  # direction: counter-clockwise
        pump(0.25)
        check("pulse_cw ignores a ccw tick (0)", [], short(take(k)))
        check("pulse_cw: 1 -> one press/release", pair_p,
              enc_send("/encp", 1, 2))
        pump(0.1)
        check("pulse_cw signed 3 -> three pairs", pair_p * 3,
              enc_send("/encp", 3, 6))
        pump(0.1)
        k = len(events)
        client.send_args("/encp", -1)
        pump(0.25)
        check("pulse_cw ignores -1", [], short(take(k)))
        check("pulse_ccw: -2 -> two pairs", pair_n * 2, enc_send("/encn", -2, 4))
        pump(0.1)

        # (4) Monitor: in and out with peers and matched names.
        entries = osc_traffic.recent()
        cport = client._sock.getsockname()[1]
        ins = [e for e in entries if e["direction"] == "in"
               and e["address"] == "/fbtn"]
        outs = [e for e in entries if e["direction"] == "out"
                and e["address"] == "/out/go"]
        hello = [e for e in entries if e["direction"] == "in"
                 and e["address"] == "/hello"]
        check("monitor: in /fbtn with peer and matched name",
              (f"{HOST}:{cport}", [input_name(fbtn)]),
              (ins[0]["peer"], ins[0]["matched"]) if ins else None)
        check("monitor: out /out/go with the phone as peer",
              (f"{HOST}:{phone.port}", [7, 1.5, "hi", True, 1.0]),
              (outs[0]["peer"], outs[0]["args"]) if outs else None)
        check("monitor: unmatched in has no input", [],
              hello[0]["matched"] if hello else None)
        fb_out = [e for e in entries if e["direction"] == "out"
                  and e["address"].startswith("/fb/")]
        check("monitor: feedback sends noted as out", True, bool(fb_out))

        # Stop: everything through the Stop stages.
        run_scope.stop()
        running = False
        ModeManager().end_run()
        pump(0.1)
        n = len(phone.got)
        sent = osc_output.send(phone_id, "/out/go", [1])
        send_go(event, Value(True))
        client.send_args("/fbtn", 1.0)
        check("after Stop: Send OSC and feedback send nothing", (False, []),
              (sent, msgs(phone.quiet(n))))
        check("after Stop: port closed", True,
              runtime._listener is None and port_free(port))

        # hold_open: the Monitor keeps the port open with no Run.
        osc_traffic.clear()
        k = len(events)
        opened = runtime.hold_open("monitor")
        check("hold_open opens the port with no Run", True,
              opened and not port_free(port))
        client.send_args("/fbtn", 1.0)
        wait_for(lambda: any(e["address"] == "/fbtn" for e in osc_traffic.recent()))
        seen = [e for e in osc_traffic.recent() if e["address"] == "/fbtn"]
        check("held open: traffic noted with matched name, no input event",
              ([input_name(fbtn)], []),
              (seen[0]["matched"] if seen else None, short(take(k))))
        runtime.release_open("monitor")
        pump(0.1)
        check("release_open closes the port", True,
              runtime._listener is None and port_free(port))
        before = len(osc_traffic.recent())
        client.send_args("/fbtn", 0.0)
        pump(0.3)
        check("released: packets not seen", before, len(osc_traffic.recent()))
    finally:
        try:
            if running:
                run_scope.stop()
            runtime.release_open("monitor")
            runtime.stop()
            osc_feedback.stop()
            osc_output.reset()
        finally:
            client.close()
            phone.close()
            phone2.close()


# -- part 3: Companion-style incoming (D-09-OSC-COMPANION) ---------------------
#
# Packets built exactly as Companion's Generic OSC module sends them: "Send
# integer" (,i), "Send float" (,f), "Send string" (,s), "Send message" with
# no arguments (,), "Send boolean" (,T / ,F: no data bytes) and "Send message"
# with several arguments ('1 "go" 2.5' -> ,isf).


def companion_packet(address: str, *typed: tuple[Any, str]) -> bytes:  # noqa: ANN401
    """A raw OSC packet with explicit type tags, as Generic OSC builds it."""
    builder = OscMessageBuilder(address=address)
    for value, tag in typed:
        builder.add_arg(value, arg_type=tag)
    return builder.build().dgram


def run_checks3() -> None:
    port = free_port()
    odf.write_server({
        "enabled": True, "host": HOST, "port": port,
        "autorelease_no_arg": True, "autorelease_delay_ms": 300,
    })
    rows = OscDevice().rows
    rows.load_dict({"inputs": []})
    fire = rows.create(BUTTON, "/sd/fire")
    fader = rows.create(AXIS, "/sd/fader", range_min=0.0, range_max=1.0)
    scene = rows.create(BUTTON, "/sd/scene", cmd_mode="data", data=["intro"],
                        delay_ms=100)
    go = rows.create(BUTTON, "/sd/go", trigger=True, delay_ms=150)
    flag = rows.create(BUTTON, "/sd/flag")
    multi_b = rows.create(BUTTON, "/sd/multi", source=0)
    multi_a = rows.create(AXIS, "/sd/multi", source=2, range_min=0.0, range_max=5.0)
    odf.save()
    shared_state.current_profile = profile_with(
        [fire, fader, scene, go, flag, multi_b, multi_a])

    runtime = OscRuntime()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, 0))

    def send(data: bytes) -> None:
        sock.sendto(data, (HOST, port))

    def send_wait(data: bytes, count: int, timeout: float = 1.5) -> list[tuple]:
        k = len(events)
        send(data)
        wait_for(lambda: len(events) >= k + count, timeout)
        pump(0.05)
        return short(take(k))

    try:
        runtime.start()

        # Send integer: press 1 / release 0.
        pkt1 = companion_packet("/sd/fire", (1, "i"))
        got = send_wait(pkt1, 1)
        got += send_wait(companion_packet("/sd/fire", (0, "i")), 1)
        check("Companion Send integer 1/0 -> button press/release",
              [("B", fire.input_id, True), ("B", fire.input_id, False)], got)

        # Send float -> axis.
        got = send_wait(companion_packet("/sd/fader", (0.75, "f")), 1)
        check("Companion Send float 0.75 -> axis 0.5",
              [("A", fader.input_id, 0.5)], got)

        # Send string -> data-mode input ("intro" fires, "outro" does not).
        k = len(events)
        send(companion_packet("/sd/scene", ("outro", "s")))
        pump(0.3)
        other = short(take(k))
        got = send_wait(companion_packet("/sd/scene", ("intro", "s")), 2)
        check("Companion Send string: other text ignored by data input", [], other)
        check("Companion Send string 'intro' -> data input press/release",
              [("B", scene.input_id, True), ("B", scene.input_id, False)], got)

        # Send message without arguments -> Trigger input press + auto-release.
        noarg = companion_packet("/sd/go")
        check("no-argument packet is address + ',' only",
              b"/sd/go\x00\x00,\x00\x00\x00", noarg)
        k = len(events)
        send(noarg)
        wait_for(lambda: len(events) >= k + 2, 1.5)
        evs = take(k)
        gap = round((evs[1]["t"] - evs[0]["t"]) * 1000) if len(evs) >= 2 else None
        check("Companion no-argument -> Trigger press + auto-release",
              [("B", go.input_id, True), ("B", go.input_id, False)], short(evs))
        check("Trigger auto-release after its 150 ms", "130..400 ms", f"{gap} ms",
              gap is not None and 130 <= gap <= 400)

        # Send boolean: T / F with no data bytes.
        pkt_t = companion_packet("/sd/flag", (True, "T"))
        pkt_f = companion_packet("/sd/flag", (False, "F"))
        check("boolean packets: tags ,T / ,F and no data bytes",
              (b",T\x00\x00", b",F\x00\x00", 16, 16),
              (pkt_t[-4:], pkt_f[-4:], len(pkt_t), len(pkt_f)))
        got = send_wait(pkt_t, 1)
        got += send_wait(pkt_f, 1)
        check("Companion Send boolean T/F -> button press/release",
              [("B", flag.input_id, True), ("B", flag.input_id, False)], got)

        # Several values: '1 "go" 2.5' -> ,isf; P1 button, P3 axis.
        pkt = companion_packet("/sd/multi", (1, "i"), ("go", "s"), (2.5, "f"))
        got = send_wait(pkt, 2)
        check("Companion '1 \"go\" 2.5': P1 button pressed, P3 axis 2.5/5 -> 0.0",
              sorted([("B", multi_b.input_id, True), ("A", multi_a.input_id, 0.0)]),
              sorted(got))
        pkt = companion_packet("/sd/multi", (0, "i"), ("go", "s"), (5.0, "f"))
        got = send_wait(pkt, 2)
        check("Companion '0 \"go\" 5.0': P1 released, P3 axis 1.0",
              sorted([("B", multi_b.input_id, False), ("A", multi_a.input_id, 1.0)]),
              sorted(got))
    finally:
        try:
            runtime.stop()
        finally:
            sock.close()


# -- part 4: outgoing to a stand-in Companion API (D-09-OSC-COMPANION) ----------


def _onoff_built() -> bool:
    """CFB's off/on values on feedback rows (gremlin/osc_feedback.py)."""
    from gremlin import osc_feedback

    source = Path(osc_feedback.__file__).read_text(encoding="utf-8")
    return "off_value" in source and "on_value" in source


def skip(name: str, why: str = "not built yet") -> None:
    results.append({"check": name, "expected": "-", "got": f"skipped ({why})",
                    "result": "SKIP"})


def run_checks4() -> None:
    from action_plugins.send_osc import SendOscData, SendOscFunctor
    from gremlin import osc_feedback, osc_output, run_scope
    from gremlin.base_classes import Value
    from gremlin.event_handler import Event
    from gremlin.mode_manager import Mode, ModeManager

    port = free_port()
    odf.write_server({
        "enabled": True, "host": HOST, "port": port,
        "autorelease_no_arg": True, "autorelease_delay_ms": 300,
        "output_enabled": True, "reply_to_sender": True,
        "feedback_enabled": True, "resend_run": True, "resend_mode": True,
        "resend_profile": True, "sync_enabled": False, "feedback_rate": 20,
    })
    rows = OscDevice().rows
    rows.load_dict({"inputs": []})
    gear = rows.create(BUTTON, "/sd/gear")
    odf.save()

    companion = Phone()  # stands in for Companion's OSC Listener (API port)
    comp_id = odf.new_id()
    odf.write_targets([{"id": comp_id, "name": "Companion", "host": HOST,
                        "port": companion.port}])
    var_addr = "/custom-variable/gremlin_mode/value"
    text_addr = "/location/1/0/3/style/text"
    colour_addr = "/location/1/0/3/style/bgcolor"
    hex_addr = "/location/1/0/4/style/bgcolor"
    onoff = _onoff_built()
    feedback: list[dict] = []
    if onoff:
        feedback += [
            {"id": "ctext", "source": {"kind": "osc_input", "input": gear.uid},
             "target": comp_id, "address": text_addr, "type": "text",
             "off_value": "GEAR UP", "on_value": "GEAR DN"},
            {"id": "ccol", "source": {"kind": "osc_input", "input": gear.uid},
             "target": comp_id, "address": colour_addr, "type": "auto",
             "off_value": "51 51 51", "on_value": "42 122 70"},
        ]
    odf.write_feedback(feedback)
    from gremlin.ui import osc_feedback_model

    model_cls = osc_feedback_model.OscFeedbackModel
    templates = onoff and hasattr(model_cls, "addTemplateRow")
    if templates:
        # The real Module Setup path: Companion templates on the model.
        model = model_cls()
        model.addTemplateRow("companion_variable", {"name": "gremlin_mode"})
        model.addTemplateRow("companion_colour", {"page": 1, "row": 0, "column": 4,
                                                  "off": "#333333", "on": "#2A7A46"})
        rows_now = odf.read_feedback()
        made = {r.get("template"): r for r in rows_now if r.get("template")}
        var_row = made.get("companion_variable", {})
        hex_row = made.get("companion_colour", {})
        check("templates: variable + colour rows on the Companion target",
              [(var_addr, "text", comp_id),
               (hex_addr, "#333333", "#2a7a46", comp_id), 1],
              [(var_row.get("address"), var_row.get("type"), var_row.get("target")),
               (hex_row.get("address"), hex_row.get("off_value"),
                hex_row.get("on_value"), hex_row.get("target")),
               len(odf.read_targets())])
        # The colour template follows a vJoy button; point it at the OSC input
        # (no vJoy here).
        for r in rows_now:
            if r.get("template") == "companion_colour":
                r["source"] = {"kind": "osc_input", "input": gear.uid}
        odf.write_feedback(rows_now)
    else:
        skip("templates: variable + colour rows on the Companion target")
        odf.write_feedback(feedback + [
            {"id": "cvar", "source": {"kind": "mode"}, "target": comp_id,
             "address": var_addr, "type": "text"}])
    feedback = odf.read_feedback()
    check("Companion target + feedback rows written",
          ("Companion", 4 if templates else len(feedback)),
          (odf.read_targets()[0]["name"], len(feedback)))

    profile = profile_with([gear])
    profile.modes.add_mode("Flight")
    first = profile.modes.first_mode
    shared_state.current_profile = profile

    runtime = OscRuntime()
    client = Client(port)
    osc_output.reset()
    event = Event(BUTTON, 1, OSC_DEVICE_UUID, first, is_pressed=True)

    def send_osc(address: str, values: list[dict]) -> SendOscFunctor:
        data = SendOscData(BUTTON)
        data.target, data.address, data.values = comp_id, address, values
        return SendOscFunctor(data)

    running = False
    try:
        n = len(companion.got)
        run_scope.begin()
        running = True
        run_scope.on_stop(run_scope.Stage.CUT_INPUT, "OSC feedback",
                          lambda: osc_feedback.stop())
        run_scope.on_stop(run_scope.Stage.CANCEL, "OSC", lambda: runtime.stop())
        ModeManager().start_run(first)
        runtime.start()
        osc_feedback.start(None)
        got = companion.wait(n, 1, var_addr)
        check("run start: custom variable gets the mode (s)",
              [(var_addr, [first], "s")], msgs(got))

        # Mode change -> /custom-variable/gremlin_mode/value "Flight" (s).
        pump(0.1)
        n = len(companion.got)
        ModeManager().switch_to(Mode("Flight", first))
        got = companion.wait(n, 1, var_addr)
        check("feedback: /custom-variable/gremlin_mode/value \"Flight\" (s)",
              [(var_addr, ["Flight"], "s")], msgs(got)[:1])

        # Send OSC to the Companion target: the same variable and key text.
        n = len(companion.got)
        send_osc(var_addr, [{"source": "fixed", "value": "Flight", "type": "text"}])(
            event, Value(True))
        check("Send OSC: /custom-variable/gremlin_mode/value \"Flight\" (s)",
              [(var_addr, ["Flight"], "s")], msgs(companion.wait(n, 1, var_addr)))
        n = len(companion.got)
        send_osc(text_addr, [{"source": "fixed", "value": "GEAR DN", "type": "text"}])(
            event, Value(True))
        check("Send OSC: /location/1/0/3/style/text \"GEAR DN\" (s)",
              [(text_addr, ["GEAR DN"], "s")], msgs(companion.wait(n, 1, text_addr)))
        n = len(companion.got)
        send_osc(colour_addr, [{"source": "fixed", "value": v, "type": "int"}
                               for v in ("42", "122", "70")])(event, Value(True))
        check("Send OSC: /location/1/0/3/style/bgcolor 42 122 70 (iii)",
              [(colour_addr, [42, 122, 70], "iii")],
              msgs(companion.wait(n, 1, colour_addr)))

        # Feedback with off/on values: key text and key colour follow the input.
        names = ("feedback off/on: style/text on press -> \"GEAR DN\" (s)",
                 "feedback off/on: style/bgcolor on press -> 42 122 70 (iii)",
                 "feedback off/on: release -> \"GEAR UP\" + 51 51 51")
        if not onoff:
            for name in names:
                skip(name)
        else:
            pump(0.1)
            n = len(companion.got)
            client.send_args("/sd/gear", 1)
            text_on = companion.wait(n, 1, text_addr)
            col_on = companion.wait(n, 1, colour_addr)
            check(names[0], [(text_addr, ["GEAR DN"], "s")], msgs(text_on)[-1:])
            check(names[1], [(colour_addr, [42, 122, 70], "iii")], msgs(col_on)[-1:])
            pump(0.1)
            n = len(companion.got)
            client.send_args("/sd/gear", 0)
            text_off = companion.wait(n, 1, text_addr)
            col_off = companion.wait(n, 1, colour_addr)
            check(names[2],
                  [(text_addr, ["GEAR UP"], "s"), (colour_addr, [51, 51, 51], "iii")],
                  msgs(text_off)[-1:] + msgs(col_off)[-1:])
        hex_name = "colour template #333333/#2a7a46: release, press -> r g b (iii)"
        if not templates:
            skip(hex_name)
        else:
            # Released above: the last sent is off; press sends on.
            off_now = companion.since(0, hex_addr)
            n = len(companion.got)
            client.send_args("/sd/gear", 1)
            on_now = companion.wait(n, 1, hex_addr)
            check(hex_name,
                  [(hex_addr, [51, 51, 51], "iii"), (hex_addr, [42, 122, 70], "iii")],
                  msgs(off_now)[-1:] + msgs(on_now)[-1:])
            n = len(companion.got)
            client.send_args("/sd/gear", 0)
            companion.wait(n, 1, hex_addr)

        run_scope.stop()
        running = False
        ModeManager().end_run()
    finally:
        try:
            if running:
                run_scope.stop()
            runtime.stop()
            osc_feedback.stop()
            osc_output.reset()
        finally:
            client.close()
            companion.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", help="write the results as JSON here")
    args = parser.parse_args()
    start = time.strftime("%H:%M:%S")
    for part in (run_checks, run_checks2, run_checks3, run_checks4):
        try:
            part()
        except Exception as exc:  # noqa: BLE001 - reported as a failed check
            import traceback

            traceback.print_exc()
            got = f"{type(exc).__name__}: {exc}"
            check(f"{part.__name__} ran to the end", "no error", got, False)
    end = time.strftime("%H:%M:%S")

    w1 = max(len(r["check"]) for r in results)
    w2 = min(45, max(len(r["expected"]) for r in results))
    print(f"\nOSC functional check {start} - {end} (temp {_TMP})\n")
    print(f"{'check':<{w1}} | {'expected':<{w2}} | got | result")
    print("-" * (w1 + w2 + 20))
    for r in results:
        print(f"{r['check']:<{w1}} | {r['expected']:<{w2}} | "
              f"{r['got']} | {r['result']}")
    failed = [r for r in results if r["result"] == "FAIL"]
    skipped = [r for r in results if r["result"] == "SKIP"]
    ran = len(results) - len(skipped)
    print(f"\n{ran - len(failed)}/{ran} passed, {len(skipped)} skipped")
    if args.json:
        Path(args.json).write_text(json.dumps(
            {"start": start, "end": end, "passed": not failed,
             "skipped": len(skipped), "results": results},
            indent=2), encoding="utf-8")
    import shutil

    shutil.rmtree(_TMP, ignore_errors=True)
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
