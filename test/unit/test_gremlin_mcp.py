# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The MCP server (tools/gremlin_mcp/server.py): one tool per API call, each
mapped to the right gremlin_ctl client call; errors come back as tool errors
carrying the client's message and code; hints, strict schemas, the log limit
and the screenshot picture (page 13, S10, S25, S30, S31)."""

from __future__ import annotations

import asyncio
import base64
import importlib.util
import json
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
        {"path": "C:/p/x.xml"},
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
        {"id": "tools.health"},
        "window.open",
        {"id": "tools.health"},
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
        {"window": "Health", "path": "C:/shots/h.png"},
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


# S31 hints ------------------------------------------------------------------

_READ_ONLY = {
    "gremlin_state",
    "gremlin_devices",
    "gremlin_commands",
    "gremlin_option_get",
    "gremlin_options_list",
    "gremlin_trace_status",
    "gremlin_log",
    "gremlin_windows",
    "gremlin_window_read",
}
_DESTRUCTIVE = {
    "gremlin_profile_load",
    "gremlin_profile_save",
    "gremlin_run_command",
    "gremlin_window_press",
    "gremlin_window_type",
}


def _tools() -> dict[str, Any]:
    return {t.name: t for t in asyncio.run(server.mcp.list_tools())}


def test_every_tool_carries_the_mcp_hints() -> None:
    for name, tool in _tools().items():
        hints = tool.annotations
        assert hints is not None, name
        assert hints.open_world_hint is False, name
        assert hints.read_only_hint is (name in _READ_ONLY), name
        if name not in _READ_ONLY:
            assert hints.destructive_hint is (name in _DESTRUCTIVE), name


def test_schemas_refuse_unknown_arguments_and_describe_each_one() -> None:
    for name, tool in _tools().items():
        schema = tool.input_schema
        assert schema.get("additionalProperties") is False, name
        for arg, prop in schema.get("properties", {}).items():
            assert prop.get("description"), f"{name}.{arg}"


def test_a_misspelled_argument_is_refused_before_the_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """trace_on(categroy=...) used to run as trace_on() and switch on all
    tracing."""
    fake = _FakeClient(result={})
    monkeypatch.setattr(server, "_connect", lambda: fake)
    with pytest.raises(ToolError, match="no argument 'categroy'; it takes 'category'"):
        asyncio.run(server.mcp.call_tool("gremlin_trace_on", {"categroy": "hidhide"}))
    with pytest.raises(ToolError, match="no argument 'force'; it takes no arguments"):
        asyncio.run(server.mcp.call_tool("gremlin_run_stop", {"force": True}))
    assert fake.calls == []


@pytest.mark.parametrize("lines", [0, 501])
def test_log_takes_1_to_500_lines(lines: int, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeClient(result={})
    monkeypatch.setattr(server, "_connect", lambda: fake)
    with pytest.raises(ToolError):
        asyncio.run(server.mcp.call_tool("gremlin_log", {"lines": lines}))
    assert fake.calls == []
    prop = _tools()["gremlin_log"].input_schema["properties"]["lines"]
    assert (prop["minimum"], prop["maximum"]) == (1, 500)


def test_screenshot_returns_the_picture_and_the_saved_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
) -> None:
    png = tmp_path / "h.png"
    data = bytes([0x89]) + b"PNG fake"
    png.write_bytes(data)
    answer = {"path": str(png), "width": 10, "height": 20}
    fake = _FakeClient(result=answer)
    monkeypatch.setattr(server, "_connect", lambda: fake)
    result = asyncio.run(
        server.mcp.call_tool(
            "gremlin_window_screenshot", {"window": "Health", "path": str(png)}
        )
    )
    text, image = result.content
    assert json.loads(text.text) == answer
    assert image.type == "image" and image.mime_type == "image/png"
    assert base64.b64decode(image.data) == data


class _CodedError(Exception):
    code = "not_found"


def test_an_error_carries_the_programs_text_and_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake = _FakeClient(error=_CodedError("No window called 'Nope'."))
    monkeypatch.setattr(server, "_connect", lambda: fake)
    with pytest.raises(
        ToolError, match=r"No window called 'Nope'\. \(code: not_found\)"
    ):
        asyncio.run(server.mcp.call_tool("gremlin_window_read", {"window": "Nope"}))


def test_an_error_reaches_the_model_as_an_is_error_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Through the protocol handler (what Claude Code gets), not a crash."""
    from mcp.types import CallToolRequestParams

    fake = _FakeClient(error=_CodedError("No window called 'Nope'."))
    monkeypatch.setattr(server, "_connect", lambda: fake)
    params = CallToolRequestParams(
        name="gremlin_window_read", arguments={"window": "Nope"}
    )
    result = asyncio.run(server.mcp._handle_call_tool(None, params))
    assert result.is_error
    assert "(code: not_found)" in result.content[0].text


def test_no_help_or_call_tool() -> None:
    """S10: MCP's own tool list is the help."""
    assert not {"gremlin_help", "gremlin_call"} & set(_tools())
