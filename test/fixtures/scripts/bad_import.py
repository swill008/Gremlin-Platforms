# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Test script that can't load: it imports a module that doesn't exist.

Its load error reads "ModuleNotFoundError: No module named
'gremlin_test_no_such_module'".
"""

import gremlin_test_no_such_module  # noqa: F401
