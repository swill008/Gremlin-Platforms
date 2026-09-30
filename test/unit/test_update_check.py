# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import io
import json
from unittest import mock

import pytest

from gremlin import util


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


@pytest.mark.parametrize(
    "latest, running, announced, expected",
    [
        ("1.0.0", "1.0.0", "1.0.0", False),  # same as running: nothing new
        ("1.0.1", "1.0.0", "1.0.0", True),  # newer release
        ("1.0.1", "1.0.0", "1.0.1", False),  # already told about it
        ("1.0.1", "1.0.0", "15.0.0", True),  # leftover R15 value must not hide it
        ("0.9.0", "1.0.0", "0.0.0", False),  # older than running
        ("1.10.0", "1.9.0", "1.9.0", True),  # compares numbers, not text
        ("bad", "1.0.0", "1.0.0", False),
    ],
)
def test_should_announce_version(
    latest: str, running: str, announced: str, expected: bool
) -> None:
    assert util.should_announce_version(latest, running, announced) is expected


def test_latest_version_reads_our_latest_release() -> None:
    body = io.BytesIO(json.dumps({"tag_name": "Gremlin-Platforms-R1-1.0.0"}).encode())
    with mock.patch.object(util.urllib.request, "urlopen", return_value=body) as opened:
        assert util.latest_gremlin_version() == "1.0.0"
    request = opened.call_args.args[0]
    assert request.full_url == util.LATEST_RELEASE_URL
    assert "swill008/JoystickGremlin_" in request.full_url


def test_latest_version_is_none_when_offline() -> None:
    offline = OSError("offline")
    with mock.patch.object(util.urllib.request, "urlopen", side_effect=offline):
        assert util.latest_gremlin_version() is None
