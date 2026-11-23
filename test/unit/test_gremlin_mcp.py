# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The MCP server (tools/gremlin_mcp/server.py): one tool per API call, each
mapped to the right gremlin_ctl client call; errors come back as tool errors
carrying the client's message."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import pathlib
import sys
from types import ModuleType
from typing import Any

import pytest

pytest.importorskip("mcp.server.mcpserver")

from mcp.server.mcpserver.exceptions import ToolError  # noqa: E402

_SERVER = (
    pathlib.Path(__file__).resolve().parents[2] / "tools" / "gremlin_mcp" / "server.py"
)


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("gremlin_mcp_server", _SERVER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


server = _load()


# tool -> (arguments, API call, arguments the client gets)
_CASES: dict[str, tuple[dict[str, Any], str, dict[str, Any]]] = {
    "gremlin_state": ({}, "state", {}),
    "gremlin_devices": ({}, "devices", {}),
    "gremlin_run_start": ({}, "run.start", {}),
    "gremlin_run_stop": ({}, "run.stop", {}),
    "gremlin_profile_load": (
        {"path": "C:/p/x.xml"},
        "profile.load",
        {"path": os.path.abspath("C:/p/x.xml")},
    ),
    "gremlin_profile_save": ({}, "profile.save", {}),
    "gremlin_commands": ({}, "commands", {}),
    "gremlin_run_command": (
        {"id": "tools.history"},
        "command.run",
        {"id": "tools.history"},
    ),
    "gremlin_option_get": ({"key": "a/b/c"}, "option.get", {"key": "a/b/c"}),
    "gremlin_option_set": (
        {"key": "a/b/c", "value": True},
        "option.set",
        {"key": "a/b/c", "value": True},
    ),
    "gremlin_options_list": ({}, "options.list", {}),
    "gremlin_trace_on": ({"category": "output"}, "trace.on", {"category": "output"}),
    "gremlin_trace_off": ({}, "trace.off", {}),
    "gremlin_trace_status": ({}, "trace.status", {}),
    "gremlin_log": (
        {"which": "trace", "lines": 5},
        "log",
        {"which": "trace", "lines": 5},
    ),
    "gremlin_windows": ({}, "window.list", {}),
    "gremlin_window_open": (
        {"command": "tools.health"},
        "window.open",
        {"command": "tools.health"},
    ),
    "gremlin_window_close": (
        {"window": "Health"},
        "window.close",
        {"window": "Health"},
    ),
    "gremlin_window_read": ({"window": "Health"}, "window.read", {"window": "Health"}),
    "gremlin_window_screenshot": (
        {"window": "Health", "path": "C:/shots/h.png"},
        "window.screenshot",
        {"window": "Health", "path": os.path.abspath("C:/shots/h.png")},
    ),
    "gremlin_window_press": (
        {"window": "Health", "button": "Close"},
        "window.press",
        {"window": "Health", "button": "Close"},
    ),
    "gremlin_window_type": (
        {"window": "Search", "field": "query", "text": "vJoy"},
        "window.type",
        {"window": "Search", "field": "query", "text": "vJoy"},
    ),
}


class _FakeClient:
    def __init__(self, result: Any = None, error: Exception | None = None) -> None:  # noqa: ANN401
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.closed = False
        self._result = result
        self._error = error

    def call(self, name: str, **args: Any) -> Any:  # noqa: ANN401
        self.calls.append((name, args))
        if self._error is not None:
            raise self._error
        return self._result

    def close(self) -> None:
        self.closed = True


def _text(result: Any) -> str:  # noqa: ANN401
    return result.content[0].text


def test_lists_one_tool_per_call() -> None:
    tools = asyncio.run(server.mcp.list_tools())
    assert sorted(t.name for t in tools) == sorted(_CASES)
    for tool in tools:
        assert tool.description and len(tool.description) > 20, tool.name


@pytest.mark.parametrize("tool", sorted(_CASES))
def test_tool_maps_to_client_call(tool: str, monkeypatch: pytest.MonkeyPatch) -> None:
    arguments, call, expected = _CASES[tool]
    fake = _FakeClient(result={"ok": tool})
    monkeypatch.setattr(server, "_connect", lambda: fake)
    result = asyncio.run(server.mcp.call_tool(tool, arguments))
    assert fake.calls == [(call, expected)]
    assert fake.closed
    assert json.loads(_text(result)) == {"ok": tool}


def test_client_error_is_a_tool_error_with_its_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeClient(error=RuntimeError("Gremlin-Platforms isn't running"))
    monkeypatch.setattr(server, "_connect", lambda: fake)
    with pytest.raises(ToolError, match="isn't running"):
        asyncio.run(server.mcp.call_tool("gremlin_state", {}))
    assert fake.closed


def test_connect_error_is_a_tool_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse() -> Any:  # noqa: ANN401
        raise RuntimeError("Control from other programs is off in Options")

    monkeypatch.setattr(server, "_connect", refuse)
    with pytest.raises(ToolError, match="is off in Options"):
        asyncio.run(server.mcp.call_tool("gremlin_run_start", {}))


def test_default_connect_uses_gremlin_ctl_client(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    """With no program (no endpoint file) the real client's message comes
    back as the tool error."""
    client = pytest.importorskip("gremlin_ctl.client")
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv(client.ENDPOINT_ENV, str(tmp_path / "missing.json"))
    with pytest.raises(ToolError) as info:
        asyncio.run(server.mcp.call_tool("gremlin_state", {}))
    assert client.NOT_RUNNING_TEXT in str(info.value)
