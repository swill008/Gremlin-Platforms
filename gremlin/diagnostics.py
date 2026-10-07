# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Help → Save Diagnostics… (01 S132): one zip with the program's logs, its
settings, the device list and the program and Windows versions, and the open
profile only when asked for. The user's name in folder paths becomes
`<user>` in everything written, file names included.

collect() runs on the main thread (it asks the input side for the devices
and the open profile for its text); write_zip() only reads files and writes
the zip, so it runs on a worker.
"""

from __future__ import annotations

import json
import logging
import os
import platform
import re
import sys
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from gremlin import clock

USER = "<user>"
# In a file name: Windows can't make a file with < or > in its name, so the
# zip's own file names use this instead.
USER_IN_NAMES = "(user)"
# A log bigger than this goes in as its last part only.
MAX_LOG_BYTES = 8 * 1024 * 1024
FAILURE_LEAD = "Diagnostics not saved."
_FALLBACK = "the zip could not be written there"


def user_names() -> list[str]:
    """The user's name as it shows in folder paths: the Windows user name
    and the name of the user's own folder (they can differ)."""
    names = {
        os.environ.get("USERNAME", ""),
        Path(os.environ.get("USERPROFILE", "") or "").name,
    }
    return sorted((n for n in names if len(n) >= 2), key=len, reverse=True)


def _component(name: str) -> re.Pattern[str]:
    # The name as a whole folder in a path: after a slash or backslash, up
    # to the next one or the end of the path.
    return re.compile(
        r"(?<=[\\/])" + re.escape(name) + r"(?=[\\/\"'\s:;,)\]>]|$)",
        re.IGNORECASE | re.MULTILINE,
    )


def scrub(text: str, names: list[str] | None = None) -> str:
    """text with the user's name in folder paths replaced by <user>."""
    for name in user_names() if names is None else names:
        text = _component(name).sub(USER, text)
    return text


def scrub_name(file_name: str, names: list[str] | None = None) -> str:
    """A file name with the user's name in it replaced by (user)."""
    for name in user_names() if names is None else names:
        file_name = re.sub(
            r"(?<![^\W_])" + re.escape(name) + r"(?![^\W_])",
            USER_IN_NAMES,
            file_name,
            flags=re.IGNORECASE,
        )
    return file_name


def default_name() -> str:
    stamp = datetime.fromtimestamp(clock.now()).strftime("%Y-%m-%d %H%M")
    return f"Gremlin-Platforms diagnostics {stamp}.zip"


def desktop_folder() -> Path:
    """The user's Desktop (the Save dialog starts there)."""
    try:
        from PySide6 import QtCore

        found = QtCore.QStandardPaths.writableLocation(
            QtCore.QStandardPaths.StandardLocation.DesktopLocation
        )
        if found:
            return Path(found)
    except Exception:
        pass
    return Path(os.environ.get("USERPROFILE", "") or Path.home()) / "Desktop"


def versions() -> dict:
    from gremlin import util

    out: dict = {
        "program": "Gremlin-Platforms R1",
        "version": util.get_code_version(),
        "windows": platform.platform(),
        "python": sys.version.split()[0],
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    try:
        win = sys.getwindowsversion()  # type: ignore[attr-defined]
        out["windowsBuild"] = f"{win.major}.{win.minor}.{win.build}"
        out["windowsEdition"] = platform.win32_edition()
    except Exception:
        pass
    try:
        import PySide6
        from PySide6 import QtCore

        out["pyside"] = PySide6.__version__
        out["qt"] = QtCore.qVersion()
    except Exception:
        pass
    return out


def _guid_text(value: object) -> str:
    return str(value or "").strip().strip("{}").upper()


def devices() -> dict:
    """The device list from the input side: every device the input driver
    lists now, and every device module (input modules say whether their
    device is connected)."""
    from gremlin.modules import hardware, registry

    out: dict = {"devices": [], "modules": []}
    try:
        for dev in hardware.devices():
            out["devices"].append({
                "name": str(dev.name),
                "id": _guid_text(dev.device_guid),
                "kind": "vJoy device" if dev.is_virtual else "Game controller",
                "connected": True,
                "vendorId": f"{int(dev.vendor_id):04X}",
                "productId": f"{int(dev.product_id):04X}",
                "axes": int(dev.axis_count),
                "buttons": int(dev.button_count),
                "hats": int(dev.hat_count),
            })
    except Exception as exc:
        out["devicesError"] = f"{type(exc).__name__}: {exc}"
    try:
        for module in registry.modules():
            row: dict = {
                "name": module.name,
                "id": _guid_text(module.bound_guid),
                "kind": "Output module" if module.is_output else "Input module",
                "file": module.path.name,
            }
            if not module.is_output:
                guid = module.bound_guid
                try:
                    row["connected"] = bool(guid) and hardware.device_connected(guid)
                except Exception:
                    row["connected"] = False
            out["modules"].append(row)
    except Exception as exc:
        out["modulesError"] = f"{type(exc).__name__}: {exc}"
    return out


@dataclass
class Plan:
    """What goes in the zip: read on the main thread, written on a worker."""

    logs: Path | None
    settings: Path | None
    devices: dict
    versions: dict
    profile_name: str = ""
    # The open profile as XML, or None when it is left out.
    profile_text: str | None = None
    names: list[str] = field(default_factory=user_names)
    made: str = ""


def _profile() -> tuple[str, str | None]:
    """The open profile's file name and its text as it is now (unsaved
    changes included)."""
    from gremlin import shared_state

    profile = shared_state.current_profile
    if profile is None:
        return "", None
    name = Path(profile.fpath).name if profile.fpath else "Untitled.xml"
    try:
        return name, profile._xml_text()
    except Exception:
        logging.getLogger("system").exception("Diagnostics: profile text")
        if profile.fpath and Path(profile.fpath).is_file():
            return name, Path(profile.fpath).read_text(encoding="utf-8-sig")
        return name, None


def collect(include_profile: bool) -> Plan:
    """What to save, read on the main thread."""
    from gremlin import util

    try:
        logs: Path | None = util.logs_dir()
    except Exception:
        logs = None
    try:
        settings: Path | None = Path(util.userprofile_path()) / "configuration.json"
    except Exception:
        settings = None
    name, text = _profile() if include_profile else ("", None)
    return Plan(
        logs=logs,
        settings=settings,
        devices=devices(),
        versions=versions(),
        profile_name=name,
        profile_text=text,
        made=datetime.fromtimestamp(clock.now()).isoformat(timespec="seconds"),
    )


def _read_text(path: Path) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if size > MAX_LOG_BYTES:
            handle.seek(size - MAX_LOG_BYTES)
        data = handle.read()
    text = data.decode("utf-8", errors="replace")
    if size > MAX_LOG_BYTES:
        kept = MAX_LOG_BYTES // 1024
        text = f"[only the last {kept} KB of {size // 1024} KB]\n" + text
    return text


def _readme(plan: Plan, included: list[str]) -> str:
    lines = [
        "Gremlin-Platforms diagnostics",
        f"Made: {plan.made}",
        "",
        "The user's name in folder paths is replaced by <user>"
        " (in file names by (user)).",
        "",
        "Contents:",
        *[f"  {name}" for name in included],
    ]
    if plan.profile_text is None:
        lines += ["", "The open profile is not included."]
    return "\n".join(lines) + "\n"


def write_zip(plan: Plan, dest: Path) -> None:
    """Writes the zip at dest (a part file, then swapped in, so a failure
    leaves no half zip). Raises OSError when it can't be written."""
    dest = Path(dest)
    names = plan.names
    entries: list[tuple[str, str]] = []

    def add(arcname: str, text: str) -> None:
        entries.append((scrub_name(arcname, names), scrub(text, names)))

    add("versions.json", json.dumps(plan.versions, indent=2))
    add("devices.json", json.dumps(plan.devices, indent=2))
    if plan.settings is not None:
        try:
            add(f"settings/{plan.settings.name}", _read_text(plan.settings))
        except OSError as exc:
            add("settings/not-read.txt", f"{plan.settings}: {exc.strerror or exc}")
    if plan.logs is not None and plan.logs.is_dir():
        for path in sorted(plan.logs.iterdir()):
            if not path.is_file():
                continue
            try:
                add(f"logs/{path.name}", _read_text(path))
            except OSError as exc:
                add(f"logs/{path.name}.not-read.txt", f"{path}: {exc.strerror or exc}")
    if plan.profile_text is not None:
        add(f"profile/{plan.profile_name or 'profile.xml'}", plan.profile_text)
    entries.insert(0, ("README.txt", _readme(plan, [n for n, _t in entries])))

    part = dest.with_name(dest.name + ".part")
    try:
        with zipfile.ZipFile(part, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for arcname, text in entries:
                zf.writestr(arcname, text.encode("utf-8"))
        os.replace(part, dest)
    except BaseException:
        try:
            part.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def failure_text(dest: Path, exc: BaseException | None = None) -> str:
    """Which file, which folder and why (as 07 Q19)."""
    from gremlin.ui.hardware_profile import export_failure

    reason = ""
    if isinstance(exc, OSError) and not isinstance(
        exc, (PermissionError, FileNotFoundError)
    ):
        reason = str(exc.strerror or exc)
    return export_failure(
        Path(dest), lead=FAILURE_LEAD, reason=reason, fallback=_FALLBACK
    )


def save(plan: Plan, dest: Path) -> tuple[bool, str]:
    """write_zip, then (ok, message): where the zip went, or the failure."""
    dest = Path(dest)
    try:
        write_zip(plan, dest)
    except Exception as exc:
        logging.getLogger("system").warning(f"Diagnostics: {dest} not written: {exc}")
        try:
            return False, failure_text(dest, exc)
        except Exception:
            return False, f"{FAILURE_LEAD} {dest.name} could not be written."
    return True, f"Diagnostics saved to {dest}."
