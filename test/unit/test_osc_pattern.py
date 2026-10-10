# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC 1.0 address patterns (D-09-OSC-PATTERNS, S147-S149): each form,
the refusals with their reasons, case, and nothing crossing a "/"."""

from __future__ import annotations

import pytest

from gremlin import osc_pattern
from gremlin.error import GremlinError


@pytest.mark.parametrize(
    ("pattern", "hits", "misses"),
    [
        ("/fader/?", ["/fader/1", "/fader/x"], ["/fader/", "/fader/12", "/fader//"]),
        ("/fader/*", ["/fader/", "/fader/1", "/fader/12"], ["/fader/1/x", "/fade/1"]),
        ("/*/go", ["/a/go", "/abc/go"], ["/a/b/go", "/go"]),
        ("/btn/[abc]", ["/btn/a", "/btn/c"], ["/btn/d", "/btn/ab", "/btn/"]),
        ("/btn/[a-c]", ["/btn/b"], ["/btn/d"]),
        ("/btn/[!a-c]", ["/btn/d", "/btn/1"], ["/btn/a", "/btn//"]),
        ("/btn/[a-]", ["/btn/a", "/btn/-"], ["/btn/b"]),
        ("/btn/[-a]", ["/btn/-", "/btn/a"], ["/btn/b"]),
        ("/{red,green}/on", ["/red/on", "/green/on"], ["/blue/on", "/redgreen/on"]),
        ("/{a*,b}", ["/a*", "/b"], ["/ax"]),
        ("/a.b", ["/a.b"], ["/axb"]),
        ("/x/[0-9]/{on,off}", ["/x/3/on", "/x/0/off"], ["/x/10/on"]),
    ],
)
def test_each_form_matches_and_misses(
    pattern: str, hits: list[str], misses: list[str]
) -> None:
    assert osc_pattern.is_pattern(pattern) or pattern == "/a.b"
    assert osc_pattern.check(pattern) == ""
    for address in hits:
        assert osc_pattern.matches(pattern, address), address
    for address in misses:
        assert not osc_pattern.matches(pattern, address), address


def test_star_and_question_never_cross_a_slash() -> None:
    assert not osc_pattern.matches("/*", "/a/b")
    assert not osc_pattern.matches("/a?b", "/a/b")
    assert not osc_pattern.matches("/a[!x]b", "/a/b")


def test_case_is_ignored_on_both_sides() -> None:
    assert osc_pattern.matches("/Fader/*", "/FADER/One")
    assert osc_pattern.matches("/btn/[A-C]", "/btn/b")
    assert osc_pattern.matches("/{Red,Green}", "/GREEN")


@pytest.mark.parametrize(
    ("text", "reason"),
    [
        ("", "Enter an address."),
        ("   ", "Enter an address."),
        ("fader/1", "An OSC address starts with /."),
        ("/a b", "space"),
        ("/a#b", "#"),
        ("/a[bc", "never closed"),
        ("/a{b,c", "never closed"),
        ("/a]", 'no "["'),
        ("/a}", 'no "{"'),
        ("/{a,{b}}", "another {"),
        ("/a[b/c]", '"/"'),
        ("/{a,b/c}", '"/"'),
        ("/a[]", "empty"),
        ("/a[!]", "empty"),
        ("/a{}", "empty"),
        ("/a[z-a]", "backwards"),
    ],
)
def test_refusals_say_why(text: str, reason: str) -> None:
    why = osc_pattern.check(text)
    assert why and reason in why
    if text.startswith("/") and osc_pattern.is_pattern(text):
        with pytest.raises(GremlinError):
            osc_pattern.compile(text)


def test_outgoing_addresses_refuse_any_pattern() -> None:
    assert osc_pattern.check("/fader/1", allow_pattern=False) == ""
    for text in ("/fader/*", "/a?", "/[ab]", "/{a,b}"):
        assert osc_pattern.check(text, allow_pattern=False) == osc_pattern.NO_PATTERN


def test_is_pattern_and_plain_addresses() -> None:
    assert not osc_pattern.is_pattern("/fader/1")
    for text in ("/a*", "/a?", "/[a]", "/{a}", "/a]", "/a}"):
        assert osc_pattern.is_pattern(text)


def test_compile_is_cached() -> None:
    assert osc_pattern.compile("/Cache/*") is osc_pattern.compile("/cache/*")
