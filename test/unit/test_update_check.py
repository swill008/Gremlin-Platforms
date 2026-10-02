# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import hashlib
import pathlib

import pytest

from gremlin import (
    updater,
    util,
)


@pytest.mark.parametrize(
    "tag, expected",
    [
        ("Gremlin-Platforms-R1-1.0.0", "1.0.0"),
        ("Gremlin-Platforms-R2-2.10.3", "2.10.3"),
        ("1.2.3", "1.2.3"),
        ("r15-osc-2026_09_07_1200", None),
        ("", None),
        (None, None),
    ],
)
def test_version_from_tag(tag: str | None, expected: str | None) -> None:
    assert util.version_from_tag(tag) == expected


_DIGEST = "a" * 64


def _release(version: str = "1.0.3", **asset: object) -> dict:
    entry = {
        "name": f"Gremlin-Platforms-R1-{version}-Setup.exe",
        "browser_download_url": "https://github.com/x/y/releases/download/t/s.exe",
        "size": 1000,
        "digest": f"sha256:{_DIGEST}",
    }
    entry.update(asset)
    return {
        "tag_name": f"Gremlin-Platforms-R1-{version}",
        "html_url": "https://github.com/x/y/releases/tag/t",
        "assets": [
            {"name": f"Gremlin-Platforms-R1-{version}.zip", "size": 5},
            entry,
        ],
    }


def test_release_picks_the_setup_asset() -> None:
    release = updater.parse_release(_release())
    assert release.version == "1.0.3"
    assert release.page_url == "https://github.com/x/y/releases/tag/t"
    assert release.setup.name == "Gremlin-Platforms-R1-1.0.3-Setup.exe"
    assert release.setup.size == 1000
    assert release.setup.sha256 == _DIGEST


@pytest.mark.parametrize(
    "change",
    [
        {"digest": None},  # GitHub gave no checksum
        {"digest": "md5:abc"},
        {"digest": "sha256:short"},
        {"browser_download_url": "http://example.com/s.exe"},  # not https
        {"size": 0},
        {"name": "Gremlin-Platforms-R1-1.0.2-Setup.exe"},  # another version
    ],
)
def test_release_without_a_verifiable_setup(change: dict) -> None:
    release = updater.parse_release(_release(**change))
    assert release is not None
    assert release.setup is None


@pytest.mark.parametrize("doc", [None, [], {}, {"tag_name": "r15-osc"}])
def test_release_without_a_version(doc: object) -> None:
    assert updater.parse_release(doc) is None


def test_local_test_server_is_allowed_for_assets() -> None:
    doc = _release(browser_download_url="http://127.0.0.1:8000/s.exe")
    assert updater.parse_release(doc).setup is not None


@pytest.mark.parametrize(
    "latest, running, skipped, manual, expected",
    [
        ("1.0.2", "1.0.2", "", True, False),  # same as running
        ("1.0.3", "1.0.2", "", False, True),  # newer
        ("1.0.3", "1.0.2", "1.0.3", False, False),  # skipped: startup stays quiet
        ("1.0.3", "1.0.2", "1.0.3", True, True),  # skipped, but the user asked
        ("1.0.4", "1.0.2", "1.0.3", False, True),  # a newer one than the skipped
        ("0.9.0", "1.0.0", "", True, False),  # older
        ("1.10.0", "1.9.0", "", False, True),  # numbers, not text
        ("bad", "1.0.0", "", True, False),
    ],
)
def test_should_offer(
    latest: str, running: str, skipped: str, manual: bool, expected: bool
) -> None:
    assert updater.should_offer(latest, running, skipped, manual) is expected


def test_install_kind(tmp_path: pathlib.Path) -> None:
    assert updater.install_kind(False, tmp_path) == updater.SOURCE
    assert updater.install_kind(True, tmp_path) == updater.PORTABLE
    (tmp_path / "unins000.exe").write_bytes(b"")
    assert updater.install_kind(True, tmp_path) == updater.INSTALLED


def test_file_matches(tmp_path: pathlib.Path) -> None:
    data = b"gremlin setup"
    path = tmp_path / "setup.exe"
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    assert updater.file_matches(path, len(data), digest)
    assert updater.file_matches(path, len(data), digest.upper())
    assert not updater.file_matches(path, len(data) + 1, digest)
    assert not updater.file_matches(path, len(data), "0" * 64)
    assert not updater.file_matches(tmp_path / "missing.exe", len(data), digest)


@pytest.mark.parametrize(
    "configured, expected",
    [
        ("", updater.LATEST_RELEASE_URL),
        ("http://localhost:8000/latest.json", "http://localhost:8000/latest.json"),
        ("https://example.com/latest", "https://example.com/latest"),
        ("http://example.com/latest", updater.LATEST_RELEASE_URL),  # plain http
        ("file:///c:/latest.json", updater.LATEST_RELEASE_URL),
    ],
)
def test_feed_url(configured: str, expected: str) -> None:
    assert updater.feed_url(configured) == expected


def test_feed_is_this_repository() -> None:
    assert "swill008/Gremlin-Platforms" in updater.LATEST_RELEASE_URL


def test_silent_update_restarts_the_program() -> None:
    args = updater.setup_arguments()
    assert "/SILENT" in args
    assert "/LAUNCH=1" in args


def test_installer_and_workflow_agree_on_names() -> None:
    root = pathlib.Path(__file__).parents[2]
    iss = (root / "installer" / "gremlin_platforms.iss").read_text(encoding="utf-8")
    workflow = (root / ".github" / "workflows" / "release-exe.yml").read_text(
        encoding="utf-8"
    )
    assert "OutputBaseFilename=Gremlin-Platforms-R1-{#MyAppVersion}-Setup" in iss
    assert "PrivilegesRequired=lowest" in iss
    assert "{param:LAUNCH|0}" in iss
    assert "Gremlin-Platforms-R1-${{ steps.version.outputs.version }}-Setup.exe" in (
        workflow
    )
    assert updater.setup_name("1.2.3") == "Gremlin-Platforms-R1-1.2.3-Setup.exe"
