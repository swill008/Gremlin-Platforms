# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
"""Search text: parsing, matching, scoring and the "Did you mean" hint.

Pure Python, no Qt. Rows are duck-typed: anything with SearchRow's
attributes (gremlin/search_index.py). Two plug-in points:

- PREFIXES: one entry per prefix name ("device:", "vjoy:" ...), the texts
  of a row it looks at and the line the ? popup shows.
- DISPLAY: one entry per Reference target kind (gremlin/references.py),
  how a target tuple reads in the results.
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

syslog = logging.getLogger("system")

# The row fields free terms look at, with their weight in the score.
FIELDS: dict[str, float] = {
    "input_label": 1.0,
    "custom_name": 1.0,
    "action_name": 0.9,
    "text": 0.7,
    "notes": 0.7,
    "targets": 0.8,
    "mode": 0.6,
    "device_name": 0.6,
    "source_name": 0.5,
}

# Scores of one term against one text (before the field weight).
EXACT = 1000.0
WORD_START = 800.0
CONTIGUOUS = 600.0
SCATTERED = 200.0

Span = tuple[int, int]
# A prefix's texts: [(span key, text)], the key naming where spans go.
Texts = list[tuple[str, str]]


# ---------------------------------------------------------------- display


def _input_label(input_type: object, input_id: object) -> str:
    """The control as the program names it ("Button 30", "X Axis", "F5");
    target tuples carry the type as a number and a key as (scan, extended)."""
    try:
        from gremlin import references
        from gremlin.types import InputType

        kind = InputType(int(input_type))  # type: ignore[arg-type]
        if isinstance(input_id, list):
            input_id = tuple(input_id)
        return references.input_label(kind, input_id)
    except Exception:  # noqa: BLE001 - no labels without the program
        return f"{input_type} {input_id}"


def _device_name(guid: object) -> str:
    """A device's shown name from a guid or its guid_key text."""
    try:
        import uuid

        from gremlin import references
        from gremlin.modules import ids
        from gremlin.modules.device_class import INTERNAL_INPUTS

        key = ids.guid_key(guid)
        for internal, (name, _) in INTERNAL_INPUTS.items():
            if ids.guid_key(internal) == key:
                return name
        name = references.device_name(uuid.UUID(hex=key))
        return name or str(guid)
    except Exception:  # noqa: BLE001 - a device nothing can name
        return str(guid)


def _vjoy(key: tuple) -> str:
    _, device, input_type, number = key
    return f"vJoy {device} {_input_label(input_type, number)}"


def _xbox(key: tuple) -> str:
    _, pad, control = key
    name = "Xbox 360 Controller" if int(pad) == 1 else f"Xbox 360 {int(pad)}"
    return f"{name} {control}"


def _input(key: tuple) -> str:
    _, guid, input_type, input_id = key
    return f"{_device_name(guid)} {_input_label(input_type, input_id)}"


def _osc_out(key: tuple) -> str:
    _, target, address = key
    return f"OSC {target} {address}".replace("  ", " ").strip()


def _profile(key: tuple) -> str:
    path = str(key[1])
    return os.path.splitext(os.path.basename(path))[0] or path


# PLUG-IN POINT: target kind -> how its tuple reads. A new kind in
# gremlin/references.py needs an entry (test_search_plugins.py checks).
DISPLAY: dict[str, Callable[[tuple], str]] = {
    "vjoy": _vjoy,
    "xbox": _xbox,
    "input": _input,
    "mode": lambda key: f"Mode {key[1]}",
    "action": lambda key: str(key[1]),
    "osc-out": _osc_out,
    "mouse": lambda key: f"Mouse {key[1]}",
    "profile": _profile,
}


def display(target_key: tuple) -> str:
    """A target tuple as the results show it; never raises."""
    try:
        kind = target_key[0]
    except (TypeError, IndexError):
        return str(target_key)
    show = DISPLAY.get(kind)
    if show is not None:
        try:
            return show(target_key)
        except Exception:  # noqa: BLE001 - a malformed tuple
            syslog.debug("search: can't show %r", target_key, exc_info=True)
    return " ".join(str(part) for part in target_key)


# --------------------------------------------------------------- prefixes


def _field(name: str) -> Callable[[Any], Texts]:
    def texts(row: Any) -> Texts:  # noqa: ANN401
        return [(name, str(getattr(row, name, "") or ""))]

    return texts


def _targets_of(kind: str) -> Callable[[Any], Texts]:
    """The display texts of a row's targets of one kind."""

    def texts(row: Any) -> Texts:  # noqa: ANN401
        keys = getattr(row, "target_keys", ()) or ()
        shown = getattr(row, "targets", ()) or ()
        out: Texts = []
        for i, key in enumerate(keys):
            if key and key[0] == kind:
                text = shown[i] if i < len(shown) else display(key)
                out.append((f"targets:{i}", str(text)))
        return out

    return texts


def _key(row: Any) -> Texts:  # noqa: ANN401
    """A keyboard row's own key, and every input the row sends or reads
    (key:F5 finds a Map to Keyboard sending F5)."""
    out = _targets_of("input")(row)
    if "key" in (getattr(row, "kinds", ()) or ()):
        out += _field("input_label")(row) + _field("custom_name")(row)
    return out


def _both(name: str, kind: str) -> Callable[[Any], Texts]:
    """The row's own field and its targets of one kind."""
    own = _field(name)
    targets = _targets_of(kind)

    def texts(row: Any) -> Texts:  # noqa: ANN401
        return own(row) + targets(row)

    return texts


def _osc(row: Any) -> Texts:  # noqa: ANN401
    out = _targets_of("osc-out")(row)
    if "osc" in (getattr(row, "kinds", ()) or ()):
        out += _field("input_label")(row) + _field("custom_name")(row)
    return out


def _action(row: Any) -> Texts:  # noqa: ANN401
    return (
        _field("action_name")(row)
        + _field("action_tag")(row)
        + _targets_of("action")(row)
    )


# PLUG-IN POINT: prefix name -> (field name or texts(row), ? popup line).
PREFIXES: dict[str, tuple[str | Callable[[Any], Texts], str]] = {
    "key": (_key, "a keyboard key or a control, pressed or sent, e.g. key:F5"),
    "vjoy": (_targets_of("vjoy"), 'a vJoy output, e.g. vjoy:"vJoy 1 Button 3"'),
    "xbox": (_targets_of("xbox"), "an Xbox 360 output, e.g. xbox:A"),
    "osc": (_osc, "an OSC input or output address, e.g. osc:/fader1"),
    "mouse": (_targets_of("mouse"), "a mouse output, e.g. mouse:Left"),
    "mode": (
        _both("mode", "mode"),
        "the mode a binding is in or changes to, e.g. mode:Combat",
    ),
    "profile": (
        _both("source_name", "profile"),
        "the profile or setup name, or a profile loaded, e.g. profile:DCS",
    ),
    "device": (
        _both("device_name", "input"),
        'the device, e.g. device:"T.16000M"',
    ),
    "action": (_action, 'the action, e.g. action:"Map to vJoy"'),
}


def prefix_texts(name: str, row: Any) -> Texts:  # noqa: ANN401
    """The texts of a row the prefix looks at."""
    look, _ = PREFIXES[name]
    if isinstance(look, str):
        return _field(look)(row)
    return look(row)


# Row fields holding a tuple of texts; spans go to "<field>:<index>".
_TUPLE_FIELDS = frozenset({"targets", "notes"})


def _row_texts(row: Any) -> Texts:  # noqa: ANN401
    out: Texts = []
    for name in FIELDS:
        if name in _TUPLE_FIELDS:
            for i, text in enumerate(getattr(row, name, ()) or ()):
                out.append((f"{name}:{i}", str(text)))
        else:
            out.append((name, str(getattr(row, name, "") or "")))
    return out


def _weight(key: str) -> float:
    return FIELDS.get(key.split(":", 1)[0], 0.5)


# ------------------------------------------------------------------ query


@dataclass(frozen=True)
class Term:
    """One search word or quoted phrase; prefix "" for a free term."""

    text: str
    prefix: str = ""
    pattern: re.Pattern[str] | None = None
    folded: str = ""


@dataclass(frozen=True)
class Query:
    text: str = ""
    terms: tuple[Term, ...] = ()
    case: bool = False
    word: bool = False
    regex: bool = False
    error: str = ""

    @property
    def empty(self) -> bool:
        return not self.terms and not self.error

    @property
    def free(self) -> tuple[Term, ...]:
        return tuple(t for t in self.terms if not t.prefix)

    @property
    def prefixed(self) -> tuple[Term, ...]:
        return tuple(t for t in self.terms if t.prefix)


@dataclass
class Match:
    score: float
    spans: dict[str, list[Span]] = field(default_factory=dict)


_TOKEN = re.compile(r'(?:(\w[\w-]*):)?(?:"([^"]*)"?|(\S*))')


def tokens(text: str) -> list[tuple[str, str]]:
    """(prefix, value) pairs; prefix "" when not a known prefix name."""
    out: list[tuple[str, str]] = []
    for m in _TOKEN.finditer(text):
        name, quoted, bare = m.group(1), m.group(2), m.group(3)
        value = quoted if quoted is not None else (bare or "")
        if name and name.lower() in PREFIXES:
            out.append((name.lower(), value))
        elif name:
            # Not a prefix: keep the text as typed.
            out.append(("", m.group(0).replace('"', "")))
        elif value:
            out.append(("", value))
    return out


def _compile(text: str, case: bool, word: bool, regex: bool) -> re.Pattern[str]:
    body = text if regex else re.escape(text)
    if word:
        body = rf"\b(?:{body})\b"
    return re.compile(body, 0 if case else re.IGNORECASE)


def parse(
    text: str, case: bool = False, word: bool = False, regex: bool = False
) -> Query:
    """The typed text as a Query; a bad regex gives Query.error, no raise."""
    text = text or ""
    pairs = tokens(text)
    if regex:
        # The free text is one pattern, spaces included.
        free = " ".join(v for p, v in pairs if not p).strip()
        pairs = [(p, v) for p, v in pairs if p] + ([("", free)] if free else [])
    terms: list[Term] = []
    for prefix, value in pairs:
        pattern = None
        if regex or word:
            try:
                pattern = _compile(value, case, word, regex)
            except re.error as err:
                return Query(text, (), case, word, regex, f"Not a valid pattern: {err}")
        if value or prefix:
            terms.append(Term(value, prefix, pattern, value.casefold()))
    return Query(text, tuple(terms), case, word, regex)


# --------------------------------------------------------------- matching


def _is_start(text: str, i: int) -> bool:
    """A word starts at i: after a non-letter, or a capital after a small."""
    if i <= 0:
        return True
    ch, prev = text[i], text[i - 1]
    if not prev.isalnum():
        return ch.isalnum()
    return ch.isupper() and prev.islower()


def _subsequence(
    term: str, text: str, shown: str, start: int = 0, starts: bool = True
) -> list[int] | None:
    """Positions of term's characters in order in text, the first at
    start, then preferring contiguous runs (and word starts when starts);
    None when not all are there."""
    out = [start]
    for ch in term[1:]:
        nxt = out[-1] + 1
        if nxt < len(text) and text[nxt] == ch:
            out.append(nxt)
            continue
        first = text.find(ch, nxt)
        if first < 0:
            return None
        pick = first
        if starts and not _is_start(shown, first):
            at = first
            while True:
                at = text.find(ch, at + 1)
                if at < 0:
                    break
                if _is_start(shown, at):
                    pick = at
                    break
        out.append(pick)
    return out


# How many places of the term's first letter fuzzy matching tries.
_ANCHORS = 12


def _fuzzy(needle: str, hay: str, text: str) -> tuple[float, list[Span]] | None:
    """The best in-order scattered match that isn't too scattered. Tries
    the first place of the term's first letter and each later one that
    starts a word ("tggl" finds "toggle" after "Text to ...")."""
    limit = 1 + (len(needle) + 1) // 2
    best: tuple[float, list[Span]] | None = None
    start = hay.find(needle[0])
    tries = 0
    while start >= 0 and tries < _ANCHORS:
        if tries == 0 or _is_start(text, start):
            tries += 1
            seen = None
            for starts in (True, False):
                positions = _subsequence(needle, hay, text, start, starts)
                if positions is None:
                    return best  # no later place can fit either
                if positions == seen:
                    continue
                seen = positions
                spans = _runs(positions)
                if len(spans) > limit:  # too scattered to mean anything
                    continue
                bonus = sum(30.0 for s, _ in spans if _is_start(text, s))
                score = SCATTERED + bonus - 20.0 * len(spans) - start * 0.01
                if best is None or score > best[0]:
                    best = (score, spans)
        start = hay.find(needle[0], start + 1)
    return best


def _runs(positions: list[int]) -> list[Span]:
    spans: list[Span] = []
    for p in positions:
        if spans and spans[-1][1] == p:
            spans[-1] = (spans[-1][0], p + 1)
        else:
            spans.append((p, p + 1))
    return spans


def score_text(
    term: Term, text: str, case: bool, folded: str | None = None
) -> tuple[float, list[Span]] | None:
    """How well one term matches one text: (score, spans) or None.
    folded: text.casefold() when the caller has it already."""
    if not text:
        return None
    if term.pattern is not None:
        found = [m.span() for m in term.pattern.finditer(text) if m.end() > m.start()]
        if not found:
            return None
        first = found[0]
        exact = first == (0, len(text))
        return (EXACT if exact else CONTIGUOUS) - first[0] * 0.01, found
    needle = term.text if case else term.folded
    hay = text if case else (folded if folded is not None else text.casefold())
    if len(hay) != len(text):  # casefold changed lengths (e.g. "ß")
        needle, hay = term.text.lower(), text.lower()
        if len(hay) != len(text):
            return None
    if not needle:
        return None
    if needle == hay:
        return EXACT, [(0, len(text))]
    at = hay.find(needle)
    if at >= 0:
        best = at
        while best >= 0 and not _is_start(text, best):
            best = hay.find(needle, best + 1)
        if best >= 0:
            return WORD_START - best * 0.01, [(best, best + len(needle))]
        return CONTIGUOUS - at * 0.01, [(at, at + len(needle))]
    if len(needle) < 2:
        return None
    return _fuzzy(needle, hay, text)


Folded = list[tuple[str, str, str, float]]


def _fold(texts: Texts) -> Folded:
    """(key, text, folded text, field weight) for the non-empty texts."""
    return [(k, t, t.casefold(), _weight(k)) for k, t in texts if t]


def _is_subsequence(needle: str, hay: str) -> bool:
    pos = 0
    for ch in needle:
        pos = hay.find(ch, pos) + 1
        if not pos:
            return False
    return True


# Each row's free texts, folded, kept while the row lives in the cache.
_cache: dict[int, tuple[Any, Folded, str, str]] = {}
_CACHE_MAX = 250_000


def _free(row: Any) -> tuple[Folded, str, str]:  # noqa: ANN401
    hit = _cache.get(id(row))
    if hit is not None and hit[0] is row:
        return hit[1], hit[2], hit[3]
    texts = _fold(_row_texts(row))
    joined = "\x00".join(t[1] for t in texts)
    joined_folded = "\x00".join(t[2] for t in texts)
    if len(_cache) >= _CACHE_MAX:
        _cache.clear()
    _cache[id(row)] = (row, texts, joined, joined_folded)
    return texts, joined, joined_folded


def clear_cache() -> None:
    """Forget the cached row texts (the index calls it after a rebuild)."""
    _cache.clear()


def _best(
    term: Term,
    texts: Folded,
    case: bool,
    containing: str = "",
) -> tuple[float, dict[str, list[Span]]] | None:
    """The term's best score over the texts and its spans in each;
    containing: only the texts that have this (already folded) text."""
    best = 0.0
    spans: dict[str, list[Span]] = {}
    for key, text, folded, weight in texts:
        if containing and containing not in (text if case else folded):
            continue
        got = score_text(term, text, case, folded)
        if got is None:
            continue
        score, where = got
        spans.setdefault(key, []).extend(where)
        best = max(best, score * weight)
    if not spans:
        return None
    return best, spans


def match(row: Any, query: Query) -> Match | None:  # noqa: ANN401
    """The row's Match for the query (every term must match), or None."""
    if query.error:
        return None
    total = 0.0
    spans: dict[str, list[Span]] = {}
    for term in query.terms:
        containing = ""
        if term.prefix:
            raw = prefix_texts(term.prefix, row)
            if not term.text:  # "vjoy:" alone: rows that have one
                if not any(t for _, t in raw):
                    return None
                continue
            texts = _fold(raw)
        else:
            texts, joined, joined_folded = _free(row)
            if term.pattern is None:
                needle = term.text if query.case else term.folded
                hay = joined if query.case else joined_folded
                if needle in hay:
                    # A whole match beats any scattered one: skip fuzzy.
                    containing = needle
                elif len(needle) < 2 or not _is_subsequence(needle, hay):
                    return None  # not even scattered over all the texts
        got = _best(term, texts, query.case, containing)
        if got is None:
            return None
        score, where = got
        total += score
        for key, found in where.items():
            spans.setdefault(key, []).extend(found)
    for key, found in spans.items():
        spans[key] = _merge(found)
    return Match(total, spans)


def _merge(spans: list[Span]) -> list[Span]:
    out: list[Span] = []
    for start, end in sorted(spans):
        if out and start <= out[-1][1]:
            out[-1] = (out[-1][0], max(end, out[-1][1]))
        else:
            out.append((start, end))
    return out


# ---------------------------------------------------- did you mean / hints


def distance(a: str, b: str, limit: int = 99) -> int:
    """Edit distance (adjacent swaps count 1), stopping past limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev2: list[int] = []
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, cb in enumerate(b, 1):
            cost = 0 if ca == cb else 1
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + cost)
            if i > 1 and j > 1 and ca == b[j - 2] and a[i - 2] == cb:
                cur[j] = min(cur[j], prev2[j - 2] + 1)
        if min(cur) > limit:
            return limit + 1
        prev2, prev = prev, cur
    return prev[-1]


def _words(vocabulary: Iterable[str]) -> dict[str, str]:
    words: dict[str, str] = {}
    for entry in vocabulary:
        for w in re.findall(r"[\w./+-]+", str(entry)):
            words.setdefault(w.casefold(), w)
    return words


def did_you_mean(text: str, vocabulary: Iterable[str]) -> str | None:
    """The text with misspelt words replaced by the nearest known word,
    or None when every word is known or nothing is near."""
    words = _words(vocabulary)
    if not words:
        return None
    changed = False
    out: list[str] = []
    for prefix, value in tokens(text or ""):
        fixed = []
        for w in value.split():
            folded = w.casefold()
            if folded in words or len(folded) < 3:
                fixed.append(w)
                continue
            limit = max(1, len(folded) // 4)
            best, best_d = None, limit + 1
            for known_folded, known in words.items():
                d = distance(folded, known_folded, limit)
                if d < best_d:
                    best, best_d = known, d
            if best is not None:
                fixed.append(best)
                changed = True
            else:
                fixed.append(w)
        joined = " ".join(fixed)
        if " " in joined and prefix:
            joined = f'"{joined}"'
        out.append(f"{prefix}:{joined}" if prefix else joined)
    return " ".join(out) if changed else None


def suggestions(
    text: str, vocabulary: Iterable[str], recent: Iterable[str], limit: int = 8
) -> list[str]:
    """Whole-text completions: recent searches first, then prefix names,
    then known names starting with the last word."""
    text = text or ""
    folded = text.casefold().strip()
    out: list[str] = []

    def add(item: str) -> None:
        if item and item not in out and item.casefold() != folded:
            out.append(item)

    for item in recent:
        if not folded or item.casefold().startswith(folded):
            add(item)
    if not folded:
        return out[:limit]
    head, _, last = text.rpartition(" ")
    stem = last.casefold()
    lead = f"{head} " if head else ""
    if stem and ":" not in stem:
        for name in PREFIXES:
            if name.startswith(stem):
                add(f"{lead}{name}:")
    value = stem.split(":", 1)[-1].strip('"')
    pre = last[: len(last) - len(value)] if ":" in stem else ""
    pre = pre.rstrip('"')
    if value:
        known = sorted({str(v) for v in vocabulary}, key=str.casefold)
        for entry in known:
            if entry.casefold().startswith(value):
                shown = f'"{entry}"' if " " in entry else entry
                add(f"{lead}{pre}{shown}")
            if len(out) >= limit:
                break
    return out[:limit]
