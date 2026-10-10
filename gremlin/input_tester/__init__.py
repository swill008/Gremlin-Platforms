# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Gremlin Input Tester (decision D-02-INPUT-TESTER).

A separate program that shows what its own process sees (DirectInput,
XInput, HID) and compares it with what Gremlin expects through HidHide.
Reads only: nothing here may import gremlin.config or touch the user's
settings; the one file it writes is result.json.
"""
