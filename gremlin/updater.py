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
# Every release with its notes, newest first: one request covers the versions
# between this copy and the latest.
RELEASES_LIST_URL = (
    "https://api.github.com/repos/swill008/Gremlin-Platforms/releases?per_page=30"
)
# Longest release note kept (GitHub allows 125000 characters).
_NOTES_LIMIT = 20000

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
    # The release notes as GitHub has them (Markdown), or "".
    notes: str = ""


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
    body = doc.get("body")
    return Release(version, page_url, setup, body if isinstance(body, str) else "")


def safe_notes(body: str) -> str:
    """Release notes Markdown with nothing that runs or loads: raw HTML
    (scripts, styles, comments, tags) goes and images become their alt text."""
    text = str(body or "")[:_NOTES_LIMIT].replace("\r\n", "\n")
    text = re.sub(r"<!--.*?(?:-->|$)", "", text, flags=re.S)
    text = re.sub(
        r"<(script|style|iframe|object|embed)\b.*?(?:</\1\s*>|$)", "", text,
        flags=re.S | re.I,
    )
    text = re.sub(r"</?[A-Za-z][^>]*>", "", text)
    # ![alt](url) and ![alt][ref]: the picture would be fetched.
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"!\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    return text.strip()


def newer_notes(docs: object, running: str, latest: str) -> list[tuple[str, str]]:
    """(version, notes) of each published release newer than running and no
    newer than latest, newest first, from a GitHub releases list reply.
    Drafts and pre-releases are left out, as GitHub's latest release does."""
    if not isinstance(docs, list):
        return []
    found: dict[str, str] = {}
    for doc in docs:
        if not isinstance(doc, dict) or doc.get("draft") or doc.get("prerelease"):
            continue
        version = util.version_from_tag(str(doc.get("tag_name") or ""))
        if version is None or not is_newer(version, running):
            continue
        if is_newer(version, latest):
            continue
        body = doc.get("body")
        found.setdefault(version, body if isinstance(body, str) else "")
    return sorted(
        found.items(), key=lambda item: _version_tuple(item[0]) or (), reverse=True
    )


def notes_markdown(entries: list[tuple[str, str]]) -> str:
    """One Markdown text: each release under its version heading, in the
    order given; "" when none of them has notes."""
    parts = []
    for version, body in entries:
        text = safe_notes(body)
        if text:
            parts.append(f"# Version {version}\n\n{text}")
    return "\n\n".join(parts)


def notes_url(feed: str) -> str:
    """The releases list next to a "latest release" feed; "" when the feed
    is not one (then only the latest release's own notes are shown)."""
    url = str(feed or "")
    if url == LATEST_RELEASE_URL:
        return RELEASES_LIST_URL
    if url.endswith("/releases/latest") and _allowed_url(url):
        return url[: -len("/latest")] + "?per_page=30"
    return ""


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
