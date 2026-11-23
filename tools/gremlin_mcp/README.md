# gremlin MCP server (development only)

An MCP (Model Context Protocol) server that lets Claude Code read and control a
running Gremlin-Platforms through its control API. Plan:
`claude/plans/control-api.md`; contract: `claude/plans/control-api-contract.md`.

- Uses `gremlin_ctl.client` only; it knows nothing about the pipe.
- stdio transport. Claude Code starts it from the project's `.mcp.json`
  (server name `gremlin`) with the Poetry venv Python.
- The `mcp` package is a Poetry dev dependency
  (`[tool.poetry.group.dev.dependencies]`); the server is not in the installer.
- Gremlin-Platforms must be running with Options › General › "Allow control
  from other programs" on. Otherwise every tool returns an error with the
  client's message.

Run by hand (it waits for an MCP client on stdin):

    python tools/gremlin_mcp/server.py

## Tools

One tool per API call. Each returns the call's result as JSON text.

| Tool | API call | Arguments |
|---|---|---|
| gremlin_state | state | |
| gremlin_devices | devices | |
| gremlin_run_start | run.start | |
| gremlin_run_stop | run.stop | |
| gremlin_profile_load | profile.load | path (made absolute) |
| gremlin_profile_save | profile.save | |
| gremlin_commands | commands | |
| gremlin_run_command | command.run | id |
| gremlin_option_get | option.get | key (section/group/name) |
| gremlin_option_set | option.set | key, value |
| gremlin_options_list | options.list | |
| gremlin_trace_on | trace.on | category (optional) |
| gremlin_trace_off | trace.off | category (optional) |
| gremlin_trace_status | trace.status | |
| gremlin_log | log | which (system/trace), lines |
| gremlin_windows | window.list | |
| gremlin_window_open | window.open | command |
| gremlin_window_close | window.close | window |
| gremlin_window_read | window.read | window |
| gremlin_window_screenshot | window.screenshot | window, path (made absolute) |
| gremlin_window_press | window.press | window, button |
| gremlin_window_type | window.type | window, field, text |

Tests: `test/unit/test_gremlin_mcp.py`.
