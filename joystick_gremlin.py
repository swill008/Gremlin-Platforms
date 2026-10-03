# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import argparse
import ctypes
import json
import logging
import logging.handlers
import os
import subprocess
import sys
import time
import traceback
import types
from pathlib import Path
from typing import Any


def _windows_scaling_disabled() -> bool:
    """Read the User Interface option before Qt loads. Default is Windows scaling on."""
    root = os.environ.get("USERPROFILE") or os.environ.get("userprofile")
    if not root:
        return False
    # Same folder as gremlin.util.USER_DATA_FOLDER, which cannot be imported
    # before Qt loads.
    path = os.path.join(root, "Gremlin Platforms", "configuration.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
        raw = data["ui"]["general"]["disable-windows-scaling"]["value"]
    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return False
    return str(raw).strip().lower() in ("1", "true", "yes")


# Value at launch, put back before a restart so the new process reads the
# setting afresh.
_LAUNCH_HIGHDPI_SCALING = os.environ.get("QT_ENABLE_HIGHDPI_SCALING")
if _windows_scaling_disabled():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"

from PySide6 import (
    QtCore,
    QtGui,
    QtQml,
    QtQuick,
    QtWidgets,
)

import dill
import resources  # noqa: F401
from gremlin.config import Configuration
from gremlin.types import PropertyType

install_path = os.path.normcase(os.path.dirname(os.path.abspath(sys.argv[0])))
os.chdir(install_path)

# Universal with scaled sizes, from theme/GremlinStyle.
os.environ["QT_QUICK_CONTROLS_STYLE"] = "GremlinStyle"
# Qt's own message and color dialogs pick their look by style name, so point
# them at the Universal versions GremlinStyle is built from.
os.environ["QT_FILE_SELECTORS"] = ",".join(
    filter(None, [os.environ.get("QT_FILE_SELECTORS", ""), "Universal"])
)

import gremlin.util

sys.path.insert(0, gremlin.util.data_folder())
gremlin.util.setup_userprofile()

# Several of these modules set things up when they load (settings, QML
# types), in this order; it has not been checked that any other order gives
# the same result, so keep it. (Circular imports are a separate matter:
# test_modules_import_alone loads every module on its own.)
# isort: off
import gremlin.audio_player
import gremlin.config
import gremlin.device_initialization
import gremlin.error
import gremlin.event_handler
import gremlin.mode_manager
import gremlin.plugin_manager
import gremlin.signal
import gremlin.tts
import gremlin.types
import gremlin.ui.action_image_generator
import gremlin.ui.backend
import gremlin.ui.button_map_options
import gremlin.ui.system_tray
import gremlin.ui.option
import gremlin.ui.osc_option  # noqa: F401
import gremlin.ui.log_option  # noqa: F401
import gremlin.ui.tools
import gremlin.ui.ui_scale_option
import gremlin.ui.update_model  # noqa: E402
import gremlin.ui.util
import gremlin.osc
import gremlin.ui.osc_device_model  # noqa: F401
import gremlin.ui.device_names  # noqa: F401
import gremlin.ui.hidhide  # noqa: F401
import gremlin.ui.vjoy_status
import gremlin.ui.window_placement
import gremlin.ui.module_model  # noqa: F401
import gremlin.deferred_write
import gremlin.ui.debug_mode
import gremlin.ui.live_debug  # noqa: F401
import gremlin.ui.binding_catalog  # noqa: F401  # Device-Configuration-Macro Change
import gremlin.ui.logical_layout  # noqa: F401
import gremlin.ui.module_pairing  # noqa: F401
import gremlin.ui.module_calibration  # noqa: F401
import gremlin.ui.shell_option  # noqa: F401
import gremlin.osc_persist  # noqa: F401
# isort: on


def configure_logger(config: dict[str, Any]) -> None:
    logger = logging.getLogger(config["name"])
    logger.setLevel(config["level"])
    if config["mode"] == "rotate":
        handler = logging.handlers.RotatingFileHandler(
            config["logfile"], maxBytes=1 * 1024 * 1024, backupCount=1
        )
    elif config["mode"] == "session":
        handler = logging.FileHandler(config["logfile"], mode="w")
    else:
        raise gremlin.error.GremlinError(f"Invalid logging mode: {config['mode']}")
    handler.setLevel(config["level"])
    formatter = logging.Formatter(config["format"], "%Y-%m-%d %H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    if config["mode"] != "session":
        logger.debug("-" * 80)
        logger.debug(time.strftime("%Y-%m-%d %H:%M"))
        logger.debug("Starting Gremlin-Platforms R1")
        logger.debug("-" * 80)


def exception_hook(
    exception_type: type[BaseException],
    value: BaseException,
    trace: types.TracebackType | None,
) -> None:
    msg = " ".join(traceback.format_exception(exception_type, value, trace))
    logging.getLogger("system").error(f"Unhandled exception: {msg}")
    try:
        gremlin.signal.display_error("An unhandled exception occurred.", msg)
    except RuntimeError:
        pass


def _message_box(text: str, title: str, flags: int) -> int:
    """A Windows message box (shown even off-screen; tests replace this)."""
    return ctypes.windll.user32.MessageBoxW(None, text, title, flags)


class StartupError(Exception):
    """The program could not start; details says why (shown to the user)."""

    def __init__(self, summary: str, details: str = "") -> None:
        super().__init__(summary)
        self.details = details


def tell_could_not_start(summary: str, details: str) -> None:
    """Shows why the program could not start, in a Windows message box: the
    program's own windows may not exist yet. The text can be copied with
    Ctrl+C for a bug report."""
    lines = [line for line in details.strip().splitlines() if line.strip()]
    shown = "\n".join(lines[-12:])
    try:
        logs = str(gremlin.util.logs_dir())
    except Exception:
        logs = os.path.join(gremlin.util.userprofile_path(), "logs")
    text = (
        "Gremlin-Platforms could not start.\n\n"
        f"{summary}\n\n{shown}\n\n"
        f"The log files are in:\n{logs}\n\n"
        "Press Ctrl+C to copy this message."
    )
    # MB_OK | MB_ICONERROR
    _message_box(text, "Gremlin-Platforms R1", 0x10)


def shutdown_cleanup() -> None:
    """Stop runtime threads and virtual devices so File/Exit does not leave a
    process."""
    log = logging.getLogger("system")
    try:
        listener = gremlin.event_handler.EventListener()
        timer = getattr(listener, "_device_update_timer", None)
        if timer is not None:
            try:
                timer.cancel()
            except Exception:
                pass
            listener._device_update_timer = None
        listener.terminate()
        mouse_hook = getattr(listener, "mouse_hook", None)
        if mouse_hook is not None:
            try:
                mouse_hook.stop()
            except Exception:
                pass
    except Exception:
        log.exception("Shutdown: event listener")
    try:
        backend = gremlin.ui.backend.Backend()
        if backend.gremlinActive:
            backend.activate_gremlin(False)
        backend.runner.stop()
        backend.process_monitor.stop()
    except Exception:
        log.exception("Shutdown: backend")
    try:
        from gremlin.modules import output

        output.reset_drivers()
    except Exception:
        log.exception("Shutdown: vJoy / Xbox")
    try:
        gremlin.audio_player.AudioPlayer().stop()
    except Exception:
        pass
    try:
        gremlin.tts.TTSManager().stop()
    except Exception:
        pass
    try:
        gremlin.osc.OscRuntime().stop()
    except Exception:
        log.exception("Shutdown: OSC")


def _this_process_tree() -> set[int]:
    tree = {os.getpid()}
    try:
        tree.add(os.getppid())
    except Exception:
        pass
    try:
        class PROCESSENTRY32(ctypes.Structure):
            _fields_ = [
                ("dwSize", ctypes.c_ulong),
                ("cntUsage", ctypes.c_ulong),
                ("th32ProcessID", ctypes.c_ulong),
                ("th32DefaultHeapID", ctypes.c_void_p),
                ("th32ModuleID", ctypes.c_ulong),
                ("cntThreads", ctypes.c_ulong),
                ("th32ParentProcessID", ctypes.c_ulong),
                ("pcPriClassBase", ctypes.c_long),
                ("dwFlags", ctypes.c_ulong),
                ("szExeFile", ctypes.c_wchar * 260),
            ]

        kernel32 = ctypes.windll.kernel32
        snapshot = kernel32.CreateToolhelp32Snapshot(2, 0)
        if snapshot in (0, -1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            return tree
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        parents: dict[int, int] = {}
        if kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
                if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
        kernel32.CloseHandle(snapshot)
        pid = os.getpid()
        for _ in range(8):
            parent = parents.get(pid)
            if not parent or parent in tree or parent <= 4:
                break
            tree.add(parent)
            pid = parent
    except Exception:
        pass
    return tree


def _process_image_name(pid: int) -> str:
    """Returns the executable basename for a PID, or an empty string."""
    if pid <= 0:
        return ""
    kernel32 = ctypes.windll.kernel32
    process_query_limited = 0x1000
    handle = kernel32.OpenProcess(process_query_limited, False, pid)
    if not handle:
        handle = kernel32.OpenProcess(0x0400, False, pid)
    if not handle:
        return ""
    try:
        buf = ctypes.create_unicode_buffer(32768)
        size = ctypes.c_ulong(len(buf))
        query = getattr(kernel32, "QueryFullProcessImageNameW", None)
        if query and query(handle, 0, buf, ctypes.byref(size)):
            return os.path.basename(buf.value).lower()
    except Exception:
        pass
    finally:
        kernel32.CloseHandle(handle)
    return ""


# Installed build first (joystick_gremlin.spec), then the name older builds used.
_GREMLIN_EXE_NAMES = ("gremlin_platforms.exe", "joystick_gremlin.exe")


def _is_gremlin_process(pid: int, python_pids: set[int] | None = None) -> bool:
    """True if the PID is a Gremlin exe or a Python interpreter running it."""
    name = _process_image_name(pid)
    if name in _GREMLIN_EXE_NAMES:
        return True
    if name in ("python.exe", "pythonw.exe"):
        known = python_pids if python_pids is not None else _command_line_process_ids()
        return pid in known
    return False


def _gremlin_window_titles() -> list[str]:
    titles: list[str] = []
    protected = _this_process_tree()
    python_pids = _command_line_process_ids()
    try:
        user32 = ctypes.windll.user32

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def _enum(hwnd: int, _: int) -> bool:
            if not user32.IsWindowVisible(hwnd):
                return True
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            title = buf.value
            if not title or "Gremlin-Platforms" not in title:
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            value = int(pid.value)
            if value in protected or not _is_gremlin_process(value, python_pids):
                return True
            titles.append(title)
            return True

        user32.EnumWindows(_enum, 0)
    except Exception:
        pass
    return titles


def _window_process_ids() -> set[int]:
    pids: set[int] = set()
    protected = _this_process_tree()
    python_pids = _command_line_process_ids()
    try:
        user32 = ctypes.windll.user32

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        def _enum(hwnd: int, _: int) -> bool:
            length = user32.GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            user32.GetWindowTextW(hwnd, buf, length)
            if "Gremlin-Platforms" not in buf.value:
                return True
            pid = ctypes.c_ulong()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            value = int(pid.value)
            if (
                value
                and value not in protected
                and _is_gremlin_process(value, python_pids)
            ):
                pids.add(value)
            return True

        user32.EnumWindows(_enum, 0)
    except Exception:
        pass
    return pids


def _command_line_process_ids() -> set[int]:
    pids: set[int] = set()
    exe_match = " -or ".join(f"$_.Name -eq '{name}'" for name in _GREMLIN_EXE_NAMES)
    try:
        completed = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_Process | Where-Object {"
                f" {exe_match} -or "
                "(($_.Name -eq 'python.exe' -or $_.Name -eq 'pythonw.exe') -and "
                "$_.CommandLine -and ($_.CommandLine -match 'joystick_gremlin\\.py'))"
                "} | ForEach-Object { $_.ProcessId }",
            ],
            capture_output=True,
            text=True,
            timeout=4,
            creationflags=0x08000000,
        )
        for line in completed.stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                pids.add(int(line))
    except Exception:
        pass
    return pids


def _lock_owner_pid() -> int | None:
    lock = QtCore.QLockFile(
        os.path.join(gremlin.util.data_folder(), "gremlin.lock")
    )
    try:
        owner_pid, _host, _app = lock.lockInfo()
        if owner_pid:
            return int(owner_pid)
    except Exception:
        pass
    return None


def _other_gremlin_pids() -> list[int]:
    protected = _this_process_tree()
    pids = _window_process_ids() | _command_line_process_ids()
    owner = _lock_owner_pid()
    if owner:
        pids.add(owner)
    return sorted(pid for pid in pids if pid > 0 and pid not in protected)


def _terminate_other_gremlin(pids: list[int]) -> None:
    protected = _this_process_tree()
    kernel32 = ctypes.windll.kernel32
    process_terminate = 0x0001
    for pid in pids:
        if pid in protected:
            continue
        handle = kernel32.OpenProcess(process_terminate, False, pid)
        if handle:
            kernel32.TerminateProcess(handle, 1)
            kernel32.CloseHandle(handle)
            continue
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                timeout=3,
                creationflags=0x08000000,
            )
        except Exception:
            pass
    time.sleep(0.4)


def _confirm_second_instance(
    lock_held: bool, windows: list[str], pids: list[int]
) -> str:
    pid_text = ", ".join(str(pid) for pid in pids) if pids else "unknown"
    extra = ""
    if windows:
        extra = "\nOpen window:\n- " + "\n- ".join(windows[:4])
    elif lock_held and not pids:
        extra = "\nAnother copy of Gremlin-Platforms is using its lock file."
    hung_hint = ""
    if pids and not windows:
        hung_hint = (
            "\nA Gremlin-Platforms process is running with no visible window."
            " It may be hung."
        )
    text = (
        "Another Gremlin-Platforms window is already running.\n"
        f"Process IDs: {pid_text}"
        f"{extra}{hung_hint}\n\n"
        "Only one copy can own vJoy.\n\n"
        "Yes = Close the other process(es) and start this copy.\n"
        "No = Start this copy anyway. vJoy mapping may not respond.\n"
        "Cancel = Do not start this copy."
    )
    result = _message_box(text, "Gremlin-Platforms R1", 0x33)
    if result == 6:
        return "close_others"
    if result == 7:
        return "continue"
    return "quit"


def acquire_instance_lock() -> QtCore.QLockFile | None:
    lock = QtCore.QLockFile(
        os.path.join(gremlin.util.data_folder(), "gremlin.lock")
    )
    lock.setStaleLockTime(30000)
    if lock.tryLock(100):
        return lock
    return None


def register_config_options() -> None:
    cfg = gremlin.config.Configuration()
    osc_ips = gremlin.osc.local_ipv4_addresses()
    osc_sec = gremlin.osc.OSC_SECTION
    osc_grp = gremlin.osc.OSC_GROUP

    cfg.register(
        "global", "internal", "last-mode", PropertyType.String, "Default",
        "Name of the last active mode", {},
    )
    cfg.register(
        "global", "internal", "last-mode-per-profile", PropertyType.Dict, {},
        "Last active mode for each profile path", {},
    )
    cfg.register(
        "global", "internal", "last-profile", PropertyType.String, "",
        "Most recently used profile", {},
    )
    cfg.register(
        "global", "internal", "recent-profiles", PropertyType.List, [],
        "List of recently opened profiles", {},
    )
    cfg.register(
        "global", "general", "check-for-updates", PropertyType.Bool, True,
        "Check online for a new version when the program starts.", {}, True,
    )
    cfg.register(
        "global", "internal", "skipped-update-version", PropertyType.String, "",
        "Release the user chose to skip in the Update dialog.", {},
    )
    cfg.register(
        "global", "internal", "button-map-recent-colours", PropertyType.List, [],
        "Colors last applied in the Button Map editor, newest first.", {},
    )
    cfg.register(
        "global", "internal", "last-run-version", PropertyType.String, "",
        "Version that ran last, to say so once after an update.", {},
    )
    cfg.register(
        "global", "internal", "update-feed-url", PropertyType.String, "",
        "Release feed used instead of GitHub (testing only).", {},
    )
    plugins = str(Path(gremlin.util.data_folder()) / "plugins")
    cfg.register(
        "global", "files", "plugin-directory", PropertyType.Path, plugins,
        "Directory containing additional action plugins.",
        {
            "is_folder": True,
            "allow_reset": True,
            "default_path": plugins,
        },
        True,
    )
    cfg.register(
        "global", "files", "data-folder", PropertyType.Path,
        gremlin.util.userprofile_path(),
        "Root folder for user files.",
        {
            "is_folder": True,
            "allow_reset": True,
            "default_path": gremlin.util.userprofile_path(),
        },
        True,
    )
    for name, key, description in (
        ("modules", "modules-folder", "Device files, pictures, and imported copies."),
        ("logs", "logs-folder", "Live log and the diagnostic logs."),
        ("profiles", "profiles-folder", "Folder the profile dialogs open in."),
        ("scripts", "scripts-folder", "User scripts."),
        ("export", "export-folder", "Device packs saved from the program."),
        (
            "deleted devices",
            "deleted-devices-folder",
            "Backup packs saved by Delete Device.",
        ),
    ):
        default = str(Path(gremlin.util.data_folder()) / name)
        cfg.register(
            "global", "files", key, PropertyType.Path, default, description,
            {"is_folder": True, "allow_reset": True, "default_path": default},
            True,
        )
    gremlin.util.ensure_data_folders()
    cfg.register(
        "action", "general", "action-priorities", PropertyType.List, [],
        "Priority order of the actions", {}, True,
    )
    cfg.register(
        "global", "general", "device-change-behavior", PropertyType.Selection,
        "Reload",
        "What the program does when a joystick is connected or disconnected.",
        {"valid_options": ["Disable", "Ignore", "Reload"]}, True,
    )
    cfg.register(
        "ui", "general", "dark-mode", PropertyType.Bool, True,
        "Use the dark mode UI.", {}, True,
    )
    cfg.register(
        "ui", "general", "ui-scale", PropertyType.Int, 100,
        "Scale the program UI when Windows scaling is disabled. "
        "The UI resizes when the slider is released.",
        {"min": 70, "max": 200}, True,
    )
    cfg.register(
        "ui", "general", "disable-windows-scaling", PropertyType.Bool, False,
        "Disable Windows display scaling and use the UI scale slider instead. "
        "Takes effect on the next start.",
        {}, True,
    )
    # One setting covers minimizing and closing. "close-to-tray" was the
    # second one: whoever had it on keeps that behavior, then it is dropped.
    was_close_to_tray = bool(
        cfg.exists("global", "general", "close-to-tray")
        and cfg.value("global", "general", "close-to-tray")
    )
    cfg.register(
        "global", "general", "minimize-to-tray", PropertyType.Bool, False,
        "Minimizing or closing the window hides it to the system tray, and the "
        "profile keeps running. Exit from File > Exit or the tray icon's menu.",
        {}, True,
    )
    if was_close_to_tray and not cfg.value("global", "general", "minimize-to-tray"):
        cfg.set("global", "general", "minimize-to-tray", True)
    cfg.register(
        "global", "internal", "live-start-empty", PropertyType.Bool, False,
        "Live Log Reader: Live starts with an empty view.", {}, False,
    )
    cfg.register(
        "global", "internal", "tray-notice-shown", PropertyType.Bool, False,
        "The one-time notice that closing kept the program in the tray was shown.",
        {}, False,
    )
    cfg.register(
        "global", "general", "log-level", PropertyType.String, "Warning",
        "Diagnostic log level written to the user-profile log files.", {}, False,
    )
    cfg.register(
        "global", "general", "refresh-axis-on-activation", PropertyType.Bool, True,
        "Use known physical device state to perform actions using these values "
        "upon profile activation.", {}, True,
    )
    cfg.register(
        "global", "general", "refresh-axis-on-mode-change", PropertyType.Bool, True,
        "Force an update of all axes by emitting axis events upon a mode change.",
        {}, True,
    )
    cfg.register(
        "ui", "general", "input-highlighting", PropertyType.Bool, True,
        "Select the input in the UI by using an input on the physical device. "
        "Selects only inputs if the active tab matches the device.", {}, True,
    )
    cfg.register(
        "profile", "automation", "enable-auto-loading", PropertyType.Bool, False,
        "Load and run a profile when its program comes to the front.", {},
        True,
    )
    cfg.register(
        "profile", "automation", "remain-active-on-focus-loss", PropertyType.Bool,
        False,
        "Keep the profile running when you switch to a program that has no "
        "profile.",
        {}, True,
    )
    cfg.register(
        "profile", "automation", "entries-auto-loading", PropertyType.List, [],
        "List of executable and profile combinations for automatic loading.",
        {}, False,
    )
    cfg.register(
        "devices", "display", "aliases", PropertyType.List, [],
        "Friendly display names for devices and inputs.", {}, False,
    )
    cfg.register(
        osc_sec, osc_grp, "enabled", PropertyType.Bool, True,
        "Listen for OSC packets while a profile is active.", {}, True,
    )
    cfg.register(
        osc_sec, osc_grp, "host", PropertyType.Selection,
        gremlin.osc.default_bind_host(),
        "Input IP the program listens on.",
        {"valid_options": osc_ips}, False,
    )
    cfg.register(
        osc_sec, osc_grp, "port", PropertyType.String, "8001",
        "Input port the program listens on. Must match Companion Target Port.",
        {}, False,
    )
    cfg.register(
        osc_sec, osc_grp, "output-host", PropertyType.Selection, "127.0.0.1",
        "Output IP for OSC feedback to Companion.",
        {"valid_options": osc_ips}, False,
    )
    cfg.register(
        osc_sec, osc_grp, "output-port", PropertyType.String, "8000",
        "Output port for OSC feedback.",
        {}, False,
    )
    cfg.register(
        osc_sec, osc_grp, "pad-args", PropertyType.Bool, False,
        "Pad zero argument commands. Treat an address-only packet as value 1.0.",
        {}, True,
    )
    cfg.register(
        osc_sec, osc_grp, "autorelease-no-arg", PropertyType.Bool, True,
        "Autorelease on no arg messages. Press then release after the delay.",
        {}, True,
    )
    cfg.register(
        osc_sec, osc_grp, "autorelease-delay", PropertyType.String, "250",
        "Default Autorelease Delay in milliseconds.",
        {}, False,
    )
    # Status layout and the chosen module file must be registered before
    # purge_unused() or the next launch deletes them.
    gremlin.ui.module_model._ensure_display_options()
    gremlin.ui.hardware_profile._binding_store()
    gremlin.ui.hidhide._ensure_options()
    gremlin.ui.window_placement._ensure()
    gremlin.ui.vjoy_status.register_options()
    gremlin.ui.button_map_options.register()


def configure_loggers() -> None:
    configure_logger({
        "name": "system", "level": logging.WARNING,
        "logfile": os.path.join(gremlin.util.logs_dir(), "system.log"),
        "format": "%(asctime)s %(levelname)10s %(message)s", "mode": "rotate",
    })
    configure_logger({
        "name": "user", "level": logging.WARNING,
        "logfile": os.path.join(gremlin.util.logs_dir(), "user.log"),
        "format": "%(asctime)s %(message)s", "mode": "rotate",
    })
    configure_logger({
        "name": "event", "level": logging.WARNING,
        "logfile": os.path.join(gremlin.util.logs_dir(), "event.log"),
        "format": "%(asctime)s,%(levelname)s,%(message)s", "mode": "session",
    })


def update_action_priorities() -> None:
    cfg = gremlin.config.Configuration()
    key = ["action", "general", "action-priorities"]
    priorities = []
    if cfg.exists(*key):
        # A copy, so set() below saves only when the list really changed.
        priorities = [list(v) for v in cfg.value(*key)]
    priority_names = [v[0] for v in priorities]
    priority_actions = ["Map to vJoy", "Macro", "Response Curve"]
    plugin_names = [
        p.name for p in gremlin.plugin_manager.PluginManager().repository.values()
    ]
    plugin_names = [n for n in priority_actions if n in plugin_names] + sorted(
        [n for n in plugin_names if n not in priority_actions]
    )
    for tag in plugin_names:
        if tag not in priority_names:
            priorities.append([tag, True])
    to_delete = []
    for i, tag in enumerate(priority_names):
        if tag not in plugin_names:
            to_delete.append(i)
    for idx in reversed(to_delete):
        del priorities[idx]
    cfg.set(*key, priorities)


class JoystickGremlinApp(QtWidgets.QApplication):
    def __init__(self, argv: list[str]) -> None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--profile", help="Path to the profile to load on startup")
        parser.add_argument(
            "--enable", help="Enable Gremlin-Platforms upon launch", action="store_true"
        )
        parser.add_argument(
            "--start-minimized",
            help="Start Gremlin-Platforms minimized",
            action="store_true",
        )
        cmd_args, qt_argv = parser.parse_known_args(argv)
        super().__init__(qt_argv)

        configure_loggers()
        gremlin.ui.live_debug.start()
        self.syslog = logging.getLogger("system")
        register_config_options()
        gremlin.ui.log_option.apply_log_level()
        try:
            gremlin.ui.hidhide.apply_on_start()
        except Exception:
            self.syslog.exception("HidHide start")
        sys.excepthook = exception_hook

        dill.DILL.init()
        device_initialization_error = None
        try:
            gremlin.device_initialization.joystick_devices_initialization()
        except gremlin.error.GremlinError as e:
            device_initialization_error = str(e)[1:-1]

        self.initialize_qt()

        if device_initialization_error is not None:
            self.engine.load(
                QtCore.QUrl.fromLocalFile(
                    gremlin.util.resource_path("qml/MainFailure.qml")
                )
            )
            self.engine.rootContext().setContextProperty(
                "errorString", device_initialization_error
            )
            self.aboutToQuit.connect(shutdown_cleanup)
            return

        self.syslog.info("Initializing plugins")
        gremlin.plugin_manager.PluginManager()
        self.cfg.purge_unused()
        update_action_priorities()

        qml_errors: list[str] = []
        self.engine.warnings.connect(
            lambda warnings: qml_errors.extend(w.toString() for w in warnings)
        )
        self.engine.load(
            QtCore.QUrl.fromLocalFile(gremlin.util.resource_path("qml/Main.qml"))
        )
        if not self.engine.rootObjects():
            raise StartupError(
                "The main window could not be loaded.", "\n".join(qml_errors)
            )

        self.process_cmd_args(cmd_args)
        self.updater.startup()
        gremlin.config.announce_damaged_settings()

        self.main_window = self.engine.rootObjects()[0]
        # Red debug mode: a frame on every window while debugging.
        gremlin.ui.debug_mode.install(self)
        self.color_information_object = self.main_window.findChild(
            QtCore.QObject, "colorInformation"
        )
        if self.color_information_object is None:
            raise gremlin.error.GremlinError(
                "Failed to find color information object in QML."
            )
        gremlin.ui.util.ColorInformation().update_colors(self.color_information_object)
        self._theme_refresh_timer = QtCore.QTimer()
        self._theme_refresh_timer.setSingleShot(True)
        self._theme_refresh_timer.setInterval(0)
        self._theme_refresh_timer.timeout.connect(self._on_theme_colors_changed)
        for changed in (
            self.color_information_object.foregroundChanged,
            self.color_information_object.backgroundChanged,
            self.color_information_object.accentChanged,
        ):
            changed.connect(self._theme_refresh_timer.start)

        self.tray_icon = gremlin.ui.system_tray.SystemTrayIcon(self.main_window)
        self.aboutToQuit.connect(self.tray_icon.release_resources)
        self.syslog.info("Gremlin UI launching")
        self.aboutToQuit.connect(shutdown_cleanup)

    def _on_theme_colors_changed(self) -> None:
        gremlin.ui.util.ColorInformation().update_colors(self.color_information_object)
        self.backend.ui_state.bumpThemeRevision()

    def process_cmd_args(self, args: argparse.Namespace) -> None:
        if args.profile is not None and os.path.isfile(args.profile):
            self.backend.loadProfile(args.profile)
        else:
            last_profile = Path(
                Configuration().value("global", "internal", "last-profile")
            )
            if last_profile.is_file():
                self.backend.loadProfile(str(last_profile))

        if args.enable:
            self.backend.activate_gremlin(True)
        if args.start_minimized:
            self.backend.minimize()

    def initialize_qt(self) -> None:
        QtCore.QLoggingCategory.setFilterRules("qt.qml.binding.removal.info=true")
        QtQuick.QQuickWindow.setTextRenderType(QtQuick.QQuickWindow.NativeTextRendering)
        app_id = "joystick.gremlin"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)
        self.setWindowIcon(QtGui.QIcon(gremlin.util.resource_path("gfx/icon.png")))
        self.setApplicationDisplayName("Gremlin-Platforms R1")
        self.setOrganizationName("H2IK")
        self.setOrganizationDomain("https://whitemagic.github.io/JoystickGremlin/")
        self.setApplicationName("Gremlin-Platforms R1")
        font = QtGui.QFont("Segoe UI")
        font.setPixelSize(gremlin.ui.ui_scale_option.dp(15))
        self.setFont(font)
        if QtGui.QFontDatabase.addApplicationFont(":/BootstrapIcons") < 0:
            self.syslog.error("Failed to load BootstrapIcons")

        self.engine = QtQml.QQmlApplicationEngine(parent=self)
        self.engine.addImportPath(gremlin.util.resource_path("theme"))
        QtQml.qmlRegisterSingletonType(
            QtCore.QUrl.fromLocalFile(gremlin.util.resource_path("qml/Style.qml")),
            "Gremlin.Style", 1, 0, "Style",
        )
        QtCore.QDir.addSearchPath(
            "core_plugins", gremlin.util.resource_path("action_plugins/")
        )
        QtCore.QDir.addSearchPath("qml", gremlin.util.resource_path("qml/"))

        self.cfg = Configuration()
        user_plugins_path = gremlin.util.plugins_dir()
        if user_plugins_path.is_dir():
            QtCore.QDir.addSearchPath("user_plugins", str(user_plugins_path))

        self.backend = gremlin.ui.backend.Backend(self.engine)
        self.backend.newProfile()
        action_image_provider = (
            gremlin.ui.action_image_generator.ActionSummaryImageProvider()
        )
        self.engine.addImageProvider("action_summary", action_image_provider)
        self.engine.rootContext().setContextProperty("backend", self.backend)
        self.engine.rootContext().setContextProperty("uiState", self.backend.ui_state)
        self.engine.rootContext().setContextProperty("signal", gremlin.signal.signal)
        self.updater = gremlin.ui.update_model.UpdateModel(self)
        self.engine.rootContext().setContextProperty("updater", self.updater)


def main() -> int:
    lock = acquire_instance_lock()
    windows = _gremlin_window_titles()
    pids = _other_gremlin_pids()
    if lock is None or windows:
        choice = _confirm_second_instance(lock is None, windows, pids)
        if choice == "quit":
            return 0
        if choice == "close_others":
            _terminate_other_gremlin(pids)
            lock = acquire_instance_lock()
    try:
        app = JoystickGremlinApp(sys.argv)
    except Exception as e:
        summary = str(e) if isinstance(e, StartupError) else f"{type(e).__name__}: {e}"
        details = getattr(e, "details", "") or traceback.format_exc()
        logging.getLogger("system").error(f"Could not start: {summary}\n{details}")
        tell_could_not_start(summary, details)
        gremlin.deferred_write.flush_all()
        # Threads started before the failure must not keep the process alive.
        os._exit(1)
    app._instance_lock = lock
    app.exec()
    logging.getLogger("system").info("Terminating Gremlin")
    try:
        shutdown_cleanup()
    except Exception:
        logging.getLogger("system").exception("Shutdown after exec")
    # Writes still waiting (settings, the activity log): os._exit below skips
    # atexit, and a restart must start from saved settings.
    gremlin.deferred_write.flush_all()
    if lock is not None:
        try:
            lock.unlock()
        except Exception:
            pass
    backend = getattr(app, "backend", None)
    update_model = getattr(app, "updater", None)
    # A started installer launches the new version itself when it is done.
    installing = update_model is not None and update_model.start_pending_install()
    if not installing and backend is not None and backend.restart_on_exit:
        program, args = gremlin.util.restart_command(
            sys.argv,
            os.path.join(install_path, os.path.basename(sys.argv[0])),
            bool(getattr(sys, "frozen", False)),
            sys.executable,
        )
        if _LAUNCH_HIGHDPI_SCALING is None:
            os.environ.pop("QT_ENABLE_HIGHDPI_SCALING", None)
        else:
            os.environ["QT_ENABLE_HIGHDPI_SCALING"] = _LAUNCH_HIGHDPI_SCALING
        logging.getLogger("system").info(f"Restarting: {program} {args}")
        QtCore.QProcess.startDetached(program, args, install_path)
    # Non-daemon listener / hook threads can otherwise keep python.exe alive.
    os._exit(0)


if __name__ == "__main__":
    sys.exit(main())
