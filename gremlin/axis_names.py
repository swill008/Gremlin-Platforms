# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The one table of axis names, by the axis number profiles store (1 = X ...
8 = Slider 2). Long words for menus and labels, short ones for tight spots,
vJoyConfig's names and the HID usage. Imports nothing, so the Input Tester can
use it without the program's settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AxisName:
    number: int  # 1-8, what profiles store
    long: str  # "X Axis" ... "Slider 2"
    short: str  # "X" ... "S2"
    vjoy_config: str  # vJoyConfig's -a / -t name
    usage: int  # HID usage, 0x30 ... 0x37


AXES: tuple[AxisName, ...] = (
    AxisName(1, "X Axis", "X", "x", 0x30),
    AxisName(2, "Y Axis", "Y", "y", 0x31),
    AxisName(3, "Z Axis", "Z", "z", 0x32),
    AxisName(4, "X Rotation", "Rx", "rx", 0x33),
    AxisName(5, "Y Rotation", "Ry", "ry", 0x34),
    AxisName(6, "Z Rotation", "Rz", "rz", 0x35),
    AxisName(7, "Slider 1", "S1", "sl0", 0x36),
    AxisName(8, "Slider 2", "S2", "sl1", 0x37),
)

_BY_NUMBER = {a.number: a for a in AXES}


def long_name(number: int) -> str:
    axis = _BY_NUMBER.get(int(number))
    return axis.long if axis else f"Axis {int(number)}"


def short_name(number: int) -> str:
    axis = _BY_NUMBER.get(int(number))
    return axis.short if axis else f"A{int(number)}"
