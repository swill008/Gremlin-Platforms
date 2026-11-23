# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""python -m gremlin_ctl, and the entry point of gremlin-ctl.exe."""

import sys

from gremlin_ctl.cli import main

if __name__ == "__main__":
    # Window titles and command names may be outside the console's code page.
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="replace")
    sys.exit(main())
