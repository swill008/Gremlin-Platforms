# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script that can't load: its top-level code raises.

Its load error reads "RuntimeError: raised on purpose at start".
"""

from gremlin import user_script

speed = user_script.IntegerVariable("Speed", "Never shown", True, 5, 0, 10)

raise RuntimeError("raised on purpose at start")
