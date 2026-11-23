# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin-ctl: the command line for the Gremlin-Platforms control pipe.

Each command makes one call (claude/plans/control-api-contract.md). Readable
text by default, --json for scripts. Exit codes (S11): 0 done, 1 the call
failed (also when the program stopped answering during it), 2 the command was
typed wrong (usage text on stderr), 3 protocol version mismatch, 4 the
program isn't running or control from other programs is off.
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
EXIT_USAGE = 2
EXIT_VERSION = 3
EXIT_NOT_RUNNING = 4

EXIT_CODES_TEXT = (
    "Exit codes: 0 done, 1 the call failed (or the program stopped answering), "
    "2 command typed wrong, 3 version mismatch, 4 not running or control off."
)
LOG_LINES_MAX = 2000

# Builds (call name, args) from the parsed command line.
Request = tuple[str, dict[str, Any]]


def _parse_value(text: str) -> Any:  # noqa: ANN401
    """option set values: JSON when it reads as JSON (true, 5, 0.5, [..]),
    otherwise the text as it is."""
    try:
        return json.loads(text)
    except ValueError:
        return text


class _ArgumentError(Exception):
    """A mistyped command line; carries the usage text of the parser that
    refused it."""

    def __init__(self, usage: str, message: str) -> None:
        super().__init__(message)
        self.usage = usage


class _Parser(argparse.ArgumentParser):
    """Mistakes are raised, not exited on, so main() can write them as JSON
    with --json and exit 2 (S11). Subparsers use this class too. `commands`
    lists the commands and their help, for `help` without the program."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ANN401
        super().__init__(*args, **kwargs)
        self.commands: list[dict[str, str]] = []

    def error(self, message: str) -> Any:  # noqa: ANN401
        raise _ArgumentError(self.format_usage(), message)


def _build_parser() -> _Parser:
    parser = _Parser(
        prog="gremlin-ctl",
        description=(
            "Read and control a running Gremlin-Platforms. Needs Options › "
            "General › Control › Allow control from other programs."
        ),
        epilog=EXIT_CODES_TEXT,
    )
    parser.add_argument("--json", action="store_true", help="print raw JSON")
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=_client.DEFAULT_CALL_TIMEOUT_S,
        help="seconds to wait for an answer (default %(default)g)",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    def add(name: str, help_text: str, build: Callable[..., Request]) -> Any:  # noqa: ANN401
        p = sub.add_parser(name, help=help_text, description=help_text)
        p.set_defaults(build=build, usage=p.format_usage)
        parser.commands.append({"command": name, "help": help_text})
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
    p.add_argument("id", help="a command id from 'gremlin-ctl commands'")

    p = add("option", "read or change an Options setting", _option_request)
    p.add_argument("action", choices=["get", "set"])
    p.add_argument("key", help="section/group/name")
    p.add_argument("value", nargs="?", help="new value (set): JSON or text")

    p = add("options", "list the Options settings", lambda a: ("options.list", {}))
    p.add_argument("action", nargs="?", choices=["list"])

    p = add("trace", "turn tracing on or off, or show it", _trace_request)
    p.add_argument("action", choices=["on", "off", "status"])
    p.add_argument(
        "category", nargs="?", help="on/off only: a category from 'trace status'"
    )

    p = add(
        "log",
        "the last lines of the system or trace log",
        lambda a: ("log", {"which": a.which, "lines": a.lines}),
    )
    p.add_argument(
        "which",
        nargs="?",
        default="system",
        choices=["system", "trace"],
        help="which log (default system)",
    )
    p.add_argument(
        "-n",
        "--lines",
        type=_log_lines,
        default=50,
        help=f"lines from the end, 1-{LOG_LINES_MAX} (default %(default)s)",
    )

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

    p = add("call", "make any call by name (args as a JSON object)", _call_request)
    p.add_argument("name", help="the call's name, e.g. log")
    p.add_argument("args", nargs="?", help='a JSON object, e.g. "{\\"lines\\": 5}"')

    add("help", "this help: the commands and what they do", lambda a: ("", {}))
    return parser


def _positive_float(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number: {text!r}") from None
    if not value > 0:
        raise argparse.ArgumentTypeError(f"must be more than 0: {text!r}")
    return value


def _log_lines(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a whole number: {text!r}") from None
    if not 1 <= value <= LOG_LINES_MAX:
        raise argparse.ArgumentTypeError(f"must be 1-{LOG_LINES_MAX}: {text!r}")
    return value


def _trace_request(a: argparse.Namespace) -> Request:
    if a.action == "status":
        if a.category:
            raise _UsageError("trace status takes no category")
        return "trace.status", {}
    return f"trace.{a.action}", {"category": a.category} if a.category else {}


def _call_request(a: argparse.Namespace) -> Request:
    if not a.args:
        return a.name, {}
    try:
        args = json.loads(a.args)
    except ValueError as e:
        raise _UsageError(f"call args must be a JSON object: {e}") from None
    if not isinstance(args, dict):
        raise _UsageError('call args must be a JSON object, e.g. {"lines": 5}')
    return a.name, args


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
        return "window.open", {"id": a.target}
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
    """One value as text: '-' for nothing or empty, yes/no, floats rounded
    to two places (19.73366 -> 19.73, 2.0 -> 2)."""
    if value is None or value == "" or value == [] or value == {}:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        text = f"{value:.2f}".rstrip("0").rstrip(".")
        return "0" if text in ("-0", "") else text
    return str(value)


def _row_value(value: Any) -> str:  # noqa: ANN401
    """A key=value row's value; text with spaces is quoted so the two-space
    separator stays readable."""
    text = _scalar(value)
    if isinstance(value, str) and value and (value != value.strip() or " " in value):
        return json.dumps(value, ensure_ascii=False)
    return text


def format_result(value: Any, indent: int = 0) -> list[str]:  # noqa: ANN401
    """Lines of readable text for any JSON result."""
    pad = "  " * indent
    if isinstance(value, dict):
        if not value:
            return [f"{pad}-"]
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)) and item:
                lines.append(f"{pad}{key}:")
                lines.extend(format_result(item, indent + 1))
            else:
                lines.append(f"{pad}{key}: {_scalar(item)}")
        return lines
    if isinstance(value, list):
        if not value:
            return [f"{pad}none"]
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(
                    pad
                    + "  ".join(
                        f"{k}={_row_value(v)}"
                        for k, v in item.items()
                        if not isinstance(v, (dict, list)) or not v
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


def _device_lines(devices: list[Any]) -> list[str]:
    """One block per device: its name and whether it is plugged in, then its
    id and counts (S21)."""
    lines: list[str] = []
    for dev in devices:
        if not isinstance(dev, dict):
            lines.append(_scalar(dev))
            continue
        name = str(dev.get("name") or "").strip() or "-"
        label = str(dev.get("label") or "").strip()
        head = name if not label or label == name else f"{name} ({label})"
        lines.append(
            f"{head}  [{'plugged in' if dev.get('plugged_in') else 'not plugged in'}]"
        )
        details = [f"id {_scalar(dev.get('guid'))}"]
        if dev.get("virtual"):
            details.append(f"vJoy {_scalar(dev.get('vjoy_id'))}")
        for key in ("axes", "buttons", "hats"):
            if dev.get(key) is not None:
                details.append(f"{key} {_scalar(dev.get(key))}")
        lines.append("  " + "  ".join(details))
    return lines or ["none"]


def _print_result(call: str, result: Any, out: TextIO, as_json: bool) -> None:  # noqa: ANN401
    if as_json:
        out.write(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        return
    if call == "commands" and isinstance(result, list):
        lines = [
            f"{c.get('id', '')}  {c.get('text', '')}"
            + (f"  ({c['group']})" if c.get("group") else "")
            for c in result
            if isinstance(c, dict)
        ] or ["none"]
    elif call == "devices" and isinstance(result, list):
        lines = _device_lines(result)
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


class _Fail(Exception):
    """Ends main() with an exit code, a readable line for stderr and the
    error code for --json."""

    def __init__(
        self, exit_code: int, text: str, code: str, usage: str = "", error: str = ""
    ) -> None:
        super().__init__(text)
        self.exit_code = exit_code
        self.code = code
        self.usage = usage
        # --json gives the error's own text (the readable line may add the call).
        self.error = error or text


def _call_line(call: str, text: str) -> str:
    """The readable error line: the call's name in front unless the text
    already starts with it."""
    return text if text.startswith(call) else f"{call}: {text}"


def main(
    argv: Sequence[str] | None = None,
    *,
    out: TextIO | None = None,
    err: TextIO | None = None,
    connect: Callable[..., _client.Client] | None = None,
) -> int:
    """Runs one command; returns the exit code (0-4 only, S11)."""
    stdout: TextIO = out if out is not None else sys.stdout
    stderr: TextIO = err if err is not None else sys.stderr
    words = _json_first(sys.argv[1:] if argv is None else argv)
    as_json = bool(words) and words[0] == "--json"
    try:
        return _run(words, stdout, connect or _client.connect)
    except _Fail as e:
        if e.usage:
            stderr.write(e.usage)
        typed_wrong = e.exit_code == EXIT_USAGE
        prefix = "gremlin-ctl: error: " if typed_wrong else "gremlin-ctl: "
        stderr.write(f"{prefix}{e}\n")
        if as_json:
            stdout.write(
                json.dumps(
                    {
                        "ok": False,
                        "code": e.code,
                        "error": e.error,
                        "exit": e.exit_code,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        return e.exit_code


def _run(
    words: list[str], stdout: TextIO, open_client: Callable[..., _client.Client]
) -> int:
    parser = _build_parser()
    try:
        args = parser.parse_args(words)
    except _ArgumentError as e:
        raise _Fail(EXIT_USAGE, str(e), "bad_args", e.usage) from None
    except SystemExit as e:  # argparse: --help
        return int(e.code or 0)
    if args.command is None:
        parser.print_help(stdout)
        return EXIT_OK
    if args.command == "help":
        if args.json:
            stdout.write(
                json.dumps(parser.commands, indent=2, ensure_ascii=False) + "\n"
            )
        else:
            parser.print_help(stdout)
        return EXIT_OK
    try:
        call, call_args = args.build(args)
    except _UsageError as e:  # missing or bad argument found after parsing
        raise _Fail(EXIT_USAGE, str(e), "bad_args", args.usage()) from None
    try:
        with open_client() as conn:
            conn.call_timeout_s = args.timeout
            result = conn.call(call, **call_args)
    except KeyboardInterrupt:
        raise _Fail(
            EXIT_CALL_ERROR, "Stopped. The call may have run.", "stopped"
        ) from None
    except _client.VersionMismatch as e:
        raise _Fail(EXIT_VERSION, str(e), e.code) from None
    except _client.NotRunning as e:
        raise _Fail(EXIT_NOT_RUNNING, str(e), e.code) from None
    except (_client.StoppedAnswering, _client.CallError) as e:
        raise _Fail(
            EXIT_CALL_ERROR, _call_line(call, str(e)), e.code, error=str(e)
        ) from None
    _print_result(call, result, stdout, args.json)
    return EXIT_OK
