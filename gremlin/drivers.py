# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Driver facts, detection and the job/result files for driver setup.

Spec: 01 S187-S192, 06 S185-S188, 12 S25/S25a/S25b. No Qt and no imports
from the rest of the program: Gremlin Device Helper imports this module.

Registry and file-version reads go through a `reg` object (the real one is
`WindowsRegistry`; tests pass `MemoryRegistry`). It has three methods:

    value(path, name) -> str | None     HKLM, 64-bit view then 32-bit view
    subkeys(path) -> list[str]          HKLM, both views, no duplicates
    file_version(path) -> str           "" when unreadable
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from gremlin import axis_names

PathLike = str | os.PathLike[str]


class Registry(Protocol):
    def value(self, path: str, name: str) -> str | None: ...
    def subkeys(self, path: str) -> list[str]: ...
    def file_version(self, path: str) -> str: ...


class RealRunnerBlocked(RuntimeError):
    """A real runner (installer, signer check, network) was called from a test."""


def _under_test() -> bool:
    return bool(os.environ.get("PYTEST_CURRENT_TEST")) or "pytest" in sys.modules


@dataclass(frozen=True)
class DriverInfo:
    key: str
    name: str
    bundled_version: str
    bundled_file: str
    sha256: str  # "" = not known yet: never run
    signer_prefix: str
    repo: str | None
    asset_regex: str | None
    install_args: tuple[str, ...]
    restart_codes: tuple[int, ...]


_MSI_ARGS = ("/exenoui", "/qn", "/norestart")  # UNTESTED (plan: "Still to test")

DRIVERS: dict[str, DriverInfo] = {
    "vjoy": DriverInfo(
        key="vjoy",
        name="vJoy",
        bundled_version="2.2.2.0",
        bundled_file="vJoySetup_v2.2.2.0_Win10_Win11.exe",
        sha256="ef569a3105cd301b89580f18f60c66b339e95296acf2c0dfcaf4b4bbf8ab68fe",
        signer_prefix="Brunner Elektronik AG",
        repo="BrunnerInnovation/vJoy",
        asset_regex=r"vJoySetup_v[\d.]+_Win10_Win11\.exe",
        install_args=("/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-"),
        restart_codes=(8,),
    ),
    "vigembus": DriverInfo(
        key="vigembus",
        name="ViGEmBus",
        bundled_version="1.22.0",
        bundled_file="ViGEmBus_1.22.0_x64_x86_arm64.exe",
        sha256="89220a7865076b342892f98865f3499fb7c4cfd673159e89d352c360fd014c6a",
        signer_prefix="Nefarius Software Solutions",
        repo=None,  # retired: no newer release will come
        asset_regex=None,
        install_args=_MSI_ARGS,
        restart_codes=(3010, 1641),
    ),
    "hidhide": DriverInfo(
        key="hidhide",
        name="HidHide",
        bundled_version="1.5.230",
        bundled_file="HidHide_1.5.230_x64.exe",
        sha256="f4bbbcb82e6258641b887c74bc81c4c5f66e4aa811808dfc304347687b7605f6",
        signer_prefix="Nefarius Software Solutions",
        repo="nefarius/HidHide",
        asset_regex=r"HidHide_[\d.]+_x64\.exe",
        install_args=_MSI_ARGS,
        restart_codes=(3010, 1641),
    ),
}

# The Visual C++ Runtime (spec 01 S193, 06 S185): only setup installs and
# updates it (its Pascal script reads this entry). It is not in DRIVERS, and
# Tools > Drivers and Gremlin Device Helper never handle it.
RUNTIME = DriverInfo(
    key="vcredist",
    name="Microsoft Visual C++ Runtime",
    bundled_version="14.44.35211",
    bundled_file="VC_redist.x64.exe",
    sha256="cc0ff0eb1dc3f5188ae6300faef32bf5beeba4bdd6e8e445a9184072096b713b",
    signer_prefix="Microsoft Corporation",
    repo=None,
    asset_regex=None,
    install_args=("/install", "/quiet", "/norestart"),
    restart_codes=(3010,),
)
RUNTIME_RESTART_CODE = 3010
RUNTIME_DONE_CODES = (0, 1638, 3010)  # done, newer present, done + restart (setup)
RUNTIME_KEYS = (
    r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
    r"SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64",
)

UNINSTALL = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
VJOY_UNINSTALL = UNINSTALL + r"\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1"
HIDHIDE_KEY = r"SOFTWARE\Nefarius Software Solutions e.U.\HidHide"
# Windows' Uninstall entry names: the installer's own, then the one in Nefarius's docs.
VIGEMBUS_DISPLAY_NAMES = (
    "ViGEm Bus Driver",
    "Nefarius Virtual Gamepad Emulation Bus Driver",
)


def vigembus_sys_path() -> str:
    root = os.environ.get("SystemRoot", r"C:\Windows")
    return os.path.join(root, "System32", "drivers", "ViGEmBus.sys")


# -- registry -----------------------------------------------------------------


class WindowsRegistry:
    """Read-only HKLM access through winreg, plus file versions."""

    def value(self, path: str, name: str) -> str | None:
        import winreg

        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ | view
                ) as key:
                    data, _ = winreg.QueryValueEx(key, name)
                    return str(data)
            except OSError:
                continue
        return None

    def subkeys(self, path: str) -> list[str]:
        import winreg

        names: list[str] = []
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE, path, 0, winreg.KEY_READ | view
                ) as key:
                    index = 0
                    while True:
                        try:
                            name = winreg.EnumKey(key, index)
                        except OSError:
                            break
                        if name not in names:
                            names.append(name)
                        index += 1
            except OSError:
                continue
        return names

    def file_version(self, path: str) -> str:
        if os.name != "nt" or not os.path.isfile(path):
            return ""
        import ctypes
        from ctypes import wintypes

        try:
            version = ctypes.WinDLL("version")
            size = version.GetFileVersionInfoSizeW(path, None)
            if not size:
                return ""
            buffer = ctypes.create_string_buffer(size)
            if not version.GetFileVersionInfoW(path, 0, size, buffer):
                return ""
            pointer = ctypes.c_void_p()
            length = wintypes.UINT()
            if not version.VerQueryValueW(
                buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)
            ):
                return ""
            # VS_FIXEDFILEINFO: dwFileVersionMS, dwFileVersionLS at words 2, 3.
            words = ctypes.cast(pointer, ctypes.POINTER(ctypes.c_uint32))
            ms, ls = words[2], words[3]
            return f"{ms >> 16}.{ms & 0xFFFF}.{ls >> 16}.{ls & 0xFFFF}"
        except (OSError, AttributeError, ValueError):
            return ""


class MemoryRegistry:
    """A fake `reg` for tests: {path: {name: value}} plus file versions."""

    def __init__(
        self,
        values: dict[str, dict[str, str]] | None = None,
        files: dict[str, str] | None = None,
    ) -> None:
        self.paths = list((values or {}).keys())
        self.values = {k.lower(): v for k, v in (values or {}).items()}
        self.files = {k.lower(): v for k, v in (files or {}).items()}

    def value(self, path: str, name: str) -> str | None:
        return self.values.get(path.lower(), {}).get(name)

    def subkeys(self, path: str) -> list[str]:
        prefix = path.lower().rstrip("\\") + "\\"
        names: list[str] = []
        for key in self.paths:
            if key.lower().startswith(prefix):
                name = key[len(prefix) :].split("\\", 1)[0]
                if name not in names:
                    names.append(name)
        return names

    def file_version(self, path: str) -> str:
        return self.files.get(path.lower(), "")


def _reg(reg: Registry | None) -> Registry:
    return reg if reg is not None else WindowsRegistry()


def uninstall_entry(
    display_prefix: str, reg: Registry | None = None
) -> tuple[str, dict[str, str]] | None:
    """The first Uninstall subkey whose DisplayName starts with the prefix."""
    reg = _reg(reg)
    for name in reg.subkeys(UNINSTALL):
        path = UNINSTALL + "\\" + name
        display = reg.value(path, "DisplayName") or ""
        if display.startswith(display_prefix):
            fields = {
                field_name: reg.value(path, field_name) or ""
                for field_name in ("DisplayName", "DisplayVersion", "UninstallString")
            }
            return name, fields
    return None


# -- versions and status ------------------------------------------------------


def version_tuple(text: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", text or ""))


def compare(a: str, b: str) -> int:
    left, right = version_tuple(a), version_tuple(b)
    width = max(len(left), len(right))
    left += (0,) * (width - len(left))
    right += (0,) * (width - len(right))
    return (left > right) - (left < right)


def installed_version(key: str, reg: Registry | None = None) -> str:
    reg = _reg(reg)
    if key == "vjoy":
        return reg.value(VJOY_UNINSTALL, "DisplayVersion") or ""
    if key == "vigembus":
        # The entry first: the .sys file's version can lag the installer's
        # (1.22.0 installs a file that says 1.21.442.0).
        for display_name in VIGEMBUS_DISPLAY_NAMES:
            entry = uninstall_entry(display_name, reg)
            if entry and entry[1]["DisplayVersion"]:
                return entry[1]["DisplayVersion"]
        return reg.file_version(vigembus_sys_path())
    if key == "hidhide":
        return reg.value(HIDHIDE_KEY, "Version") or ""
    raise KeyError(key)


def _runtime_key(reg: Registry) -> str | None:
    """The first Runtimes key (64-bit view, then WOW6432Node) with Installed=1."""
    for path in RUNTIME_KEYS:
        if (reg.value(path, "Installed") or "").strip() == "1":
            return path
    return None


def runtime_installed(reg: Registry | None = None) -> bool:
    return _runtime_key(_reg(reg)) is not None


def runtime_version(reg: Registry | None = None) -> str:
    """The installed runtime's version ("v14.51.36247.00" -> "14.51.36247.00")."""
    reg = _reg(reg)
    path = _runtime_key(reg)
    if path is None:
        return ""
    return (reg.value(path, "Version") or "").strip().lstrip("vV")


@dataclass(frozen=True)
class DriverStatus:
    key: str
    name: str
    installed: str
    bundled: str
    state: str  # "missing" | "older" | "same" | "newer"


def status(key: str, reg: Registry | None = None) -> DriverStatus:
    info = DRIVERS[key]
    installed = installed_version(key, reg)
    if not installed:
        state = "missing"
    else:
        state = {-1: "older", 0: "same", 1: "newer"}[
            compare(installed, info.bundled_version)
        ]
    return DriverStatus(key, info.name, installed, info.bundled_version, state)


def all_status(reg: Registry | None = None) -> list[DriverStatus]:
    reg = _reg(reg)
    return [status(key, reg) for key in DRIVERS]


# -- newer releases -----------------------------------------------------------


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    name: str


Fetch = Callable[[str, float], bytes]


def real_fetch(url: str, timeout: float) -> bytes:
    if _under_test():
        raise RealRunnerBlocked("drivers.real_fetch called from a test")
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "Gremlin-Platforms",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def latest_release(
    key: str, fetch: Fetch | None = None, timeout: float = 5.0
) -> Release | None:
    """GitHub's latest release of the driver; None for no repo, no network, error."""
    info = DRIVERS[key]
    if not info.repo or not info.asset_regex:
        return None
    fetch = fetch or real_fetch
    url = f"https://api.github.com/repos/{info.repo}/releases/latest"
    try:
        data = json.loads(fetch(url, timeout))
        version = str(data["tag_name"]).lstrip("vV")
        for asset in data.get("assets", []):
            name = str(asset.get("name", ""))
            if re.fullmatch(info.asset_regex, name):
                link = str(asset.get("browser_download_url", ""))
                if link.startswith("https://"):
                    return Release(version, link, name)
    except RealRunnerBlocked:
        raise
    except Exception:  # noqa: BLE001 - no network or a bad answer: bundled only
        return None
    return None


# -- file checks --------------------------------------------------------------


def sha256_of(path: PathLike) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_bundled(path: PathLike, info: DriverInfo) -> str:
    """ "" when the bundled file's SHA-256 matches, else why it must not run."""
    if not info.sha256:
        return f"no SHA-256 is known for the bundled {info.name}"
    if not os.path.isfile(path):
        return f"bundled {info.name} file not found: {path}"
    try:
        actual = sha256_of(path)
    except OSError as error:
        return f"bundled {info.name} file could not be read: {error}"
    if actual.lower() != info.sha256.lower():
        return f"bundled {info.name} file fingerprint (SHA-256) does not match"
    return ""


Signer = Callable[[str], tuple[bool, str]]
SIGNER_TIMEOUT_S = 30.0


def real_signer(path: PathLike) -> tuple[bool, str]:
    """PowerShell Get-AuthenticodeSignature: (valid, signer subject)."""
    if _under_test():
        raise RealRunnerBlocked("drivers.real_signer called from a test")
    if os.name != "nt":
        return False, ""
    literal = str(path).replace("'", "''")
    script = (
        # UTF-8 out, read as bytes: signer subjects carry non-ASCII letters
        # (vJoy's "S=Zürich"), which broke a text-mode read (found on the
        # user's PC, 2026-11-21).
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        f"$s = Get-AuthenticodeSignature -LiteralPath '{literal}'; "
        "Write-Output $s.Status; Write-Output $s.SignerCertificate.Subject"
    )
    try:
        done = subprocess.run(
            [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                script,
            ],
            capture_output=True,
            timeout=SIGNER_TIMEOUT_S,
            check=False,
            shell=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return False, ""
    return signer_output(done.stdout or b"")


def signer_output(raw: bytes) -> tuple[bool, str]:
    """(valid, subject) from real_signer's PowerShell output (UTF-8; any
    byte that isn't is replaced, never an error)."""
    text = raw.decode("utf-8", errors="replace")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return False, ""
    return lines[0] == "Valid", (lines[1] if len(lines) > 1 else "")


def subject_cn(subject: str) -> str:
    """The CN part of a certificate subject ("CN=Name, O=..." or quoted)."""
    match = re.search(r'(?:^|,)\s*CN=("(?:[^"]|"")*"|[^,]*)', subject or "")
    if not match:
        return ""
    value = match.group(1).strip()
    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1].replace('""', '"')
    return value


def check_download(
    path: PathLike, info: DriverInfo, signer: Signer | None = None
) -> str:
    """ "" when the Windows signature is valid and from the expected signer."""
    if not os.path.isfile(path):
        return f"downloaded {info.name} file not found: {path}"
    signer = signer or real_signer
    try:
        valid, subject = signer(str(path))
    except RealRunnerBlocked:
        raise
    except Exception as error:  # noqa: BLE001 - reported, never a crash
        return f"downloaded {info.name} signature could not be checked: {error}"
    if not valid:
        return f"downloaded {info.name} has no valid digital signature"
    name = subject_cn(subject)
    if not name.startswith(info.signer_prefix):
        return (
            f"downloaded {info.name} is signed by {name or 'unknown'}, "
            f"not {info.signer_prefix}"
        )
    return ""


# -- vJoy layouts -------------------------------------------------------------

VJOY_AXES = tuple(a.vjoy_config for a in axis_names.AXES)
VJOY_AXIS_LABELS = tuple(a.short for a in axis_names.AXES)
VJOY_MAX_DEVICES = 16
_SHORT_BY_VJOY = {a.vjoy_config: a.short for a in axis_names.AXES}


def axis_label(name: str) -> str:
    """vJoyConfig name -> the axis table's short name: "sl0" -> "S1"."""
    return _SHORT_BY_VJOY.get(name.lower(), name.upper())


@dataclass
class VJoyDevice:
    id: int
    axes: tuple[str, ...] = VJOY_AXES  # ticked axis names, VJOY_AXES order
    buttons: int = 128
    hats: int = 4  # continuous

    def __post_init__(self) -> None:
        names = {str(a).lower() for a in self.axes}
        known = tuple(a for a in VJOY_AXES if a in names)
        self.axes = known + tuple(sorted(names - set(VJOY_AXES)))

    def problem(self) -> str:
        if not 1 <= self.id <= VJOY_MAX_DEVICES:
            return f"device number {self.id} is outside 1-16"
        unknown = [a for a in self.axes if a not in VJOY_AXES]
        if unknown:
            return f"device {self.id}: unknown axis {', '.join(unknown)}"
        if not 0 <= self.buttons <= 128:
            return f"device {self.id}: buttons {self.buttons} outside 0-128"
        if not 0 <= self.hats <= 4:
            return f"device {self.id}: hats {self.hats} outside 0-4"
        return ""


def default_buttons(vjoy_id: int) -> int:
    """Button count for a new device: vJoy 1 = 128, 2 = 127, ... 0-128.

    Every device gets its own count so the program can tell them apart.
    """
    return max(0, min(128, 129 - vjoy_id))


def new_device(vjoy_id: int) -> VJoyDevice:
    """A new device: all axes, the countdown button count, 4 hats."""
    return VJoyDevice(vjoy_id, VJOY_AXES, default_buttons(vjoy_id), 4)


PRESETS: dict[str, list[VJoyDevice]] = {
    "1 device, full": [new_device(1)],
    "2 devices, full": [new_device(1), new_device(2)],
}


def layout_key(dev: VJoyDevice) -> tuple[int, int, int]:
    """The program's own sameness rule: axes, buttons, hats."""
    return (len(dev.axes), dev.buttons, dev.hats)


def alike_devices(devices: list[VJoyDevice]) -> list[list[int]]:
    """Groups of 2+ device ids with the same layout, sorted."""
    by_key: dict[tuple[int, int, int], list[int]] = {}
    for dev in devices:
        by_key.setdefault(layout_key(dev), []).append(dev.id)
    groups = [sorted(ids) for ids in by_key.values() if len(ids) > 1]
    return sorted(groups)


def can_untick_axis(dev: VJoyDevice, name: str) -> bool:
    """False when `name` is the device's only ticked axis (vJoyConfig without
    -a would give the device every axis)."""
    return not (name in dev.axes and len(dev.axes) <= 1)


def in_use_warning(ids: list[int]) -> str:
    """The Yes/No question before changing devices another program holds."""
    ids = sorted(ids)
    if not ids:
        return ""
    names = [f"vJoy {i}" for i in ids]
    if len(names) == 1:
        who, verb, them = names[0], "is", "it"
    else:
        who = ", ".join(names[:-1]) + " and " + names[-1]
        verb, them = "are", "them"
    return (
        f"{who} {verb} in use by another program. Changing {them} can stop "
        "that program's controls working until it restarts. "
        f"Change {them} anyway?"
    )


def alike_warning(groups: list[list[int]]) -> str:
    """One sentence per group of alike devices; "" when there are none."""
    sentences = []
    for group in groups:
        names = [f"vJoy {i}" for i in group]
        who = ", ".join(names[:-1]) + " and " + names[-1]
        sentences.append(
            f"{who} have the same number of axes, buttons and hats, so "
            "Gremlin-Platforms can't tell them apart and won't use them."
        )
    return " ".join(sentences)


# -- job and result files -----------------------------------------------------

JOB_OPS = ("install", "update", "remove", "vjoy_setup")
FILE_KINDS = ("download", "bundled")
RESULT_STATES = ("waiting", "running", "done", "failed")
FILE_VERSION = 1


@dataclass
class Job:
    op: str
    driver: str
    files: list[dict] = field(default_factory=list)
    devices: list[VJoyDevice] = field(default_factory=list)


@dataclass
class JobResult:
    state: str
    message: str = ""
    restart: bool = False
    used: str = ""  # "bundled" | "download" | ""


def _atomic_write_json(path: PathLike, data: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
        handle.flush()
        os.fsync(handle.fileno())
    # A reader holding the file open on Windows blocks the replace briefly.
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def write_jobs(path: PathLike, jobs: list[Job]) -> None:
    data = {
        "version": FILE_VERSION,
        "jobs": [
            {
                "op": job.op,
                "driver": job.driver,
                "files": [
                    {"path": str(f["path"]), "kind": f["kind"]} for f in job.files
                ],
                "devices": [
                    {
                        "id": d.id,
                        "axes": list(d.axes),
                        "buttons": d.buttons,
                        "hats": d.hats,
                    }
                    for d in job.devices
                ],
            }
            for job in jobs
        ],
    }
    _atomic_write_json(path, data)


def _axes(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(
        isinstance(a, str) and a in VJOY_AXES for a in value
    ):
        raise ValueError("axes is not a list of known axis names")
    return tuple(value)


def _int(value: object, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{what} is not a whole number")
    return value


def read_jobs(path: PathLike) -> list[Job]:
    """The jobs in a job file; ValueError for a missing or bad file."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"job file could not be read: {error}") from error
    if not isinstance(data, dict) or data.get("version") != FILE_VERSION:
        raise ValueError("job file has no version 1")
    raw_jobs = data.get("jobs")
    if not isinstance(raw_jobs, list):
        raise ValueError("job file has no job list")
    jobs: list[Job] = []
    for number, raw in enumerate(raw_jobs, 1):
        if not isinstance(raw, dict):
            raise ValueError(f"job {number} is not an object")
        op, driver = raw.get("op"), raw.get("driver")
        if op not in JOB_OPS:
            raise ValueError(f"job {number}: unknown op {op!r}")
        if not isinstance(driver, str) or driver not in DRIVERS:
            raise ValueError(f"job {number}: unknown driver {driver!r}")
        files = raw.get("files", [])
        if not isinstance(files, list):
            raise ValueError(f"job {number}: files is not a list")
        clean_files: list[dict] = []
        for item in files:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("path"), str)
                or item.get("kind") not in FILE_KINDS
            ):
                raise ValueError(f"job {number}: bad file entry {item!r}")
            clean_files.append({"path": item["path"], "kind": item["kind"]})
        if op in ("install", "update") and not clean_files:
            raise ValueError(f"job {number}: {op} lists no file")
        raw_devices = raw.get("devices", [])
        if not isinstance(raw_devices, list):
            raise ValueError(f"job {number}: devices is not a list")
        devices: list[VJoyDevice] = []
        for item in raw_devices:
            if not isinstance(item, dict):
                raise ValueError(f"job {number}: bad device entry {item!r}")
            device = VJoyDevice(
                _int(item.get("id"), "device id"),
                _axes(item.get("axes", list(VJOY_AXES))),
                _int(item.get("buttons", 128), "buttons"),
                _int(item.get("hats", 4), "hats"),
            )
            problem = device.problem()
            if problem:
                raise ValueError(f"job {number}: {problem}")
            devices.append(device)
        if op == "vjoy_setup" and (driver != "vjoy" or not devices):
            raise ValueError(f"job {number}: vjoy_setup needs vjoy and devices")
        if op == "remove" and driver != "hidhide":
            raise ValueError(f"job {number}: only HidHide can be removed")
        jobs.append(Job(op, driver, clean_files, devices))
    return jobs


def write_results(path: PathLike, results: list[JobResult], finished: bool) -> None:
    data = {
        "version": FILE_VERSION,
        "finished": bool(finished),
        "jobs": [
            {
                "state": r.state,
                "message": r.message,
                "restart": bool(r.restart),
                "used": r.used,
            }
            for r in results
        ],
    }
    _atomic_write_json(path, data)


def read_results(path: PathLike) -> tuple[list[JobResult], bool]:
    """The results and the finished flag; ([], False) when missing or partial."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or data.get("version") != FILE_VERSION:
            return [], False
        results = [
            JobResult(
                state=str(item["state"]),
                message=str(item.get("message", "")),
                restart=bool(item.get("restart", False)),
                used=str(item.get("used", "")),
            )
            for item in data["jobs"]
        ]
        if any(r.state not in RESULT_STATES for r in results):
            return [], False
        return results, bool(data.get("finished", False))
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError):
        return [], False


# -- the HidHide two-step update ----------------------------------------------


def app_dir() -> Path | None:
    """Folder of the frozen exe, else None (running from source)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return None


def pending_path(app: Path) -> Path:
    return Path(app) / "drivers" / "pending.json"


def read_pending(app: Path) -> dict | None:
    try:
        with open(pending_path(app), encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, UnicodeDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) and data else None


def write_pending(app: Path, data: dict) -> None:
    _atomic_write_json(pending_path(app), data)


def clear_pending(app: Path) -> None:
    pending_path(app).unlink(missing_ok=True)
