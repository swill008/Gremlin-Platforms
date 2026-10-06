# Gremlin-Platforms: handoff from the Grok project history

> **Archived (historical, as of 2026-09-30).** Kept for background only; much
> of "Where things stand now" is out of date (UI scaling, branches, HEAD).
> Current plans: `claude/todo.md` and `claude/system-maps.md`; current
> issues: the tracker.

Reviewed 2026-09-30. This covers all 11 conversations in Grok project "Joystick Gremlin" (2026-09-12 to 2026-09-30), plus that project's `grok_rules`, `.grok/project_memory.md` and the `Gremlin-Rewrite-Features` design docs.
All SHAs below are what Grok reported. Grok could not run the Windows app, so "pushed" does not mean "tested".

## Where things stand now
- **Product:** Gremlin-Platforms R1 1.0.0, a fork of Joystick Gremlin R15 (Python + PySide6 + QML). It is meant for public release. The exe is `gremlin_platforms.exe`; the source entry is still `joystick_gremlin.py`. It is a portable zip, not an installer. Profile format stays v14.
- **Repo:** `swill008/JoystickGremlin_` (upstream WhiteMagic/JoystickGremlin).
- **Active branch:** `Gremlin-Platforms`, cut 2026-09-30 from `ccef173976`. Stacie wants it to become the single branch. The others get deleted later, only when she names them. `develop` is the GitHub default and has to be switched first.
- **Branch tips when the new branch was cut:**
  - `develop` `72925ca`
  - `VKB-joystick-Button-Map` `8463fcb` (all work from 09-13 to 09-30, including the abandoned scaling experiments)
  - `R15-OSC-Optimization` `b1a50a4`
  - `Xbox_integration_ViGEmClient_dll` `4925e22`
  - `feature/osc-streamdeck` `1cb94cb` (do not touch)
- **Last reported HEAD on Gremlin-Platforms:** `33b58db8`. The commits since the base:
  - `4c022506`: the `[role]` Shiboken fix and the plugin-directory default/Reset.
  - `5aeb5af0`: registers `ui/general/ui-scale` (int 70–200, default 100) and `disable-windows-scaling`, and fixes the slider widget.
  - `33b58db8`: removes the `contentItem.scale` paint magnification.

  Result: the slider saves a value that nothing reads, so there is **no working UI scaling right now**.
- **Where Grok stopped:** Grok died mid-reply on 2026-09-30 14:11–14:16. No pushes were reported, so the branch needs checking for anything after `33b58db8`.

## Open task #1: UI scaling (Stacie's lock)
"I want UI scaling that R16 uses, with one exception: add a slider from 70 to 200." Default 100, and the setting applies on slider release.

Grok's approved plan (not done):
1. Add R16's `dp()` scale function, reading the saved slider value.
2. Turn Windows scaling off before Qt starts, as R16 does. This conflicts with the earlier decision "Windows scaling on by default + Options switch to disable". **Needs Stacie's decision.**
3. Size windows with `dp()`. No paint magnification.
4. Convert fixed pixel sizes to `dp()`. On this branch that is 988 raw sizes in 93 of 118 QML files.
5. Delete every other scale path.

**Unresolved:** does "R16's way" mean adopting R16's Metrics/Kobold control tokens, or converting sizes by hand? Grok contradicted itself on this. Compare with upstream `develop` (R16, `2d33d46`) before planning.

Fixes that exist only on `VKB-joystick-Button-Map` (the `openEditor` name clash in BindingCatalog.qml, the Options right padding) may need re-applying. Stacie said she wants "the same fixes identified here" on the new branch.

## Other open items
- **Logical Device page** (built 09-28/29):
  - No way to delete a single action; an empty Sequence is left on Button 1.
  - No invert on axis Map to Logical Device.
  - The child indent change isn't visible.
  - The batch-add group field is free text.
- **Untested:**
  - the mode fix `72884707` (one mode for editing and running)
  - the Xbox model fix `b0db08ef`
  - Status Compact View
  - app-wide PointerTip
  - the Loader teardown fixes
  - the release builds (runs 36642381375 and 36696556203; their results were never checked)
- **Button Map export:** PDF/PNG/JPG/HTML. "Export PDF" still writes a PNG.
- **vJoy Viewer dash chips** (NXT buttons 30–56): agreed the right half should show the wire's vJoy number. Not built.
- **Startup config writes:** 15 remain, down from ~1275.
- **Leftovers after moving user data to `%USERPROFILE%\Joystick Gremlin`:**
  - Stock images are no longer in git.
  - Old `qml/maps` path prefixes are still inside the module files.
- **Yellow debug path bar:** remove it before any beta.
- **Update-check URL:** still a placeholder.
- **HidHide review items 3–8 not done:**
  - vJoy picture match
  - the Test note
  - crash-skips-restore
  - gaming filter persistence
  - list sorting
  - startup debug log
  - splitting `hidhide.py`
- **NXT USB parent ID:** stays on the blacklist.
- **Xbox branch (from 09-13):**
  - Unfixed logic bugs:
    - LT/RT rest at 50%.
    - Hat-to-DPad reads as pressed at center.
    - `available()` is cached forever.
  - The HID filter is too broad.
  - The PyInstaller spec lacks ViGEmClient.dll and map_to_xbox.
  - It was never merged.

## Architecture locks
- **Pipeline:** real hardware → input module (the only thing that sees DILL) → wire → output module. Exemptions: Configure module screens, Assign hardware, Calibration, viewers, and hooks.
- **Module files:** `<data>/modules/<slug>.json` (`control.hardware`). A module holds the claimed controls, names, photo, display options and calibration. Actions live only in the profile XML.
- **Input module:** decides which module file every screen uses. Importing a file copies it; the imported originals are never modified.
- **User data:** lives in `%USERPROFILE%\Joystick Gremlin` (modules, logs, profiles, scripts, export, images, plugins), not in the repo.
- **Config data changes:** Stacie hand-edits `configuration.json`. Never write one-time migration code.
- **Rooms:**
  - Home (formerly Status): device cards.
  - Configuration: a bindings catalog with inline quick-add and a right-side Action pane.
  - Output Module View.
  - Logical Device page.
  - Button Mapper: one generic editor for all devices, on a 32000×18000 world page with a photo pose.
  - HiDHide window.
  - Device Pack import/export.
- **Look:** a dense, dark, Photoshop-2016-style tool. Match the existing kit; aesthetics matter.
- **Upstream R16:** Kobold UI and Dill2 were rejected. Five small fixes were ported.

## How Stacie wants the AI to work
From `grok_rules` 1–28 plus the chats:
1. **Plan first.** No code until an explicit "go / ok go / code it / implement / land it / push it". "Plan only" means no code at all, and a question like "did you push?" is not an instruction.
2. **Lead with the recommendation;** alternatives come after.
3. **Real fixes only:**
   - Do root-cause analysis. Don't treat symptoms, and don't do half-measures.
   - No hacks or workarounds unless she asks for one.
   - Use Qt/QML/Gremlin best practice.
   - Don't invent methods; reuse existing program paths, or R16 / the reference implementation (e.g. HidHide source).
4. **No dead code or one-time migration code.**
   - Ask before any copy, fallback or backward-compatibility path; that is her choice.
   - No special-case code for a single use.
5. **Test and verify before claiming anything works.** Check the whole path and analyse the impact on other code.
6. **Git:**
   - Small incremental commits so each step can be reverted.
   - Announce every push with its SHA and commit name.
   - Tag restore points before big changes.
7. **Match the existing UI.** The user controls saving; never auto-save.
8. **Communication:**
   - Plain full sentences, no jargon or shorthand, one idea per sentence.
   - Answer the question directly first.
   - Tables for comparisons.
   - Handoffs go in a copyable code block.
9. **Mockups:**
   - Only show what the program can actually draw.
   - Base them on her real screenshots or photos.
   - One image at a time, and it must actually display in chat.
10. **Hardware:**
    - VKBsim Gladiator EVO R, EVO OT L and NXT, mapped to vJoy 1–3.
    - Monitors: LG ULTRAGEAR+, LG TV, CF15T.
    - EVO R lock: 1/2 trigger, 3 red, 4 cap, 5 lower white, 6–10 and 11–15 5-ways, 16–20 wheel, 21/22 paddle, 23/24 En2, 25/26 En1, 27/28/29 pads, hat1 ministick, axes 1–3 gimbal, axis 4 slider.

**Her main frustrations with Grok:** coding without permission, repeated untested pushes that crashed the app, going in circles and swapping approaches instead of doing what she asked (5 hours on UI scaling), silent one-time/migration code, truncated or overwritten large files, and claims that weren't verified.

**Local setup:**
- Windows machine, GitHub Desktop, Poetry.
- Repo path: `E:\Users\Stacie\Documents\GitHub\JoystickGremlin_`
- Run with: `poetry run python joystick_gremlin.py`
- Live config: `C:\Users\Stacie\Joystick Gremlin\`
