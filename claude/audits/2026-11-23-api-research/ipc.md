# Control API transport and protocol: research against published sources (agent R-IPC, 2026-11-23)

Read-only study. Started 16:07, ended 16:10. Every statement about a source below comes
from a page fetched in this session (URL given). Statements about our code come from
`gremlin/control_api.py`, `gremlin/ui/control_windows.py`, `gremlin/threads.py`
(`main_call_wait`), `gremlin_ctl/client.py`, `claude/program-map/13-control-api.md` and
`claude/audits/2026-11-23-api-responses/server.md` (AUD-SRV). Where something could not be
confirmed from a fetched page it is marked **unverified**.

## Sources

| # | Source | URL | Fetch |
|---|---|---|---|
| 1 | Microsoft: Named Pipe Security and Access Rights | https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-security-and-access-rights | ok |
| 2 | Microsoft: CreateNamedPipeA | https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-createnamedpipea | ok |
| 3 | Microsoft: Named Pipe Client | https://learn.microsoft.com/en-us/windows/win32/ipc/named-pipe-client | ok |
| 4 | Microsoft: CreateFileW (SQOS flags) | https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew | ok |
| 5 | Microsoft: Impersonation Levels | https://learn.microsoft.com/en-us/windows/win32/secauthz/impersonation-levels | ok |
| 6 | Microsoft: GetNamedPipeClientProcessId / GetNamedPipeServerProcessId | https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeclientprocessid , https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getnamedpipeserverprocessid | ok |
| 7 | Python docs: multiprocessing (Connection, Listeners and Clients, Authentication keys) | https://docs.python.org/3/library/multiprocessing.html | ok (two reads, offset 0 and 100000) |
| 8 | CPython source: Lib/multiprocessing/connection.py (main) | https://raw.githubusercontent.com/python/cpython/main/Lib/multiprocessing/connection.py | ok |
| 9 | Python docs: os (chmod on Windows) and Microsoft CRT `_open` (pmode) | https://docs.python.org/3/library/os.html , https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/open-wopen | ok |
| 10 | Python docs: concurrent.futures (Future.cancel / result timeout) | https://docs.python.org/3/library/concurrent.futures.html | ok |
| 11 | obs-websocket 5 protocol | https://raw.githubusercontent.com/obsproject/obs-websocket/master/docs/generated/protocol.md | ok (the github.com/blob page gave HTTP 503; the raw file was read, first 100 000 characters) |
| 12 | JSON-RPC 2.0 specification | https://www.jsonrpc.org/specification | ok |
| 13 | Language Server Protocol 3.17 (VS Code's protocol) | https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/ | ok (first 100 000 characters) |
| 14 | Discord RPC | https://docs.discord.com/developers/topics/rpc | ok (discord.com/developers/docs/topics/rpc redirected here) |
| 15 | Microsoft UI Automation: AutomationId | https://learn.microsoft.com/en-us/dotnet/api/system.windows.automation.automationelement.automationelementinformation.automationid | ok |
| 16 | Microsoft UI Automation: Invoke control pattern | https://learn.microsoft.com/en-us/windows/win32/winauto/uiauto-implementinginvoke | ok |
| 17 | Klocwork checker SV.PIPE.CONST (pipe hijacking) | https://help.klocwork.com/2024/en-us/reference/sv.pipe.const.htm | ok |
| - | Tenable: PsExec local privilege escalation (pipe squatting) | https://medium.com/tenable-techblog/psexec-local-privilege-escalation-2e8069adc9c8 | **failed (HTTP 403)**; nothing from it is used |
| - | Web search "named pipe squatting FILE_FLAG_FIRST_PIPE_INSTANCE" | (search result snippets only) | used only to find 17; snippets are not cited as facts |

## Key points per source

**1. Named pipe security.** A pipe created with a NULL security descriptor gets a default
one: full control for LocalSystem, administrators and the creator owner, and read access
for Everyone and the anonymous account. `FILE_APPEND_DATA` and `FILE_CREATE_PIPE_INSTANCE`
share one value, so `FILE_GENERIC_WRITE` also lets a holder create a pipe instance. To keep
out remote users and other terminal sessions, put the logon SID in the pipe's DACL.

**2. CreateNamedPipe.** `PIPE_ACCEPT_REMOTE_CLIENTS` (value 0, the default) accepts remote
clients and checks them against the security descriptor; `PIPE_REJECT_REMOTE_CLIENTS`
"automatically rejected" remote connections. With `FILE_FLAG_FIRST_PIPE_INSTANCE`, creating
a second instance of a name that already exists fails with `ERROR_ACCESS_DENIED`. Message
pipes report `ERROR_MORE_DATA` when a message isn't read completely.

**3. Named pipe client.** A client opens the pipe with CreateFile, waits with WaitNamedPipe
on `ERROR_PIPE_BUSY`, and must switch to message-read mode itself.

**4, 5. Impersonation.** A client can limit what the server may do with its identity by
passing `SECURITY_SQOS_PRESENT` plus a level (Anonymous, Identification, Impersonation,
Delegation) to CreateFile. SecurityImpersonation is the default for named pipe servers; at
that level the server can act in the client's security context on the local system;
at SecurityIdentification it can read the client's identity but can't impersonate it.

**6. Process ids.** `GetNamedPipeClientProcessId` gives the client's process id for a pipe
instance; `GetNamedPipeServerProcessId` gives the server's. Both pages say the handle "must
be created by the CreateNamedPipe function"; whether the server-id call works from the
client's CreateFile handle is **not stated** on the page (unverified).

**7. Python multiprocessing docs.** `authkey` drives an HMAC challenge in both directions;
the key itself is never sent. Keys can come from `os.urandom()`. `Connection.recv()`
unpickles and is a risk unless the peer is trusted; `send_bytes`/`recv_bytes` are the raw
alternatives. If a message is longer than `maxlength`, `recv_bytes` raises OSError and "the
connection will no longer be readable". The docs treat all processes of the same user as
trusted and say isolation from them must come from the operating system.

**8. CPython connection.py.** `PipeListener` creates its first instance with
`FILE_FLAG_FIRST_PIPE_INSTANCE`, message mode, unlimited instances, 64 KiB buffers, and a
NULL security descriptor (so the default DACL of source 1); it does **not** pass
`PIPE_REJECT_REMOTE_CLIENTS`. `PipeClient` calls CreateFile with no SQOS flags. The
handshake uses HMAC-SHA256 by default (`{sha256}` prefix, 40 random bytes, checked with
`hmac.compare_digest`), handshake messages capped at 256 bytes. An oversize message raises
`OSError("bad message length")` after peeking how much is left.

**9. File mode on Windows.** `os.chmod` on Windows only sets the read-only flag; the CRT
`_open` pmode only knows `_S_IREAD`/`_S_IWRITE` and notes all files are readable. So the
`0o600` in `_write_endpoint` does not limit who can read endpoint.json; its protection is
the folder's ACL (the default ACL of `%USERPROFILE%` was not checked in a fetched source:
unverified).

**10. concurrent.futures.** `Future.cancel()` succeeds only while the call has not started;
a running or finished call can't be cancelled. `result(timeout)` raises TimeoutError; the
page does not say the work stops (it does not).

**11. obs-websocket 5.** JSON messages `{"op", "d"}`; Hello → Identify → Identified, with
SHA-256 salt/challenge authentication and `rpcVersion` negotiation (close code 4010 when
unsupported). Each Request carries a client `requestId` echoed in the response with
`requestType`. `requestStatus` = `result` (bool), `code`, optional `comment`. Codes are
grouped: 100 Success; 2xx request-level (204 UnknownRequestType, 207 NotReady "retry after
a delay"); 3xx missing fields (300 MissingRequestField); 4xx bad fields (400
InvalidRequestField, 401 InvalidRequestFieldType, 402 RequestFieldOutOfRange, 403
RequestFieldEmpty, 404 TooManyRequestFields); 5xx state (OutputRunning...); 6xx resources
(600 ResourceNotFound, 604 InvalidResourceState); 7xx action failures (702
RequestProcessingFailed, where a comment is required; 703 CannotAct). RequestBatch has
`haltOnFailure` and `executionType`; "Requests are processed serially (in order) by the
server." Events are opt-in by a bitmask, and high-volume events must be subscribed to
explicitly.

**12. JSON-RPC 2.0.** The server replies with the same `id`. An error is `{code, message,
data?}` with fixed codes: -32700 parse error, -32600 invalid request, -32601 method not
found, -32602 invalid params, -32603 internal error, -32000..-32099 server-defined.

**13. LSP 3.17.** `$/cancelRequest` names a request id; a cancelled request must still get
an answer ("It can not be left open"), advised with code RequestCancelled (-32800); a server
may cancel its own requests with ServerCancelled (-32802). Requests may run in parallel
only when reordering can't change results. Each message carries a byte `Content-Length`.

**14. Discord RPC.** Local IPC (a named pipe on Windows) is the preferred transport; the
old localhost WebSocket checks the Origin header. Each command has a `nonce` echoed in its
response; events come only after SUBSCRIBE and carry no nonce. Errors come as an ERROR
event with `code` and `message`.

**15. UI Automation AutomationId.** Unique among siblings, not across the desktop; the same
in every instance "regardless of the local language"; recommended for test scripts, not
guaranteed stable across releases.

**16. UI Automation Invoke.** Invoke "must return immediately without blocking", especially
when it opens a modal dialog; the Invoked event should come after the action completes when
practical. An element can vanish from the tree right after it is invoked.

**17. Klocwork SV.PIPE.CONST.** Flags CreateNamedPipe without `FILE_FLAG_FIRST_PIPE_INSTANCE`
as "potential pipe hijacking"; the fix is that flag.

## Applies to us

| Topic | Source says | We do | Suggestion | Finding |
|---|---|---|---|---|
| Pipe squatting of our name | First instance should use FILE_FLAG_FIRST_PIPE_INSTANCE (2, 17) | Python's PipeListener sets it on the first instance (8); the name has 16 random hex characters, new each start | none | OK |
| Remote clients | PIPE_REJECT_REMOTE_CLIENTS rejects them; default accepts (2); logon SID in the DACL keeps out remote and other-session users (1) | Not set (Python's listener has no option for it, 8); default DACL gives Everyone read (1). Remote callers still need the key (HMAC, 7) and write access, which the default DACL gives only to owner/admins/SYSTEM (1) | Defence in depth only: a custom listener (ctypes/_winapi `CreateNamedPipe` with `PIPE_REJECT_REMOTE_CLIENTS` and an owner-only DACL). Costs owning our own pipe code instead of the stdlib's | Low risk gap (no known exploit path; the key gates every call) |
| Client being impersonated by a fake server | Clients can open with SECURITY_SQOS_PRESENT + SECURITY_IDENTIFICATION; default is impersonation (4, 5) | gremlin_ctl uses Python's PipeClient, which passes no SQOS flags (8). A process that created a pipe with our name first could impersonate the client at connect, before the key check fails. It would have to read endpoint.json (same user, 7, 9) | Optional: a client that opens the pipe with SQOS Identification; or accept, because the docs treat same-user processes as trusted (7) | Low risk; accepted by Python's own model |
| Mutual authentication | HMAC both ways, key not sent (7, 8) | `_handshake` runs deliver + answer challenge, bounded 5 s; Client(authkey) does the other half | none | OK |
| Pickle | recv() unpickles; use recv_bytes for untrusted peers (7) | Only send_bytes/recv_bytes with JSON | none | OK |
| endpoint.json protection | Windows mode bits only set read-only (9) | `os.open(..., 0o600)`: has no access effect on Windows; the file relies on the user-profile folder ACL (unverified) | Say so in the code comment and spec S12 (the mode doesn't protect it); optional explicit owner-only ACL | Documentation gap |
| Request ids | Every request id echoed (11 requestId, 12 id, 14 nonce) | None: one call per round trip on one connection, so answers can't be mixed up | Not needed while one call at a time per connection; add `id` only if pipelining or events arrive | OK for now |
| Error codes | Machine-readable codes grouped by kind (11, 12) | `{"ok": false, "error": "<plain text>"}` only; clients (CLI exit codes, MCP) can't tell "busy, retry" from "bad argument" from "not found" without matching text | Add a short `code` beside the text, e.g. `busy`, `timeout`, `unknown_call`, `bad_args`, `not_found`, `not_ready`, `refused`, `failed` (OBS groups 2xx-7xx are a model). Spec change (S8/S9) | Gap: improvement |
| Unknown / missing argument keys | OBS has MissingRequestField, InvalidRequestFieldType, TooManyRequestFields (11); JSON-RPC invalid params (12) | Unknown keys ignored; missing `text` clears a field (AUD-SRV finding 2) | Declare argument keys in `register`; refuse unknown and missing ones. Matches OBS 300/400/404 | Confirms AUD-SRV 2 |
| Not ready | OBS 207 NotReady: retry after a delay (11) | "The program's window isn't ready yet." (text only) | Same text plus `code: not_ready` | Fits the code list above |
| Timed-out main-thread call runs later | A queued job can be cancelled only before it starts (10); LSP: a cancelled request still gets a definite answer (13) | `main_call_wait` leaves the job queued; it may run after the client was told it failed (AUD-SRV 3) | In `main_call_wait`: a flag set on timeout, checked at job start, so a job that hasn't started is skipped (the futures rule). A job already running can't be stopped: answer "took over N s; it may still finish" for that case only | Confirms AUD-SRV 3, with a precise rule |
| Busy wait plus call limit | (no source on this exact point) LSP: requests in parallel only when order can't change results (13); OBS processes serially (11) | One call at a time (`_busy`), busy wait up to the limit, then the call up to the limit: up to 2x (AUD-SRV 4) | Keep one at a time (matches OBS serial processing and our main-thread design); use one deadline for wait + call, or a short busy wait answering `busy` | Confirms AUD-SRV 4 |
| Request over 1 MB | recv_bytes over maxlength raises OSError and the connection can't be read again (7, 8) | `_serve` catches OSError and closes with no answer (AUD-SRV 14) | Catch that case, send `{"ok": false, "code": "too_large", "error": "The request is over 1 MB."}` (writing still possible; only reading is lost, 7), log it, then close | Confirms AUD-SRV 14 |
| Answer size | LSP frames carry Content-Length (13) | No cap on answers; window.read or log lines could be large; the stdlib frames each message (8) | Fine; keep `log` capped at 2000 lines | OK |
| Events / subscriptions | OBS and Discord push events only after an explicit subscribe; high-volume ones separate (11, 14) | None; clients poll `state` | Not needed for today's uses (scripts, Claude). If wanted later (Run started/stopped, profile changed), follow the opt-in model and keep high-volume input events out | No gap |
| Version handshake | OBS negotiates rpcVersion and closes on mismatch (11) | `hello` returns version; endpoint.json has version; client raises VersionMismatch | none | OK |
| Batch | OBS RequestBatch with haltOnFailure (11); JSON-RPC arrays (12) | None | Not needed | No gap |
| Element names | AutomationId: unique among siblings, language-independent, for scripts (15) | QML `objectName`; ambiguous names answer "2 buttons called x... name one by its objectName" | Keep objectName as the stable id; a guard that names are unique per window would match "unique among siblings" | OK; optional guard |
| Press returns before the action | Invoke returns at once, especially before modal dialogs (16) | window.press is queued; answer `{"pressed"}` at once (S6 "by design") | Matches UIA; say in help that the answer means "sent", and that window.read shows the result | OK |
| Did the action take effect | Invoked event after the action completes when practical (16) | window.close answers `{"closed"}` even when the window refused (AUD-SRV 1); window.type forces text past validators (AUD-SRV 10) | Check after the action: window still visible means an error ("didn't close: it asks about unsaved changes"); field text not as typed means an error | Confirms AUD-SRV 1 and 10 |
| Relative paths | (no fetched source on this) | Resolved against the program's working folder (AUD-SRV 15) | Refuse relative paths (spec decision) | No research input |

## Conclusion

The transport is sound against the fetched guidance: the first pipe instance blocks name
squatting, the name and key are random per start, the HMAC-SHA256 check runs both ways
without sending the key, and only raw bytes with JSON are exchanged, so the pickle warning
doesn't apply. The remaining transport gaps are defence in depth, not open doors: remote
clients are not rejected by flag, the client doesn't limit impersonation, and the `0o600`
on endpoint.json does nothing on Windows. Python's docs treat same-user processes as
trusted, which is the model we already rely on.

The protocol lessons from OBS, JSON-RPC, LSP and Discord are about answers, not transport:

1. Add a short machine-readable `code` next to every error text (busy, timeout,
   not_ready, unknown_call, bad_args, not_found, refused, too_large, failed), as OBS's
   status codes and JSON-RPC's error codes do. Spec change (S8/S9).
2. Declare each call's argument keys and refuse missing or unknown ones (OBS 300/400/404).
3. Never leave a timed-out request with an ambiguous outcome: skip queued main-thread jobs
   that haven't started (the `Future.cancel` rule), and say "may still finish" only for one
   already running (LSP's "can not be left open").
4. Answer a too-large request with an error before closing; the connection can still be
   written to.
5. Report whether a UI action took effect (window.close, window.type), as UI Automation's
   Invoked-after-completion convention suggests; keep press as "sent".
6. Request ids, batches and events are not needed while there is one call at a time per
   connection and clients poll; if events are ever added, make them opt-in like OBS and
   Discord.
