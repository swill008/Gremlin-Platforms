# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The Home OSC card's second line, end to end on the real program
(D-09-OSC-CARD-LINE, 2026-10-12).

A journey (test/journeys/_harness.py): the app is built off-screen in its
own process with a temporary USERPROFILE; the harness points OSC's server
at 127.0.0.1 and a port the OS picked. Messages come from a real UDP
socket on 127.0.0.1 (the loopback exception for OSC socket tests). The
line is read from the OSC card on Home, the label the card shows.

Run "open" (the port free):
1. once start-up opens the port: "Listening on 127.0.0.1:<port>";
2. a message from the loopback client: "From 127.0.0.1: /test 0.5";
3. back to "Listening on ..." about 3 s after the last message;
4. 100 messages in 1 s: the line changes at most 4 times a second and ends
   on the newest;
5. Listen for OSC messages off: "Not listening (Listen for OSC messages is
   off)"; on again: "Listening on ...";
6. OSC's Device Bindings page shows "Open Sound Control (OSC)" under its
   title (objectName "oscFullName").

Run "busy" (another socket holds the port before the program starts):
"Server not started: port <p> is in use" in the warning colour.
"""

from __future__ import annotations

import pathlib
import sys
import time
import traceback
from typing import Any

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "test" / "journeys"))
from _harness import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    Journey,
    pump,
    run_journey,
    step,
)

PREFIXES = ("Listening on", "From ", "Server not started", "Not listening")


# +-------------------------------------------------------------------------
# | Script side (the child process)


class _Part:
    """Runs one part; an error is recorded under the part's name and the
    next part still runs."""

    def __init__(self, j: Journey, name: str) -> None:
        self.j = j
        self.name = name

    def __enter__(self) -> _Part:
        return self

    def __exit__(self, kind: Any, exc: Any, tb: Any) -> bool:  # noqa: ANN401
        if exc is not None:
            self.j.out[f"{self.name}:error"] = f"{kind.__name__}: {exc}"
            self.j.out[f"{self.name}:traceback"] = traceback.format_exc()
        return True


def _shown(item: Any) -> bool:  # noqa: ANN401
    while item is not None:
        if not item.isVisible():
            return False
        item = item.parentItem()
    return True


def _osc_card(j: Journey) -> Any:  # noqa: ANN401
    return next(
        (
            i
            for i in Journey.walk(j.win.contentItem())
            if i.objectName() == "statusCard" and i.property("slug") == "osc"
        ),
        None,
    )


def _line_item(j: Journey) -> Any:  # noqa: ANN401
    """The OSC card's second line: its shown text item that holds one of
    the line's texts."""
    card = _osc_card(j)
    if card is None:
        return None
    for item in Journey.walk(card):
        text = item.property("text")
        if isinstance(text, str) and text.startswith(PREFIXES) and _shown(item):
            return item
    return None


def _line(j: Journey) -> str | None:
    item = _line_item(j)
    return None if item is None else str(item.property("text"))


def _card_texts(j: Journey) -> list[str]:
    card = _osc_card(j)
    if card is None:
        return []
    return [
        str(i.property("text"))
        for i in Journey.walk(card)
        if isinstance(i.property("text"), str) and _shown(i)
    ]


def _hex(color: Any) -> str | None:  # noqa: ANN401
    if color is None:
        return None
    name = getattr(color, "name", None)
    return (name() if callable(name) else str(color)).lower()


def _packet(address: str, *values: object) -> bytes:
    from pythonosc.osc_message_builder import OscMessageBuilder

    builder = OscMessageBuilder(address=address)
    for value in values:
        builder.add_arg(value)
    return builder.build().dgram


def _port() -> int:
    from gremlin import osc_device_file

    return int(osc_device_file.read_server()["port"])


def _go_home(j: Journey) -> None:
    j.ev("uiState.setCurrentRoom('status'); true")
    j.wait_until(lambda: _osc_card(j) is not None, "the OSC card on Home")
    j.settle()


def _start_up(j: Journey) -> None:
    """What main() does at start-up (the harness builds the app itself)."""
    from gremlin import osc

    j.out["start:lineBefore"] = _line(j)
    osc.OscRuntime().open_always()
    j.settle()


def _part_listening(j: Journey, port: int) -> None:
    from gremlin import osc

    j.out["listen:info"] = osc.OscRuntime().listenInfo()
    j.out["listen:line"] = j.await_value(
        lambda: _line(j), f"Listening on 127.0.0.1:{port}"
    )
    j.out["listen:texts"] = _card_texts(j)


def _part_message(j: Journey, sock: Any, port: int) -> None:  # noqa: ANN401
    listening = f"Listening on 127.0.0.1:{port}"
    sock.sendto(_packet("/test", 0.5), ("127.0.0.1", port))
    sent = time.monotonic()
    j.out["msg:line"] = j.await_value(
        lambda: _line(j), "From 127.0.0.1: /test 0.5", timeout=2.0
    )
    # Still showing after 2 s; back to listening about 3 s after it.
    while time.monotonic() - sent < 2.0:
        pump(20)
    j.out["msg:lineAt2s"] = _line(j)
    j.out["msg:back"] = j.await_value(lambda: _line(j), listening, timeout=4.0)
    j.out["msg:backAfter"] = round(time.monotonic() - sent, 2)


def _part_burst(j: Journey, sock: Any, port: int) -> None:  # noqa: ANN401
    from PySide6 import QtCore

    listening = f"Listening on 127.0.0.1:{port}"
    item = _line_item(j)
    assert item is not None, "no OSC card line"
    changes: list[float] = []
    texts: list[str] = []
    start = time.monotonic()

    def changed(*_a: Any) -> None:  # noqa: ANN401
        changes.append(round(time.monotonic() - start, 3))
        texts.append(str(item.property("text")))

    ok = QtCore.QObject.connect(item, QtCore.SIGNAL("textChanged(QString)"), changed)
    if not ok:
        QtCore.QObject.connect(item, QtCore.SIGNAL("textChanged()"), changed)
    for n in range(100):
        sock.sendto(_packet("/burst", n), ("127.0.0.1", port))
        target = start + (n + 1) / 100.0
        pump(max(0, int((target - time.monotonic()) * 1000)))
    j.out["burst:sendSeconds"] = round(time.monotonic() - start, 2)
    # The newest shows within one throttle step of the last message.
    j.out["burst:final"] = j.await_value(
        lambda: _line(j), "From 127.0.0.1: /burst 99", timeout=1.0
    )
    window_end = time.monotonic() - start
    j.out["burst:changes"] = [c for c in changes if c <= window_end]
    j.out["burst:window"] = round(window_end, 2)
    j.out["burst:texts"] = texts[:20]
    j.out["burst:back"] = j.await_value(lambda: _line(j), listening, timeout=5.0)


def _part_listen_off(j: Journey, port: int) -> None:
    from gremlin import osc_device_file
    from gremlin.signal import signal as ui_signal

    def listen(on: bool) -> None:
        server = osc_device_file.read_server()
        server["enabled"] = on
        osc_device_file.write_server(server, "OSC card line journey")
        changed = getattr(ui_signal, "oscServerSettingsChanged", None)
        if changed is not None:
            changed.emit()
        j.settle()

    listen(False)
    j.out["off:line"] = j.await_value(
        lambda: _line(j), "Not listening (Listen for OSC messages is off)"
    )
    listen(True)
    j.out["off:onAgain"] = j.await_value(
        lambda: _line(j), f"Listening on 127.0.0.1:{port}"
    )


def _part_bindings_name(j: Journey) -> None:
    j.ev("openDeviceBindingsForCard(_moduleModel.cardMap('osc'))")
    j.wait_until(lambda: j.ev("uiState.currentTab") == "osc", "OSC's page")
    j.settle()
    label = j.wait_until(
        lambda: next(
            (
                i
                for i in Journey.walk(j.win.contentItem())
                if i.objectName() == "oscFullName"
            ),
            None,
        ),
        "the oscFullName label",
    )
    j.out["name:text"] = label.property("text")
    j.out["name:shown"] = _shown(label)


def story_open(j: Journey) -> None:
    import socket

    port = _port()
    j.out["port"] = port
    with _Part(j, "start"):
        _go_home(j)
        _start_up(j)
    with _Part(j, "listen"):
        _part_listening(j, port)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind(("127.0.0.1", 0))
        with _Part(j, "msg"):
            _part_message(j, sock, port)
        with _Part(j, "burst"):
            _part_burst(j, sock, port)
    with _Part(j, "off"):
        _part_listen_off(j, port)
    with _Part(j, "name"):
        _part_bindings_name(j)


_HELD: list[Any] = []


def story_busy(j: Journey) -> None:
    from gremlin import osc

    port = _port()
    j.out["port"] = port
    with _Part(j, "busy"):
        _go_home(j)
        _start_up(j)
        j.out["busy:info"] = osc.OscRuntime().listenInfo()
        j.out["busy:line"] = j.await_value(
            lambda: _line(j), f"Server not started: port {port} is in use"
        )
        item = _line_item(j)
        color = None if item is None else item.property("color")
        j.out["busy:color"] = _hex(color)
        j.out["busy:warnColors"] = [
            _hex(j.ev("Style.warn")),
            _hex(j.ev("Style.warning")),
        ]
        j.out["busy:mutedColor"] = _hex(j.ev("Style.fgMuted"))
        j.out["busy:texts"] = _card_texts(j)
    for sock in _HELD:
        sock.close()


def main() -> None:
    if "busy" in sys.argv[1:]:

        def hold(_j: Journey) -> None:
            import socket

            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind(("127.0.0.1", _port()))
            _HELD.append(sock)

        Journey(hold).run(story_busy)
    else:
        Journey().run(story_open)


# +-------------------------------------------------------------------------
# | Pytest side


@pytest.fixture(scope="module")
def run(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_line"))


@pytest.fixture(scope="module")
def busy(tmp_path_factory: pytest.TempPathFactory) -> dict:
    return run_journey(__file__, tmp_path_factory.mktemp("osc_busy"), "busy")


def _no_error(out: dict, part: str) -> None:
    assert f"{part}:error" not in out, (
        out.get(f"{part}:error"),
        out.get(f"{part}:traceback"),
    )


def test_listening_on_the_servers_address(run: dict) -> None:
    _no_error(run, "start")
    _no_error(run, "listen")
    port = step(run, "port")
    info = step(run, "listen:info")
    assert info["state"] == "listening", info
    assert (info["host"], int(info["port"])) == ("127.0.0.1", port), info
    assert step(run, "listen:line") == f"Listening on 127.0.0.1:{port}", step(
        run, "listen:texts"
    )


def test_a_message_shows_its_sender_address_and_value(run: dict) -> None:
    _no_error(run, "msg")
    assert step(run, "msg:line") == "From 127.0.0.1: /test 0.5"
    assert step(run, "msg:lineAt2s") == "From 127.0.0.1: /test 0.5"


def test_back_to_listening_three_seconds_after_the_last_message(run: dict) -> None:
    _no_error(run, "msg")
    port = step(run, "port")
    assert step(run, "msg:back") == f"Listening on 127.0.0.1:{port}"
    assert 2.5 <= step(run, "msg:backAfter") <= 4.5, step(run, "msg:backAfter")


def test_a_flood_changes_the_line_at_most_four_times_a_second(run: dict) -> None:
    _no_error(run, "burst")
    port = step(run, "port")
    assert step(run, "burst:final") == "From 127.0.0.1: /burst 99"
    changes = step(run, "burst:changes")
    window = step(run, "burst:window")
    assert changes, "the line never changed during the flood"
    # 250 ms apart at most 4 a second: one at the start plus 4 per second.
    assert len(changes) <= 1 + 4 * window + 1, (changes, window)
    for n, at in enumerate(changes):
        in_second = [c for c in changes[n:] if c - at < 1.0]
        assert len(in_second) <= 5, (changes, step(run, "burst:texts"))
    assert step(run, "burst:back") == f"Listening on 127.0.0.1:{port}"


def test_listen_off_says_so_and_on_listens_again(run: dict) -> None:
    _no_error(run, "off")
    port = step(run, "port")
    assert step(run, "off:line") == "Not listening (Listen for OSC messages is off)"
    assert step(run, "off:onAgain") == f"Listening on 127.0.0.1:{port}"


def test_oscs_page_shows_its_full_name(run: dict) -> None:
    _no_error(run, "name")
    assert step(run, "name:text") == "Open Sound Control (OSC)"
    assert step(run, "name:shown") is True


def test_no_program_errors(run: dict) -> None:
    assert run.get("error") is None, (run.get("error"), run.get("traceback"))
    assert run.get("_errors") == []


def test_port_in_use_shows_why_in_the_warning_colour(busy: dict) -> None:
    _no_error(busy, "busy")
    port = step(busy, "port")
    info = step(busy, "busy:info")
    assert info["state"] == "failed", info
    assert info["reason"] == f"port {port} is in use", info
    assert step(busy, "busy:line") == (
        f"Server not started: port {port} is in use"
    ), step(busy, "busy:texts")
    color = step(busy, "busy:color")
    assert color in step(busy, "busy:warnColors"), color
    assert color != step(busy, "busy:mutedColor")
    assert busy.get("error") is None, (busy.get("error"), busy.get("traceback"))


if __name__ == "__main__":
    main()
