# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Live test: does a Map to Mouse click stop the program reading input?

Map to Mouse sends clicks with SendInput from the input thread, the pattern
that stopped keyboard input before the key sender thread (22720a3c). Runs
against the INSTALLED program through gremlin-ctl, like
tools/live_mode_release_check.py (whose helpers it reuses):

  1. temporary profile: Keyboard F13 -> Map to Mouse "Forward" (the X2 mouse
     button, harmless in most windows), Keyboard F15 -> Map to Keyboard F16
     (the probe that input is still read);
  2. Run stop, load it, Run start;
  3. probe F15 -> F16 once before any click (baseline);
  4. five rounds: F13 down (Forward held?), F13 up (released?), then the
     F15 probe (F16 held? released?);
  5. always: keys and button up, Run stop, the user's profile back, Run
     start and tracing on when they were;
  6. verdict: PASS (input read after every click), GAP (the probe stopped
     after a click) or INCONCLUSIVE.

    python tools/live_mouse_click_check.py [--ctl PATH]
"""

from __future__ import annotations

import argparse
import ctypes
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_mode_release_check as base  # noqa: E402

SC_F13, SC_F15, SC_F16 = 0x64, 0x66, 0x67
VK_F16 = 0x7F
VK_XBUTTON2 = 0x06
ROUNDS = 5

KB = base.KEYBOARD_GUID


def _input(scan: int, root: str) -> str:
    return f"""
        <input>
            <device-id>{KB}</device-id>
            <input-type>key</input-type>
            <mode>Default</mode>
            <input-id>{scan}</input-id>
            <action-configuration>
                <root-action>{root}</root-action>
                <behavior>button</behavior>
            </action-configuration>
        </input>"""


def _root(root: str, child: str) -> str:
    return f"""
        <action id="{root}" type="root">
            <actions>
                <action-id>{child}</action-id>
            </actions>
            <property type="string">
                <name>action-label</name>
                <value>Root</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>disallowed</value>
            </property>
        </action>"""


R1, R2 = "a0000000-0000-4000-8000-000000000011", "a0000000-0000-4000-8000-000000000012"
A1, A2 = "b0000000-0000-4000-8000-000000000011", "b0000000-0000-4000-8000-000000000012"

PROFILE_XML = f"""<?xml version="1.0" ?>
<profile version="16">
    <inputs>{_input(SC_F13, R1)}{_input(SC_F15, R2)}
    </inputs>
    <settings>
        <startup-mode>Default</startup-mode>
        <macro-default-delay>0.05</macro-default-delay>
    </settings>
    <library>
        <action id="{A1}" type="map-to-mouse">
            <property type="string">
                <name>mode</name>
                <value>Button</value>
            </property>
            <property type="string">
                <name>button</name>
                <value>Forward</value>
            </property>
            <property type="string">
                <name>action-label</name>
                <value>Map to Mouse</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>both</value>
            </property>
        </action>
        <action id="{A2}" type="map-to-keyboard">
            <input>
                <property type="int">
                    <name>scan-code</name>
                    <value>{SC_F16}</value>
                </property>
                <property type="bool">
                    <name>is-extended</name>
                    <value>False</value>
                </property>
            </input>
            <property type="string">
                <name>action-label</name>
                <value>Map to Keyboard</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>both</value>
            </property>
        </action>{_root(R1, A1)}{_root(R2, A2)}
    </library>
    <modes>
        <mode>Default</mode>
    </modes>
    <scripts/>
    <devices/>
</profile>
"""


def held(vk: int) -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def probe(label: str) -> bool:
    """F15 -> F16: True when F16 went down and came back up."""
    base.send_key(SC_F15, True)
    time.sleep(0.2)
    down = held(VK_F16)
    base.send_key(SC_F15, False)
    time.sleep(0.2)
    up = not held(VK_F16)
    print(f"  {label}: probe F16 down={down} up={up}")
    return down and up


def live(ctl: base.Ctl, temp: Path) -> int:
    before = ctl.state()
    user_profile = before.get("profile") or ""
    was_running = before.get("run") == "running"
    was_tracing = bool(before.get("tracing"))
    print(f"User's profile: {user_profile!r}, run {before.get('run')}, "
          f"tracing {was_tracing}")
    if before.get("unsaved"):
        print("REFUSED: the open profile has unsaved changes; save it first.")
        return 1
    if not user_profile:
        print("REFUSED: no saved profile is open to load back afterwards.")
        return 1

    verdict = "NOT RUN"
    try:
        ctl.call("run", "stop")
        ctl.wait_run("stopped")
        ctl.call("profile", "load", str(temp))
        ctl.call("run", "start")
        ctl.wait_run("running")
        time.sleep(0.5)

        if not probe("baseline"):
            verdict = "INCONCLUSIVE: the keyboard probe failed before any click"
        else:
            clicks_ok = True
            stopped_at = None
            for n in range(1, ROUNDS + 1):
                base.send_key(SC_F13, True)
                time.sleep(0.2)
                down = held(VK_XBUTTON2)
                base.send_key(SC_F13, False)
                time.sleep(0.2)
                up = not held(VK_XBUTTON2)
                print(f"Round {n}: Forward down={down} up={up}")
                clicks_ok = clicks_ok and down and up
                if not probe(f"round {n}"):
                    stopped_at = n
                    break
            if stopped_at:
                verdict = f"GAP: input stopped after click round {stopped_at}"
            elif not clicks_ok:
                verdict = "INCONCLUSIVE: input kept working, but a click did not show"
            else:
                verdict = f"PASS: {ROUNDS} clicks, input read after every one"
    finally:
        for scan in (SC_F13, SC_F15):
            try:
                base.send_key(scan, False)
            except OSError as e:
                print(f"  cleanup: {e}")
        try:
            ctl.call("run", "stop", check=False)
            ctl.wait_run("stopped")
        except RuntimeError as e:
            print(f"  cleanup: {e}")
        if held(VK_F16):
            base.send_key(SC_F16, False)
            print("  cleanup: F16 sent up")
        ctl.call("profile", "load", user_profile, check=False)
        if was_running:
            ctl.call("run", "start", check=False)
        if was_tracing and not ctl.state().get("tracing"):
            ctl.call("trace", "on", check=False)
        after = ctl.state()
        print(f"Restored: profile {after.get('profile')!r}, run {after.get('run')}, "
              f"tracing {after.get('tracing')}")
    print(f"VERDICT: {verdict}")
    return 0 if verdict.startswith(("PASS", "GAP")) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--ctl", type=Path, default=base.DEFAULT_CTL)
    args = parser.parse_args()
    temp = Path(tempfile.gettempdir()) / "gremlin_mouse_click_check.xml"
    temp.write_text(PROFILE_XML, encoding="utf-8")
    print(f"Temporary profile: {temp}")
    if not args.ctl.is_file():
        print(f"No gremlin-ctl at {args.ctl}")
        return 1
    return live(base.Ctl(args.ctl), temp)


if __name__ == "__main__":
    sys.exit(main())
