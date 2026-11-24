# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""B3 live test: does a held key's output come up after a mode change?

claude/plans/b3-mode-change-release.md, "Live test first". Runs against the
INSTALLED program through gremlin-ctl:

  1. reads the open profile (refuses when it has unsaved changes);
  2. writes a temporary profile in %TEMP%: Keyboard F13 in Default -> Map to
     Keyboard F16, Keyboard F14 in Default -> Change Mode Switch to B, mode B
     with F13 unbound;
  3. Run stop, load the temporary profile, Run start;
  4. SendInput F13 down (no Gremlin mark, so the program reads it), F16 held?,
     F14 down/up, mode is B?, F13 up, F16 still held?
  5. always: keys up, Run stop, the user's profile back, Run start and
     tracing on when they were;
  6. prints the verdict: PASS (F16 released) or GAP (F16 still held).

--dry-run only writes the temporary profile and checks it loads with the
program's own Python profile reader (a subprocess with a temporary
USERPROFILE, off-screen Qt, run from the repo's Python).

    python tools/live_mode_release_check.py [--dry-run] [--ctl PATH]
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import subprocess
import sys
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_CTL = (
    Path(os.environ.get("LOCALAPPDATA", ""))
    / "Programs"
    / "Gremlin-Platforms"
    / "gremlin-ctl.exe"
)

# dill.UUID_Keyboard
KEYBOARD_GUID = "6f1d2b61-d5a0-11cf-bfc7-444553540000"
# Scan codes from gremlin/keyboard.py (none extended).
SC_F13, SC_F14, SC_F16 = 0x64, 0x65, 0x67
VK_F16 = 0x7F

PROFILE_XML = f"""<?xml version="1.0" ?>
<profile version="16">
    <inputs>
        <input>
            <device-id>{KEYBOARD_GUID}</device-id>
            <input-type>key</input-type>
            <mode>Default</mode>
            <input-id>{SC_F13}</input-id>
            <action-configuration>
                <root-action>a0000000-0000-4000-8000-000000000001</root-action>
                <behavior>button</behavior>
            </action-configuration>
        </input>
        <input>
            <device-id>{KEYBOARD_GUID}</device-id>
            <input-type>key</input-type>
            <mode>Default</mode>
            <input-id>{SC_F14}</input-id>
            <action-configuration>
                <root-action>a0000000-0000-4000-8000-000000000002</root-action>
                <behavior>button</behavior>
            </action-configuration>
        </input>
    </inputs>
    <settings>
        <startup-mode>Default</startup-mode>
        <macro-default-delay>0.05</macro-default-delay>
    </settings>
    <library>
        <action id="b0000000-0000-4000-8000-000000000001" type="map-to-keyboard">
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
        </action>
        <action id="b0000000-0000-4000-8000-000000000002" type="change-mode">
            <property type="string">
                <name>change-type</name>
                <value>Switch</value>
            </property>
            <target-mode>
                <property type="string">
                    <name>name</name>
                    <value>B</value>
                </property>
            </target-mode>
            <property type="string">
                <name>action-label</name>
                <value>Change Mode</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>press</value>
            </property>
        </action>
        <action id="a0000000-0000-4000-8000-000000000001" type="root">
            <actions>
                <action-id>b0000000-0000-4000-8000-000000000001</action-id>
            </actions>
            <property type="string">
                <name>action-label</name>
                <value>Root</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>disallowed</value>
            </property>
        </action>
        <action id="a0000000-0000-4000-8000-000000000002" type="root">
            <actions>
                <action-id>b0000000-0000-4000-8000-000000000002</action-id>
            </actions>
            <property type="string">
                <name>action-label</name>
                <value>Root</value>
            </property>
            <property type="activation-mode">
                <name>activation-mode</name>
                <value>disallowed</value>
            </property>
        </action>
    </library>
    <modes>
        <mode>Default</mode>
        <mode>B</mode>
    </modes>
    <scripts/>
    <devices/>
</profile>
"""

# Run by --dry-run in a subprocess: the program's own reader must load it.
VALIDATE = r"""
import sys
from pathlib import Path
# As the unit tests start: fake driver and vJoy (never the real one), then
# the program's settings.
sys.path.insert(0, str(Path.cwd() / "test"))  # stdlib's "test" shadows ours
import fake_hardware
fake_hardware.install(vjoy_ids=(1,))
import joystick_gremlin
joystick_gremlin.register_config_options()
from gremlin.profile import Profile
from gremlin.types import InputType

from gremlin import shared_state
p = Profile()
shared_state.current_profile = p  # as the program does before reading
p.from_xml(Path(sys.argv[1]))
modes = p.modes.mode_names()
assert "Default" in modes and "B" in modes, modes
found = {}
for dev_items in p.inputs.values():
    for item in dev_items:
        found[(item.input_type, item.input_id, item.mode)] = item
f13 = found[(InputType.Keyboard, (0x64, False), "Default")]
f14 = found[(InputType.Keyboard, (0x65, False), "Default")]
assert not any(k[1] == (0x64, False) and k[2] == "B" for k in found), found
root13 = f13.action_sequences[0].root_action
root14 = f14.action_sequences[0].root_action
kinds13 = [a.tag for a in root13.get_actions()[0]]
kinds14 = [a.tag for a in root14.get_actions()[0]]
assert kinds13 == ["map-to-keyboard"], kinds13
assert kinds14 == ["change-mode"], kinds14
target = [getattr(m, "name", m) for m in root14.get_actions()[0][0]._target_modes]
assert target == ["B"], target
print("VALID: F13 -> Map to Keyboard, F14 -> Change Mode, modes", modes)
"""


def write_profile() -> Path:
    path = Path(tempfile.gettempdir()) / "gremlin_b3_mode_release_check.xml"
    path.write_text(PROFILE_XML, encoding="utf-8")
    return path


def validate(path: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="b3live-home-") as home:
        env = dict(os.environ)
        env.update(
            USERPROFILE=home,
            APPDATA=str(Path(home) / "AppData" / "Roaming"),
            LOCALAPPDATA=str(Path(home) / "AppData" / "Local"),
            QT_QPA_PLATFORM="offscreen",
            PYTHONPATH=str(REPO),
        )
        res = subprocess.run(
            [sys.executable, "-c", VALIDATE, str(path)],
            cwd=REPO,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    sys.stdout.write(res.stdout)
    if res.returncode != 0:
        sys.stdout.write(res.stderr[-3000:])
        raise SystemExit(f"The temporary profile did not load ({res.returncode}).")


class Ctl:
    def __init__(self, exe: Path) -> None:
        self.exe = exe

    def call(self, *words: str, check: bool = True) -> dict:
        res = subprocess.run(
            [str(self.exe), "--json", *words],
            capture_output=True,
            text=True,
            timeout=60,
        )
        print(f"  gremlin-ctl {' '.join(words)} -> exit {res.returncode}")
        if check and res.returncode != 0:
            raise RuntimeError(
                f"gremlin-ctl {' '.join(words)} failed ({res.returncode}): "
                f"{(res.stdout + res.stderr).strip()}"
            )
        try:
            return json.loads(res.stdout) if res.stdout.strip() else {}
        except json.JSONDecodeError:
            return {}

    def state(self) -> dict:
        return self.call("state")

    def wait_run(self, want: str, seconds: float = 20.0) -> None:
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.state().get("run") == want:
                return
            time.sleep(0.25)
        raise RuntimeError(f"Run did not reach '{want}' in {seconds:.0f} s")


# SendInput, scan-code keyboard events, dwExtraInfo 0 (not Gremlin's mark).
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
ULONG_PTR = ctypes.c_size_t


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _U(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def send_key(scan: int, down: bool) -> None:
    flags = KEYEVENTF_SCANCODE | (0 if down else KEYEVENTF_KEYUP)
    inp = INPUT(INPUT_KEYBOARD, _U(ki=KEYBDINPUT(0, scan, flags, 0, 0)))
    sent = ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
    if sent != 1:
        raise OSError(f"SendInput failed for scan code {scan:#x}")


def key_held(vk: int) -> bool:
    return bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)


def live(ctl: Ctl, temp: Path) -> int:
    before = ctl.state()
    user_profile = before.get("profile") or ""
    was_running = before.get("run") == "running"
    was_tracing = bool(before.get("tracing"))
    print(
        f"User's profile: {user_profile!r}, run {before.get('run')}, "
        f"tracing {was_tracing}"
    )
    if before.get("unsaved"):
        print("REFUSED: the open profile has unsaved changes; save it first.")
        return 1
    if not user_profile:
        print("REFUSED: no saved profile is open to load back afterwards.")
        return 1

    verdict = "NOT RUN"
    held_before = held_after = None
    mode_after = None
    try:
        ctl.call("run", "stop")
        ctl.wait_run("stopped")
        ctl.call("profile", "load", str(temp))
        ctl.call("run", "start")
        ctl.wait_run("running")
        time.sleep(0.5)

        send_key(SC_F13, True)
        time.sleep(0.2)
        held_before = key_held(VK_F16)
        print(f"F13 down: F16 held = {held_before}")
        send_key(SC_F14, True)
        time.sleep(0.05)
        send_key(SC_F14, False)
        time.sleep(0.3)
        mode_after = ctl.state().get("mode")
        print(f"F14 tapped: mode = {mode_after!r}")
        send_key(SC_F13, False)
        time.sleep(0.3)
        held_after = key_held(VK_F16)
        print(f"F13 up in mode {mode_after!r}: F16 held = {held_after}")

        if not held_before:
            verdict = "INCONCLUSIVE: F16 never went down on F13 press"
        elif mode_after != "B":
            verdict = f"INCONCLUSIVE: mode is {mode_after!r}, not 'B'"
        elif held_after:
            verdict = "GAP: F16 still held after the mode change"
        else:
            verdict = "PASS: F16 released after the mode change"
    finally:
        for scan in (SC_F13, SC_F14):
            try:
                send_key(scan, False)
            except OSError as e:
                print(f"  cleanup: {e}")
        try:
            ctl.call("run", "stop", check=False)
            ctl.wait_run("stopped")
        except RuntimeError as e:
            print(f"  cleanup: {e}")
        if key_held(VK_F16):
            send_key(SC_F16, False)
            print("  cleanup: F16 sent up")
        ctl.call("profile", "load", user_profile, check=False)
        if was_running:
            ctl.call("run", "start", check=False)
        if was_tracing and not ctl.state().get("tracing"):
            ctl.call("trace", "on", check=False)
        after = ctl.state()
        print(
            f"Restored: profile {after.get('profile')!r}, run {after.get('run')}, "
            f"tracing {after.get('tracing')}"
        )
    print(f"VERDICT: {verdict}")
    return 0 if verdict.startswith(("PASS", "GAP")) else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="only write the temporary profile and check that it loads",
    )
    parser.add_argument("--ctl", type=Path, default=DEFAULT_CTL)
    args = parser.parse_args()

    temp = write_profile()
    print(f"Temporary profile: {temp}")
    if args.dry_run:
        validate(temp)
        return 0
    if not args.ctl.is_file():
        print(f"No gremlin-ctl at {args.ctl}")
        return 1
    return live(Ctl(args.ctl), temp)


if __name__ == "__main__":
    sys.exit(main())
