# Plan: a vJoy update keeps the devices (2026-11-22, planning, not built)

Why: on the user's PC the vJoy update 2.1.9 -> 2.2.2.0 (setup, 05:29) left
vJoy 4 out: its registry key only had 2.1.9's spelling `HidReportDesctiptor`,
2.2.2.0 reads only `HidReportDescriptor` (claude/audits/2026-11-22-vjoy-new-axes/vjoy.md).
The user thinks vJoy 4 was already turned off; the risk stays for others.
Setup and Tools › Drivers already read the devices before (setup
`ReadVJoyLayout`, .iss ~1605) but set them up after an update only when edited.

Decided by the user 2026-11-22:
- Check after the update; put back only what is missing or different, exactly
  as it was; never change a configuration the user didn't edit.
- Log the devices "before" and "after" every time (helper log; never History).
- Two prompts: before the update an information prompt with **OK** only;
  after it, only when something was lost, **Repair Now** / **Repair Later**.
- No line about the administrator prompt in the wording.
- Devices not readable before the update: prompt 1 says so (2a).
- Tests with stand-ins only, no vJoy 2.1.9 in the test machine (3b).
- 1.1.1 waits for this (5b).

Prompt 1 (before, OK):

> **vJoy update and your devices**
> Updating vJoy can lose vJoy devices that were set up with older vJoy tools.
> Gremlin-Platforms has noted your 3 vJoy devices (vJoy 1, vJoy 2, vJoy 3) and
> checks them after the update. If one is missing or different, you'll be
> asked whether to repair it.
> **OK**

Not readable (2a): "vJoy's devices couldn't be read before the update, so they
can't be checked afterwards. Check them in Tools › Drivers after the update." OK

Prompt 2 (after, only when lost):

> **The vJoy update lost a device**
> After updating vJoy, vJoy 4 (8 axes, 32 buttons, 0 hats) is missing. It was
> probably set up with an older vJoy tool that the new vJoy doesn't read.
> Gremlin-Platforms can put it back exactly as it was.
> **Repair Now** | **Repair Later**

Open: what "Repair Later" does (see the chat question).

## Reproduced in the test machine (2026-11-22, 05:56-06:00)

Clean machine; vJoy 2.1.9.1 (jshafer817 release, signed by Justin Shafer)
installed; its vJoyConfig set vJoy 2 to X Y Z, 32 buttons, 0 hats; registry
`Device02` had only `HidReportDesctiptor`. Gremlin-Platforms 1.1.1 installed
silently, then Gremlin Device Helper ran the real job `update vjoy` (bundled
2.2.2.0): result "Updating vJoy (bundled copy): done", vjoy.sys 2.2.2.0.
After: `vJoyConfig -t` (2.2.2.0) shows **Device 2: MISSING** and a
**Device 1: FREE** that nobody set up (no Device01 key: the new driver's
default device). So the update loses old-tool devices and adds a default
vJoy 1. Scripts: scratchpad vmt/t15a.ps1, t15c.ps1.

## Answers 2026-11-22 (continued)

- Only when vJoy is ticked for **update** (setup or Tools › Drivers): no
  check and no prompts when vJoy isn't ticked or is freshly installed.
- 2b: a vJoy device that appears only because of the update (the new driver's
  default vJoy 1) is left alone and only mentioned in the results line; the
  program needs at least one vJoy device anyway (user: "one has to be added
  to install the program so its expected behaviour"). Its layout wasn't read
  in the test; the existing alike-devices check covers a clash.
- 1a: **Repair Later** remembers the lost devices; Tools › Drivers shows them
  as rows marked "lost in the vJoy update" with a **Repair** button.
- At least one vJoy device stays while vJoy is installed (recorded in 01 S187
  and 06 S185 as existing behaviour, user 2a).

Plan complete; waiting for the user's "build". 1.1.1 waits for it.
