# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

# Test script that can't load: a syntax error on line 8 (the call is never
# closed). Its load error reads "Syntax error, line 8: ...".
from gremlin import user_script
speed = user_script.IntegerVariable("Speed", "How fast", True, 5, 0, 10
