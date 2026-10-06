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
6. Pass this section on to any agent you start.
