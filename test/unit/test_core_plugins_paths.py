# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Every core_plugins: path in the action plugins names a real file, exact case.

Windows finds a file whatever the case, so a wrong-case path works here and
breaks anywhere case matters (R11d: no behaviour change).
"""

from __future__ import annotations

import os
import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PLUGINS = _ROOT / "action_plugins"
_PATH_RE = re.compile(r"core_plugins:([^\"'\s)]+)")


def _exists_exact_case(base: pathlib.Path, relative: str) -> bool:
    current = base
    for part in relative.strip("/").split("/"):
        if not current.is_dir() or part not in os.listdir(current):
            return False
        current = current / part
    return current.is_file()


def test_core_plugins_paths_exist_with_exact_case() -> None:
    found = []
    bad = []
    for source in sorted(_PLUGINS.rglob("*.py")):
        text = source.read_text(encoding="utf-8")
        for match in _PATH_RE.finditer(text):
            path = match.group(1)
            found.append(path)
            if not _exists_exact_case(_PLUGINS, path):
                bad.append(f"{source.relative_to(_ROOT)}: core_plugins:{path}")
    assert found, "no core_plugins: paths found; the pattern is out of date"
    assert bad == []
