# Click zone + grid box (lead, 2026-10-11 23:05) — user: "go ahead and code it"
Decisions (user, 2026-10-11): (1) the click zone is the ENTIRE viewable area of the Device Mapping Editor
view at every zoom and pan; (2) the grid is drawn over the map's box (VkbRigEditor item) scaled 1.2x about
its centre (so at the lowest zoom, 50 % = zoom 0.667, it fills the view minus 10 % each side), NOT clipped
to the page, with a border line on its edge (visual only; clicks work beyond it); (3) NO page outline.
Evidence: user's trace 22:49: view (270,42 1569x1307), editor/pointerArea/grid (509,243 1046x871) at zoom
0.667; right-clicks outside that box hit _viewport (VkbRigFace.qml:230: WheelHandler + _midPan DragHandler)
and nobody took them.
Rules: read scratchpad/agent_rules.md. Edit only your files. Run only your tests (pytest -v, off-screen,
temp USERPROFILE, fake hardware; pipe through tools/agent_log.py <AGENT>). No full run, no commit.
Show each new test fails on the old code (git show HEAD:<file> into a scratch copy; never checkout/stash)
and passes on the new. Grid and its border never print or export (S87). The temporary click trace
(gremlin/ui/click_trace.py, OT-5) must keep working. Estimate 3-8 min (timings.md: agent fix); limit 15.
Report start/end clock, files/lines, tests, not verified, map lines, no process left running.
