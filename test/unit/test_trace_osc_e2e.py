# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC tracing end to end on the real program (D-09-OSC-TRACE).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE, the fake joystick driver and a
fake vJoy. The OSC listener binds 127.0.0.1 on a port the OS picks (port
0); messages come from a python-osc client over the loopback. The Send OSC
target "Loopback" is a UDP socket of this test on 127.0.0.1, port 0: what
the program sends never leaves the PC.

OSC's file has an axis (/fader), a button (/btn), an encoder (/enc), a
pattern input (/strip/*/mute) and a button /refuse. /btn has a Send OSC to
"Loopback" (/sent); /refuse has a Send OSC to a target that doesn't exist.
A feedback row sends /btn's state to "Loopback" as /fb/btn.

1. Tracing off: a Run with messages writes no line and no trace.log.
2. Tracing on with all five OSC areas ticked; Run; /btn pressed gives, in
   order, the receive line, the match line, the event line, the Send OSC
   output line and the feedback line, in the wording of the contract; the
   pattern and encoder inputs give their lines.
3. A wildcard address gives a BLOCKED line; 200 fast /fader messages give
   few receive lines with "(N messages between)"; the same refusal 15
   times is never capped (D-09-OSC-TRACE-ERRORS): no "repeated" note, every
   refusal is a line or counted "(N messages between)"; a new Run writes
   it again.
4. A sender off the allow-list gives BLOCKED lines.
5. Tracing off again: nothing more is written.
Through all of it system.log (and the system/user loggers) have no ERROR
and no traceback.

Spec: 01 S146, S148, S149; 09 D-09-OSC-TRACE, S168 (D-09-OSC-TRACE-ERRORS).
"""

from __future__ import annotations

import logging
import pathlib
import re
import socket
import sys
import time
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    run_journey,
    step,
)

FADER = "/fader"
BTN = "/btn"
ENC = "/enc"
PATTERN = "/strip/*/mute"
PATTERN_SENT = "/strip/3/mute"
REFUSE = "/refuse"
SENT = "/sent"
FB = "/fb/btn"
WILDCARD = "/fader/*"
TARGET_ID = "loopback-target"
TARGET_NAME = "Loopback"
MISSING = "missing-target"
FAST = 200
REFUSALS = 15


# +-------------------------------------------------------------------------
# | Script side (the child process)


def _loopback_listener() -> None:
    """The listener binds 127.0.0.1 on an OS-picked port (port 0)."""
    from gremlin import osc

    real = osc.OscListener

    class LoopbackListener(real):  # type: ignore[misc, valid-type]
        def start(self) -> None:
            host, port = self.host, self.port
            self.host, self.port = "127.0.0.1", 0
            try:
                super().start()
            finally:
                self.host, self.port = host, port

    osc.OscListener = LoopbackListener  # type: ignore[misc]


def _bound_port(listener: Any) -> int:  # noqa: ANN401
    method: Any = getattr(listener, "bound_port", None)
    if callable(method):
        return int(method())  # pyright: ignore[reportArgumentType]
    return int(listener._server.server_address[1])


def _server(allow: list[str]) -> None:
    from gremlin import osc_device_file

    osc_device_file.write_server(
        {
            "enabled": True,
            "host": "127.0.0.1",
            "port": 9000,
            "output_enabled": True,
            "feedback_enabled": True,
            "feedback_rate": 50,
            "announce": False,
            "find_devices": False,
            "allow_senders": list(allow),
        }
    )


def _osc_row(address: str) -> Any:  # noqa: ANN401
    from gremlin.osc import OscDevice

    for row in OscDevice().rows.rows():
        if row.label == address:
            return row
    raise AssertionError(f"no OSC input {address}")


def _parent_key(address: str) -> str:
    from gremlin.types import InputType

    row = _osc_row(address)
    word = {InputType.JoystickAxis: "axis", InputType.JoystickHat: "hat"}.get(
        row.input_type, "button"
    )
    return f"parent:{word}:{row.input_id}"


def _open_osc_page(j: Journey) -> Any:  # noqa: ANN401
    from gremlin.ui.osc_layout import OscLayoutModel

    j.ev('openConfigurationForCard(_moduleModel.cardMap("osc"))')
    j.wait_until(lambda: j.backend.uiState.currentTab == "osc", "the OSC page")
    return j.wait_until(
        lambda: j.win.findChild(OscLayoutModel), "the OSC page's layout model"
    )


def _add(j: Journey, settings: dict) -> bool:
    from gremlin.ui.osc_device_model import OscDeviceManagementModel

    model = j.win.findChild(OscDeviceManagementModel) or OscDeviceManagementModel()
    made = bool(model.createConfiguredInput(settings))
    j.settle()
    return made


def _send_osc(target: str, address: str) -> Any:  # noqa: ANN401
    from gremlin import plugin_manager
    from gremlin.types import InputType

    action = plugin_manager.PluginManager().create_instance(
        "Send OSC", InputType.JoystickButton
    )
    action.target = target
    action.address = address
    action.values = [{"source": "input", "value": "", "type": "int"}]
    return action


def _bind(j: Journey, page: Any, address: str, action: Any) -> None:  # noqa: ANN401
    """Adds an action in the shared pane and presses OK, as the page does."""
    page.beginNewAction(_parent_key(address))
    page._pane_shadow.action_sequences[0].root_action.insert_action(action, "children")
    page.commitPane()
    page.endPane()
    j.settle()


def _run(j: Journey) -> Any:  # noqa: ANN401
    """Run; a client on the loopback to the listener's OS-picked port."""
    from pythonosc.udp_client import SimpleUDPClient

    from gremlin import osc

    if not j.backend.runner.is_running():
        j.backend.toggleActiveState()
    runtime = osc.OscRuntime()
    listener = j.wait_until(lambda: runtime._listener, "the OSC listener", 10)
    return SimpleUDPClient("127.0.0.1", _bound_port(listener))


def _stop(j: Journey) -> None:
    if j.backend.runner.is_running():
        j.backend.toggleActiveState()
    j.settle()


def _lines() -> list[list]:
    from gremlin import trace

    return [list(line) for line in trace.lines()]


def _osc_lines(since: int = 0) -> list[list]:
    """OSC trace lines (control "OSC <Area>") from index since on."""
    return [ln for ln in _lines()[since:] if str(ln[1]).startswith("OSC ")]


def _wait_line(j: Journey, check: Any, what: str, timeout: float = 5.0) -> bool:  # noqa: ANN401
    try:
        j.wait_until(check, what, timeout)
        return True
    except TimeoutError:
        return False


class _Errors(logging.Handler):
    """ERROR lines and tracebacks from any logger, in this process."""

    def __init__(self) -> None:
        super().__init__(logging.DEBUG)
        self.seen: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno >= logging.ERROR or record.exc_info:
            try:
                text = record.getMessage()
            except Exception:  # noqa: BLE001
                text = str(record.msg)
            self.seen.append(f"{record.name} {record.levelname}: {text}")


class _Receiver:
    """The "Loopback" target: a UDP socket on 127.0.0.1, OS-picked port."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.setblocking(False)
        self.port = int(self.sock.getsockname()[1])
        self.got: list[tuple[str, list]] = []

    def drain(self) -> list[tuple[str, list]]:
        from pythonosc.osc_message import OscMessage

        while True:
            try:
                data = self.sock.recv(65536)
            except (BlockingIOError, OSError):
                break
            try:
                msg = OscMessage(data)
                self.got.append((msg.address, list(msg.params)))
            except Exception:  # noqa: BLE001
                self.got.append(("?", []))
        return self.got

    def close(self) -> None:
        self.sock.close()


def story(j: Journey) -> None:  # noqa: PLR0915
    from gremlin import osc_device_file, trace, util

    out = j.out
    errors = _Errors()
    for name in ("", "system", "user"):
        logging.getLogger(name).addHandler(errors)
    receiver = _Receiver()
    try:
        _loopback_listener()
        _server([])
        osc_device_file.write_targets(
            [{"id": TARGET_ID, "name": TARGET_NAME, "host": "127.0.0.1",
              "port": receiver.port}]
        )
        out["receiver-port"] = receiver.port

        # --- profile and OSC inputs -----------------------------------------
        page = _open_osc_page(j)
        out["added"] = [
            _add(j, {"address": FADER, "mode": "axis",
                     "range_min": 0.0, "range_max": 1.0}),
            _add(j, {"address": BTN, "mode": "button"}),
            _add(j, {"address": ENC, "mode": "encoder", "enc_format": "direction",
                     "enc_step": 0.05, "enc_output": "axis"}),
            _add(j, {"address": PATTERN, "mode": "button"}),
            _add(j, {"address": REFUSE, "mode": "button"}),
        ]
        _bind(j, page, BTN, _send_osc(TARGET_ID, SENT))
        _bind(j, page, REFUSE, _send_osc(MISSING, "/nowhere"))
        feedback_rows = [
            {
                "id": "fb-btn",
                "enabled": True,
                "source": {"kind": "osc_input", "input": _osc_row(BTN).uid},
                "target": TARGET_ID,
                "address": FB,
                "min": 0.0,
                "max": 1.0,
                "type": "int",
            }
        ]
        osc_device_file.write_feedback(feedback_rows)
        j.settle()

        # --- 1. tracing off: nothing written ---------------------------------
        out["file-at-start"] = trace.file_path().exists()
        client = _run(j)
        client.send_message(BTN, 1)
        client.send_message(BTN, 0)
        client.send_message(FADER, 0.5)
        j.QTest.qWait(500)
        out["off-lines"] = _osc_lines()
        out["off-file"] = trace.file_path().exists()
        _stop(j)

        # --- 2. tracing on, all five OSC areas -------------------------------
        trace.set_osc_all(True)
        trace.set_enabled(True)
        out["ticked"] = trace.osc_ticked()
        start = len(_lines())
        # A real change (an unused second target): unchanged rows aren't
        # written, which is right and traced as "not written".
        osc_device_file.write_targets(
            [{"id": TARGET_ID, "name": TARGET_NAME, "host": "127.0.0.1",
              "port": receiver.port},
             {"id": "spare-target", "name": "Spare", "host": "127.0.0.1",
              "port": receiver.port}],
            "OSC page",
        )
        # The same feedback rows again: nothing is written.
        osc_device_file.write_feedback(feedback_rows, "OSC page")
        j.settle()
        client = _run(j)
        out["port"] = _bound_port(osc_runtime_listener())
        receiver.drain()
        receiver.got.clear()
        client.send_message(BTN, 1)

        def fb_line() -> bool:
            # The press's value (1), not the resend at Run start (0);
            # feedback lines are rate-limited, so poll until a deadline.
            press = re.compile(rf"^row 1 .+ → {re.escape(FB)} 1\b")
            return any(
                ln[1] == "OSC Feedback" and press.search(ln[3])
                for ln in _osc_lines(start)
            )

        out["fb-seen"] = _wait_line(j, fb_line, "the feedback line")
        client.send_message(BTN, 0)
        client.send_message(PATTERN_SENT, 1)
        client.send_message(PATTERN_SENT, 0)
        client.send_message(ENC, 1)
        _wait_line(
            j,
            lambda: any("ticks" in ln[3] for ln in _osc_lines(start)),
            "the encoder line",
        )
        j.QTest.qWait(300)
        out["sent-to-target"] = [a for a, _v in receiver.drain()]

        # Wildcard address: refused, no traceback.
        client.send_message(WILDCARD, 1.0)
        _wait_line(
            j,
            lambda: any(WILDCARD in ln[3] and ln[2] == "BLOCKED"
                        for ln in _osc_lines(start)),
            "the wildcard BLOCKED line",
        )
        out["main-lines"] = _osc_lines(start)

        # 200 fast fader messages.
        fast_start = len(_lines())
        t0 = time.monotonic()
        for i in range(FAST):
            client.send_message(FADER, (i % 100) / 100.0)
        out["fast-send-s"] = round(time.monotonic() - t0, 3)
        j.QTest.qWait(1500)  # pending lines flushed
        out["fast-elapsed-s"] = round(time.monotonic() - t0, 3)
        out["axis-rate"] = trace.axis_rate()
        out["fast-lines"] = [
            ln for ln in _osc_lines(fast_start) if FADER in ln[3]
        ]

        # The same refusal 15 times.
        refuse_start = len(_lines())
        for _ in range(REFUSALS):
            client.send_message(REFUSE, 1)
            client.send_message(REFUSE, 0)
        j.QTest.qWait(800)
        out["refuse-lines"] = [
            ln for ln in _osc_lines(refuse_start) if ln[1] == "OSC Output"
        ]
        _stop(j)

        # A new Run starts the counts again.
        rerun_start = len(_lines())
        client = _run(j)
        client.send_message(REFUSE, 1)
        client.send_message(REFUSE, 0)
        _wait_line(
            j,
            lambda: any(ln[1] == "OSC Output" and ln[2] == "BLOCKED"
                        for ln in _osc_lines(rerun_start)),
            "a refusal after the new Run",
        )
        out["rerun-lines"] = [
            ln for ln in _osc_lines(rerun_start) if ln[1] == "OSC Output"
        ]
        _stop(j)

        # --- 4. a sender off the allow-list ----------------------------------
        _server(["10.0.0.0/8"])
        j.settle()
        blocked_start = len(_lines())
        client = _run(j)
        client.send_message(BTN, 1)
        client.send_message(BTN, 0)
        _wait_line(
            j,
            lambda: any("not on Allowed senders" in ln[3]
                        for ln in _osc_lines(blocked_start)),
            "the blocked sender line",
        )
        out["blocked-lines"] = _osc_lines(blocked_start)
        _stop(j)
        _server([])
        j.settle()

        # The file has the lines.
        j.QTest.qWait(300)
        path = trace.file_path()
        out["file-text"] = path.read_text("utf-8", errors="replace") \
            if path.exists() else None

        # --- 5. tracing off again --------------------------------------------
        trace.set_enabled(False)
        off_start = len(_lines())
        size = trace.file_size()
        client = _run(j)
        client.send_message(BTN, 1)
        client.send_message(BTN, 0)
        client.send_message(WILDCARD, 1.0)
        client.send_message(REFUSE, 1)
        j.QTest.qWait(500)
        out["off-again-lines"] = _lines()[off_start:]
        out["off-again-grew"] = trace.file_size() - size
        _stop(j)
    finally:
        receiver.close()
        for name in ("", "system", "user"):
            logging.getLogger(name).removeHandler(errors)
        out["logged-errors"] = errors.seen
        try:
            system_log = pathlib.Path(util.logs_dir()) / "system.log"
            out["system-log"] = system_log.read_text("utf-8", errors="replace") \
                if system_log.exists() else ""
        except Exception:  # noqa: BLE001
            out["system-log"] = traceback.format_exc()


def osc_runtime_listener() -> Any:  # noqa: ANN401
    from gremlin import osc

    return osc.OscRuntime()._listener


def main() -> None:
    def before(j: Journey) -> None:
        j.input_module()
        j.vjoy_module()

    Journey(before).run(story)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("trace_osc_e2e"))


def _area(lines: list[list], area: str) -> list[list]:
    return [ln for ln in lines if ln[1] == f"OSC {area}"]


def _first(lines: list[list], area: str, pattern: str) -> int:
    """Index of the first line of area whose detail matches pattern."""
    regex = re.compile(pattern)
    for i, ln in enumerate(lines):
        if ln[1] == f"OSC {area}" and regex.search(ln[3]):
            return i
    raise AssertionError(f"no OSC {area} line matching {pattern!r} in:\n"
                         + "\n".join(f"  {ln[1]} | {ln[2]} | {ln[3]}" for ln in lines))


def test_inputs_are_added_and_ticks_are_all_five(run: dict) -> None:
    assert step(run, "added") == [True] * 5
    assert step(run, "ticked") == ["receive", "inputs", "output", "feedback", "setup"]


def test_tracing_off_writes_nothing(run: dict) -> None:
    assert step(run, "file-at-start") is False
    assert step(run, "off-lines") == []
    assert step(run, "off-file") is False


def test_a_press_is_traced_from_receive_to_feedback_in_order(run: dict) -> None:
    lines = step(run, "main-lines")
    port = step(run, "port")
    rport = step(run, "receiver-port")
    esc = re.escape
    receive = _first(lines, "Receive", rf"^in 127\.0\.0\.1:\d+ {esc(BTN)} \S+ 1\b")
    match = _first(lines, "Inputs", rf"^{esc(BTN)} → .+ \(button\)")
    event = _first(lines, "Inputs", r"^event .+ pressed")
    output = _first(
        lines, "Output",
        rf"^out {TARGET_NAME} 127\.0\.0\.1:{rport} {esc(SENT)} \S+ 1 \(Send OSC\)",
    )
    # The source is the input's name, as in the match line, not its id.
    feedback = _first(lines, "Feedback", rf"^row 1 OSC Button \d+ → {esc(FB)} 1\b")
    assert receive < match < event < output < feedback, (
        receive, match, event, output, feedback, lines)
    assert lines[receive][2] == "OSC" and lines[output][2] == "OSC"
    assert isinstance(port, int) and port > 0
    # The feedback row's message goes out too, named as feedback.
    _first(lines, "Output", rf"^out {TARGET_NAME} .+ {esc(FB)} .+\(feedback row 1\)")
    assert SENT in step(run, "sent-to-target")
    assert FB in step(run, "sent-to-target")


def test_pattern_and_encoder_inputs_are_traced(run: dict) -> None:
    lines = step(run, "main-lines")
    esc = re.escape
    _first(lines, "Receive", rf"^in 127\.0\.0\.1:\d+ {esc(PATTERN_SENT)} ")
    _first(lines, "Inputs", rf"^{esc(PATTERN_SENT)} → .+ \(button\)")
    _first(lines, "Inputs", r": -?\d+ ticks ×")


def test_setup_lines_when_oscs_file_is_saved(run: dict) -> None:
    lines = step(run, "main-lines")
    _first(lines, "Setup and files", r"^OSC/module\.json saved \(.+\)$")
    _first(lines, "Setup and files", r"^OSC/module\.json not written \(.*unchanged\)$")


def test_a_wildcard_address_is_blocked_without_a_traceback(run: dict) -> None:
    lines = step(run, "main-lines")
    i = _first(
        lines, "Receive",
        rf"^BLOCKED wildcard address {re.escape(WILDCARD)} from 127\.0\.0\.1 "
        r"\(inputs need exact addresses\)$|"
        rf"^wildcard address {re.escape(WILDCARD)} from 127\.0\.0\.1 "
        r"\(inputs need exact addresses\)$",
    )
    assert lines[i][2] == "BLOCKED", lines[i]
    # Only the Receive refusal: no Inputs line for the same address.
    assert not any(
        ln[1] == "OSC Inputs" and WILDCARD in ln[3] for ln in lines
    ), [ln for ln in lines if WILDCARD in ln[3]]


def test_200_fast_messages_give_rate_limited_lines(run: dict) -> None:
    fast = [ln for ln in step(run, "fast-lines") if ln[1] == "OSC Receive"]
    rate = float(step(run, "axis-rate"))
    elapsed = float(step(run, "fast-elapsed-s"))
    assert fast, "no receive lines for the fast fader"
    most = int(rate * elapsed) + 3
    assert len(fast) <= most, (len(fast), most, rate, elapsed)
    counts = [int(m.group(1)) for ln in fast
              if (m := re.search(r"\((\d+) messages between\)", ln[3]))]
    assert counts, fast
    # Every message is either a line or counted between lines (loopback
    # UDP may still drop a few: never more than were sent).
    assert len(fast) + sum(counts) <= FAST, (len(fast), counts)
    assert len(fast) + sum(counts) >= FAST * 0.9, (len(fast), counts)


def test_the_same_refusal_15_times_is_never_capped(run: dict) -> None:
    # D-09-OSC-TRACE-ERRORS: a refusal is no error; rate limited, not capped.
    lines = [ln for ln in step(run, "refuse-lines") if "no target named" in ln[3]]
    assert lines, lines
    assert not any("repeated" in ln[3] for ln in lines), lines
    assert all(ln[2] == "BLOCKED" for ln in lines), lines
    assert all(ln[3].startswith("send refused: no target named") for ln in lines), lines
    between = [int(m.group(1)) for ln in lines
               if (m := re.search(r"\((\d+) messages? between\)", ln[3]))]
    # Every press is a line or counted between lines (UDP may drop a few).
    assert len(lines) + sum(between) >= REFUSALS * 0.9, (lines, between)


def test_a_new_run_starts_the_counts_again(run: dict) -> None:
    lines = [ln for ln in step(run, "rerun-lines") if "no target named" in ln[3]]
    assert len(lines) == 1, lines
    assert "repeated" not in lines[0][3], lines


def test_a_sender_off_the_allow_list_is_blocked(run: dict) -> None:
    lines = step(run, "blocked-lines")
    i = _first(lines, "Receive",
               r"^(BLOCKED )?sender 127\.0\.0\.1 not on Allowed senders$")
    assert lines[i][2] == "BLOCKED", lines[i]
    # Nothing reached the inputs.
    assert not [ln for ln in _area(lines, "Inputs") if BTN in ln[3]], lines


def test_the_trace_file_has_the_osc_lines(run: dict) -> None:
    text = step(run, "file-text")
    assert text, "no trace.log"
    for area in ("OSC Receive", "OSC Inputs", "OSC Output", "OSC Feedback"):
        assert area in text, area
    assert "in 127.0.0.1:" in text and "not on Allowed senders" in text


def test_tracing_off_again_writes_nothing(run: dict) -> None:
    assert step(run, "off-again-lines") == []
    assert step(run, "off-again-grew") == 0


def test_no_error_or_traceback_in_the_logs(run: dict) -> None:
    errors = [e for e in step(run, "logged-errors") if "OSC" in e or "osc" in e]
    assert errors == [], errors
    text = step(run, "system-log")
    assert "Traceback" not in text, text[-3000:]
    bad = [ln for ln in text.splitlines() if " ERROR " in ln or "CRITICAL" in ln]
    assert bad == [], bad


if __name__ == "__main__":
    main()
