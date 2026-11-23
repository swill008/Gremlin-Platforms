# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""MCP server for the Gremlin-Platforms control API (development only).

One tool per API call (spec page 13, S10; no help or call tool). Every call
goes through gremlin_ctl.client, the only code that knows the pipe's
protocol; this file knows nothing about pipes. Started by Claude Code from
the project's .mcp.json over stdio:

    python tools/gremlin_mcp/server.py

The program must be running with Options > General > "Allow control from
other programs" switched on.
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections.abc import Callable
from typing import Annotated, Any, Literal, Protocol

from mcp.server.mcpserver import Image, MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ConfigDict, Field, model_validator

# gremlin_ctl lives at the repository root; the server may be started from
# anywhere.
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


_INSTRUCTIONS = (
    "Reads and controls a running Gremlin-Platforms (joystick remapper) on "
    "this PC through its control API. Use these tools to read the program's "
    "state, devices, settings and logs, to look at, screenshot and drive its "
    "windows, and to start and stop the Run while testing the program. The "
    "program must be running with Options > General > 'Allow control from "
    "other programs' switched on; otherwise every tool returns an error "
    "saying so. Windows are named by their shown title (case-insensitive). "
    "Menu command ids come from gremlin_commands. Errors end with the "
    "program's error code, e.g. '(code: not_found)'."
)

mcp = MCPServer("gremlin", instructions=_INSTRUCTIONS)

LOG_LINES_MAX = 500

# S31: the program is local (never open-world); read-only tools only read.
_READ = ToolAnnotations(
    read_only_hint=True, idempotent_hint=True, open_world_hint=False
)
_CHANGE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=False,
    open_world_hint=False,
)
_CHANGE_SAME = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)
_DESTRUCTIVE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=False,
)


def _strict(name: str) -> None:
    """Make a registered tool refuse unknown arguments and publish
    additionalProperties: false. The SDK drops unknown keys silently, so a
    misspelled optional argument (trace_on's category) would run the call
    without it."""
    tool = mcp._tool_manager.get_tool(name)  # the SDK has no public getter
    assert tool is not None, name
    base = tool.fn_metadata.arg_model
    allowed = sorted(f.alias or n for n, f in base.model_fields.items())
    takes = ", ".join(f"'{a}'" for a in allowed) or "no arguments"

    class Strict(base):  # type: ignore[valid-type,misc]
        model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

        @model_validator(mode="before")
        @classmethod
        def _known_arguments(cls, data: Any) -> Any:  # noqa: ANN401
            if isinstance(data, dict):
                unknown = sorted(set(data) - set(allowed))
                if unknown:
                    names = ", ".join(f"'{u}'" for u in unknown)
                    raise ValueError(
                        f"{name} has no argument {names}; it takes {takes}."
                    )
            return data

    Strict.__name__ = base.__name__
    tool.fn_metadata.arg_model = Strict
    tool.parameters = Strict.model_json_schema(by_alias=True)


def _tool(
    annotations: ToolAnnotations,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Register a text tool with its hints and a strict input schema."""

    def register(fn: Callable[..., Any]) -> Callable[..., Any]:
        mcp.add_tool(fn, annotations=annotations, structured_output=False)
        _strict(fn.__name__)
        return fn

    return register


class _Client(Protocol):
    def call(self, name: str, **args: object) -> object: ...


def _connect() -> _Client:
    """A connected gremlin_ctl client (a fresh one per call: the program
    may have restarted since the last call)."""
    from gremlin_ctl import client

    return client.connect()


def _error_text(exc: Exception) -> str:
    """The client's message with its error code (S25)."""
    text = str(exc) or type(exc).__name__
    code = getattr(exc, "code", None)
    return f"{text} (code: {code})" if code else text


def _call_raw(name: str, **args: object) -> object:
    """Make one API call; errors become tool errors (isError results)
    carrying the program's text and code."""
    args = {k: v for k, v in args.items() if v is not None}
    try:
        conn = _connect()
        try:
            return conn.call(name, **args)
        finally:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(_error_text(exc)) from exc


def _json(result: object) -> str:
    return json.dumps(result, indent=1, ensure_ascii=False, default=str)


def _call(name: str, **args: object) -> str:
    """One API call; the result as JSON text."""
    return _json(_call_raw(name, **args))


_Window = Annotated[
    str,
    Field(
        description="The window's shown title, case-insensitive (see gremlin_windows)."
    ),
]


# State ---------------------------------------------------------------------


@_tool(_READ)
def gremlin_state() -> str:
    """Overall state of the running program: version, running profile, mode,
    tracing on or off, Health count (bindings with a problem), Screen Saver
    Mode state and wake counts. Use it first to check the program is
    reachable and what it is doing."""
    return _call("state")


@_tool(_READ)
def gremlin_devices() -> str:
    """The input devices the program knows (real devices only, each once),
    with whether each is plugged in now. Use it to find a device's name or
    to check a device was seen."""
    return _call("devices")


# Run -----------------------------------------------------------------------


@_tool(_CHANGE_SAME)
def gremlin_run_start() -> str:
    """Start running the loaded profile, the same as the Run button. Answers
    {"run": "running"} only once the Run has started; already running, it
    answers at once. A Run that fails to start is an error with the
    program's own reason; no start within 10 s is the error "The Run didn't
    start within 10 s." """
    return _call("run.start")


@_tool(_CHANGE_SAME)
def gremlin_run_stop() -> str:
    """Stop running the profile. Answers {"run": "stopped"} only once the Run
    has stopped; already stopped, it answers at once. No stop within 10 s is
    the error "The Run didn't stop within 10 s." """
    return _call("run.stop")


# Profile -------------------------------------------------------------------


@_tool(_DESTRUCTIVE)
def gremlin_profile_load(
    path: Annotated[
        str,
        Field(
            description="Full path of the profile file (.xml); a short path is refused."
        ),
    ],
) -> str:
    """Load a profile file (.xml) into the program, replacing the open
    profile. Refused while the open profile has unsaved changes (save it with
    gremlin_profile_save, or discard the changes in the program first), for a
    short (relative) path ("Give the full path."), and for a file that is
    missing or can't be read (the error gives the reason)."""
    return _call("profile.load", path=path)


@_tool(_DESTRUCTIVE)
def gremlin_profile_save() -> str:
    """Save the open profile to its file, overwriting it. Its History entries
    are marked as made by the API. Refused for an Untitled profile (one that
    has never been saved to a file: save it once in the program)."""
    return _call("profile.save")


# Menu commands -------------------------------------------------------------


@_tool(_READ)
def gremlin_commands() -> str:
    """The main window's menu commands: id, shown text and group. Use the ids
    with gremlin_run_command and gremlin_window_open."""
    return _call("commands")


@_tool(_DESTRUCTIVE)
def gremlin_run_command(
    id: Annotated[
        str, Field(description="The menu command id, from gremlin_commands.")
    ],
) -> str:
    """Run a main window menu command by its id, as if the user chose it from
    the menu (any command, including ones that change or close things).
    Answers {"ran": true|false}: false when the command can't be used now. An
    id that isn't a main window command is an error (not_found). For a
    command that opens a window, gremlin_window_open also waits for it."""
    return _call("command.run", id=id)


# Options -------------------------------------------------------------------

_Key = Annotated[
    str,
    Field(
        description='The setting as "section/group/name" (see gremlin_options_list).'
    ),
]


@_tool(_READ)
def gremlin_option_get(key: _Key) -> str:
    """Read one Options setting's current value. An unknown key is an error
    (not_found)."""
    return _call("option.get", key=key)


@_tool(_CHANGE_SAME)
def gremlin_option_set(
    key: _Key,
    value: Annotated[
        bool | int | float | str,
        Field(description="The new value, of the setting's type."),
    ],
) -> str:
    """Change one Options setting. Recorded in Tools > History as made by the
    API. Refused for the "Allow control from other programs" switch (only
    the user changes it), for an unknown key (not_found) and for a value of
    the wrong type or out of range (bad_args)."""
    return _call("option.set", key=key, value=value)


@_tool(_READ)
def gremlin_options_list() -> str:
    """Every Options setting with its key and current value. Use it to find a
    key for gremlin_option_get or gremlin_option_set."""
    return _call("options.list")


# Tracing and logs ----------------------------------------------------------


@_tool(_CHANGE_SAME)
def gremlin_trace_on(
    category: Annotated[
        str | None,
        Field(
            description="The trace category (names from gremlin_trace_status); "
            "leave out for all of them."
        ),
    ] = None,
) -> str:
    """Turn tracing on, for one category or (without one) all of them. Read
    the result with gremlin_log(which="trace"). An unknown category is an
    error."""
    return _call("trace.on", category=category)


@_tool(_CHANGE_SAME)
def gremlin_trace_off(
    category: Annotated[
        str | None,
        Field(description="The trace category; leave out for all of them."),
    ] = None,
) -> str:
    """Turn tracing off, for one category or (without one) all of them. An
    unknown category is an error."""
    return _call("trace.off", category=category)


@_tool(_READ)
def gremlin_trace_status() -> str:
    """Whether tracing is on and which trace categories are on (their names
    are the ones gremlin_trace_on and gremlin_trace_off take)."""
    return _call("trace.status")


@_tool(_READ)
def gremlin_log(
    which: Annotated[
        Literal["system", "trace"],
        Field(description='"system" (the system log) or "trace" (the trace log).'),
    ] = "system",
    lines: Annotated[
        int,
        Field(
            ge=1,
            le=LOG_LINES_MAX,
            description=f"How many lines from the end, 1-{LOG_LINES_MAX}.",
        ),
    ] = 50,
) -> str:
    """The last lines of the system log or the trace log, with the log file's
    full path. Every API call writes one "API: ..." line to the system log.
    At most 500 lines per call, to keep the answer small."""
    return _call("log", which=which, lines=lines)


# Windows -------------------------------------------------------------------


@_tool(_READ)
def gremlin_windows() -> str:
    """The program's windows: shown title and whether each is visible. Use the
    titles with the other gremlin_window_* tools."""
    return _call("window.list")


@_tool(_CHANGE)
def gremlin_window_open(
    id: Annotated[
        str,
        Field(
            description="The menu command id that opens the window "
            "(from gremlin_commands)."
        ),
    ],
) -> str:
    """Open a window by running its menu command, where the program normally
    opens it. An id that isn't a main window command is not_found, a command
    that can't be used now is not_ready, and a command that opens no window
    is refused (use gremlin_run_command for it)."""
    return _call("window.open", id=id)


@_tool(_CHANGE_SAME)
def gremlin_window_close(window: _Window) -> str:
    """Close a window; answers once it has closed. Refused for the main window
    and for a window that stays open (for example one asking about unsaved
    changes; the error gives the reason). No such window is not_found."""
    return _call("window.close", window=window)


@_tool(_READ)
def gremlin_window_read(window: _Window) -> str:
    """A window's visible text, buttons, fields and check boxes as a list
    (kind, name, text, enabled). Use it before gremlin_window_press or
    gremlin_window_type to find the names. No such window is not_found."""
    return _call("window.read", window=window)


@_tool(_CHANGE_SAME)
def gremlin_window_screenshot(
    window: _Window,
    path: Annotated[
        str,
        Field(
            description="Full path of the PNG file to write; a short path is refused."
        ),
    ],
) -> list[str | Image]:
    """Take a picture of one Gremlin window (the window only), save it as a
    PNG file and return the picture itself, with the file's path and size.
    Refused for a short (relative) path ("Give the full path."); no such
    window is not_found."""
    result = _call_raw("window.screenshot", window=window, path=path)
    saved = result.get("path", path) if isinstance(result, dict) else path
    try:
        data = pathlib.Path(str(saved)).read_bytes()
    except OSError as exc:
        return [
            _json(result),
            f"The picture was saved but couldn't be read back: {exc}",
        ]
    return [_json(result), Image(data=data, format="png")]


@_tool(_DESTRUCTIVE)
def gremlin_window_press(
    window: _Window,
    button: Annotated[
        str,
        Field(
            description="The button's visible text or name, from gremlin_window_read."
        ),
    ],
) -> str:
    """Press a button in a window, as if the user clicked it (it may change,
    delete or close things). The system log notes it was the API. No such
    window or button is not_found; a disabled button is refused."""
    return _call("window.press", window=window, button=button)


@_tool(_DESTRUCTIVE)
def gremlin_window_type(
    window: _Window,
    field: Annotated[
        str, Field(description="The field's name, from gremlin_window_read.")
    ],
    text: Annotated[
        str, Field(description="The text to enter; it replaces the field's text.")
    ],
) -> str:
    """Type text into a field in a window, replacing its text. The system log
    notes it was the API. No such window or field is not_found; text the
    field doesn't keep is refused."""
    return _call("window.type", window=window, field=field, text=text)


if __name__ == "__main__":
    mcp.run("stdio")
