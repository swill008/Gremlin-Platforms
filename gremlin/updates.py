# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Online version check used by Options -> Check for updates.

The fetch / parse / compare / notify path in Backend.check_for_updates() is
unchanged. Replace UPDATE_VERSION_URL later with this project's version.json.
The file is expected to look like:

    {"version": "1.0.0"}
"""

from __future__ import annotations

import json
import urllib.request

# Placeholder. Swap this URL when the project version feed exists.
UPDATE_VERSION_URL = "https://example.invalid/r15-osc/version.json"


def latest_gremlin_version() -> str | None:
    """Returns the latest published version string, or None on failure."""
    try:
        with urllib.request.urlopen(UPDATE_VERSION_URL, timeout=5) as response:
            data = response.read()
            json_data = json.loads(data)
            return json_data.get("version", None)
    except Exception:
        return None


def _install() -> None:
    import gremlin.util

    gremlin.util.latest_gremlin_version = latest_gremlin_version


_install()
