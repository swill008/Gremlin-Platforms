# Noticing a switched-off stick plugged back in (S23 gap), 2026-11-24

Research only; nothing built. Live trace: USB arrival of the NXT SEM THQ 15:54:28 (Windows LastArrivalDate), switched on 15:54:50, on the right Gladiator's unplug. The retry hangs on `device_change_event`, fed by dill (game controllers only).

| Way | Documented | Not documented / risk |
|---|---|---|
| A. `WM_DEVICECHANGE` / `DBT_DEVNODES_CHANGED` | Broadcast when a device is added or removed; no registration; top-level windows only (message-only windows get no broadcasts); does not say which device | Whether a disabled device's return sends it. Our listener window is top-level (`screen_saver_mode.py` `_listen`), but exists only while the listener runs |
| B. `CM_Register_Notification`, type DEVICEINSTANCE, one instance id | Windows 8+; no window; "enumerated" when a new matching instance is enumerated, "started" when it starts, "removed" when no longer present; Microsoft's sample registers one id; callbacks must be quick; unregistering inside one can deadlock | Whether "enumerated" fires for a disabled device, or for an id absent when registering |
| C. `CM_Disable_DevNode` without `CM_DISABLE_PERSIST` | Off until reboot by default, then on again; `CM_DISABLE_PERSIST` (Windows 10+) keeps it across reboots | Nothing found on unplug/replug. Changes S21-S24 behaviour |
| D. Interface arrival | Fires when an interface is enabled | So not for a disabled one (inference) |

SDL commit 56b0b3315 (2026-10-28) moved its HIDAPI notifications to `CM_Register_Notification` to stop depending on the Windows message loop. No report of exactly our case was found.

Sources: MicrosoftDocs/sdk-api (cm_register_notification, cm_notify_filter, cm_notify_action, cm_unregister_notification, cm_disable_devnode); learn.microsoft.com dbt-devnodes-changed, window-features; github.com/libsdl-org/SDL.
