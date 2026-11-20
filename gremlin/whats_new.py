# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The release notes shipped with the program, for the "Updated" banner and
the What's New window (01 S183). Pure, no Qt."""

from __future__ import annotations

import logging
from pathlib import Path

from gremlin import (
    updater,
    util,
)


def notes_dir() -> Path:
    """The folder of release-notes/<version>.md files (also when frozen)."""
    return Path(util.resource_path("release-notes"))


def _key(version: str) -> tuple[int, ...] | None:
    return updater._version_tuple(version)


def available_versions() -> list[str]:
    """Every version with a notes file, newest first."""
    found = []
    try:
        for path in notes_dir().glob("*.md"):
            if _key(path.stem) is not None:
                found.append(path.stem)
    except OSError:
        return []
    return sorted(found, key=lambda v: _key(v) or (), reverse=True)


def versions_between(last: str | None, current: str) -> list[str]:
    """Versions newer than `last` up to and including `current`, newest
    first. Versions without a notes file are still listed (they show the
    "unavailable" text), so a skipped version is never silently dropped:
    the list is the notes files in that range, plus `current` itself."""
    cur = _key(current)
    old = _key(last) if last else None
    if cur is None or old is None or not cur > old:
        return []
    versions = {
        v for v in available_versions()
        if old < (_key(v) or ()) <= cur
    }
    versions.add(current)
    return sorted(versions, key=lambda v: _key(v) or (), reverse=True)


def banner_versions(last: str | None, current: str) -> list[str]:
    """The versions the "Updated" banner covers; [] for no banner: a first
    start (nothing recorded) or the same or a newer version than last time."""
    if not last:
        return []
    return versions_between(last, current)


def read_notes(version: str) -> str:
    """The notes file of one version; "" when missing or unreadable."""
    try:
        return (notes_dir() / f"{version}.md").read_text(encoding="utf-8")
    except (OSError, ValueError) as exc:
        logging.getLogger("system").warning(
            "What's New: no notes for %s (%s)", version, exc
        )
        return ""


def notes_html(versions: list[str]) -> str:
    """The notes of these versions in the order given, as HTML; never
    empty ("Release notes unavailable." when nothing can be shown)."""
    try:
        html_text = updater.notes_html([(v, read_notes(v)) for v in versions])
    except Exception:
        logging.getLogger("system").exception("What's New: notes failed")
        html_text = ""
    return html_text or f'<p class="none">{updater._UNAVAILABLE}</p>'
