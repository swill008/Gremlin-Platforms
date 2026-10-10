# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""OSC 1.0 address patterns (D-09-OSC-PATTERNS, S147-S149).

`?` one character, `*` any run, `[abc]` `[a-z]` `[!a-z]` one character from
(or not from) a set, `{a,b}` one of the words. None of them crosses a `/`.
Matching ignores case: pattern and address are both lowercased.

The one owner of address checks: OscRows, the OSC page and the outgoing
address fields all call check(). Pure: no Qt, no file access."""

from __future__ import annotations

import functools
import re

from gremlin.error import GremlinError

PATTERN_CHARS = frozenset("?*[]{}")

BLANK = "Enter an address."
NO_SLASH = "An OSC address starts with /."
NO_PATTERN = "An address sent out can't be a pattern (* ? [ ] { })."


def is_pattern(text: object) -> bool:
    """True when the address uses any pattern character."""
    return any(ch in PATTERN_CHARS for ch in str(text or ""))


def check(text: object, *, allow_pattern: bool = True) -> str:
    """Why text can't be an OSC address ("" when it can). With
    allow_pattern=False (outgoing addresses, S149) any pattern is refused."""
    address = str(text if text is not None else "")
    if not address.strip():
        return BLANK
    if not address.startswith("/"):
        return NO_SLASH
    if " " in address:
        return "An OSC address can't contain a space."
    if "#" in address:
        return "An OSC address can't contain #."
    if is_pattern(address):
        if not allow_pattern:
            return NO_PATTERN
        try:
            _translate(address.lower())
        except GremlinError as error:
            return str(error)
    return ""


def compile(text: str) -> re.Pattern[str]:  # noqa: A001 - the module's verb
    """The pattern as a regular expression matching a lowercased address.
    Raises GremlinError with the reason for a bad pattern."""
    return _compiled(str(text).lower())


def matches(pattern: str, address: str) -> bool:
    """True when the address (any case) matches the pattern."""
    return compile(pattern).fullmatch(str(address).lower()) is not None


@functools.lru_cache(maxsize=512)
def _compiled(lowered: str) -> re.Pattern[str]:
    return re.compile(_translate(lowered))


def _translate(text: str) -> str:
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "*":
            out.append("[^/]*")
        elif ch == "?":
            out.append("[^/]")
        elif ch == "[":
            close = text.find("]", i + 1)
            if close < 0:
                raise GremlinError(f'"[" at position {i + 1} is never closed.')
            out.append(_bracket(text[i + 1 : close]))
            i = close
        elif ch == "{":
            close = text.find("}", i + 1)
            if close < 0:
                raise GremlinError(f'"{{" at position {i + 1} is never closed.')
            body = text[i + 1 : close]
            if "{" in body:
                raise GremlinError("A {..} can't hold another {.")
            if "/" in body:
                raise GremlinError('A {..} can\'t hold a "/".')
            if body == "":
                raise GremlinError("A {..} can't be empty.")
            words = body.split(",")
            out.append("(?:" + "|".join(re.escape(w) for w in words) + ")")
            i = close
        elif ch == "]":
            raise GremlinError(f'"]" at position {i + 1} has no "[" before it.')
        elif ch == "}":
            raise GremlinError(f'"}}" at position {i + 1} has no "{{" before it.')
        else:
            out.append(re.escape(ch))
        i += 1
    return "".join(out)


def _bracket(body: str) -> str:
    """One [..] set as a regex class; a negated set never matches "/"."""
    negate = body.startswith("!")
    if negate:
        body = body[1:]
    if body == "":
        raise GremlinError("A [..] can't be empty.")
    if "/" in body:
        raise GremlinError('A [..] can\'t hold a "/".')
    parts: list[str] = []
    j = 0
    while j < len(body):
        # "-" first or last is a plain "-" (OSC 1.0).
        if j + 2 < len(body) and body[j + 1] == "-":
            low, high = body[j], body[j + 2]
            if low > high:
                raise GremlinError(f'The range "{low}-{high}" runs backwards.')
            parts.append(f"{re.escape(low)}-{re.escape(high)}")
            j += 3
        else:
            parts.append(re.escape(body[j]))
            j += 1
    if negate:
        return "[^/" + "".join(parts) + "]"
    return "[" + "".join(parts) + "]"
