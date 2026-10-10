# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""ViGEm XUSB types. Adapted from Nefarius ViGEm / GremlinEx."""

from ctypes import Structure, c_short, c_ubyte, c_ushort
from enum import IntEnum, IntFlag


class XUSB_BUTTON(IntFlag):
    XUSB_GAMEPAD_DPAD_UP = 0x0001
    XUSB_GAMEPAD_DPAD_DOWN = 0x0002
    XUSB_GAMEPAD_DPAD_LEFT = 0x0004
    XUSB_GAMEPAD_DPAD_RIGHT = 0x0008
    XUSB_GAMEPAD_START = 0x0010
    XUSB_GAMEPAD_BACK = 0x0020
    XUSB_GAMEPAD_LEFT_THUMB = 0x0040
    XUSB_GAMEPAD_RIGHT_THUMB = 0x0080
    XUSB_GAMEPAD_LEFT_SHOULDER = 0x0100
    XUSB_GAMEPAD_RIGHT_SHOULDER = 0x0200
    XUSB_GAMEPAD_GUIDE = 0x0400
    XUSB_GAMEPAD_A = 0x1000
    XUSB_GAMEPAD_B = 0x2000
    XUSB_GAMEPAD_X = 0x4000
    XUSB_GAMEPAD_Y = 0x8000


class XUSB_REPORT(Structure):
    _fields_ = [
        ("wButtons", c_ushort),
        ("bLeftTrigger", c_ubyte),
        ("bRightTrigger", c_ubyte),
        ("sThumbLX", c_short),
        ("sThumbLY", c_short),
        ("sThumbRX", c_short),
        ("sThumbRY", c_short),
    ]


class VIGEM_ERRORS(IntEnum):
    VIGEM_ERROR_NONE = 0x20000000
    VIGEM_ERROR_BUS_NOT_FOUND = 0xE0000001
    VIGEM_ERROR_NO_FREE_SLOT = 0xE0000002
    VIGEM_ERROR_INVALID_TARGET = 0xE0000003
    VIGEM_ERROR_REMOVAL_FAILED = 0xE0000004
    VIGEM_ERROR_ALREADY_CONNECTED = 0xE0000005
    VIGEM_ERROR_TARGET_UNINITIALIZED = 0xE0000006
    VIGEM_ERROR_TARGET_NOT_PLUGGED_IN = 0xE0000007
    VIGEM_ERROR_BUS_VERSION_MISMATCH = 0xE0000008
    VIGEM_ERROR_BUS_ACCESS_FAILED = 0xE0000009
    VIGEM_ERROR_XUSB_USERINDEX_OUT_OF_RANGE = 0xE0000014
