# Fix plan: main window shows with its pages unloaded ("black page area")

PLAN-WIN, read-only scout, 2026-11-19, 13:02-13:08. Nothing in the program, the spec or the tests was changed.

## 1. What we know

- The running 1.0.39 was started at 03:40:37 by the installer with no arguments (process 15848's command line is just `gremlin_platforms.exe`; `installer/gremlin_platforms.iss:424` uses SW_SHOWNORMAL). So `--start-minimized` was not used.
- From 03:40 to now, `system.log` only has Screen Saver Mode entries. At 06:38:34 the displays were powered off, the main thread stalled for 9 s, and the devices were disabled and enabled again. `qt.log` has nothing for that day. No tray step is logged because the program logs none (gap).
- Home's Loader is `active: !_root.trayed` (`qml/Main.qml:2431`). `trayed` is set only by `enterTray()` and cleared only by `leaveTray()` (`Main.qml:148-160`). Those two are called only by `tray_memory.enter_tray` and `leave_tray` (`gremlin/ui/tray_memory.py:28-38`), and those only from `SystemTrayIcon._window_mode_changed_cb` (`gremlin/ui/system_tray.py:243-267`).
- Qt facts (verified unless marked otherwise):
  - `QWindow::isVisible()` and `visibility()` come from Qt's own flag (`d->visible`), not from Windows. Qt's Windows platform has no WM_SHOWWINDOW handling. So if something outside Qt shows a window that Qt hid, Qt still thinks it is hidden and `visibilityChanged` never fires. Source: qt-research.md Q1.
  - Open Qt bug QTBUG-124177: a hidden window shown again after a remote-desktop reconnect stays hidden on the Qt side. Details are unverified (the bug report could not be opened). The user uses RustDesk.
  - `QWindowPrivate::setVisible(bool visible)` sets `d->visible`, then emits `visibilityChanged` through `updateVisibility()`, and only at the end calls `platformWindow->setVisible(visible)` with the **parameter**, not the member. Verified from qwindow.cpp, Qt 6.11 branch, code.qt.io.
  - `showMinimized()` is `setWindowStates(Minimized); setVisible(true);`. Verified from the same file.

## 2. Ways `trayed` can be true while the window shows, ranked by evidence

| # | Path | Evidence | Fits today? |
|---|---|---|---|
| A | **Windows shows the hidden window without Qt knowing.** The window was in the tray (Qt has it hidden, `trayed` true). Then Windows or another program shows the native window: for example ShowWindow or SetWindowPlacement from Windows 11's display-reconnect features ("Minimize windows when a monitor is disconnected" / "Remember window locations based on monitor connection"), RustDesk, or Win+Shift+M. Qt's flag stays Hidden, no signal fires, and the pages stay unloaded. | Qt behaviour is verified (above). That those particular programs call ShowWindow on a hidden window is **unverified**. | Best fit. Powering the displays off at 06:38 can disconnect the monitor. If "minimize on disconnect" is on, Windows minimizes Gremlin, and Minimize to tray then hides it (`system_tray.py:261-267`), so the user never chose the tray. On reconnect Windows puts the window back on its monitor, which matches the new position (the place is only saved on X, `system_tray.py:101`). The user's display settings are unverified. |
| B | **`hide()` inside the visibility callback while Qt is showing the window.** The callback calls `self._window.hide()` from inside the Minimized emission (`system_tray.py:267`). If that emission comes from `setVisible(true)` (window state Minimized), the nested hide sets `d->visible` false and runs `enterTray`. Then the outer `setVisible` goes on and calls `platformWindow->setVisible(true)`, which shows the native window. Result: Windows shows a minimized window with a taskbar button, Qt says Hidden, and `trayed` is true. Restoring it from the taskbar changes only the window state, and visibility stays Hidden, so no signal fires. | Verified by reading the Qt source (above). The live run is **unverified**. | Not today's trigger (no `--start-minimized`). It is a real latent bug: `--start-minimized` with Minimize to tray on follows exactly this path. `backend.minimize()` (`gremlin/ui/backend.py:593-595`) runs `showMinimized` on the visible window, so Minimized is emitted twice and the second emission comes from inside `setVisible(true)`. The S10 hands-on check only read Qt's state ("Hidden"), never the native state. |
| C | **Screens removed and added again** (display power-off). Qt may destroy and remake the window, hiding and re-showing it. | **Unverified.** qt-research found no Windows code that shows or hides windows on display or power events (only InvalidateRect). | Low. If it did happen, the re-show runs `setVisible(true)` and fires the signal, so `leaveTray` would run (unless path B applies). |
| D | **Python `_trayed` and QML `trayed` out of step.** At `system_tray.py:254-256`, `_trayed` is set True before `enter_tray`, and `enter_tray` returns early when `window.isVisible()` (`tray_memory.py:30`). That leaves Python True and QML false, the opposite of today's state. The `invokeMethod` return value is ignored (`tray_memory.py:32,38`), so a failed `leaveTray` would go unnoticed. | Verified from the code. No known way for `invokeMethod` to fail here. | No (wrong direction), but it is a second source of truth that should go. |
| E | `release()` after 400 ms, `joystick_gremlin.py:1363` hide at quit, `_helpFront` `showNormal`, `window_placement.restore_window` / `_set_maximized`, the quit request's `restore_window` | All of these go through Qt's `setVisible`/`setVisibility`, so the signal fires. `release` checks `isVisible`. | No. |

**A safe live check, for the user to do (it changes nothing):** right-click the tray icon. The menu label comes from Qt's flag (`system_tray.py:330-334`).
- If it says **"Show Gremlin-Platforms"**, Qt thinks the window is hidden. That confirms path A (or B).
- If it says **"Hide…"**, Qt thinks it is shown, and the cause is elsewhere. In that case, re-check the "black = `trayed`" inference (for example, graphics lost while the displays were off). That alternative is **unverified**.

**Recovery today:** in case A, a left-click on the tray icon runs `restore_window` → `setVisibility` → the signal fires → `leaveTray`, and the pages come back.

## 3. Proposed fix (at the owner, `gremlin/ui/system_tray.py`; page 09 owns the code, page 01 holds the tray statements)

The cleanest current design: one owner and one truth. Windows' actual visibility of the window decides "in the tray".

1. **One source of truth.** Add `SystemTrayIcon._sync_tray(reason)`. It reads the actual state: `IsWindowVisible(hwnd)` and `IsIconic`, using `hwnd = int(window.winId())`. In the tray means "the native window is not visible and the tray icon is present".
   - When that state changes, it calls `enterTray` or `leaveTray`.
   - It sets `_trayed` only when `invokeMethod` returns True; if it returns False, it logs a WARNING.
   - `enter_tray` and `leave_tray` return a bool. The `isVisible()` early return moves into `_sync_tray`.
   - QML `trayed` stays a plain property that only Python sets.
2. **When Windows shows the window behind Qt's back, adopt it.** A native event filter on the main window's HWND (`QAbstractNativeEventFilter`, installed with `app.installNativeEventFilter`) watches WM_SHOWWINDOW (wParam=1) and WM_WINDOWPOSCHANGED with SWP_SHOWWINDOW. When the native window is visible but `window.isVisible()` is False, it queues `QTimer.singleShot(0, …)` to `setVisibility(current native state)`. That brings Qt's flag back in line, the signal fires, and `leaveTray` runs.
   - Backstop: an `Expose` event in the existing `eventFilter` while `_trayed` and `isExposed()` also calls `_sync_tray`. Whether expose fires on an outside show is **unverified**; the native filter is the main hook.
   - The other option, re-hiding the window, is the opposite behaviour and needs the user's choice (question 1 below).
3. **No nested hide.** The Minimized branch (`system_tray.py:261-267`) becomes `QTimer.singleShot(0, self, self._hide_if_still_minimized)`. That runs after the current `setVisible` has finished, and it re-checks `visibility() == Minimized` first. This closes path B.
4. **Logging.** One `system.log` INFO line for every tray change, with its cause. Examples: `Tray: hidden (minimize | X | tray menu)`, `Tray: shown (tray click | tray menu | Windows showed it)`. Plus a WARNING `Tray: out of step: Windows shows the window while Qt has it hidden; showing it` whenever step 2 fires.

## 4. Spec proposals (page 01; nothing written; numbers to be assigned)

- **S87 (changed):** "While the window is hidden in the tray, the pages should be unloaded (Device Bindings stays while it has unsaved display edits) and loaded again **whenever the window is shown, by Gremlin or by Windows (for example a monitor reconnect or a remote-desktop tool)**. The profile keeps running throughout."
- **S174 (new):** "Whether the window is in the tray should follow what Windows actually shows. If Windows shows the window while Gremlin has it hidden, Gremlin should treat it as shown: load the pages and leave the tray."
- **S175 (new):** "Each time the window goes to the tray or comes back, a line in system.log should say so and why (minimize, X, tray click or menu, Windows showed it)."
- **S85 (wording added):** "…minimizing should hide the window to the tray **once the minimize has finished** (with `--start-minimized` too: no taskbar button is left behind)."
- **Decision row D-01-TRAY-TRUTH:** Windows' actual window visibility is the single source of truth for the tray. It is synced by `system_tray.py` from Qt's visibility signal, the native show messages and expose. `hide()` is never called inside the visibility signal.

**Question for the user**
1. **When Windows shows the hidden window by itself, should Gremlin keep it on screen or send it back to the tray?**

   Windows (or a remote-desktop tool) can show the window while it is hidden in the tray. Gremlin has to pick one response.

   - a) Keep it on screen and load the pages (recommended: the user can see it, so it should work).
   - b) Hide it to the tray again.

## 5. Tests

**Existing tests that pin tray behaviour**
- `test/unit/test_tray_memory.py`: 3 tests. They call `enter_tray` and `leave_tray` directly on an off-screen window, plus a check of the Loader text.
- `test/unit/test_final_09.py:258-380`: the `tray` fixture, with `enter_tray` and `leave_tray` stubbed out (`:325-326`) and a fake window, plus `test_s73_start_minimized…`. These need updating for the deferred hide (they expect the hide to happen at once) and for `_sync_tray`.
- `test/unit/test_stage1_app_profile.py::test_minimize_to_tray_hides_on_minimize_and_close`: may expect a synchronous hide. Update it.
- `test_final_01.py::test_s10…` and `test_audit3_startup.py` / `test_audit2_startup_devices.py` tray-icon checks: unaffected.

**New tests.** Each runs a real QWindow and the real `SystemTrayIcon` in a subprocess with `QT_QPA_PLATFORM=windows`. The window sits off the main screen (test-off-main-screen rule) with opacity 0. The win32 tray calls are stubbed so no real icon is made. The native state is read with `IsWindowVisible(int(window.winId()))`.

1. `test_start_minimized_to_tray_leaves_no_native_window`: `showMinimized()` with Minimize to tray on, then wait for events. Expected: `IsWindowVisible == window.isVisible() == False` and `trayed` True. **Fails on the old code** (path B: the native window is visible).
2. `test_window_shown_behind_qts_back_reloads_pages`: hide to the tray, then `ShowWindow(hwnd, SW_SHOWNOACTIVATE)` through ctypes. Expected: within 2 s, `trayed` is False and `window.isVisible()` is True. **Fails on the old code** (`trayed` stays True).
3. `test_tray_steps_are_logged`: minimize, then tray click. Expected: `system` log records "Tray: hidden (minimize)" and "Tray: shown (tray click)". Fails on the old code (no lines).
4. `test_python_and_qml_tray_flags_agree`: `enter_tray` while visible must not leave `_trayed` True. Fails on the old code (path D).

## 6. Files, owners, risks, effort

| File | Owner (map page) | Change |
|---|---|---|
| `gremlin/ui/system_tray.py` | 09 (statements on 01) | `_sync_tray`, native event filter, deferred hide, logging |
| `gremlin/ui/tray_memory.py` | 09 | `enter_tray`/`leave_tray` return bool; drop the `isVisible` early return |
| `joystick_gremlin.py` | 01 | install the native event filter, or let `SystemTrayIcon` do it (preferred: no change here) |
| `qml/Main.qml` | 01 | none expected |
| `test/unit/test_tray_window_sync.py` (new), `test_final_09.py`, `test_stage1_app_profile.py` | tests | as in section 5 |
| `claude/program-map/01-app-shell.md`, `09-osc-sound-misc.md` | spec/map | S85/S87/S174/S175, D-01-TRAY-TRUTH, sections 4/5/10/11 |

**Risks**
- The native filter sees every message for the process, so it must check the HWND first and do nothing else.
- `setVisibility` from the filter must be queued, never run inside the Windows message.
- A real-window test needs a second screen or an off-screen position (test rule).
- The deferred hide leaves a short minimize animation visible before the hide; that was already true.
- Whether Windows 11's monitor-reconnect feature really calls ShowWindow on a hidden window is unverified. Test 2 covers the general case whatever the trigger.

**Effort** (timings.md, "Agent fix / feature / docs": 3-8 min per agent; a batch of parallel agents about 10 min): three parallel agents (code, tests, spec/map) take about 10 min. Add the lead's checks, the quick tests (`--changed`, targeted tests, pyright baseline) and the commit; the timings table has no rows for the lead's own steps, so that part is a rough guess of about 10 min. Total: about 20 min before continuous integration (CI) runs.
