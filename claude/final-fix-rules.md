# Final phase fix round: rules for every agent

Repo: E:\Users\Stacie\Documents\GitHub\Gremlin-Platforms. The full test plan is in `claude/final-test-plan/` (one file per spec page) and the findings in `claude/final-test-plan/_findings.md`. The user's answers are the newest rows at the end of `claude/decisions.md` (2026-10-07): follow them exactly.

## Ownership (strict)
- 6 agents work at once. Edit ONLY the files your prompt lists, plus a new test file `test/unit/test_fix_<your id>.py` if you need one. Never edit test/conftest.py, `test/unit/test_final_*.py` (the lead removes their xfail marks after you), or `claude/` files unless your prompt says so.
- A change needed in someone else's file: describe it in your report ("Requests").
- Never run git add/commit/checkout/stash/reset.

## Fix rules
- Fix at the owner, the smallest correct change; follow the spec page and decisions. Each fix gets a test that fails on the old code (the matching `test_final_*` strict xfail counts: run it with `--runxfail` to see it pass after your fix, or add your own test).
- Program rules: threads only via `gremlin.threads`, bounded waits, `gremlin.clock` for timed loops (a test that steps the clock steps only its own loop), layer rule hardware → input module → wiring → output module → driver. On-screen text follows `claude/glossary.md`.

## Live output (user rule)
Pipe every shell command through the log tool, from the repo root:
`PYTHONUNBUFFERED=1 <command> 2>&1 | C:/Users/Stacie/AppData/Local/pypoetry/Cache/virtualenvs/joystickgremlin-4UY8FelE-py3.13/Scripts/python.exe tools/agent_log.py <your id>` (PYTHONUNBUFFERED=1 makes lines show up live; use pytest -v, not -q, so each test is its own line)

## Testing and safety
- Python: C:/Users/Stacie/AppData/Local/pypoetry/Cache/virtualenvs/joystickgremlin-4UY8FelE-py3.13/Scripts/python.exe
- Run only the test files for your area (never the full suite). Lint: `python tools/pyright_baseline.py` → no new errors in your files.
- Off-screen only; never touch the user's data (C:\Users\Stacie\Gremlin Platforms); no keys/mouse to the PC; never change HidHide, vJoy or ViGEm state; no network. Leave nothing behind in tests.

## Report (short)
Fixed (id, what, spec ref) · not done and why · files · tests run (which fail on old code) · requests · new on-screen texts.
