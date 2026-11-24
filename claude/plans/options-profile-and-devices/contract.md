# Contract: Options profile pages + remembered Devices list (2026-11-24)

Approved spec: 12 S12, S21, S25, S27, S28, S35, S43 (D-12-DEVICES-REMEMBERED); 04 S96 (S97, S98 unchanged), 01 S58, S65 (D-04-OPTIONS-PROFILE). Never change spec statements; stop and report on a conflict.

## Rules for every agent
Read .claude/CLAUDE.md and follow it. No artifacts, no commits, no further agents. Every command: `PYTHONUNBUFFERED=1 <cmd> 2>&1 | python tools/agent_log.py <AGENT>`, pytest -v. Only tests for your files; `poetry run ruff check` on changed Python; `poetry run python tools/pyright_baseline.py`. Program runs use a temp USERPROFILE, off-screen. No real devices, vJoy or Windows device calls in tests. Never walk the whole disk or /dev; never open vJoy's raw control device. Don't touch tools/scan_selftest.py, claude/plans/steam-controller-design.md, tools/monitor_keep_off_test.log, or another agent's files (ask the lead in your report). Unreleased program: no old-layout readers, no migration. Estimate 3-8 min (timings.md: agent fix); report start/end (`date +%H:%M`), changes, tests, what failed on the old code.

## Options (OPT, SHELL, HELP, OPT-TESTS)
- DialogOptions.qml: sidebar rows below Folders: a line, heading "This profile" (objectName optionsProfileHeading), buttons objectName `optionsSection:startup-macros`, `optionsSection:vjoy`, `optionsSection:scripts` with texts "Startup and macros", "vJoy", "Scripts". Right side: title, then strip (objectName optionsProfileStrip; profile name objectName optionsProfileName = backend.windowTitle, note objectName optionsProfileSavedNote), then the page. Strip only on these three.
- `function showPage(id): bool` with ids "startup-macros", "vjoy", "scripts" (clears the search, shows the page; false on an unknown id).
- Pages reuse ProfileSettingsGeneral.qml, ProfileSettingsVJoy.qml, ScriptManager.qml (inner objectNames unchanged, vjoyInitialValue:* too). Page loaded only while shown or searched. Search options also finds rows on these pages (count and filter). DialogProfileSettings.qml and DialogScripts.qml are deleted.
- Main.qml: both toolbar buttons, openProfileSettings(), openScripts() and their callers go; main_commands.js loses tools.profileSettings and tools.scripts.
- Help link to a page: `show:optionpage/<id>` (ids above); Main._helpLinkReveal opens Options (tools.options) and calls showPage. help_links.js accepts exactly these ids. Links open:tools.profileSettings / open:tools.scripts are replaced.

## Devices list (SSM-MODEL, SSM-UI)
- gremlin/device_key.py: `device_key(name, instance_id) -> str` (S43) and `device_numbers(instance_id)` (maker, model, MI, Col; "" when absent).
- Stored rows (same setting `devices`): {"key","name","instance_ids":[...],"rate","choice":"automatic"|"manual","virtual","last_seen": ISO text or ""}. Rows without "key" are dropped (no conversion).
- Model for QML: `_ssm.devices` = list of {key,name,rate,choice,virtual,found,foundText ("" or "Not found · last seen today 16:27")}; `setDeviceChoice(key, choice)`, `removeDevice(key)`, `devicesSummary` (S12 counts), `devicesMessage`, `refreshDevices()`, `scanningDevices`, `helperMessage`, `tryAgain()` as today. setSwitchOff and Switch off are removed.
- `_saved_pairs()` = (name, instance id) of present devices matching Automatic rows, looked up at the power-off (S21, S43), never virtual; reads present ids without opening devices; a product name is read only when two rows share numbers. The real lookup refuses under pytest; tests inject a fake.
- QML objectNames: ssmTabs bar with ssmTabSettings, ssmTabDevices, ssmTabWake (below ssmEnabled/ssmTestNow/description, full width); ssmOpenDevices, ssmDevicesSummary; ssmRefreshDevices, ssmDeviceList, ssmDeviceName, ssmDeviceFound, ssmDeviceAutomatic, ssmDeviceManual, ssmDeviceRemove.
