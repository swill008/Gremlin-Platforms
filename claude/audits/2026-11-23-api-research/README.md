# API research and reassessment (2026-11-23)

The user asked to research published API practice before answering the open
questions from claude/audits/2026-11-23-api-responses/ ("do not guess, do
not use your memory"). Four agents read primary sources this session; every
claim in their reports cites a fetched URL.

- protocol.md (R-RPC): message and error standards.
- cli.md (R-CLI): command-line conventions and exit codes.
- mcp.md (R-MCP): the MCP spec and Anthropic's tool guidance.
- ipc.md (R-IPC): local IPC security and desktop control protocols.

## What the research confirms in the audit's fix list

- A timed-out main-thread call must not run later (gRPC deadlines;
  concurrent.futures can cancel only before start; LSP: every request gets
  an answer).
- One deadline for the busy wait and the call (OBS handles requests in
  order; S9).
- A request over 1 MB gets an error answer (LSP; multiprocessing docs).
- window.close checks the window is gone; window.type checks the text was
  kept (Windows UI Automation: an action returns before its effect).
- Error messages say what to do; no tracebacks for expected errors
  (clig.dev; Anthropic tool-call guidance).
- help works while the program isn't running (clig.dev; GNU --help).
- The transport has no open hole: CPython sets FILE_FLAG_FIRST_PIPE_INSTANCE;
  the HMAC key check runs both ways; messages are JSON, not pickle.

## New from the research

- A machine-readable error code beside the text (JSON-RPC, AIP-193,
  RFC 9457, Microsoft REST guidelines, OBS).
- Unknown argument names refused, declared once per call (RFC 9413,
  Microsoft guidelines, MCP spec "MUST validate", OBS). Confirmed on MCP SDK
  2.3 that misspelled arguments are dropped today.
- Usage exit code: 2 is the convention (Bash builtins, argparse, Azure CLI,
  AWS CLI); 4 is allowed (clig.dev asks only for distinct codes; gh and
  docker choose their own). sysexits is deprecated (FreeBSD sysexits(3)).
- MCP: no generic call or help tool (Anthropic article, Claude API docs;
  tools/list is the help); tool annotations; schema limits; longer
  descriptions; screenshot returned as an image (SDK Image).
- Optional transport layers: PIPE_REJECT_REMOTE_CLIENTS, the client's
  impersonation level; endpoint.json mode 0o600 has no effect on Windows.

## Questions put to the user

In the chat on 2026-11-23 (16:12), each with its source; the answers go
into claude/program-map/13-control-api.md.
