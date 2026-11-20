# Screen Saver Mode freeze: web research (agent WEBFREEZE, 2026-11-20, 05:47 to ~05:58)

Labels: [docs] = verified in Microsoft/Qt pages read; [users] = reported by users/forums; [unverified] = inference or not confirmed.
Search results were thin and mostly old forum posts. No source found describing this exact combination.

## App facts checked first (code read)
- `power_off_displays` (gremlin/screen_saver_mode.py ~368-381) PostMessageW's WM_SYSCOMMAND/SC_MONITORPOWER/2 to `_power_window`.
- That hwnd is created by the input-listener class (~1232-1291) on its own Python message-loop thread, NOT the Qt GUI thread. So DefWindowProc's handling of the power-off runs on the listener thread. The same window_proc also handles WM_INPUT and WM_POWERBROADCAST (calls `display_state_handler`, ~1218-1225) on that thread. Check what that handler touches (any Qt object or lock the GUI thread also needs would link the two threads).

## 1. SC_MONITORPOWER: does it block?
- Hang reports are about SendMessage (waits for reply) from a thread with no message pump; fix suggested was PostMessage. [users] https://lists.freepascal.org/fpc-pascal/2017-August/051973.html
- Raymond Chen: broadcasting the power-off message is "very dangerous"; result depends on which window handles it last (monitor may blink off/on). Advice: do not post to random windows; create your own window and let it get default processing. This is what the app already does. [docs/blog] https://devblogs.microsoft.com/oldnewthing/?p=30893
- Broadcast to HWND_BROADCAST is the common recipe; one commenter calls it bad practice. [users] https://www.codeproject.com/Articles/12794/Complete-Guide-on-How-To-Turn-A-Monitor-On-Off-Sta
- A PostMessage variant (PowerShell) exists, avoids waiting. [users] https://www.powershellgallery.com/packages/ProductivityTools.SetMonitorOff/0.0.2/Content/ProductivityTools.SetMonitorOff.psm1
- NirCmd offers `monitor off` and `monitor async_off`; async is for when the tool stays in memory (blocking) after off. [docs, vendor] https://www.nirsoft.net/nircmd/monitor.html
- Using SC_MONITORPOWER may also put the PC to sleep on some systems. [users] https://mail.python.org/pipermail/python-win32/2021-June/014504.html
- NOT found: any source saying DefWindowProc's SC_MONITORPOWER itself blocks the posting/own thread. [unverified]
- Applies: the app already posts (not sends) to its own window on a non-GUI thread, so this call is unlikely to be what freezes the GUI thread. [unverified, consistent with the sources]

## 2. Why displays come back on right after power-off
- SC_MONITORPOWER only requests the power-saving state; any input (mouse move, key, HID report) wakes it. [users] https://www.codeproject.com/Messages/1173526/Great and https://answers.microsoft.com/en-us/windows/forum/all/display-not-wake-up-a-often/5c8b06b7-7ee3-4d10-9aee-15ebe2cdedd2
- A device can send input even when "allow this device to wake the computer" is off (that setting is for sleep, not display). [users] same Microsoft answers page.
- Stack Overflow report: since Windows 8's newer power handling, SC_MONITORPOWER wake/off behaves oddly (screen on then off again). [users] https://kiwix.lema.org/stackoverflow.com_en_all_2023-11/questions/25011141/turn-off-on-monitor-can-t-turn-on
- A video-playback or other program can power the monitor back on quickly (DisplayLink user). [users] https://displaylink.org/forum/showthread.php?p=96720
- Monitor firmware/signal handling: monitors that drop DisplayPort signal in deep sleep produce reconnect events on wake; users suggest toggling the monitor's deep-sleep/eco setting. [users] Samsung thread https://us.community.samsung.com/t5/Monitors-and-Memory/Monitor-won-t-stay-off-in-sleep-mode/m-p/2512651/highlight/true
- Windows 10+ dims the display 10 s before off; display state has Off/On/Dim. [docs] https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdm/ne-wdm-_monitor_display_state
- Modern Standby: user input must wake the SoC and turn the display on. [docs] https://learn.microsoft.com/en-us/windows-hardware/design/device-experiences/modern-standby-wake-sources
- Known workaround patterns (all [users], none proven): wait (Sleep ~500 ms) between messages; re-send off; unplug suspect USB devices; stop other programs sending input.
- Applies: disabling 3 HID devices at the same moment could itself generate device-arrival/removal and input-like activity, and a helper process doing SetupAPI disable is a plausible wake source. [unverified]. Waking is not itself a cause of a GUI freeze, but each wake/off cycle is a display-state change the GUI thread has to process (see 3).

## 3. Qt/PySide freezes on monitor power-off
- Qt interest list, March 2026: main thread (or Quick rendering) appears to freeze while the screen is off, new since Qt 6.9 (worked 6.8.2, broken 6.9.3); no replies found. [users] https://lists.qt-project.org/pipermail/interest/2026-March/040450.html  Closest match to this app (Qt 6.11). Worth reading with its follow-ups and the Qt 6.9 changelog.
- Qt Windows screen list depends on WM_DISPLAYCHANGE delivered to top-level windows; DPI-change and geometry messages can arrive before it, so Qt scales against a stale screen. [users/bug] https://bugreports.qt.io/browse/QTBUG-119851 and https://bugreports.qt.io/browse/QTBUG-108349
- Crash/exception in screen handling on monitor disconnect/shutdown: QTBUG-81359, QTBUG-109217 (screen manager), older Qt 5.5.1 crash https://forum.qt.io/topic/62371/qt-5-5-1-application-crash-when-monitor-is-shut-down . Hangs on KDE Wayland when a DP monitor sleeps (QScreen destructor path): https://bugs.kde.org/show_bug.cgi?id=450679 (not Windows).
- Windows paint stops while screen locked/asleep: QTBUG-96100, QTBUG-43263, QTBUG-66557. [users]
- NOT found: a Qt bug with "Windows + main thread hang for seconds when display powers off" other than the March 2026 post. [unverified]
- Applies: storms of display off/on (4-9 in 10 s) mean 4-9 rounds of Qt screen/geometry/DPI handling plus the app's own handlers; any Python slot connected to screenAdded/Removed/primaryScreenChanged or geometry changes runs on the GUI thread. [unverified hypothesis]

## 4. Disabling HID devices while the app has them open
- Microsoft: apps holding a handle should close it on DBT_DEVICEQUERYREMOVE and reopen on QUERYREMOVEFAILED; reregister on remove-complete. [docs] https://learn.microsoft.com/en-us/windows/win32/devio/processing-a-request-to-remove-a-device
- OSR report: SetupDiCallClassInstaller (INSTALL/PROPERTYCHANGE) hung on Vista while another app had the driver's device open; running it in a separate process was discussed. Old. [users] https://community.osr.com/discussion/comment/293834/
- SetupDiCallClassInstaller calls CM_Disable_DevNode internally; CM_Disable_DevNode reported much faster than SetupDi calls issued from a WM_DEVICECHANGE handler (30 s case). [users] https://community.osr.com/t/help-disabling-a-device-using-setupdixxx-fns-after-wm-devicechange-msg/23464 ; doc: https://learn.microsoft.com/en-us/windows/win32/api/cfgmgr32/nf-cfgmgr32-cm_disable_devnode
- DICS_DISABLE can fail with ERROR_NOT_DISABLEABLE on HID keyboards. [users] https://community.osr.com/discussion/comment/300340
- NOT found: confirmation that open DirectInput/HID handles make PnP wait on the app's GUI thread. [unverified]
- Applies: the disable is in a helper process (good). PnP broadcasts WM_DEVICECHANGE to top-level windows of the app; if any window on the GUI thread (Qt creates one for device notifications, as may the app's own code) handles it slowly, or if the app's DirectInput/SDL/HID threads hold handles the removal waits on, the GUI thread can stall around the disable. [unverified]. Check in the stack dumps (FREEZE agent) what the GUI thread is waiting in.

## 5. How other programs do monitor-off
- NirCmd: SC_MONITORPOWER with async variant. [docs, vendor] https://www.nirsoft.net/nircmd/monitor.html
- PowerShell/AutoIt/C# recipes: PostMessage (or SendMessage) to HWND_BROADCAST (0xFFFF), wParam 0xF170, lParam 2. [users] https://gist.github.com/EugeneLoy/150044d04b08e35d09e164c864e78da7 , https://mybyways.com/blog/command-to-turn-off-monitor-in-windows-10
- DDC/CI tools (ControlMyMonitor, Twinkle Tray) can switch real monitor power state instead of OS standby; anecdotal for a monitor that ignored the Windows message. [users] https://gist.github.com/PCHSwS/39e213aac7c574b89673da8dc575e7fa
- Not found: how PowerToys Awake, Monitorian, f.lux or DisplayFusion implement it (Awake is keep-awake, not monitor-off). [unverified]

## Ranked fix ideas (recommended first)
1. Move every display-state reaction off the GUI thread and make it cheap: the display_state_handler, tray power-notification handler and any screen signal slots should only set a flag/queue and return; no Qt widget work, logging with I/O waits or blocking calls on the GUI thread during the storm. (Matches the Qt 6.9+ report; unverified for this app until the stack dump confirms.)
2. Do not run the HID disable at the same instant as monitor-off: stagger (e.g. disable after displays are confirmed off and stable, or before), and never during a display-state change. Also release the app's own handles to those 3 devices first, per Microsoft's QUERYREMOVE pattern, so PnP has nothing to wait on.
3. Stop "keep off" re-sending on every wake; use a debounce (ignore display-on notifications for ~1-2 s after sending, re-send at most once, then wait for real user input). Each extra off/on is another Qt screen/DPI pass and another wake.
4. Identify and stop the wake source: test with the 3 HID devices already disabled before power-off (disable first, then off), and with the helper process not spawned; check `powercfg /requests` and Modern Standby status on this PC.
5. Keep the current design (post to own hidden window on its own thread) rather than HWND_BROADCAST; Raymond Chen's advice supports it. Optionally try SendNotifyMessage/async from a dedicated worker thread only if tests show the listener thread is the one stalled.
6. Monitor-side: Deep Sleep off already helps (DP disconnect events); alternative is DDC/CI power control (real power-off, no OS display-state storm) but adds a new dependency and per-monitor support risk.
7. Qt-side mitigation to test: temporarily defer/ignore QGuiApplication screenAdded/screenRemoved/primaryScreenChanged handling and QWindow screen-change work while the saver is active; try a Qt 6.8.x build to see if the 6.9+ regression is the cause (unverified).

## Open questions for the other agents
- What does the GUI thread stack show at the freeze (Qt screen code, WM_DEVICECHANGE, a lock, a Python slot)?
- What does `display_state_handler` call, and does it take a lock the GUI thread also takes?
