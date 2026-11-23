# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""gremlin-ctl: read and control a running Gremlin-Platforms from outside.

client.py is the only code that knows the control pipe's protocol; cli.py
(gremlin-ctl.exe) and the MCP server in tools/gremlin_mcp/ are built on it.
Standard library only, no Qt and nothing from gremlin, so the exe stays small.
"""
