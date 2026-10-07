# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import threading

import win32gui
import win32process
from PySide6 import QtCore

from gremlin import threads


class ProcessMonitor(QtCore.QObject):
    """Monitors the currently active window process.

    This class continuously monitors the active window and whenever
    it changes the path to the executable is retrieved and signaled
    to the rest of the system using Qt's signal / slot mechanism.
    """

    # Signal emitted when the active window changes
    process_changed = QtCore.Signal(str)

    # Definition of the flags for limited information queries
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

    # kernel32.dll library handle
    kernel32 = ctypes.windll.kernel32

    def __init__(self) -> None:
        """Creates a new instance."""
        QtCore.QObject.__init__(self)
        # The wide (Unicode) path: a program in a folder with non-ASCII
        # characters is matched by auto-load too.
        self._buffer = ctypes.create_unicode_buffer(1024)
        self._buffer_size = ctypes.wintypes.DWORD(1024)
        self._stop = threading.Event()
        self._current_path = ""
        self._current_pid = -1
        self.running = False
        self._update_thread = None

    def start(self) -> None:
        """Starts monitoring the current process (it runs only while
        auto-load is on, 02 Q19)."""
        if not self.running:
            self.running = True
            # Each start has its own stop request: a loop still finishing
            # after stop() ends by itself and never runs next to a new one.
            self._stop = threading.Event()
            # The program in front when it starts is announced, as at start.
            self._current_pid = -1
            self._update_thread = threads.start(
                "process monitor", self._update, self._stop, stop=self._ask_to_stop
            )

    def _ask_to_stop(self) -> None:
        self.running = False
        self._stop.set()

    def stop(self) -> None:
        """Stops monitoring the current process."""
        self._ask_to_stop()
        if self._update_thread is not None:
            self._update_thread.join(timeout=2.0)

    def _update(self, stop: threading.Event) -> None:
        """Monitors the active process for changes."""
        while not stop.is_set():
            _, pid = win32process.GetWindowThreadProcessId(
                win32gui.GetForegroundWindow()
            )

            if pid != self._current_pid:
                self._current_pid = pid
                path = self._image_path(pid)
                # A program that can't be read (one run as administrator)
                # isn't announced: the previous program's path used to be
                # sent again as if it were this one.
                if path:
                    self._current_path = path
                    self.process_changed.emit(self.current_path)

            stop.wait(1.0)

    def _image_path(self, pid: int) -> str:
        """The program's path, "" when it can't be read."""
        handle = ProcessMonitor.kernel32.OpenProcess(
            ProcessMonitor.PROCESS_QUERY_LIMITED_INFORMATION, False, pid
        )
        if not handle:
            return ""
        try:
            self._buffer_size = ctypes.wintypes.DWORD(1024)
            ok = ProcessMonitor.kernel32.QueryFullProcessImageNameW(
                handle, 0, self._buffer, ctypes.byref(self._buffer_size)
            )
        finally:
            ProcessMonitor.kernel32.CloseHandle(handle)
        if not ok or not self._buffer.value:
            return ""
        return os.path.normpath(self._buffer.value).replace("\\", "/")

    @property
    def current_path(self) -> str:
        """Returns the path to the currently active executable.

        Returns:
            The path to the currently active executable
        """
        return self._current_path


def list_current_processes() -> list[str]:
    """Returns a list of executable paths to currently active processes.

    Returns:
       The list of active process executable paths
    """
    from win32com.client import GetObject

    wmi = GetObject("winmgmts:")
    processes = wmi.InstancesOf("Win32_Process")
    process_list = []
    for entry in processes:
        executable = entry.Properties_("ExecutablePath").Value
        if executable is not None:
            process_list.append(os.path.normpath(executable).replace("\\", "/"))
    return sorted(set(process_list))
