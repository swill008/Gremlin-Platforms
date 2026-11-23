# API research: the MCP server against the MCP spec and Anthropic's tool guidance

Agent R-MCP, 2026-11-23, 16:07-16:10. Read-only study; no program or spec files changed.

Subject: `tools/gremlin_mcp/server.py` (22 tools, mcp Python SDK 2.3.0 in the Poetry dev group, `MCPServer`), read with `claude/program-map/13-control-api.md`, `claude/audits/2026-11-23-api-responses/client.md` (rows 27-29, findings 10-12) and `server.md`.

Rule for this file: every "source says" claim comes from a page fetched this session (URLs below). Where a page didn't cover a point, that is said. Two points were checked on our own installed SDK instead (marked "checked locally").

## Sources

1. MCP specification 2025-11-25, Tools: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
2. MCP specification 2025-11-25, Schema reference (ToolAnnotations, CallToolResult): https://modelcontextprotocol.io/specification/2025-11-25/schema
3. MCP specification 2025-11-25, Lifecycle (Timeouts): https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle
4. MCP specification 2025-11-25, Cancellation: https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/cancellation
5. MCP specification 2025-11-25, Progress: https://modelcontextprotocol.io/specification/2025-11-25/basic/utilities/progress
6. MCP specification 2025-11-25, Security Best Practices: https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices
7. MCP Python SDK README: https://github.com/modelcontextprotocol/python-sdk (no tool-error, image or annotation detail; pointed to the docs site)
8. MCP Python SDK docs: https://py.sdk.modelcontextprotocol.io/ , and its pages servers/tools/, servers/structured-output/, servers/media/, servers/handling-errors/
9. Anthropic Engineering, "Writing effective tools for agents — with agents" (11 Sep 2025): https://www.anthropic.com/engineering/writing-tools-for-agents
10. Claude API docs, Define tools (redirected from docs.claude.com implement-tool-use): https://platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use
11. Claude API docs, Handle tool calls: https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls
12. Claude Code docs, MCP: https://code.claude.com/docs/en/mcp

Fetch notes: the first read of source 2 was cut before ToolAnnotations; a second read from offset 100000 gave the text used here. Source 12 was read in two parts. Source 7 had none of the details asked for, so source 8 was used.

## Key points per source

**1. MCP Tools.**
- Tool names should be 1-128 characters of letters, digits, `_`, `-`, `.`; case-sensitive; unique in the server.
- `inputSchema` must be a valid JSON Schema object (2020-12 by default). For a tool with no arguments, the recommended form is `{"type": "object", "additionalProperties": false}` (only an empty object is accepted); plain `{"type": "object"}` accepts any object.
- `outputSchema` is optional. If given, the server must return `structuredContent` that conforms to it; a tool returning structured content should also send the same JSON as a text block.
- Content can be text, image (base64 `data` + `mimeType`), audio, resource links and embedded resources.
- Two kinds of error. Protocol errors (JSON-RPC) are for unknown tools, malformed requests and server errors. Tool execution errors (`isError: true` in the result) are for API failures, input validation errors (wrong format, out of range) and business-logic errors. Execution errors carry "actionable feedback" so the model can correct itself and retry.
- Security: servers must validate all tool inputs, apply access controls, rate-limit calls and sanitise outputs. Clients should confirm sensitive operations with the user, show tool inputs, and apply timeouts. A human should be able to deny tool calls.

**2. MCP Schema.**
- ToolAnnotations are hints only, never guarantees; clients should not decide on them for untrusted servers.
- `readOnlyHint` (default false): changes nothing. `destructiveHint` (default true; only when not read-only): may make destructive updates, false means additive only. `idempotentHint` (default false): repeating the call with the same arguments has no further effect. `openWorldHint` (default true): talks to an open world of outside entities; false for a closed domain.
- CallToolResult.isError: errors that come from the tool should be reported in the result with `isError` set, not as a protocol error, "Otherwise, the LLM would not be able to see that an error occurred" (paraphrase of the doc comment around that line).
- `outputSchema` is limited to `type: "object"` at the root.

**3. Lifecycle, Timeouts.** Senders should set timeouts on every request, send a cancellation when one expires, and always enforce a maximum timeout even when progress notifications reset the clock. SDKs should allow per-request timeouts.

**4. Cancellation.** Either side may send `notifications/cancelled` with the request id. The receiver should stop work and free resources, may ignore it if the work is done or can't be cancelled, and both sides must handle the race where the answer was already sent.

**5. Progress.** A request may carry a `progressToken`; the receiver may send `notifications/progress` with a rising `progress`, optional `total` and `message`. Sending progress is optional.

**6. Security Best Practices.** Most sections are about OAuth proxies, tokens, SSRF and HTTP sessions, none of which apply to a stdio server on a private named pipe. The section that applies is "Local MCP Server Compromise": local servers run with the user's rights; servers meant to run locally should use the stdio transport so only the MCP client can reach them, or restrict HTTP with a token or a restricted IPC channel. Bugs in a legitimate local server can also lose data.

**7-8. Python SDK (v2, `MCPServer`).**
- The function's type hints are the input schema; the docstring is the description. `Annotated[..., Field(description=..., ge=..., le=...)]` adds per-argument text and becomes `minimum`/`maximum`; `Literal` becomes an enum. Bad arguments are refused before the function runs, as a tool error the model can read ("Input should be less than or equal to 50").
- Annotations: `from mcp.types import ToolAnnotations`, passed as `@mcp.tool(annotations=...)`; `title=` is also accepted. The docs say these are hints for clients, not security controls.
- Errors: `ToolError` gives `is_error=True` with the message shown to the model (prefixed with the tool name). `MCPError` becomes a JSON-RPC protocol error. Any other exception gives `is_error=True` with only a generic "Error executing tool X"; the text stays in the server log.
- Structured output: the return annotation becomes the `outputSchema`; `structured_output=False` makes a text-only tool with no schema and no `structured_content`. A Pydantic model or TypedDict return gives a real object schema and a JSON text mirror.
- Images: return `Image(path=...)` or `Image(data=..., format="png")` from `mcp.server.mcpserver`, annotated `-> Image`; the client gets an `ImageContent` block (base64 + MIME type); no structured content.
- The docs don't say how unknown argument keys are treated (see "checked locally" below).

**9. Writing effective tools for agents.**
- More tools are not better. Wrapping every API endpoint one-to-one often works poorly; build a few tools for the high-value workflows and consolidate multi-step operations into one tool. Each tool should have a clear, distinct purpose; overlapping tools distract the agent.
- Namespace related tools with a shared prefix (service, then resource), and test the choice.
- Return high-signal, natural-language fields rather than opaque ids; offer a `response_format` (concise/detailed) where useful.
- For large answers use pagination, filtering, truncation and sensible defaults. Claude Code limits tool responses to 25,000 tokens by default. When truncating, steer the agent to narrower calls.
- Errors should be actionable: say what to fix, with an example of correct input, not opaque codes or tracebacks.
- Write descriptions as for a new team member; make implicit context explicit; use unambiguous parameter names (`user_id`, not `user`) and strict input models.
- Evaluate with realistic multi-step tasks and read the transcripts.

**10. Define tools (Claude API).**
- Detailed descriptions are "by far the most important factor in tool performance". Say what the tool does, when to use it and when not, what each parameter means, and caveats. Aim for at least 3-4 sentences per tool.
- Consolidate related operations into fewer tools, for example one tool with an `action` parameter instead of `create_pr`/`review_pr`/`merge_pr`; fewer tools reduce selection ambiguity.
- Prefix names with the service; return only high-signal fields. `input_examples` help for format-sensitive inputs.

**11. Handle tool calls (Claude API).** On a failed or invalid call return `is_error: true`; Claude may retry, so limit retries. Write instructive messages saying what went wrong and what to try next, not "failed". Invalid calls during development usually mean the description needs more detail. Tool results may hold images. Tool results can carry untrusted content (prompt injection); keep it inside tool results.

**12. Claude Code MCP docs.**
- Output: a warning above 10,000 tokens; default maximum 25,000 tokens (`MAX_MCP_OUTPUT_TOKENS`); a text result over the limit, or over 50,000 characters, is saved to a file and replaced by its path.
- Images: a PNG/JPEG/GIF/WebP image from an MCP tool is shown to Claude inline (possibly scaled down) and the original is also saved to a file whose path Claude gets.
- Annotations Claude Code uses: `readOnlyHint` tools run in parallel with other read-only calls; `readOnlyHint` or `idempotentHint` tools may be repeated once after a dropped connection (HTTP servers and connectors).
- `_meta["anthropic/requiresUserInteraction"]: true` on a tool forces its permission prompt on every call, in every permission mode, with no "don't ask again".
- Tool search is on by default: only tool names and server instructions load at start, so the server instructions should say what the tools are for and when to search for them. Instructions and upfront descriptions are cut at 4,096 characters; deferred descriptions at 16,384. Put the key words first.
- Timeouts: `MCP_TOOL_TIMEOUT` and a per-server `timeout` in `.mcp.json`; stdio idle timeout 30 min by default; a main-conversation call over 2 minutes moves to the background.

**Checked locally (our installed SDK 2.3.0, scratch probe, no program code run).**
- Published schema for an argument `category: str | None = None`: `{"type": "object", "properties": {"category": ...}}`, **no `additionalProperties: false`**; no-argument tools publish `{"type": "object", "properties": {}}`; `annotations` is `None` on every tool.
- Calling it with a misspelled key `{"categroy": "hidhide"}` **succeeded and ran with `category=None`** (the extra key was dropped silently). A wrong type (`5`) was refused as a tool error carrying the raw Pydantic text, including a pydantic.dev link.
- A raised `ToolError("nice message")` reached the caller as "Error executing tool boom: nice message".

## Applies to us

| # | Topic | Source says | We do | Suggestion | Finding / question |
|---|---|---|---|---|---|
| 1 | Tool count and a generic `call` tool | Few targeted tools; don't wrap every endpoint one-to-one; consolidate related operations, e.g. one tool with an `action` parameter (9, 10). Each tool needs a clear, distinct purpose (9). | 22 tools, one per API call (server.py:7); no `call` tool (decision recorded in client.md finding 10). | Do **not** add a generic `gremlin_call(name, args)`: it would overlap all 22 tools, has no per-call schema, so no validation or descriptions, and the guidance favours distinct, described tools. If the count is to come down, consolidate by resource with an `action` enum: for example `gremlin_trace(action: on/off/status, category)` (3 to 1), `gremlin_run(action: start/stop)` (2 to 1), `gremlin_option(action: get/set/list, key, value)` (3 to 1). | Finding: the sources support "no `call` tool". Question for the user: keep one tool per call (clear names, simple schemas), or consolidate to about 14 tools with `action` parameters? The sources lean to consolidation, but neither source gives a number. |
| 2 | A `help` tool | The spec's discovery is `tools/list` itself (1). With tool search, server instructions say what the tools are for (12). No source recommends a help tool. | No `help` tool; instructions name the program, the switch, window naming, and command ids from `gremlin_commands`. | Keep no `help` tool: `tools/list` plus descriptions already are the help for an MCP client, and a help tool would duplicate them. Put what `help` would say into the descriptions and the instructions. Record this in S10 as the decision client.md finding 10 asks for. | Finding: supports the "MCP has no help tool" decision; the S10 wording still needs the user's OK (client.md finding 10). |
| 3 | Error shape | Tool failures, validation errors and business-logic errors go in the result with `isError` (1, 2); messages should say what went wrong and what to try next (9, 11). SDK: `ToolError` text reaches the model; other exceptions become a generic message (8). | Every failure is re-raised as `ToolError(str(exc))` (server.py:59-75), so the program's text reaches the model with `isError`. | Keep it. Improve texts at the source (client.md row 27, finding 9: say the next step, e.g. "switch on Options › General › Allow control from other programs"; neutral version-mismatch text). | OK; the wording gaps are already listed in client.md. |
| 4 | Unknown or misspelled arguments | Servers must validate all tool inputs (1). For no-argument tools the recommended schema has `additionalProperties: false` (1). Strict input models (9). | Checked locally: our schemas have no `additionalProperties: false`, and a misspelled key is dropped and the call runs (`gremlin_trace_on(categroy=...)` would switch on **all** tracing, the same hazard server.md row 131 found in the API). | Make every tool refuse unknown keys: publish `additionalProperties: false` and refuse extra keys before the call. In SDK 2.3 this needs either a strict argument model per tool or a small check in `_call`; which way works with `MCPServer` has to be tried, not assumed. | Gap (spec S9/S10 say nothing of unknown keys at the MCP layer; server.md proposes refusing them in the API, which would also cover MCP). Question: fix once in the API (server.md suggestion) and rely on it, or also at the MCP layer? |
| 5 | Validation messages | Bad arguments are refused before the function runs, as a readable tool error (8); errors should not be raw tracebacks (9). | Checked locally: a wrong type gives the raw Pydantic text with a pydantic.dev link. | Acceptable; optional: add `Field(description=...)` so the schema prevents most of them. | Minor. |
| 6 | Annotations on changing tools | `readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`, all hints, defaults read-only false, destructive true, open-world true (2). Claude Code runs read-only tools in parallel and may repeat read-only or idempotent tools after a dropped connection (12). | No annotations, so every tool is treated by the defaults: not read-only, destructive, open world. | Add `ToolAnnotations` (8) to every tool, `openWorldHint=False` on all (a closed, local program). Read-only: state, devices, commands, option_get, options_list, trace_status, log, windows, window_read. Changing but not destructive, idempotent: trace_on, trace_off, option_set, run_start, run_stop, window_close. Destructive: profile_load (replaces the loaded profile), profile_save (overwrites the file), run_command (any menu command, including exit), window_press, window_type. window_open and window_screenshot (writes a file): not read-only, not destructive. | Gap (no spec statement; S1 doesn't cover annotations). The exact mapping per tool is for the user to approve; run_start/run_stop idempotency should be checked against S24 (does a second start error?). |
| 7 | Forcing a prompt for risky tools | `_meta["anthropic/requiresUserInteraction"]` forces a permission prompt on every call in every mode (12). | Not used. | Offer it for `gremlin_run_command` (can run `file.exit`) and `gremlin_profile_save`, if the user wants a hard stop even in bypass mode. Note it also blocks agents and `-p` runs from using those tools. | Question for the user (option, not a recommendation). |
| 8 | Screenshot as an image (CTL-MCP-SCREENSHOT) | Tool results may contain image content, base64 + MIME type (1); SDK `Image(path=...)` or `Image(data=..., format="png")` (8); Claude Code shows MCP images inline and also saves the original to a file (12). Images still count against `MAX_MCP_OUTPUT_TOKENS` (12). | `gremlin_window_screenshot` writes a PNG to a given path and returns the path as JSON text. | Return the picture: after the call, return `[TextContent(path + size), Image(path=png)]` (or `Image` alone). Make `path` optional (default: a temp file) since Claude Code keeps its own copy. Keep the file write for the CLI. | Gap CTL-MCP-SCREENSHOT is directly solvable with the SDK's `Image` type; spec S6 says "to a PNG file", so returning the image too is an addition to confirm with the user. |
| 9 | Output size (log lines) | Use pagination, filtering, truncation and sensible defaults; Claude Code's default limit is 25,000 tokens, 10,000 warns (9, 12). | `gremlin_log.lines` has no bound in the schema (server.py:220); the API treats 0 as 50 and clamps over 2000 silently (server.md rows 142-143). | Bound it in the schema: `Annotated[int, Field(ge=1, le=500)]` (8) with the reason in the description; optionally a `contains` filter (the article's `search_logs` example). `options_list`, `commands` and `window_read` could also be large; check their real token sizes before adding filters. | Gap (client.md finding 11). The bound value is a small detail; the filter is a new feature for the user to decide. |
| 10 | Description accuracy and detail | Descriptions are the most important factor; say what, when, parameter meaning, caveats; 3-4 sentences or more (10); explicit context, unambiguous names (9). | One or two sentences per tool. Known inaccuracy: `gremlin_profile_load` says loading is recorded in History, which it isn't (client.md finding 5). Missing: run start/stop answer after the Run has changed and a failed start is an error (S24); load refuses with unsaved changes, save refuses Untitled (S20). | Fix the History line; add S20/S24 behaviour; add "when to use" lines and the next tool to call (e.g. window_read before press/type). Use `Annotated[..., Field(description=...)]` so argument text sits in the schema. Consider `window_title` rather than `window`, and `command_id` for both `id` and `command` (the same thing named two ways, server.md finding 17). | Gaps listed in client.md finding 11; renaming arguments is a protocol change (server.md finding 17) and needs the user. |
| 11 | Structured output | Optional `outputSchema` + `structuredContent`, with a text mirror (1); SDK makes it from the return type (8). | `structured_output=False` everywhere; JSON text only. | Leave as is for now: Claude reads the text; structured output helps programmatic clients, and an output schema forces each call's answer shape to be written down twice (API and MCP). | No change suggested. |
| 12 | Relative paths | Validate all inputs (1). | MCP makes paths absolute against its own folder (server.py:78-81); the API resolves relative paths against the program's folder (server.md finding 15). | Fine at the MCP layer; the API question stays with server.md finding 15. | Already listed. |
| 13 | Timeouts, cancellation, progress | Senders set timeouts and cancel on expiry; receivers should stop work on cancellation; progress is optional (3, 4, 5). Claude Code: stdio idle timeout 30 min; per-server `timeout` in `.mcp.json` (12). | The client library has bounded waits (10 s, 30 s for load/screenshot, S9); no progress; a cancelled MCP call still waits for the pipe answer. | No change needed: all calls finish within 30 s, well under Claude Code's limits. Optional: set `"timeout"` for the "gremlin" entry in `.mcp.json` to about 40 s so a stuck call fails fast. | Optional small detail. |
| 14 | Security | Local servers should use stdio so only the client reaches them (6); validate inputs, rate-limit, sanitise outputs (1); tool results may carry prompt-injection text (11). | stdio from `.mcp.json`; the pipe needs the secret key (S12); development only. | Nothing to add for the transport. Note: `gremlin_window_read` and `gremlin_log` return text from profiles and logs; that text is data to Claude, not instructions. A rate limit isn't needed for a one-client local tool (the API runs one call at a time, S9). | OK. |
| 15 | Names | 1-128 chars of `[A-Za-z0-9_.-]`, unique (1); prefix by service (9, 10). | `gremlin_<resource>_<verb>`, all valid. | Keep. | OK. |
| 16 | Server instructions | With tool search only names and instructions load at start; say what tasks the tools handle and when to search; 4,096-character cut (12). | About 380 characters; says what the program is and the switch. | Add one line of "use these tools to read the program's state, its logs and windows, and to drive it while testing"; list the tool groups. | Small improvement. |

## Conclusion

1. **Keep no generic `call` tool and no `help` tool.** The sources favour distinct, well-described tools (9, 10), and `tools/list` plus descriptions are the MCP help (1, 12). If the tool count is to drop, consolidating with an `action` parameter (trace, run, option) is what the guidance recommends (10). That is a question for the user.
2. **Unknown argument keys are silently dropped today** (checked locally), the same hazard server.md found in the API. The spec says servers must validate all inputs and recommends `additionalProperties: false` (1). Fix it at one shared owner: in the API (server.md's suggestion), and decide whether MCP also refuses them.
3. **Add tool annotations** (2, 8, 12): read-only on the 9 read tools (Claude Code then runs them in parallel), `openWorldHint=False` on all, destructive on profile load/save, run_command, window press/type. Optionally `requiresUserInteraction` on the riskiest (12).
4. **Return the screenshot as image content** with the SDK's `Image` type (8); Claude Code shows it inline and keeps a file copy (12). This closes CTL-MCP-SCREENSHOT; it adds to S6, so it needs the user's OK.
5. **Bound `gremlin_log.lines` in the schema** (`ge=1`, `le=` a few hundred) against Claude Code's 25,000-token limit (9, 12).
6. **Make descriptions longer and correct** (10): fix the History claim on profile_load, add the S20/S24 answers and refusals, and put argument text in the schema with `Field(description=...)`.
7. **Errors are already right in shape** (`ToolError` gives `isError` with the program's text, 1, 8); improve the texts at the client and API as client.md lists (actionable next step, 9, 11).
