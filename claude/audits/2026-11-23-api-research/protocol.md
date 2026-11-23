# Control API: what published protocol standards say (agent R-RPC, 2026-11-23)

Read-only research for the control API (`claude/program-map/13-control-api.md`, S1-S24),
mapped onto the two answer audits in `claude/audits/2026-11-23-api-responses/`
(`server.md`, `client.md`) and their 7 open questions. Every statement about a standard
below comes from a page fetched in this session (list below). Nothing is filled in from
memory. Where a page didn't cover a point, that is said.

Read in the repo: the spec page 13, `claude/plans/control-api-contract.md`, both audits,
`gremlin/control_api.py` (`dispatch`, `_run`, `handle_bytes`), `gremlin_ctl/client.py`
(timeouts and `NotRunning`).

## Sources (all fetched 2026-11-23)

1. JSON-RPC 2.0 specification: https://www.jsonrpc.org/specification
2. Language Server Protocol (LSP) 3.17 specification, base protocol: https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ (only the first 100,000 characters were read: base protocol, lifecycle, URIs, error codes)
3. gRPC status codes: https://grpc.io/docs/guides/status-codes/
4. gRPC deadlines: https://grpc.io/docs/guides/deadlines/
5. gRPC cancellation: https://grpc.io/docs/guides/cancellation/
6. gRPC retry: https://grpc.io/docs/guides/retry/
7. Google API Improvement Proposal (AIP) 193, errors: https://google.aip.dev/193
8. AIP-180, backwards compatibility: https://google.aip.dev/180
9. Microsoft Azure REST API guidelines: https://raw.githubusercontent.com/microsoft/api-guidelines/vNext/azure/Guidelines.md (first 100,000 of 108,729 characters read)
10. RFC 9457, Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457.html
11. RFC 9413, Maintaining Robust Protocols (the critique of Postel's law): https://www.rfc-editor.org/rfc/rfc9413.html
12. Model Context Protocol (MCP) 2025-06-18, server tools: https://modelcontextprotocol.io/specification/2025-06-18/server/tools
13. Command Line Interface Guidelines: https://clig.dev/

Not fetched: AIP-181 (stability levels) was not needed for these questions and wasn't read.

## Key points per source

**1. JSON-RPC 2.0.**
- A response has exactly one of `result` or `error`.
- The error object is `code` (an integer), `message` (a string) and an optional `data` (anything the server defines). The message "SHOULD be limited to a concise single sentence."
- Reserved codes: -32700 the request isn't JSON; -32600 not a valid request; -32601 method not found; -32602 invalid params; -32603 internal error; -32000 to -32099 for the server's own errors. The rest of the number space is free for application errors.
- Every request carries an `id` (a string or a whole number), and the answer echoes it. A request without an id is a notification and gets no answer.
- Batches (an array of requests) may be answered in any order; the id matches answer to request.
- Named params must match the expected names exactly, case included; a server may return an error when expected names are missing. The spec says nothing about extra (unknown) params and nothing about timeouts.

**2. LSP 3.17.**
- "Every processed request must send a response back to the sender of the request." Only notifications are unanswered.
- Cancelling: the client sends `$/cancelRequest`; the cancelled request must still get an answer (a partial result, or an error with `RequestCancelled`, -32800).
- `ContentModified` (-32801): the result no longer matches the current state because the content changed while the request was being worked on.
- `RequestFailed` (-32803): a request that was syntactically correct but failed. `ServerNotInitialized` (-32002): a request before `initialize`.
- Capabilities are exchanged in `initialize`; a missing property means the capability is absent; clients ignore server capabilities they don't understand, and servers ignore unknown properties in the client's capabilities object. Unknown `$/` notifications may be ignored; an unknown `$/` request must be answered with `MethodNotFound`.
- File locations are `DocumentUri` strings that must parse as valid Uniform Resource Identifiers (URIs, RFC 3986); every example is an absolute `file:///` URI. No relative paths.
- Ordering: answers generally follow request order; reordering is allowed only when it can't change correctness.

**3. gRPC status codes.**
- `INVALID_ARGUMENT`: the argument is bad whatever the system's state (a malformed file name, for example).
- `FAILED_PRECONDITION`: the argument may be fine, but the system isn't in the state the operation needs; the client shouldn't retry until the state is fixed.
- `NOT_FOUND`, `UNIMPLEMENTED`, `OUT_OF_RANGE`, `ABORTED` (retry at a higher level), `UNAVAILABLE` (retry with backoff, though retrying non-idempotent operations may not be safe), `INTERNAL` (a broken invariant, serious), `UNKNOWN`.
- `DEADLINE_EXCEEDED`: "The deadline expired before the operation could complete." For operations that change state, the page says the operation may have completed anyway, because a late success can miss the deadline.

**4. gRPC deadlines.** When the client's deadline passes the server cancels the call; the application must stop the work it started, and long work should check for cancellation now and then. Deadlines are passed on as remaining time. The page's diagram shows the server still working a while after the client stopped waiting.

**5. gRPC cancellation.** The server is told when a call is cancelled and "the server should stop any ongoing computation". The page says nothing about rolling back changes already made, or about retries.

**6. gRPC retry.** Without a retry policy gRPC retries only when it is sure the server didn't process the call (it never left the client, or never reached the application code). "Without a retry policy, gRPC cannot safely retry RPCs in most cases."

**7. AIP-193 (Google errors).**
- An error has a canonical numeric code, a brief developer-facing English message, and an `ErrorInfo` with a `reason` (UPPER_SNAKE_CASE, at most 63 characters), a `domain` and `metadata` (key/value). "All error responses must include an `ErrorInfo` within `details`."
- One error always has the same (reason, domain) pair, and different errors never share one.
- Any request-specific detail in the message must also be in `metadata`; metadata keys may be added but never removed.
- Clients should branch on `reason`, not on the message text. Once an error carries `ErrorInfo`, its message may change; without it, the message has to stay stable.
- Messages are brief, actionable, and readable without expert or implementation knowledge.

**8. AIP-180 (compatibility).** Adding methods, fields and messages is compatible; removing or renaming anything is not (a rename is a remove plus an add); changing a field's type or default is not; "New required fields **must not** be added to existing request messages". Visible behaviour must not change in ways likely to break reasonable client code, even undocumented behaviour. The page says nothing about error codes or messages.

**9. Microsoft Azure REST API guidelines.**
- An error answer is an `error` object with a required `code` (a string) and `message` (human-readable), plus optional `target`, `details` and `innererror`. The code is part of the contract and can't change; the other fields aren't, so clients shouldn't depend on them.
- Unknown JSON field names or values in a request fail with 400 Bad Request (unknown request headers are tolerated; unsupported query parameters are an error).
- Operations must be idempotent so clients can retry safely; POSTs should support repeatable-request ids (`Repeatability-Request-ID`). Work that takes over about a second (99th percentile) should be a long-running operation the client polls.

**10. RFC 9457 (problem details).** An error is `type` (a URI naming the kind of problem), `title` (short, the same for every occurrence of that type), `status`, `detail` (this occurrence, written to help the client fix it, not debugging internals) and `instance`. "Consumers SHOULD NOT parse the "detail" member for information." Extensions may be added; consumers must ignore extensions they don't recognise. Several validation problems can go in an extension array, each with a JSON Pointer to the field.

**11. RFC 9413 (robustness).** Being liberal in what you accept lets defects pile up and become de facto standards that every new implementation has to copy; tolerating unexpected input "instead conceals problems". It recommends that specifications say how errors are handled and that implementations fail visibly ("virtuous intolerance"), with explicit error signals, and that extensibility be designed in advance (how new messages and parameters are handled) rather than left to accident.

**12. MCP tools.** Two kinds of error: protocol errors (JSON-RPC errors such as an unknown tool or invalid arguments, e.g. -32602) and tool execution errors, returned as a result with `isError: true` and the text in `content`. Each tool has an `inputSchema` (JSON Schema, with `required`). Servers MUST validate all tool inputs; clients SHOULD put timeouts on tool calls. A structured result goes in `structuredContent`, with the same JSON also as text.

**13. Command Line Interface Guidelines (clig.dev).** "Map the non-zero exit codes to the most important failure modes." Machine-readable output goes to stdout, errors and messages to stderr; `--json` prints JSON. Error messages are rewritten for a person and say how to fix the problem. Validate input early and stop before anything harmful happens. Network timeouts are configurable with a sensible default so the program never hangs.

## Applies to us

| # | Topic | Standard says | We do (spec / code) | Suggestion | Finding / question |
|---|---|---|---|---|---|
| 1 | Error object shape | A machine-readable code plus a short human message: JSON-RPC `code` + `message` (+`data`) [1]; AIP-193 code + message + `ErrorInfo.reason` [7]; Azure `code` (stable string) + `message` [9]; RFC 9457 `type` + `title` + `detail` [10] | `{"ok": false, "error": "<text>"}`, text only (S9; `control_api.py` `dispatch`, `_run`) | Add a stable code next to the text: `{"ok": false, "error": "<text>", "code": "UNKNOWN_ARGUMENT"}`. Keep `error` as the text so nothing else changes (AIP-180: adding a field is compatible [8]). A short fixed list (below) | Question 4 (error wording), question 7 (`--json` errors) |
| 2 | Which codes | JSON-RPC: parse error, invalid request, method not found, invalid params, internal [1]; gRPC: `INVALID_ARGUMENT` vs `FAILED_PRECONDITION` vs `NOT_FOUND` vs `DEADLINE_EXCEEDED` vs `UNAVAILABLE` vs `INTERNAL` [3] | One text for all; the CLI folds every call error into exit 1 | A set drawn from [1] and [3]: `BAD_REQUEST` (not JSON, not a request), `UNKNOWN_CALL`, `INVALID_ARGUMENT` (bad, missing or unknown argument), `NOT_FOUND` (no such window, setting, command, file), `FAILED_PRECONDITION` (unsaved changes, Untitled, switch off, window not ready, can't be used now), `BUSY`, `TIMED_OUT`, `INTERNAL` (an unexpected fault, today's "<ExceptionName>: text") | server findings 2, 9, 11, 17; question 4 |
| 3 | Clients read the code, not the text | Clients branch on `reason`, not message text [7]; consumers should not parse `detail` [10]; only the code is contract in Azure [9] | gremlin-ctl and MCP pass the text through; nothing parses it today | Once codes exist, the wording can be tidied freely (full stops, quotes, "Missing 'window'" vs "needs a window name") without breaking scripts: AIP-193 allows message changes once a machine reason exists [7] | Question 4; server finding 17 |
| 4 | Message style | One concise sentence [1]; brief, actionable, no implementation detail [7]; helps the client fix the problem [10]; say how to fix it [13] | Mostly one plain line (S8); some say what to do ("options.list lists them"); some don't ("The profile didn't open (the program says why)", "The profile was not saved."); some Python words ("(int)") | One sentence, ends with a full stop, names the thing and the next step: "profile.load needs a full path.", "No window called 'X'. window.list lists them." Put the reason in profile.load / profile.save errors | server findings 5, 8, 12, 17; client finding 9; question 4 |
| 5 | Unknown argument names | Microsoft: unrecognised JSON field names fail with 400 [9]; RFC 9413: tolerating unexpected input conceals problems, fail visibly [11]; MCP: servers MUST validate tool inputs, tools publish an input schema [12]. JSON-RPC is silent on extra params [1]. LSP ignores unknown properties only inside the capabilities object, an extension point designed for that [2] | Ignored; the call runs as if the argument were missing (`trace.on {"categroy"}` turns all tracing on; `window.type` without `text` clears the field) | Refuse them: each call declares its argument names (and which are required) at `register(...)`; dispatch answers `INVALID_ARGUMENT` "trace.on has no argument 'categroy' (it takes: category)." `help` lists the arguments, and the MCP tools can use the same list for their `inputSchema`. Make `text` required for `window.type` | server finding 2; question 1 |
| 6 | Argument names consistent | AIP-180: a rename is a remove plus an add; the old name must stay in a released API [8] | `command.run {id}` but `window.open {command}`; window errors "Missing 'window'" vs "profile.load needs a path." | The program is unreleased (CLAUDE.md: no legacy compatibility by default), so rename now in one batch (program, client, MCP, Help) to one name, e.g. `id` for a menu command id, with no alias | server finding 17; question 4 |
| 7 | window.open messages | gRPC separates `NOT_FOUND` (no such thing) from `FAILED_PRECONDITION` (exists, wrong state) [3] | One message for both: "Command 'x' isn't a menu command or can't be used now"; command.run splits them (S17) | Same split as command.run: `NOT_FOUND` "No command called 'x'." and `FAILED_PRECONDITION` "'x' can't be used now." Answer the opened window's title when one opened | server finding 9; question 2 |
| 8 | Relative paths | LSP sends locations only as URIs, every example an absolute `file:///` URI [2]; gRPC: a malformed file name is `INVALID_ARGUMENT` [3] | Resolved against the program's working folder (`profile.load`, `window.screenshot`); gremlin-ctl resolves them first, MCP and raw clients don't | The program refuses a relative path: `INVALID_ARGUMENT` "profile.load needs a full path." The client front ends (gremlin-ctl) keep turning a typed relative path into a full one, since that is the user's own folder | server finding 15; question 3 |
| 9 | A timed-out call may still run | gRPC: after `DEADLINE_EXCEEDED` a state-changing operation may have completed [3]; the server should stop work on cancel, but stopping is the handler's job and nothing promises a rollback [4][5] | The program answers "took over N s; the program carried on without it." but `threads.main_call_wait` still runs the queued job later, so option.set / profile.load / window.type may happen after "failed" | Two parts, both from [3]-[5]: (a) don't start a job whose caller has already given up (the gRPC "stop the work" rule, at the shared owner `threads.main_call_wait`); (b) a job already running can't be stopped, so the timeout text says so: "profile.load didn't finish within 30 s; it may still finish." with code `TIMED_OUT` | server finding 3 |
| 10 | One deadline, and the server answers before the client gives up | gRPC passes the remaining time on, so every step works to one deadline [4]; LSP: every request gets an answer [2]; MCP: clients put timeouts on tool calls [12] | Busy wait and call each get the full limit (up to 60 s), past gremlin-ctl's 40 s; a request over 1 MB is dropped without an answer | One deadline per call covering the busy wait and the run; answer the 1 MB case ("The request is over 1 MB.") instead of closing | server findings 4, 14 |
| 11 | Exit code when the program stops answering or closes mid-call | gRPC has distinct codes: `UNAVAILABLE` (couldn't reach it; retry may be unsafe for non-idempotent calls) [3]; `DEADLINE_EXCEEDED` (may have completed) [3]; gRPC only retries by itself when sure the server never processed the call [6]; clig: map exit codes to the important failure modes [13] | Both give exit 2 "isn't running", the code for "nothing happened, the program isn't there" | Keep 2 only for "never reached the program" (no endpoint, pipe gone, wrong key: the gRPC transparent-retry case [6]). A call that was sent and then got no answer or a closed pipe is a different failure mode: the call may have run [3]. Recommended: give it 1 (the call failed), with the text "Gremlin-Platforms didn't answer run.start within 40 s; it may still have run." / "...closed before answering run.start; it may have run." The other option (a new code 5) also fits [13] but S11 says no other code is used | client findings 8 (rows 15-16); question 5 |
| 12 | Request ids | JSON-RPC and LSP: every request has an id echoed in the answer, to match answers to requests and to cancel [1][2] | No id; one call at a time per connection, and the client waits for each answer | Not needed while one connection carries one call at a time: there is nothing to mismatch. An id becomes needed only with batches, several calls in flight, or cancelling a call | none (noted) |
| 13 | Version and capabilities | LSP: capabilities exchanged at start; a missing capability means absent [2]; AIP-180: added calls and fields are compatible within a version, removals and renames are not [8] | `hello` returns version 1; mismatch is exit 3; `help` lists the calls | Fits. With the program unreleased, renames in question 4 don't need a version bump. After release, add calls and fields without a bump; bump only for a removal or rename. `help` listing each call's arguments (row 5) serves as the capability list | client finding 12 |
| 14 | MCP `help` and `call` tools | MCP: the server publishes its tools with an input schema in `tools/list` [12] | 22 tools; no `gremlin_help` or `gremlin_call` | `tools/list` already does `help`'s job for an MCP client [12], so `gremlin_help` adds little. A `gremlin_call` (any call by name with JSON args) is the only way to reach a call that has no tool yet; it matches S23. If added, it should still validate its input [12]. Recommendation: add `gremlin_call`, and record in S10 that `help` is command line and `tools/list` covers MCP | client finding 10; question 6 |
| 15 | MCP error kinds | Unknown tool and invalid arguments are protocol errors (-32602); a failed call is a result with `isError: true` [12] | Every failure is a `ToolError` with the client's text | Fits (the `mcp` package turns `ToolError` into `isError` results; not verified in this study). With codes (row 1), the text can start with the code so Claude can tell "bad argument" from "not running" | client findings 11, 27 |
| 16 | `--json` errors | clig: machine-readable output on stdout, errors on stderr, `--json` prints JSON [13]; JSON-RPC, Azure, RFC 9457 all give errors as structured objects [1][9][10] | With `--json`, an error is plain text on stderr and nothing on stdout | With `--json`, print the program's error object on stdout (`{"ok": false, "error": "...", "code": "..."}`) and the readable line on stderr as well, same exit code. Scripts then read the code, and people still see the text | client finding 13; question 7 |
| 17 | Validate input early in the CLI | clig: validate input early and stop before anything harmful [13]; RFC 9413: fail visibly [11] | `--timeout 0`, `log -n 0`, `trace status <category>` accepted; `call state [1]` crashes | Refuse them as typed wrong (exit 4) | client findings 1, 7 |
| 18 | Idempotent calls | Azure: operations idempotent so clients can retry; repeatable-request ids for POSTs [9]; gRPC: retrying non-idempotent calls may not be safe [3] | run.start / run.stop answer at once when already in the state (S24), so they are idempotent; option.set is too; profile.save, command.run and window.press are not | No change; say in Help which calls are safe to repeat after a "may have run" error (row 11) | question 5 (follow-on) |

## Conclusion

The standards agree on four things that our API doesn't do yet:

1. **A stable machine-readable code next to the message** (JSON-RPC, AIP-193, Azure, RFC 9457). Adding a `code` field beside today's `error` text is the change with the widest payoff. It also answers question 4: once scripts read the code, the wording can be tidied freely.
2. **Refuse unknown or misspelled arguments** (Azure, RFC 9413, MCP "validate all tool inputs"). Declaring each call's arguments at `register()` fixes server finding 2 at its shared owner, and feeds `help` and the MCP input schemas (question 1).
3. **A call that timed out may still have run** (gRPC `DEADLINE_EXCEEDED`). Don't start a job after its caller has given up. Say "it may still finish" for one already running. Give "sent but no answer" its own outcome, not exit 2 "isn't running" (question 5, recommendation exit 1 with that text).
4. **Every request gets an answer, and errors are structured for scripts** (LSP; clig). Answer the over-1 MB request. Use one deadline so the program answers before the client's limit. Print the error object on stdout with `--json` (question 7).

For the other questions: question 2, window.open uses command.run's not-found / can't-be-used-now split (gRPC `NOT_FOUND` vs `FAILED_PRECONDITION`); question 3, the program refuses relative paths (LSP absolute URIs) and gremlin-ctl keeps resolving them for the user; question 6, add `gremlin_call` and leave `help` to MCP's own `tools/list`.

Request ids, batches and cancellation (JSON-RPC, LSP) aren't needed while each connection carries one call at a time.

Every row above that changes behaviour is a spec change on page 13 (S8, S9, S10, S11) and needs the user's answer before code (change control).
