# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""OSC listener and the thread rules (G-OSC10): one receive thread started
through gremlin.threads, no thread per packet, and a stop that returns at
once. Loopback only, on an OS-picked port."""

from __future__ import annotations

import socket
import threading
import time

from gremlin import osc, threads


def _packet(address: str, value: float) -> bytes:
    from pythonosc.osc_message_builder import OscMessageBuilder

    builder = OscMessageBuilder(address=address)
    builder.add_arg(value)
    return builder.build().dgram


def _wait_for(check, seconds: float = 3.0) -> bool:  # noqa: ANN001
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if check():
            return True
        time.sleep(0.005)
    return check()


def _listener(got: list) -> osc.OscListener:
    def on_message(address: str, args: tuple, peer: object) -> None:
        got.append((address, args, threading.current_thread().name))

    listener = osc.OscListener(host="127.0.0.1", port=0, callback=on_message)
    listener.start()
    return listener


def test_one_receive_thread_for_many_packets() -> None:
    got: list = []
    listener = _listener(got)
    try:
        port = listener.bound_port()
        baseline = threading.active_count()
        peak = baseline
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for i in range(500):
                sender.sendto(_packet("/flood", float(i)), ("127.0.0.1", port))
                peak = max(peak, threading.active_count())
                if i % 50 == 49:
                    # Let the receiver catch up so the loopback drops nothing.
                    _wait_for(lambda n=i + 1: len(got) >= n, 2.0)
        assert _wait_for(lambda: len(got) >= 500)
        assert len(got) == 500
        assert peak <= baseline
        names = {name for _a, _v, name in got}
        assert len(names) == 1
        assert next(iter(names)) == threads.PREFIX + "OSC listener"
        assert [args[0] for _a, args, _n in got] == [float(i) for i in range(500)]
    finally:
        listener.stop()


def test_stop_returns_at_once_and_frees_the_port() -> None:
    got: list = []
    listener = _listener(got)
    port = listener.bound_port()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        sender.sendto(_packet("/one", 1.0), ("127.0.0.1", port))
    assert _wait_for(lambda: len(got) == 1)

    started = time.perf_counter()
    listener.stop()
    took = time.perf_counter() - started
    assert took < 0.05, f"stop blocked the caller for {took:.3f} s"

    # The port is free straight away: the same port can be bound again.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as again:
        again.bind(("127.0.0.1", port))

    # The receive thread ends by itself, soon.
    assert _wait_for(
        lambda: threads.PREFIX + "OSC listener" not in threads.running(), 1.0
    )


def test_restart_on_the_same_port_still_receives() -> None:
    got: list = []
    listener = _listener(got)
    port = listener.bound_port()
    listener.stop()
    listener.port = port
    listener.start()
    try:
        assert listener.bound_port() == port
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(_packet("/back", 0.5), ("127.0.0.1", port))
        assert _wait_for(lambda: len(got) == 1)
        assert got[0][0] == "/back"
    finally:
        listener.stop()


def test_malformed_packet_is_reported_and_listening_goes_on(
    monkeypatch: object,
) -> None:
    reported: list = []
    monkeypatch.setattr(  # type: ignore[attr-defined]
        osc, "report_malformed", lambda client, reason: reported.append(reason)
    )
    got: list = []
    listener = _listener(got)
    try:
        port = listener.bound_port()
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            sender.sendto(b"not osc at all", ("127.0.0.1", port))
            sender.sendto(_packet("/after", 1.0), ("127.0.0.1", port))
        assert _wait_for(lambda: len(got) == 1)
        assert reported
        assert got[0][0] == "/after"
    finally:
        listener.stop()
