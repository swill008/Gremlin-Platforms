# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Lazy ctypes loader for ViGEmClient.dll. Does not connect at import."""

from __future__ import annotations

import ctypes
import logging
import os
import sys
from ctypes import c_bool, c_uint, c_ulong, c_ushort, c_void_p
from pathlib import Path

from vigem.vigem_commons import XUSB_REPORT

_LOG = logging.getLogger("system")
_dll = None
_load_attempted = False
_load_error = ""


def _candidate_paths() -> list[Path]:
    here = Path(__file__).resolve().parent
    names = [here / "ViGEmClient.dll"]
    if hasattr(sys, "_MEIPASS"):
        names.append(Path(sys._MEIPASS) / "ViGEmClient.dll")
        names.append(Path(sys._MEIPASS) / "vigem" / "ViGEmClient.dll")
    names.append(Path.cwd() / "ViGEmClient.dll")
    names.append(Path.cwd() / "vigem" / "ViGEmClient.dll")
    return names


def dll_path() -> Path | None:
    for path in _candidate_paths():
        if path.is_file():
            return path
    return None


def load_error() -> str:
    return _load_error


def client() -> ctypes.CDLL | None:
    global _dll, _load_attempted, _load_error
    if _load_attempted:
        return _dll
    _load_attempted = True
    path = dll_path()
    if path is None:
        _load_error = (
            "ViGEmClient.dll is missing from the program folder, so Xbox "
            "outputs can't work. Reinstall Gremlin-Platforms."
        )
        _LOG.warning(_load_error)
        return None
    try:
        _dll = ctypes.cdll.LoadLibrary(os.fspath(path))
    except OSError as exc:
        _load_error = f"Failed to load {path}: {exc}"
        _LOG.warning(_load_error)
        _dll = None
        return None
    _bind(_dll)
    return _dll


def _bind(lib: ctypes.CDLL) -> None:
    lib.vigem_alloc.argtypes = ()
    lib.vigem_alloc.restype = c_void_p
    lib.vigem_free.argtypes = (c_void_p,)
    lib.vigem_free.restype = None
    lib.vigem_connect.argtypes = (c_void_p,)
    lib.vigem_connect.restype = c_uint
    lib.vigem_disconnect.argtypes = (c_void_p,)
    lib.vigem_disconnect.restype = None
    lib.vigem_target_x360_alloc.argtypes = ()
    lib.vigem_target_x360_alloc.restype = c_void_p
    lib.vigem_target_free.argtypes = (c_void_p,)
    lib.vigem_target_free.restype = None
    lib.vigem_target_add.argtypes = (c_void_p, c_void_p)
    lib.vigem_target_add.restype = c_uint
    lib.vigem_target_remove.argtypes = (c_void_p, c_void_p)
    lib.vigem_target_remove.restype = c_uint
    lib.vigem_target_x360_update.argtypes = (c_void_p, c_void_p, XUSB_REPORT)
    lib.vigem_target_x360_update.restype = c_uint
    lib.vigem_target_is_attached.argtypes = (c_void_p,)
    lib.vigem_target_is_attached.restype = c_bool
    lib.vigem_target_get_index.argtypes = (c_void_p,)
    lib.vigem_target_get_index.restype = c_ulong
    lib.vigem_target_x360_get_user_index.argtypes = (c_void_p, c_void_p, c_void_p)
    lib.vigem_target_x360_get_user_index.restype = c_uint
    lib.vigem_target_set_vid.argtypes = (c_void_p, c_ushort)
    lib.vigem_target_set_vid.restype = None
    lib.vigem_target_set_pid.argtypes = (c_void_p, c_ushort)
    lib.vigem_target_set_pid.restype = None
