# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""python -m gremlin_ctl, and the entry point of gremlin-ctl.exe."""

import sys

from gremlin_ctl.cli import main


def _utf8_console() -> None:
    """Window titles, command names and "Options › General" are outside the
    console's old code page: switch a Windows console to UTF-8 and write
    UTF-8 (a pipe or file gets UTF-8 too)."""
    if sys.platform == "win32":
        try:
            import ctypes

            ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        except (AttributeError, OSError):
            pass
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


if __name__ == "__main__":
    _utf8_console()
    sys.exit(main())
