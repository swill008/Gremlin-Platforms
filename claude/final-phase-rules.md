# Final phase rules for every agent (one-time catch-up)

Repo: E:\Users\Stacie\Documents\GitHub\Gremlin-Platforms (branch Gremlin-Platforms). PySide6/QML joystick mapper.
Batches 1–3 are done (d68f4d88, 31861922, ae635492). This phase builds the **full test plan** and writes the **missing tests**, so the code base has a checked baseline before the first push.

Read first: `claude/todo.md` ("ONE-TIME CATCH-UP"), your spec page in `claude/program-map/` (section 8 statements + section 12 decisions; decisions win; `claude/decisions.md` has later decisions), the batch plans in `claude/catchup-test-plan.md`, `AGENTS.md`, `.claude/CLAUDE.md`.

## Your job (one spec page per agent)
1. **Plan.** For every section 8 statement (S…, and the RB/Q decisions that state behaviour) on your page, find what checks it: an existing test (search `test/` by the S/Q ref, the GL id, names and behaviour), or a hands-on check. Write `claude/final-test-plan/<page>.md` with one table:
   `| Ref | Statement (short) | Check | Status |` — Status is `covered` (name the test: file::test), `hands-on` (say exactly what to do and what to see), `new` (you wrote the test), or `gap` (can't be tested automatically and isn't hands-on, with why). Add the batch hands-on checks for your page from `claude/catchup-test-plan.md`.
2. **Tests.** For each statement with no check that can be tested off-screen, write a test in your own new file `test/unit/test_final_<page>.py` (one file; split into `_a/_b` only if it gets very long). Test the real path (models, slots, the owner modules), not source text. Each new test must pass on the current code. If a test fails because the program is wrong (code differs from the spec), do NOT change program code: mark the test `@pytest.mark.xfail(strict=True, reason="FINAL-<page>-<n>: <what is wrong>")` and list it under "Bugs found" in your report. The lead routes the fix.
3. Don't change existing tests or program files. Only your plan file and your test file(s).

## Live output (user rule)
Pipe every shell command through the log tool, from the repo root:
`PYTHONUNBUFFERED=1 <command> 2>&1 | C:/Users/Stacie/AppData/Local/pypoetry/Cache/virtualenvs/joystickgremlin-4UY8FelE-py3.13/Scripts/python.exe tools/agent_log.py <your id>` (PYTHONUNBUFFERED=1 makes lines show up live; use pytest -v, not -q, so each test is its own line)

## Testing and safety
- Python: C:/Users/Stacie/AppData/Local/pypoetry/Cache/virtualenvs/joystickgremlin-4UY8FelE-py3.13/Scripts/python.exe
- Run only your test file and the files you need to check coverage, never the full suite (9 agents share the PC).
- New tests follow the program thread rules: no fixed sleeps; bounded waits on conditions; time via `gremlin.clock` where a test steps it, and only for its own loop (the integration fake clock trap, see claude/todo.md and `test/integration/test_e2e_profile_simple.py::patched_time`). Leave nothing behind: tmp folders, settings put back (monkeypatch), no threads left running, no files in the real modules/profile folders.
- Off-screen only (QT_QPA_PLATFORM=offscreen, temp USERPROFILE, GREMLIN_OFFLINE=1, QT_QPA_FONTDIR=C:/Windows/Fonts); never touch the user's data (C:\Users\Stacie\Gremlin Platforms); never send keys/mouse to the PC; never change HidHide, vJoy or ViGEm state (no integration tests; fakes only); no network.
- Lint: `python tools/pyright_baseline.py` must show no new errors in your test file.
- Never run git add/commit/checkout/stash/reset. The lead commits.

## Final report (short)
1. Counts: statements on the page; covered / new / hands-on / gap.
2. Bugs found (xfail ids, what's wrong, spec ref, likely owner file).
3. Files written.
4. Test results.
5. Anything unclear in the spec (questions for the user).
