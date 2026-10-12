# Common brief, BG-COMPOSITE batch (lead, 2026-10-11 22:00)
1. Read scratchpad/agent_rules.md, bgpic/contract.md, bgpic/split.md (your row) and bgpic/spec_draft.md.
2. User approved (2026-10-11): 1a (save a picture of the whole visible background whenever it changes;
   every "device's photo" place shows it), 100 % export = the background picture with the most detail
   ("1.a"), and "put an agent on the task". The lead's previous batch is committed (3515b8cd), so
   wave 1 and wave 2 run together now.
3. Write code and tests. You MAY run the tests for YOUR files only (pytest -v, off-screen, temp
   USERPROFILE, fake hardware). No full run, no commit. Show each new test fails on the old code
   (a scratch copy via `git show HEAD:<file>`, never git checkout/stash) and passes on the new.
4. Edit ONLY your files. Need a change elsewhere (joystick_gremlin.py, Main.qml,
   DialogDeviceMappingEditor.qml are the lead's): put the exact change in your report.
5. Pipe every shell command: PYTHONUNBUFFERED=1 <cmd> 2>&1 | python tools/agent_log.py <AGENT>
6. Spec refs in comments as "07 S157" etc. (A-DOCS assigns: S157 the device photo file; S83 changed).
   Glossary: on-screen words from claude/glossary.md; US spelling (center, color).
7. Estimate 3-8 min (timings.md: agent fix/feature); limit 20 min, check in if more.
8. Final report: start/end clock, files, what each part does (file:line), tests (failed-on-old /
   passes-on-new), NOT VERIFIED, map lines for the pages you touch (sections 2/3/4/5/10/11),
   anything you need from others, and that no process of yours is running.
