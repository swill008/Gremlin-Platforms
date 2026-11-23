# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin-ctl: the command line for the Gremlin-Platforms control pipe.

Each command makes one call (claude/plans/control-api-contract.md). Readable
text by default, --json for scripts. Exit codes: 0 ok, 1 the call failed,
2 the program isn't running or control is off, 3 protocol version mismatch.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any, TextIO

from gremlin_ctl import client as _client

EXIT_OK = 0
EXIT_CALL_ERROR = 1
EXIT_NOT_RUNNING = 2
EXIT_VERSION = 3

# Builds (call name, args) from the parsed command line.
Request = tuple[str, dict[str, Any]]


def _parse_value(text: str) -> Any:  # noqa: ANN401
    """option set values: JSON when it reads as JSON (true, 5, 0.5, [..]),
    otherwise the text as it is."""
    try:
        return json.loads(text)
    except ValueError:
        return text


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gremlin-ctl",
        description=(
            "Read and control a running Gremlin-Platforms. Needs Options › "
            "General › Allow control from other programs."
        ),
        epilog="Exit codes: 0 ok, 1 call failed, 2 not running or control off, "
        "3 version mismatch.",
    )
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    parser.add_argument(
        "--timeout",
        type=float,
        default=_client.DEFAULT_CALL_TIMEOUT_S,
        help="seconds to wait for an answer (default %(default)g)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def add(name: str, help_text: str, build: Callable[..., Request]) -> Any:  # noqa: ANN401
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.set_defaults(build=build)
        return p

    add(
        "state",
        "program version, profile, mode, tracing, Health, Screen Saver Mode",
        lambda a: ("state", {}),
    )
    add("devices", "devices, plugged in or not", lambda a: ("devices", {}))

    p = add("run", "start or stop the profile", lambda a: (f"run.{a.action}", {}))
    p.add_argument("action", choices=["start", "stop"])

    p = add("profile", "load or save the profile", _profile_request)
    p.add_argument("action", choices=["load", "save"])
    p.add_argument("file", nargs="?", help="profile file (load)")

    add("commands", "menu command ids and names", lambda a: ("commands", {}))
    p = add(
        "run-command",
        "run a menu command by its id",
        lambda a: ("command.run", {"id": a.id}),
    )
    p.add_argument("id")

    p = add("option", "read or change an Options setting", _option_request)
    p.add_argument("action", choices=["get", "set"])
    p.add_argument("key", help="section/group/name")
    p.add_argument("value", nargs="?", help="new value (set): JSON or text")

    p = add("options", "list the Options settings", lambda a: ("options.list", {}))
    p.add_argument("action", nargs="?", choices=["list"])

    p = add(
        "trace",
        "turn tracing on or off, or show it",
        lambda a: (
            ("trace.status", {})
            if a.action == "status"
            else (f"trace.{a.action}", {"category": a.category} if a.category else {})
        ),
    )
    p.add_argument("action", choices=["on", "off", "status"])
    p.add_argument("category", nargs="?")

    p = add(
        "log",
        "the last lines of the system or trace log",
        lambda a: ("log", {"which": a.which, "lines": a.lines}),
    )
    p.add_argument("which", nargs="?", default="system", choices=["system", "trace"])
    p.add_argument("-n", "--lines", type=int, default=50)

    add("windows", "the program's windows", lambda a: ("window.list", {}))

    p = add(
        "window",
        "open, close, read, screenshot, press or type in a window",
        _window_request,
    )
    p.add_argument(
        "action", choices=["open", "close", "read", "screenshot", "press", "type"]
    )
    p.add_argument("target", help="command id (open) or window title")
    p.add_argument(
        "rest", nargs="*", help="screenshot: FILE.png; press: BUTTON; type: FIELD TEXT"
    )

    p = add(
        "call",
        "make any call by name (args as a JSON object)",
        lambda a: (a.name, json.loads(a.args) if a.args else {}),
    )
    p.add_argument("name")
    p.add_argument("args", nargs="?")

    add(
        "help",
        "this help and the calls the running program offers",
        lambda a: ("help", {}),
    )
    return parser


def _profile_request(a: argparse.Namespace) -> Request:
    if a.action == "save":
        return "profile.save", {}
    if not a.file:
        raise _UsageError("profile load needs a file")
    return "profile.load", {"path": str(Path(a.file).resolve())}


def _option_request(a: argparse.Namespace) -> Request:
    if a.action == "get":
        return "option.get", {"key": a.key}
    if a.value is None:
        raise _UsageError("option set needs a value")
    return "option.set", {"key": a.key, "value": _parse_value(a.value)}


def _window_request(a: argparse.Namespace) -> Request:
    need = {"open": 0, "close": 0, "read": 0, "screenshot": 1, "press": 1, "type": 2}[
        a.action
    ]
    if len(a.rest) != need:
        raise _UsageError(f"window {a.action} takes {need + 1} argument(s)")
    if a.action == "open":
        return "window.open", {"command": a.target}
    args: dict[str, Any] = {"window": a.target}
    if a.action == "screenshot":
        args["path"] = str(Path(a.rest[0]).resolve())
    elif a.action == "press":
        args["button"] = a.rest[0]
    elif a.action == "type":
        args["field"], args["text"] = a.rest
    return f"window.{a.action}", args


class _UsageError(Exception):
    pass


# Readable text ------------------------------------------------------------


def _scalar(value: Any) -> str:  # noqa: ANN401
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    return str(value)


def format_result(value: Any, indent: int = 0) -> list[str]:  # noqa: ANN401
    """Lines of readable text for any JSON result."""
    pad = "  " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(format_result(item, indent + 1))
            else:
                lines.append(f"{pad}{key}: {_scalar(item) if item != [] else '-'}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{pad}(none)"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(
                    pad
                    + "  ".join(
                        f"{k}={_scalar(v)}"
                        for k, v in item.items()
                        if not isinstance(v, (dict, list))
                    )
                )
                for k, v in item.items():
                    if isinstance(v, (dict, list)) and v:
                        lines.append(f"{pad}  {k}:")
                        lines.extend(format_result(v, indent + 2))
            else:
                lines.append(pad + _scalar(item))
        return lines
    return [pad + _scalar(value)]


def _print_result(call: str, result: Any, out: TextIO, as_json: bool) -> None:  # noqa: ANN401
    if as_json:
        out.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return
    if call == "log" and isinstance(result, list):
        lines = [str(line) for line in result]
    elif call == "commands" and isinstance(result, list):
        lines = [
            f"{c.get('id', '')}  {c.get('text', '')}"
            + (f"  ({c['group']})" if c.get("group") else "")
            for c in result
            if isinstance(c, dict)
        ] or ["(none)"]
    elif call == "help" and isinstance(result, list):
        lines = ["Calls the program offers:"] + [
            f"  {c.get('name', '')}  {c.get('summary', '')}".rstrip()
            for c in result
            if isinstance(c, dict)
        ]
    else:
        lines = format_result(result)
    out.write("\n".join(lines) + "\n")


# Entry --------------------------------------------------------------------


def _json_first(argv: Sequence[str]) -> list[str]:
    """--json may follow the command too (gremlin-ctl state --json): moved to
    the front. Words after a lone "--" are kept as they are."""
    words = list(argv)
    end = words.index("--") if "--" in words else len(words)
    flags = [w for w in words[:end] if w == "--json"]
    rest = [w for w in words[:end] if w != "--json"]
    return flags + rest + words[end:]


def main(
    argv: Sequence[str] | None = None,
    *,
    out: TextIO | None = None,
    err: TextIO | None = None,
    connect: Callable[..., _client.Client] | None = None,
) -> int:
    """Runs one command; returns the exit code."""
    stdout: TextIO = out if out is not None else sys.stdout
    stderr: TextIO = err if err is not None else sys.stderr
    open_client = connect or _client.connect
    parser = _build_parser()
    try:
        args = parser.parse_args(_json_first(sys.argv[1:] if argv is None else argv))
    except SystemExit as e:  # argparse: --help or bad usage
        return int(e.code or 0)
    if args.command is None:
        parser.print_help(stdout)
        return EXIT_OK
    try:
        call, call_args = args.build(args)
    except (_UsageError, ValueError) as e:
        stderr.write(f"gremlin-ctl: {e}\n")
        return EXIT_CALL_ERROR
    if call == "help" and not args.json:
        parser.print_help(stdout)
        stdout.write("\n")
    try:
        with open_client() as conn:
            conn.call_timeout_s = args.timeout
            result = conn.call(call, **call_args)
    except _client.VersionMismatch as e:
        stderr.write(f"gremlin-ctl: {e}\n")
        return EXIT_VERSION
    except _client.NotRunning as e:
        if call == "help" and not args.json:
            stdout.write(f"({e}: the list of calls needs the program.)\n")
            return EXIT_OK
        stderr.write(f"gremlin-ctl: {e}\n")
        return EXIT_NOT_RUNNING
    except _client.CallError as e:
        stderr.write(f"gremlin-ctl: {call}: {e}\n")
        return EXIT_CALL_ERROR
    _print_result(call, result, stdout, args.json)
    return EXIT_OK
