# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

> For full coding standards, style rules, and patterns, see [AGENTS.md](../AGENTS.md).

Run linting and type checks before considering any task complete.

## Change control (required, user 2026-10-06)

The program's intended behaviour is the approved spec in `claude/program-map/`
(one page per subsystem: section 8 statements plus the decisions recorded in
section 12; where they disagree, the decision wins). The plan is
`claude/system-maps.md` ("The plan", "How we work").

1. Before changing behaviour, read the spec page(s) for the subsystem.
2. If a change would add, change, remove or contradict a spec statement or
   decision, stop and tell the user first; update the spec with their answer,
   then code. Never change the spec silently.
3. Where today's code differs from the spec, that is a gap to fix (start with
   a failing test), not a reason to change the spec.
4. Follow "How we work" in `claude/system-maps.md`: trace end to end first, fix
   at the shared owner, tests that drive the real path and fail on the old
   code, independent re-trace, build in a batch then test.
5. Every commit that touches program code (`gremlin/`, `qml/`,
   `action_plugins/`, `dill/`, `vigem/`, `joystick_gremlin.py`) has a line
   `Spec: <page> <S/Q refs>` naming what it implements, or
   `Spec: none (no behaviour change)`. `test/unit/test_spec_line.py` fails
   otherwise.
6. Keep the whole program map current (user, 2026-10-09), not only section 8:
   every batch updates the pages it touches (section 2 files, 3 owns, 4 entry
   points, 5 talks to, 10 known gaps, 11 tests, the README counts) before its
   commit; each agent adds its own entries. `test/unit/test_program_map_covers_files.py`
   fails when a program file isn't on the map. Before every release, do a full
   map check (counts, gaps, anything stale) as part of the release steps.
7. Pass this section on to any agent you start.

## Working standard (required, user 2026-10-07)

Every piece of work, not only big batches:

1. **Status line.** Start every message to the user with the one-line status,
   e.g. `[History deltas ▓▓░░░░░░░░ 20% · H1 + H2 building · next: screenshots]`.
2. **Progress page.** Keep https://claude.ai/artifact/NQJw6xzumYopoJn5NXJxqR
   current with the Artifact tool (its data is the ArtifactData document
   `progress/now`): what is happening now, what is next, the steps of the
   current work, every agent and its state, the last test result and a short
   log. Update it at every step (agents started/finished, test runs, commits,
   pushes, CI). Show results the user should look at (screenshots, reports)
   as artifacts too.
3. **Live output.** Every agent pipes every shell command through
   `tools/agent_log.py <AGENT>`, with `PYTHONUNBUFFERED=1` in front and
   pytest `-v`:
   `PYTHONUNBUFFERED=1 <command> 2>&1 | python tools/agent_log.py <AGENT>`.
   Output goes to `.agent-logs/<AGENT>.log` and, prefixed with the agent's
   name, to `.agent-logs/all.log` (not in git). The lead's own runs use the
   name `lead`. **Whenever agents are spawned (user 2026-10-07), open a live
   log view for the user straight away** — a separate PowerShell window
   (`Start-Process powershell -ArgumentList '-NoLogo','-NoProfile','-NoExit',
   '-Command',"Get-Content '<repo>\.agent-logs\all.log' -Wait -Tail 80"`;
   the Terminal panel's tabs don't start here) — unless one is already open,
   and give the watch commands with full paths:
   `Get-Content "<repo>\.agent-logs\<AGENT>.log" -Wait -Tail 50` per agent and
   `Get-Content "<repo>\.agent-logs\all.log" -Wait -Tail 80` for all of them.
4. **Agents: parallel by default (user 2026-10-07).** Before starting any
   task, and again whenever new work appears mid-task (several CI failures,
   several findings), split it into independent pieces and give each its own
   agent, running at the same time, whenever that finishes sooner. Contract
   first, one owner per file; the lead keeps shared files and routes
   cross-file needs. Use one agent only when the pieces depend on each other
   or share the same files, and say why in one line. Don't hand a second,
   unrelated problem to an agent busy with the first: start another agent.
   Stay within about 8–10 agents at once on the user's PC. Put rules 2–3 and
   5 in every agent's prompt. This holds for small jobs too (user
   2026-10-09): always divide the work when feasible to cut the time a
   change takes, with tight time budgets; don't divide it when doing so
   would certainly cause errors.
5. **Test runs (agents; user 2026-10-07).**
   - The full run is `python test/run_tests.py --random-order` (6 parts, ~3
     min): once, at the end, after the targeted tests pass.
   - While working, run only the tests for the files you changed.
   - To reproduce a CI failure, run that part once with CI's seed
     (`--seed N --parts 3`); never run a whole part in one pytest process.
   - No more proof runs once a fix is shown (the test failed on the old code
     and passes on the new): stop and go to the final full run.
   - Before any command expected to take over 3 min, log
     `AGENT: <step>, expect ~N min, why`; anything over 5 min other than the
     one full run needs the lead's OK first.
6. **Overseeing agents (the lead; user 2026-10-07).**
   - Give every agent a time budget in its brief ("about 20 min; check in
     if you need more").
   - Watch commands, not only results: the lead's monitor reports each new
     command an agent starts with its expected time, and alerts on any single
     test command running over 6 min.
   - When an agent's fix is proven, check in: stop extra proof runs, move it
     to the final full run and its report.
   - Tell the user about any agent step over 5 min when it starts, not after.
