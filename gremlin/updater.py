# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Finding, checking and installing a newer release.

A release on GitHub carries "Gremlin-Platforms-R1-X.Y.Z-Setup.exe". An installed
copy downloads it, checks its size and SHA-256 against what GitHub reports, and
runs it silently after Gremlin has closed. A portable copy or one running from
source is only told about the release.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from gremlin import util

LATEST_RELEASE_URL = (
    "https://api.github.com/repos/swill008/Gremlin-Platforms/releases/latest"
)
RELEASES_PAGE_URL = "https://github.com/swill008/Gremlin-Platforms/releases"

INSTALLED = "installed"
PORTABLE = "portable"
SOURCE = "source"


@dataclass(frozen=True)
class Asset:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class Release:
    version: str
    page_url: str
    setup: Asset | None


def setup_name(version: str) -> str:
    return f"Gremlin-Platforms-R1-{version}-Setup.exe"


def _asset(doc: dict) -> Asset | None:
    digest = str(doc.get("digest") or "")
    algorithm, _, value = digest.partition(":")
    if algorithm.lower() != "sha256" or not re.fullmatch(r"[0-9a-fA-F]{64}", value):
        return None
    url = str(doc.get("browser_download_url") or "")
    if not _allowed_url(url):
        return None
    try:
        size = int(doc.get("size"))
    except (TypeError, ValueError):
        return None
    if size <= 0:
        return None
    return Asset(str(doc.get("name") or ""), url, size, value.lower())


def parse_release(doc: object) -> Release | None:
    """The release described by a GitHub "latest release" reply.

    None when the tag has no X.Y.Z version. setup is None when the installer
    is missing or GitHub gave no usable size, https URL or SHA-256 digest for
    it, so nothing unverified is ever downloaded.
    """
    if not isinstance(doc, dict):
        return None
    version = util.version_from_tag(doc.get("tag_name"))
    if version is None:
        return None
    setup = None
    for entry in doc.get("assets") or []:
        if isinstance(entry, dict) and entry.get("name") == setup_name(version):
            setup = _asset(entry)
            break
    page_url = str(doc.get("html_url") or RELEASES_PAGE_URL)
    return Release(version, page_url, setup)


def _version_tuple(value: str) -> tuple[int, ...] | None:
    try:
        return tuple(int(part) for part in str(value).split("."))
    except (TypeError, ValueError):
        return None


def is_newer(latest: str, running: str) -> bool:
    latest_v = _version_tuple(latest)
    running_v = _version_tuple(running)
    return latest_v is not None and running_v is not None and latest_v > running_v


def should_offer(latest: str, running: str, skipped: str, manual: bool) -> bool:
    """True when the user should be asked about this release.

    A startup check stays quiet about a version the user chose to skip; a
    check the user asked for always reports a newer version.
    """
    if not is_newer(latest, running):
        return False
    return manual or latest != skipped


def install_kind(frozen: bool, exe_dir: Path) -> str:
    """How this copy was installed: the installer leaves its uninstaller
    (unins000.exe) next to the program; a portable copy has none."""
    if not frozen:
        return SOURCE
    if any(Path(exe_dir).glob("unins*.exe")):
        return INSTALLED
    return PORTABLE


def file_matches(path: Path, size: int, sha256: str) -> bool:
    """True when the file has exactly the size and SHA-256 GitHub reported."""
    try:
        if Path(path).stat().st_size != int(size):
            return False
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
    except OSError:
        return False
    return digest.hexdigest() == str(sha256).lower()


def setup_arguments(log_path: str | None = None) -> list[str]:
    """Arguments for a silent update: progress window only, no questions,
    start the new version when done (the installer's /LAUNCH=1). With
    log_path, setup writes its log there (kept in the updates folder, so a
    failed update can be traced)."""
    args = ["/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/LAUNCH=1"]
    if log_path:
        args.append(f"/LOG={log_path}")
    return args


def _allowed_url(url: str) -> bool:
    """https anywhere, or http on this machine (a local test server)."""
    parsed = urlparse(str(url or ""))
    if parsed.scheme == "https":
        return bool(parsed.hostname)
    return parsed.scheme == "http" and parsed.hostname in ("localhost", "127.0.0.1")


def feed_url(configured: str) -> str:
    """The release feed: the hidden update-feed-url setting when it is allowed
    (used for testing), otherwise GitHub."""
    url = str(configured or "").strip()
    return url if url and _allowed_url(url) else LATEST_RELEASE_URL


def updates_dir() -> Path:
    return Path(util.data_folder()) / "updates"
