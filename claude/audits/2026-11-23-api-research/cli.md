# CLI research: exit codes, output streams, JSON errors, help (gremlin-ctl)

Agent R-CLI, 2026-11-23, 16:07-16:10. Read-only study; no program file changed.
Every claim below comes from a page fetched in this session (URLs listed). Where a
fetch failed or a page did not cover a point, that is said; nothing is filled in
from memory.

Our side was read from: `claude/program-map/13-control-api.md` (S9, S11, S23,
sections 10 and 12), `claude/audits/2026-11-23-api-responses/client.md` (rows 1-33,
findings 1-14), `server.md` (open questions on unknown argument keys and relative
paths), `gremlin_ctl/cli.py` (exit constants lines 24-28, error writes 296-335),
`gremlin_ctl/client.py` (timeouts 106-166).

## Sources

| # | Source | URL | Fetched? |
|---|---|---|---|
| 1 | Command Line Interface Guidelines | https://clig.dev/ | Yes |
| 2 | Bash Reference Manual, 3.7.5 Exit Status (case.edu copy) | https://tiswww.case.edu/php/chet/bash/bashref.html | Yes (the gnu.org copy, https://www.gnu.org/software/bash/manual/html_node/Exit-Status.html, answered 429 / 403 every time) |
| 3 | POSIX Shell Command Language, 2.8 | https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html | Yes (first 100 000 characters) |
| 4 | sysexits(3), FreeBSD | https://man.freebsd.org/cgi/man.cgi?query=sysexits&sektion=3 | Yes |
| 5 | Python argparse | https://docs.python.org/3/library/argparse.html | Yes |
| 6 | Python sys.exit | https://docs.python.org/3/library/sys.html | Yes |
| 7 | GNU Coding Standards, --help | https://www.gnu.org/prep/standards/html_node/_002d_002dhelp.html | Yes (second try) |
| 8 | GNU Coding Standards, --version and Errors | https://www.gnu.org/prep/standards/html_node/_002d_002dversion.html, .../Errors.html | **No** (429) |
| 9 | GitHub CLI exit codes | https://cli.github.com/manual/gh_help_exit-codes | Yes |
| 10 | GitHub CLI formatting (--json) | https://cli.github.com/manual/gh_help_formatting | Yes |
| 11 | Azure CLI README, Exit codes | https://raw.githubusercontent.com/Azure/azure-cli/dev/README.md | Yes |
| 12 | Azure CLI troubleshooting | https://learn.microsoft.com/en-us/cli/azure/use-azure-cli-successfully-troubleshooting | Yes |
| 13 | AWS CLI return codes | https://docs.aws.amazon.com/cli/latest/topic/return-codes.html | Yes (found while searching for Azure's codes) |
| 14 | kubectl reference | https://kubernetes.io/docs/reference/kubectl/ | Yes; it documents `-o json` but no exit codes |
| 15 | docker run (exit status) | https://docs.docker.com/engine/containers/run/ | Yes |
| 16 | Terraform validate -json | https://developer.hashicorp.com/terraform/cli/commands/validate | Yes |
| 17 | oclif --json and error handling | https://oclif.io/docs/json, https://oclif.io/docs/error_handling | Yes; neither says how errors look under --json |
| 18 | 12 Factor CLI Apps (Heroku, jdxcode) | https://medium.com/@jdxcode/12-factor-cli-apps-dd3c227a0e46 | **No** (403) |

## What each source says (paraphrased)

1. **clig.dev.** Zero on success, non-zero on failure, and map the non-zero codes
   to the most important failure modes. Primary output, machine-readable output
   included, goes to stdout; errors and messages go to stderr. Offer `--json`
   where it doesn't hurt usability; human text may change, scripts should use
   `--json`. Show full help for `-h` / `--help`; with no arguments show short help
   with examples; help in the terminal works without a network. Catch expected
   errors and rewrite them for humans, suggest the next step, keep noise low, put
   the most important line last; unexpected errors get debug detail and a way to
   report the bug. Timeouts should be configurable with a default that doesn't hang
   forever; make operations safe to run again after a passing failure. Prefer flags
   to positional arguments. Nothing on relative versus absolute paths. Quote:
   "Map the non-zero exit codes to the most important failure modes."
2. **Bash manual 3.7.5.** 0 is success; 126 found but not executable; 127 not
   found; 128+N for a fatal signal N; all builtins return 2 for incorrect usage
   (bad options, missing arguments).
3. **POSIX 2.8.2.** 127 not found, 126 not executable, above 128 for a signal
   (which signal is implementation-defined). It sets no code for a utility's usage
   error; each utility's page says its own.
4. **sysexits(3).** EX_USAGE 64 (invoked wrongly), EX_DATAERR 65, EX_NOINPUT 66,
   EX_UNAVAILABLE 69 (a needed service is unavailable), EX_SOFTWARE 70,
   EX_TEMPFAIL 75 (temporary, try again later), EX_PROTOCOL 76 (the remote side
   sent an impossible answer), EX_NOPERM 77, EX_CONFIG 78. The page itself says the
   interface is deprecated, kept for compatibility, its use discouraged and not
   portable. Quote: "has been deprecated and is retained only for compatibility."
5. **argparse.** A bad argument list prints a message to stderr and exits 2
   (`error()` prints usage plus `PROG: error: ...` and exits 2). `exit_on_error=False`
   (3.9+) raises `ArgumentError` instead. `print_help` writes to stdout. From 3.14
   `suggest_on_error` offers "maybe you meant" for mistyped string choices and
   subcommands (default True from 3.15); help is coloured by default from 3.14.
6. **sys.exit.** Zero is success; most systems need 0-127. Quote: "Unix programs
   generally use 2 for command line syntax errors".
7. **GNU --help.** Print usage to standard output and exit successfully; ignore the
   other options; don't do the normal work.
9. **gh exit codes.** 0 ok, 1 failed for any reason, 2 cancelled, 4 needs
   authentication; individual commands may add codes.
10. **gh --json.** Plain text by default; `--json` on the commands that support it,
    with `--jq` / `--template`. Says nothing on error format or stream.
11. **Azure CLI.** 0 ok, 1 generic error, 2 parser error (check the command line),
    3 missing resource (for `show` existence checks).
12. **Azure troubleshooting.** Error categories (unrecognised argument, missing
    argument, invalid value, not found...); `--debug` shows the full trace and the
    log file. Much of the page is about quoting differences between Bash,
    PowerShell and cmd.exe; for JSON arguments it recommends an `@<file>` form to
    get past the shell's quoting.
13. **AWS CLI.** 0 ok, 1 (s3 only), 2 parse failure (plus an s3 meaning), 130 Ctrl-C,
    252 bad syntax / unknown parameter, 253 bad environment or configuration,
    254 the service returned an error, 255 catch-all, not to be relied on.
14. **kubectl.** `-o json` / `-o yaml` print the API object; plain text by default.
    The page documents no exit codes and no error format.
15. **docker run.** 125 error in Docker itself (example: an undefined flag), 126 the
    command can't be invoked, 127 not found; anything else is the container's code.
16. **Terraform validate -json.** On stdout a JSON object `{valid, error_count,
    warning_count, diagnostics[{severity, summary, detail}]}`, so errors are JSON
    too; it warns that Terraform can fail before that and print non-JSON, which
    consumers should treat as a generic error.
17. **oclif.** `--json` prints the return value as JSON and suppresses logs. The
    fetched pages don't say how errors look under `--json`.

## Where the sources disagree

- **What 2 means.** Bash builtins, argparse, Python's sys.exit note, Azure CLI and
  AWS CLI use 2 for "typed wrong". gh uses 2 for "cancelled". docker uses 125 for
  its own flag errors. AWS uses both 2 and 252 for syntax. sysexits uses 64.
- **sysexits.** It names the cases we have (64 usage, 69 unavailable, 75 temporary,
  76 protocol) but its own page calls it deprecated and discouraged; none of the
  CLIs fetched (gh, Azure, AWS, docker) uses it.
- **JSON errors.** Terraform puts errors in its `-json` output; gh, kubectl and
  oclif document `--json` for results only and don't say. clig.dev says
  machine-readable output belongs on stdout and errors on stderr, but doesn't
  address errors under `--json`. No consensus found.
- **No common scheme beyond 0 / non-zero.** clig.dev only says to map codes to the
  main failure modes; each tool picks its own small set (gh 0/1/2/4, Azure 0-3).

## Applies to us

| Topic | Sources say | We do (S11, cli.py) | Suggestion | Finding / question |
|---|---|---|---|---|
| Code for "typed wrong" | 2 in Bash builtins, argparse, sys.exit note, Azure, AWS; 64 in sysexits (deprecated); 125 docker | 4 (D-13-USAGE-EXIT); 2 = not running | Either keep 4 (clig.dev only asks for a documented mapping, gh shows tools pick their own) or move usage to 2 and not-running to another number | **Question for the user**: 4 is legitimate but unconventional; the most common usage code among the sources is 2, which we use for "not running". Moving would mean renumbering 2/4 (unreleased, no compatibility needed). |
| Use sysexits numbers (64/69/75)? | Its own page: deprecated, discouraged, not portable; no fetched CLI uses it | Not used | Don't adopt | None (confirms current choice) |
| Avoid shell-reserved codes | 126, 127, 128+N reserved by Bash/POSIX; AWS 130 for Ctrl-C | 0-4 only | Keep below 126 | OK. Ctrl-C during a call was not checked: cli.py has no `KeyboardInterrupt` handling (grep), so a Python traceback is likely; not run |
| Errors to stderr, results to stdout | clig.dev, argparse, GNU --help | Errors on stderr, results on stdout (cli.py 296-335) | - | OK |
| Usage text on a usage error | argparse `error()`: usage + `PROG: error:` to stderr, exit 2 | argparse-caught errors do; hand-checked ones (cli.py:312-314) print only `gremlin-ctl: <text>` | Route the hand-checked errors through `parser.error`-style output so every usage error looks the same | Matches client.md finding 6 (gap vs S11) |
| Help exits 0 on stdout | GNU --help; argparse prints help to stdout | `--help` / `COMMAND --help` exit 0 on stdout | - | OK |
| Help while not running | clig.dev: terminal help works offline; GNU: --help ignores other work and succeeds | `help` exits 0 with a note; `--json help` exits 2 | Make `help` print the offline command list and exit 0 in both forms; the live call list is an extra when the program answers | **Question** (client.md finding 13): sources favour help always working; `--json help` exiting 2 is the odd one out |
| JSON errors under `--json` | Terraform: yes, structured on stdout; gh/kubectl/oclif: not documented; clig.dev: errors to stderr | Plain text on stderr, stdout empty | Option a) keep (clig.dev split, exit code carries the kind); b) Terraform style: `{"ok": false, "error": ..., "code": N}` on stdout (the S9 wire answer already has this shape) | **Question** (client.md finding 13); sources split |
| Stopped answering / closed mid-call | sysexits has 75 temporary and 76 bad protocol answer (deprecated); clig.dev: timeouts with a sane default, make reruns safe; AWS separates "service returned an error" (254) from "could not run" (253) | Both exit 2 "isn't running" | Don't call a silent program "not running"; say "didn't answer within N s" and, for a close mid-call, "the call may have run". On the code: 1 (the call failed) is closest to AWS's split; a new code would be a spec change | **Question** (client.md finding 8): no source sets a code for this; text fix is supported by clig.dev |
| Messages that say what to do | clig.dev: rewrite for humans, suggest the next step, most important last; Azure: categorised errors + `--debug` | Not-running / off / wrong key texts give no next step | Add the next step ("start it, or switch on Options › General › Allow control from other programs"; wrong key: "switch the option off and on") | client.md finding 9 (gap vs S2, low) |
| Tracebacks | clig.dev: only unexpected errors get debug detail | `call state [1]` gives a Python traceback | Refuse non-object JSON as typed wrong | client.md finding 1 (gap vs S11) |
| "Did you mean" | argparse 3.14+ `suggest_on_error` (string choices and subcommands); clig.dev: suggest, don't run | Not checked which Python the exe is built with | If the build is 3.14+, it may already happen for mistyped commands; for unknown call argument keys the server could name the accepted keys | Ties to server.md's unknown-argument-key question; the source supports naming the valid choices |
| JSON on the command line | Azure: shell quoting differs across Bash, PowerShell, cmd.exe; use `@<file>` for JSON | `call NAME JSON` only; Help example breaks in cmd.exe | Fix the Help example (client.md finding 3); optionally accept `@file` for `call` | Optional addition (would extend S23: needs the user) |
| Prefer flags to positionals | clig.dev | `call name args`, `window press T B` are positional | Leave; low value now | None |
| --version | GNU --version page not fetched (429) | No `--version` flag (grep) | - | Not researched (fetch failed); not raised |
| Relative paths | No fetched source covers it | gremlin-ctl resolves against the caller's folder; MCP/raw clients go to the program's folder | - | No source; server.md's question stays a design choice |
| Configurable timeout | clig.dev: configurable, doesn't hang forever | `--timeout` exists; 0 and negatives accepted | Refuse `--timeout <= 0` (exit as typed wrong) | client.md row 5 |

## Conclusion

- Our split of results to stdout and errors to stderr, help on stdout with exit 0,
  staying below the shell-reserved codes 126-128+, and not using sysexits all match
  the sources.
- The one convention we break: among the sources that name a usage code, 2 is the
  most common (Bash builtins, argparse, Python, Azure, AWS), and we use 2 for "not
  running" and 4 for usage. This is a choice, not an error: clig.dev only asks for a
  documented mapping, and gh, docker and AWS each use their own numbers. Since the
  program is unreleased, swapping to usage = 2 is cheap if the user wants the
  convention; that would change S11 and D-13-USAGE-EXIT, so it is the user's call.
- Sources support: help that always works without the program; messages that name
  the next step; no tracebacks for expected errors; a timeout text that doesn't say
  "not running" about a running program.
- Sources are split on JSON errors under `--json` (Terraform yes; others silent;
  clig.dev implies stderr), and none sets a code for a program that stops answering
  mid-call. Both stay open questions for the user.
- Not covered by any fetched source: relative paths. Not fetched: GNU --version and
  error-format pages (429), Bash's gnu.org page (403; read from the case.edu copy),
  12 Factor CLI Apps (403).
