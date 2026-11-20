# OT-1..OT-5 removal: check of the user's real data (OTCHECK, 2026-11-20 08:2x, read-only)

Data folder scanned: C:\Users\Stacie\Gremlin Platforms (read-only; own scripts, python -I).

- OT-1 (device folders move): nothing left. modules/folders.json marker present (layout 2, 2026-10-11); no *.json at the
  modules root other than the marker. Old setting global/internal/module-file-bindings is still in configuration.json
  (one key); only the removed mover reads it, purge_unused would drop it. Root leftovers (modules/vkb_evo_l, vkb_evo_r,
  hidhide_photos, configuration, empty imported) are not touched by the mover and nothing reads them.
- OT-2 (old photo -> bottom background picture): NOT done. Live maps still in the old layout (top-level "image", no
  bottom background picture node): Keyboard, Logical Device, OSC, Xbox 360 Controller, vJoy 1, vJoy 3, VKBsim Gladiator
  EVO OT L (also has photo/imageWidth/imageHeight). Already new: VKB NXT SEM THQ FSM.GA, VKBsim Gladiator EVO R, vJoy 2,
  vJoy 4. No photo: HID Remapper 2DGG, Xbox 360 2/3/4. Old-layout copies also in modules/vJoy 2/imported/module
  2026-11-OCT_19_37_13.json, modules/VKBsim Gladiator EVO OT L/imported/*.json (3), export/VKBsim Gladiator EVO R.gmap
  (module.json + bindings/outputs/vJoy 2.json), history/files/c16f87...gmap (only exact/imported/module 2026-11-OCT_19_37_13.json),
  _Old zips, backup/2026-10-11 device folders move (a record). Device Library saved setups: library.json has none.
- OT-3: nothing left. No "button-map" section, no global/internal/button-map-* keys; device-mapping-editor section and
  device-map-* keys exist. Stale window ids "button-map*", "buttonmap-options", "help-buttonmap" remain inside the
  tool-windows / tool-rows JSON values; OT-3 never moved them (harmless dead geometry).
- OT-4: nothing left in the live data. library.json: 0 "button_map" (1 "device_map"); history jsonl files 0. Old id only in
  backup/2026-10-11 library part id move and (2) (a record).
- OT-5: nothing on disk depends on it; only log lines in logs/system.log and trace.log.
