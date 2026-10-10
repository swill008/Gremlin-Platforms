# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import copy
import ctypes
import ctypes.wintypes as ctwt
import os
import sys
import uuid
from enum import Enum
from typing import Callable


class DILLError(Exception):
    """Exception raised when an error occurs within the DILL module."""

    def __init__(self, value: str) -> None:
        """Creates a new error instance with the given message.

        Args:
            value: the error message to use
        """
        super().__init__(value)


class _GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", ctypes.c_ulong),
        ("Data2", ctypes.c_ushort),
        ("Data3", ctypes.c_ushort),
        ("Data4", ctypes.c_uint8 * 8),
    ]


def _attempt_decoding_device_name(data: bytes) -> str:
    ansi_code_page = f"cp{ctypes.windll.kernel32.GetACP()}"
    return data.decode(ansi_code_page, errors="ignore")


_GUID_SysKeyboard = _GUID()
_GUID_SysKeyboard.Data1 = 0x6F1D2B61
_GUID_SysKeyboard.Data2 = 0xD5A0
_GUID_SysKeyboard.Data3 = 0x11CF
_GUID_SysKeyboard.Data4[0] = 0xBF
_GUID_SysKeyboard.Data4[1] = 0xC7
_GUID_SysKeyboard.Data4[2] = 0x44
_GUID_SysKeyboard.Data4[3] = 0x45
_GUID_SysKeyboard.Data4[4] = 0x53
_GUID_SysKeyboard.Data4[5] = 0x54
_GUID_SysKeyboard.Data4[6] = 0x00
_GUID_SysKeyboard.Data4[7] = 0x00

_GUID_Virtual = _GUID()
_GUID_Virtual.Data1 = 0x89D5E905
_GUID_Virtual.Data2 = 0x1E26
_GUID_Virtual.Data3 = 0x4C52
_GUID_Virtual.Data4[0] = 0xAD
_GUID_Virtual.Data4[1] = 0x46
_GUID_Virtual.Data4[2] = 0x7B
_GUID_Virtual.Data4[3] = 0xCC
_GUID_Virtual.Data4[4] = 0x06
_GUID_Virtual.Data4[5] = 0xDF
_GUID_Virtual.Data4[6] = 0x4C
_GUID_Virtual.Data4[7] = 0x20

_GUID_LogicalDevice = _GUID()
_GUID_LogicalDevice.Data1 = 0xF0AF472F
_GUID_LogicalDevice.Data2 = 0x8E17
_GUID_LogicalDevice.Data3 = 0x493B
_GUID_LogicalDevice.Data4[0] = 0xA1
_GUID_LogicalDevice.Data4[1] = 0xEB
_GUID_LogicalDevice.Data4[2] = 0x73
_GUID_LogicalDevice.Data4[3] = 0x33
_GUID_LogicalDevice.Data4[4] = 0xEE
_GUID_LogicalDevice.Data4[5] = 0x85
_GUID_LogicalDevice.Data4[6] = 0x43
_GUID_LogicalDevice.Data4[7] = 0xF2

_GUID_Invalid = _GUID()
_GUID_Invalid.Data1 = 0x00000000
_GUID_Invalid.Data2 = 0x0000
_GUID_Invalid.Data3 = 0x0000
_GUID_Invalid.Data4[0] = 0x00
_GUID_Invalid.Data4[1] = 0x00
_GUID_Invalid.Data4[2] = 0x00
_GUID_Invalid.Data4[3] = 0x00
_GUID_Invalid.Data4[4] = 0x00
_GUID_Invalid.Data4[5] = 0x00
_GUID_Invalid.Data4[6] = 0x00
_GUID_Invalid.Data4[7] = 0x00


class _JoystickInputData(ctypes.Structure):
    _fields_ = [
        ("device_guid", _GUID),
        ("input_type", ctypes.c_uint8),
        ("input_index", ctypes.c_uint8),
        ("value", ctwt.LONG),
    ]


class _AxisMap(ctypes.Structure):
    _fields_ = [("linear_index", ctwt.DWORD), ("axis_index", ctwt.DWORD)]


class _DeviceSummary(ctypes.Structure):
    _fields_ = [
        ("device_guid", _GUID),
        ("vendor_id", ctwt.DWORD),
        ("product_id", ctwt.DWORD),
        ("joystick_id", ctwt.DWORD),
        ("name", ctypes.c_char * ctwt.MAX_PATH),
        ("axis_count", ctwt.DWORD),
        ("button_count", ctwt.DWORD),
        ("hat_count", ctwt.DWORD),
        ("axis_map", _AxisMap * 8),
    ]


class GUID:
    def __init__(self, guid: _GUID) -> None:
        assert isinstance(guid, _GUID)
        self._ctypes_guid = copy.deepcopy(guid)
        self.guid = (
            guid.Data1,
            guid.Data2,
            guid.Data3,
            (guid.Data4[0] << 8) + guid.Data4[1],
            (guid.Data4[2] << 40)
            + (guid.Data4[3] << 32)
            + (guid.Data4[4] << 24)
            + (guid.Data4[5] << 16)
            + (guid.Data4[6] << 8)
            + guid.Data4[7],
        )

    @staticmethod
    def from_str(value: str) -> GUID:
        return GUID.from_uuid(uuid.UUID(value))

    @staticmethod
    def from_uuid(value: uuid.UUID) -> GUID:
        try:
            raw_guid = _GUID()
            raw_guid.Data1 = int.from_bytes(value.bytes[0:4], "big")
            raw_guid.Data2 = int.from_bytes(value.bytes[4:6], "big")
            raw_guid.Data3 = int.from_bytes(value.bytes[6:8], "big")
            for i in range(8):
                raw_guid.Data4[i] = value.bytes[8 + i]
            return GUID(raw_guid)
        except (ValueError, AttributeError) as _:
            raise DILLError(f"Failed parsing GUID from value '{value}'")

    @property
    def ctypes(self) -> _GUID:
        return self._ctypes_guid

    @property
    def uuid(self) -> uuid.UUID:
        return uuid.UUID(str(self))

    def __str__(self) -> str:
        return "{:08X}-{:04X}-{:04X}-{:04X}-{:012X}".format(
            self.guid[0], self.guid[1], self.guid[2], self.guid[3], self.guid[4]
        )

    def __eq__(self, other: GUID) -> bool:
        return hash(self) == hash(other)

    def __lt__(self, other: GUID) -> bool:
        return str(self) < str(other)

    def __hash__(self) -> int:
        return hash(
            (
                self._ctypes_guid.Data1,
                self._ctypes_guid.Data2,
                self._ctypes_guid.Data3,
                self._ctypes_guid.Data4[0],
                self._ctypes_guid.Data4[1],
                self._ctypes_guid.Data4[2],
                self._ctypes_guid.Data4[3],
                self._ctypes_guid.Data4[4],
                self._ctypes_guid.Data4[5],
                self._ctypes_guid.Data4[6],
                self._ctypes_guid.Data4[7],
            )
        )


GUID_Keyboard = GUID(_GUID_SysKeyboard)
UUID_Keyboard = GUID_Keyboard.uuid
GUID_Virtual = GUID(_GUID_Virtual)
UUID_Virtual = GUID_Virtual.uuid
GUID_LogicalDevice = GUID(_GUID_LogicalDevice)
UUID_LogicalDevice = GUID_LogicalDevice.uuid
GUID_Invalid = GUID(_GUID_Invalid)
UUID_Invalid = GUID_Invalid.uuid


class InputType(Enum):
    Axis = (1,)
    Button = (2,)
    Hat = 3

    @staticmethod
    def from_ctype(value: int) -> InputType:
        if value == 1:
            return InputType.Axis
        elif value == 2:
            return InputType.Button
        elif value == 3:
            return InputType.Hat
        else:
            raise DILLError(f"Invalid input type value {value}")


class DeviceActionType(Enum):
    Connected = 1
    Disconnected = 2

    @staticmethod
    def from_ctype(value: int) -> DeviceActionType:
        if value == 1:
            return DeviceActionType.Connected
        elif value == 2:
            return DeviceActionType.Disconnected
        else:
            raise DILLError(f"Invalid device action type {value}")


class InputEvent:
    def __init__(self, data: _JoystickInputData) -> None:
        self.device_guid = GUID(data.device_guid)
        self.input_type = InputType.from_ctype(data.input_type)
        self.input_index = int(data.input_index)
        self.value = int(data.value)


class AxisMap:
    def __init__(self, data: _AxisMap) -> None:
        self.linear_index = data.linear_index
        self.axis_index = data.axis_index


class DeviceSummary:
    def __init__(self, data: _DeviceSummary) -> None:
        self.device_guid = GUID(data.device_guid)
        self.vendor_id = data.vendor_id
        self.product_id = data.product_id
        self.joystick_id = data.joystick_id
        self.name = _attempt_decoding_device_name(data.name)
        self.axis_count = data.axis_count
        self.button_count = data.button_count
        self.hat_count = data.hat_count
        self.axis_map = []
        for i in range(8):
            self.axis_map.append(AxisMap(data.axis_map[i]))
        self.axis_lookup = {}
        for entry in self.axis_map:
            self.axis_lookup[entry.axis_index] = entry.linear_index
        self.vjoy_id = -1

    @property
    def is_virtual(self) -> bool:
        return self.vendor_id == 0x1234 and self.product_id == 0xBEAD

    def set_vjoy_id(self, vjoy_id: int) -> None:
        assert self.is_virtual is True
        self.vjoy_id = vjoy_id

    @property
    def device_uuid(self) -> uuid.UUID:
        return self.device_guid.uuid


C_EVENT_CALLBACK = ctypes.CFUNCTYPE(None, _JoystickInputData)
C_DEVICE_CHANGE_CALLBACK = ctypes.CFUNCTYPE(None, _DeviceSummary, ctypes.c_uint8)

DLL_NAME = "dill.dll"

# Where Windows may look for what dill.dll itself needs: its own folder,
# System32 and the program's folder. Never the working folder or PATH.
_LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR = 0x00000100
_LOAD_LIBRARY_SEARCH_DEFAULT_DIRS = 0x00001000


def dll_path(meipass: str | None = None, package_dir: str | None = None) -> str:
    """Where the reader is: the frozen program's folder, else next to this
    file. Never the working folder (the program imports this before it
    changes to its install folder)."""
    if meipass is None:
        meipass = getattr(sys, "_MEIPASS", None)
    if meipass is not None:
        return os.path.abspath(os.path.join(meipass, DLL_NAME))
    return os.path.abspath(
        os.path.join(package_dir or os.path.dirname(__file__), DLL_NAME)
    )


def _load_dll(path: str) -> ctypes.CDLL:
    """Loads dill.dll from its absolute path, once."""
    if not os.path.isfile(path):
        raise DILLError(f"Unable to locate {DLL_NAME} library at {path}")
    return ctypes.CDLL(
        path,
        winmode=_LOAD_LIBRARY_SEARCH_DLL_LOAD_DIR | _LOAD_LIBRARY_SEARCH_DEFAULT_DIRS,
    )


_dll_path = dll_path()
_di_listener_dll = _load_dll(_dll_path)


class DILL:
    _dll_path = _dll_path
    # The one load above; tests swap in a fake by setting DILL._dll.
    _dll = _di_listener_dll
    _dill_initialized = False
    device_change_callback_fn = None
    input_event_callback_fn = None
    # Old C callbacks stay referenced so the DLL thread cannot enter a freed one.
    _retired_callbacks: list = []
    api_functions = {
        "init": {"arguments": [], "returns": None},
        "set_input_event_callback": {"arguments": [C_EVENT_CALLBACK], "returns": None},
        "set_device_change_callback": {
            "arguments": [C_DEVICE_CHANGE_CALLBACK],
            "returns": None,
        },
        "get_device_information_by_index": {
            "arguments": [ctypes.c_uint],
            "returns": _DeviceSummary,
        },
        "get_device_information_by_guid": {
            "arguments": [_GUID],
            "returns": _DeviceSummary,
        },
        "get_device_count": {"arguments": [], "returns": ctypes.c_uint},
        "device_exists": {"arguments": [_GUID], "returns": ctypes.c_bool},
        "get_axis": {"arguments": [_GUID, ctwt.DWORD], "returns": ctwt.LONG},
        "get_button": {"arguments": [_GUID, ctwt.DWORD], "returns": ctypes.c_bool},
        "get_hat": {"arguments": [_GUID, ctwt.DWORD], "returns": ctwt.LONG},
    }

    @staticmethod
    def init() -> None:
        if not DILL._dill_initialized:
            DILL._dll.init()
            DILL._dill_initialized = True

    @staticmethod
    def set_input_event_callback(callback: Callable[[InputEvent], None]) -> None:
        if DILL.input_event_callback_fn is not None:
            DILL._retired_callbacks.append(DILL.input_event_callback_fn)
        DILL.input_event_callback_fn = C_EVENT_CALLBACK(callback)
        DILL._dll.set_input_event_callback(DILL.input_event_callback_fn)

    @staticmethod
    def set_device_change_callback(callback: Callable[[DeviceSummary], None]) -> None:
        if DILL.device_change_callback_fn is not None:
            DILL._retired_callbacks.append(DILL.device_change_callback_fn)
        DILL.device_change_callback_fn = C_DEVICE_CHANGE_CALLBACK(callback)
        DILL._dll.set_device_change_callback(DILL.device_change_callback_fn)

    @staticmethod
    def get_device_count() -> int:
        return DILL._dll.get_device_count()

    @staticmethod
    def get_device_information_by_index(index: int) -> DeviceSummary:
        return DeviceSummary(DILL._dll.get_device_information_by_index(index))

    @staticmethod
    def get_device_information_by_guid(guid: GUID) -> DeviceSummary:
        return DeviceSummary(DILL._dll.get_device_information_by_guid(guid.ctypes))

    @staticmethod
    def get_axis(guid: GUID, index: int) -> float:
        return DILL._dll.get_axis(guid.ctypes, index)

    @staticmethod
    def get_button(guid: GUID, index: int) -> bool:
        return DILL._dll.get_button(guid.ctypes, index)

    @staticmethod
    def get_hat(guid: GUID, index: int) -> int:
        return DILL._dll.get_hat(guid.ctypes, index)

    @staticmethod
    def get_device_name(guid: GUID) -> str:
        info = DeviceSummary(DILL._dll.get_device_information_by_guid(guid.ctypes))
        return info.name

    @staticmethod
    def device_exists(guid: GUID) -> bool:
        return DILL._dll.device_exists(guid.ctypes)

    @staticmethod
    def initialize_capi() -> None:
        for fn_name, params in DILL.api_functions.items():
            dll_fn = getattr(DILL._dll, fn_name)
            if "arguments" in params:
                dll_fn.argtypes = params["arguments"]
            if "returns" in params:
                dll_fn.restype = params["returns"]


DILL.initialize_capi()
