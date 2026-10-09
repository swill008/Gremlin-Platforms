"""Send OSC messages to a running Gremlin Platforms for hands-on checks.

Sends only (UDP, python-osc); never listens. Defaults to 127.0.0.1:8001,
the program's default OSC listening port. Every packet sent is printed.

Usage:
    python tools/osc_send.py [--host H] [--port P] [--dry-run] COMMAND ...

Commands:
    send ADDRESS [VALUES...]       one message; numbers become int/float, else text
    press ADDRESS [--hold S]       sends 1, waits S (default 0.2), sends 0
    tap ADDRESS                    address only, no value
    sweep ADDRESS [--from A] [--to B] [--steps N] [--interval S]
    repeat ADDRESS [--count N] [--interval S] [VALUES...]
    script FILE                    one command per line; `wait SECONDS`;
                                   blank lines and `#` comments skipped

Examples, by Add window mode (prefix: python tools/osc_send.py):
    Button               press /btn/1 --hold 0.5
                         send /btn/1 1   then   send /btn/1 0
    Trigger on message   tap /fire   (any message presses, released after the delay)
    Axis 0..1            sweep /fader/1 --from 0 --to 1 --steps 20
    Change               send /mode 1   then   send /mode 2   (each new value presses)
    Message + data       send /scene 3 go   (presses when the values equal the data)
    Source P2            send /pad 7 0.75   (P1 = 7, P2 = 0.75)
    Repeat               repeat /btn/1 --count 5 --interval 0.3 1
    Dry run              --dry-run sweep /fader/1   (prints, sends nothing)

Git Bash rewrites arguments starting with "/" into Windows paths; run from
PowerShell/cmd, or set MSYS_NO_PATHCONV=1 first.
"""

from __future__ import annotations

import argparse
import shlex
import sys
import time

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8001


def parse_value(text: str) -> int | float | str:
    """Number if it reads as one (int first), else the text."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


class Sender:
    """Sends (or, in dry run, only prints) OSC messages."""

    def __init__(self, host: str, port: int, dry_run: bool) -> None:
        self.host = host
        self.port = port
        self.dry_run = dry_run
        self._client = None
        if not dry_run:
            from pythonosc.udp_client import SimpleUDPClient

            self._client = SimpleUDPClient(host, port)

    def send(self, address: str, values: list[int | float | str]) -> None:
        if not address.startswith("/"):
            raise ValueError(f"OSC address must start with '/': {address!r}")
        shown = " ".join(repr(v) for v in values)
        tag = "DRY" if self.dry_run else "SENT"
        print(f"{tag} {self.host}:{self.port} {address} {shown}".rstrip(), flush=True)
        if self._client is not None:
            # An empty list sends an address-only message.
            self._client.send_message(address, values)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Send OSC messages to Gremlin Platforms.",
        epilog="Values: numbers become int/float, anything else is sent as text. "
        "Use `--` before negative numbers, e.g. send /x -- -0.5",
    )
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument(
        "--dry-run", action="store_true", help="print packets without sending"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("send", help="one message")
    p.add_argument("address")
    p.add_argument("values", nargs="*")

    p = sub.add_parser("press", help="send 1, hold, send 0")
    p.add_argument("address")
    p.add_argument("--hold", type=float, default=0.2)

    p = sub.add_parser("tap", help="address only, no value")
    p.add_argument("address")

    p = sub.add_parser("sweep", help="ramp a value from A to B")
    p.add_argument("address")
    p.add_argument("--from", dest="start", type=float, default=0.0)
    p.add_argument("--to", dest="end", type=float, default=1.0)
    p.add_argument("--steps", type=int, default=20)
    p.add_argument("--interval", type=float, default=0.05)

    p = sub.add_parser("repeat", help="send the same message N times")
    p.add_argument("address")
    p.add_argument("values", nargs="*")
    p.add_argument("--count", type=int, default=5)
    p.add_argument("--interval", type=float, default=0.25)

    p = sub.add_parser("script", help="run commands from a file")
    p.add_argument("file")
    return parser


def _wait(sender: Sender, seconds: float) -> None:
    if seconds > 0 and not sender.dry_run:
        time.sleep(seconds)


def run_command(args: argparse.Namespace, sender: Sender) -> None:
    cmd = args.command
    if cmd == "send":
        sender.send(args.address, [parse_value(v) for v in args.values])
    elif cmd == "press":
        sender.send(args.address, [1])
        _wait(sender, args.hold)
        sender.send(args.address, [0])
    elif cmd == "tap":
        sender.send(args.address, [])
    elif cmd == "sweep":
        steps = max(1, args.steps)
        for i in range(steps + 1):
            value = args.start + (args.end - args.start) * i / steps
            sender.send(args.address, [round(value, 6)])
            if i < steps:
                _wait(sender, args.interval)
    elif cmd == "repeat":
        values = [parse_value(v) for v in args.values]
        for i in range(max(0, args.count)):
            sender.send(args.address, values)
            if i < args.count - 1:
                _wait(sender, args.interval)
    elif cmd == "script":
        run_script(args.file, sender)


def run_script(path: str, sender: Sender) -> None:
    parser = build_parser()
    with open(path, encoding="utf-8") as fh:
        lines = fh.readlines()
    for number, raw in enumerate(lines, 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        words = shlex.split(line, posix=True)
        if words[0] == "wait":
            seconds = float(words[1]) if len(words) > 1 else 0.0
            print(f"wait {seconds}", flush=True)
            _wait(sender, seconds)
            continue
        if words[0] == "script":
            raise SystemExit(f"{path}:{number}: nested script not allowed")
        try:
            sub_args = parser.parse_args(words)
        except SystemExit:
            raise SystemExit(f"{path}:{number}: bad line: {line}") from None
        run_command(sub_args, sender)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    sender = Sender(args.host, args.port, args.dry_run)
    try:
        run_command(args, sender)
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
