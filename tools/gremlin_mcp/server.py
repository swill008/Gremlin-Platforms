# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""MCP server for the Gremlin-Platforms control API (development only).

One tool per API call. Every call goes through gremlin_ctl.client, the only
code that knows the pipe's protocol; this file knows nothing about pipes.
Started by Claude Code from the project's .mcp.json over stdio:

    python tools/gremlin_mcp/server.py

The program must be running with Options > General > "Allow control from
other programs" switched on.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Literal, Protocol

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

# gremlin_ctl lives at the repository root; the server may be started from
# anywhere.
_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


_INSTRUCTIONS = (
    "Reads and controls a running Gremlin-Platforms (joystick remapper) on "
    "this PC through its control API. The program must be running with "
    "Options > General > 'Allow control from other programs' switched on; "
    "otherwise every tool returns an error saying so. Windows are named by "
    "their shown title (case-insensitive). Menu command ids come from "
    "gremlin_commands."
)

mcp = MCPServer("gremlin", instructions=_INSTRUCTIONS)


class _Client(Protocol):
    def call(self, name: str, **args: object) -> object: ...


def _connect() -> _Client:
    """A connected gremlin_ctl client (a fresh one per call: the program
    may have restarted since the last call)."""
    from gremlin_ctl import client

    return client.connect()


def _call(name: str, **args: object) -> str:
    """Make one API call; the result as JSON text, errors as tool errors
    carrying the client's message."""
    args = {k: v for k, v in args.items() if v is not None}
    try:
        conn = _connect()
        try:
            result = conn.call(name, **args)
        finally:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError(str(exc) or type(exc).__name__) from exc
    return json.dumps(result, indent=1, ensure_ascii=False, default=str)


def _absolute(path: str) -> str:
    """The program runs in its own folder, so relative paths are made
    absolute here, against this server's working folder."""
    return os.path.abspath(os.path.expanduser(path))


# State ---------------------------------------------------------------------


@mcp.tool(structured_output=False)
def gremlin_state() -> str:
    """Overall state: program version, running profile, mode, tracing on/off,
    Health count (bindings with a problem), Screen Saver Mode state and wake
    counts."""
    return _call("state")


@mcp.tool(structured_output=False)
def gremlin_devices() -> str:
    """The input devices the program knows, with whether each is plugged in."""
    return _call("devices")


# Profile -------------------------------------------------------------------


@mcp.tool(structured_output=False)
def gremlin_run_start() -> str:
    """Start running the loaded profile (same as the Run button)."""
    return _call("run.start")


@mcp.tool(structured_output=False)
def gremlin_run_stop() -> str:
    """Stop running the profile."""
    return _call("run.stop")


@mcp.tool(structured_output=False)
def gremlin_profile_load(path: str) -> str:
    """Load a profile file (.xml) into the program. Recorded in Tools >
    History as made by the API.

    Args:
        path: The profile file; a relative path is taken from this server's
            working folder.
    """
    return _call("profile.load", path=_absolute(path))


@mcp.tool(structured_output=False)
def gremlin_profile_save() -> str:
    """Save the loaded profile to its file."""
    return _call("profile.save")


# Menu commands -------------------------------------------------------------


@mcp.tool(structured_output=False)
def gremlin_commands() -> str:
    """The program's menu commands: id, shown text and group. Use the ids with
    gremlin_run_command and gremlin_window_open."""
    return _call("commands")


@mcp.tool(structured_output=False)
def gremlin_run_command(id: str) -> str:
    """Run a menu command by its id (from gremlin_commands), as if the user
    chose it from the menu. Returns {"ran": true|false}.

    Args:
        id: The menu command id.
    """
    return _call("command.run", id=id)


# Options -------------------------------------------------------------------


@mcp.tool(structured_output=False)
def gremlin_option_get(key: str) -> str:
    """Read one Options setting.

    Args:
        key: The setting as "section/group/name" (see gremlin_options_list).
    """
    return _call("option.get", key=key)


@mcp.tool(structured_output=False)
def gremlin_option_set(key: str, value: bool | int | float | str) -> str:
    """Change one Options setting. Recorded in Tools > History as made by the
    API. The "Allow control from other programs" switch can't be changed
    this way.

    Args:
        key: The setting as "section/group/name" (see gremlin_options_list).
        value: The new value, of the setting's type.
    """
    return _call("option.set", key=key, value=value)


@mcp.tool(structured_output=False)
def gremlin_options_list() -> str:
    """Every Options setting with its key and current value."""
    return _call("options.list")


# Tracing and logs ----------------------------------------------------------


@mcp.tool(structured_output=False)
def gremlin_trace_on(category: str | None = None) -> str:
    """Turn tracing on, for one category or (without one) all of them.

    Args:
        category: The trace category; leave out for all (see
            gremlin_trace_status for the names).
    """
    return _call("trace.on", category=category)


@mcp.tool(structured_output=False)
def gremlin_trace_off(category: str | None = None) -> str:
    """Turn tracing off, for one category or (without one) all of them.

    Args:
        category: The trace category; leave out for all.
    """
    return _call("trace.off", category=category)


@mcp.tool(structured_output=False)
def gremlin_trace_status() -> str:
    """Which trace categories are on."""
    return _call("trace.status")


@mcp.tool(structured_output=False)
def gremlin_log(which: Literal["system", "trace"] = "system", lines: int = 50) -> str:
    """The last lines of the system log or the trace log.

    Args:
        which: "system" or "trace".
        lines: How many lines from the end.
    """
    return _call("log", which=which, lines=lines)


# Windows -------------------------------------------------------------------


@mcp.tool(structured_output=False)
def gremlin_windows() -> str:
    """The program's windows: shown title and whether each is visible."""
    return _call("window.list")


@mcp.tool(structured_output=False)
def gremlin_window_open(command: str) -> str:
    """Open a window by running its menu command id (from gremlin_commands).
    It opens where the program normally opens it.

    Args:
        command: The menu command id.
    """
    return _call("window.open", command=command)


@mcp.tool(structured_output=False)
def gremlin_window_close(window: str) -> str:
    """Close a window.

    Args:
        window: The window's shown title (case-insensitive).
    """
    return _call("window.close", window=window)


@mcp.tool(structured_output=False)
def gremlin_window_read(window: str) -> str:
    """A window's visible text, buttons, fields and check boxes as a list
    (kind, name, text, enabled).

    Args:
        window: The window's shown title (case-insensitive).
    """
    return _call("window.read", window=window)


@mcp.tool(structured_output=False)
def gremlin_window_screenshot(window: str, path: str) -> str:
    """Save a picture (PNG) of one Gremlin window, the window only.

    Args:
        window: The window's shown title (case-insensitive).
        path: The PNG file to write; a relative path is taken from this
            server's working folder.
    """
    return _call("window.screenshot", window=window, path=_absolute(path))


@mcp.tool(structured_output=False)
def gremlin_window_press(window: str, button: str) -> str:
    """Press a button in a window. The system log notes it was the API.

    Args:
        window: The window's shown title (case-insensitive).
        button: The button's visible text or objectName.
    """
    return _call("window.press", window=window, button=button)


@mcp.tool(structured_output=False)
def gremlin_window_type(window: str, field: str, text: str) -> str:
    """Type text into a field in a window. The system log notes it was the
    API.

    Args:
        window: The window's shown title (case-insensitive).
        field: The field's name (from gremlin_window_read).
        text: The text to enter.
    """
    return _call("window.type", window=window, field=field, text=text)


if __name__ == "__main__":
    mcp.run("stdio")
