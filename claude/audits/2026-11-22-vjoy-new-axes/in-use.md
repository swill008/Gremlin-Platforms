# What happens when another program holds a vJoy device (INUSE scout, 2026-11-22)

Read-only code trace; nothing run, vJoy not loaded. Everything below is "verified from code" unless marked UNVERIFIED (no live read of a real BUSY device).
vJoy status values: vjoy/vjoy_interface.py:18 `Bust = 2` "owned by another application" (the driver's BUSY); OWN = owned by the caller.

## 1. Start-up / discovery: listed, not marked, not hidden
- `gremlin/modules/output.py:445-451` `vjoy_ids()` lists devices 1-16 where `vjoy.device_exists` (vjoy/vjoy.py:75-88) is true: any status except MISSING/UNKNOWN. A BUSY device is listed like a free one. Nothing hides it; no owner name or PID is ever looked up (GetOwnerPid is used only to compare with our own PID: vjoy.py:71, 500, 549, 569).
- The one marker is `vjoy_in_use_elsewhere` (output.py:494-501, wraps `held_by_another_program`, vjoy.py:67-72: status Bust and owner pid != ours). Errors give False.

## 2. At Run
- `CodeRunner._start` -> `open_claimed_vjoy()` (output.py:1098-1120, spec 06 S106) opens each vJoy a module claims; also opened lazily on a write (`_open_vjoy`, output.py:~290-345).
- `VJoy.__init__` (vjoy.py:476-520): status != Free: if owner is us -> VJoyConcurrencyError (retried); if Bust -> debug log only + `VJoyBusyError("vJoy N is in use by another program")`; other status -> VJoyError, logged error. AcquireVJD is never called on a BUSY device. `VJoyProxy.__getitem__` re-raises Busy (vjoy.py:907).
- `_open_vjoy` (output.py:318-338) on Busy: stamps `_vjoy_failed_at` (retry every `_VJOY_RETRY` = 3.0 s, output.py:49, 313); syslog warning once per Run (`_log_once`, key ("vjoy-open", vid)): "vJoy N is in use by another program. Its outputs won't move until that program lets it go."; and once per Run per device (`_told_busy`) `signal.display_error("vJoy N is in use by another program.", "Its outputs won't move until that program lets it go.")` (an error box/toast, not History). Writes are dropped silently after that (returns None). When the other program lets go, the next retry opens it and logs "vJoy N opened" (output.py:339-343). `clear_blocked_log` (output.py:265-275) resets all of it each Run.
- Mid-Run loss: `VJoy.ensure_ownership` (vjoy.py:536-560) reacquires if the owner pid isn't ours; if AcquireVJD fails it raises VJoyError "Failed to re-acquire" (logged error). `vjoy_lost()` (output.py:655-665) exists but nothing calls it except tests (grep: only `vjoy_held` is used, live_input.py:284). UNVERIFIED how the driver behaves when a second feeder acquires a device we hold (vJoy normally refuses a second AcquireVJD).
- User sees: error message once per Run + warning in the system log; no History line (consistent with the "History is configuration only" rule); no owner name.

## 3. UI
- Only the Home card: `_card_status` (gremlin/ui/module_model.py:836-847) returns "In use by another program" for a vJoy output card whose device is held elsewhere, else "Virtual". Used at module_model.py:2102, 2423, 2457, 2481 (full reload and in-place refresh share the rule). It is computed when the card loads/refreshes, not live (no timer).
- No status label on the vJoy Viewer / output pickers / Map to vJoy picker / Device Bindings: `output_modules.py` offers claimed ids the driver "really has" (spec 05 S118) with no busy flag (grep found no other user of `vjoy_in_use_elsewhere`; tests: test_stage1_modules.py:643-656, test_batch2_b3.py:67-77, test_device_fixes.py:131-134).

## 4. Tools > Drivers / setup (changing or deleting vJoy devices)
- `driver_jobs.vjoy_setup` (gremlin/driver_jobs.py:288-345): reads `vJoyConfig -t` (`parse_status_list`, :379-411, which counts OWNED, FREE and BUSY as existing), computes `stale` = every existing device not in the wanted list, creates/changes the wanted ones (`vJoyConfig N -f -a.. -b.. -p.. [-l]`), then `vJoyConfig -d <stale>` (the delete always refreshes the driver), then reads each back with `-t N`.
- Nothing checks the status text per device: a device that `-t` reports BUSY (held by CLS2Sim) is treated like any other. It would be reconfigured if wanted, or deleted if not in the wanted list, with no warning and no refusal in our code. What vJoyConfig/the driver does to a held device (refuse, or refresh and drop the other program's handle) is UNVERIFIED; vJoyConfig exit code is 0 even on bad arguments (driver_jobs.py:289), so only the read-back reports failure, with a generic message ("vJoyConfig failed" / the read-back mismatch).
- `current_vjoy_devices` (:420-440) is what the Drivers window/installer show as "what vJoy has now"; the status field is parsed away, so a BUSY device is not shown as busy there. The same rules are mirrored in installer/gremlin_platforms.iss:1370-1540 (read-only `vJoyConfig -t`, "S not MISSING or UNKNOWN", lines 1498-1499): no busy handling either.
- Our own Run holding a device during setup is separate (drivers_model closes/"Refused" paths concern the device-disable elevation, drivers_model.py:51, 81, 651), not other programs.
- Important consequence for CLS2Sim: since `stale` deletes every device not in our list, an unpublished-number device used by another program is deleted unless the Drivers list includes it (the list starts from `current_vjoy_devices`, so it is kept only if the user leaves it in). UNVERIFIED whether the Drivers window makes that obvious.

## 5. Spec
- 03 S34 (claude/program-map/03-modules.md:349): told once per Run, retried every 3 s, card says "In use by another program". Code matches.
- 06 S52 (06-runtime-outputs.md:328): shows "vJoy N is in use by another program." once per Run, logs once, retries every 3 s, carries on by itself when free. Code matches. 06 S106 (:384): Run-start open handles busy the same way; matches. 06 Q10 (:411) recommends the busy message as the user's signal.
- Gaps / notes (planning only; spec untouched):
  a. Spec is silent on vJoy setup (Tools > Drivers / installer) with a BUSY device: no statement on warning, refusal, or sparing a device another program holds. Code does nothing.
  b. Spec is silent on pickers/viewers/discovery showing a busy device (only the Home card).
  c. Mid-Run takeover (`vjoy_lost`, 05 S83 is a different statement; the docstring cites "05 S83" but that statement is Map to vJoy Relative): not wired to any UI.
  d. claude/program-map/03-modules.md:534 says `_refresh_inplace` resets the status to "Virtual"; the code now uses `_card_status` everywhere (module_model.py:2457), so that map note looks stale (map check item).
