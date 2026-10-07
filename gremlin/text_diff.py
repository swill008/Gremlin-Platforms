# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""What changed between two texts, line by line and word by word, for the
History window's Before and After (08 S104, D-08-HISTORY-DIFF).

rows() lines the two texts up row for row. A line only on one side faces a
blank filler row on the other. Each row has a kind: "same", "removed" (only
Before), "added" (only After) or "changed" (both, different). A changed row
also has the character ranges of its changed words on each side.
"""

from __future__ import annotations

import difflib
import re

# Words, runs of spaces and single other characters: "buttons (1, 2)"
# compares "1", ",", " ", "2" one by one.
_TOKEN = re.compile(r"\w+|\s+|[^\w\s]")


def _tokens(line: str) -> list[tuple[int, int, str]]:
    return [(m.start(), m.end(), m.group()) for m in _TOKEN.finditer(line)]


def _add_span(spans: list[list[int]], start: int, end: int) -> None:
    if start >= end:
        return
    if spans and spans[-1][1] >= start:
        spans[-1][1] = max(spans[-1][1], end)
    else:
        spans.append([start, end])


def _range(
    tokens: list[tuple[int, int, str]], first: int, last: int
) -> tuple[int, int]:
    """Character range of tokens[first:last], without spaces at its ends."""
    while first < last and tokens[first][2].isspace():
        first += 1
    while last > first and tokens[last - 1][2].isspace():
        last -= 1
    if first >= last:
        return 0, 0
    return tokens[first][0], tokens[last - 1][1]


def word_spans(before: str, after: str) -> tuple[list[list[int]], list[list[int]]]:
    """The changed words' [start, end) character ranges in each line."""
    old, new = _tokens(before), _tokens(after)
    matcher = difflib.SequenceMatcher(
        None, [t[2] for t in old], [t[2] for t in new], autojunk=False
    )
    old_spans: list[list[int]] = []
    new_spans: list[list[int]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        _add_span(old_spans, *_range(old, i1, i2))
        _add_span(new_spans, *_range(new, j1, j2))
    return old_spans, new_spans


def _row(kind: str, before: str = "", after: str = "") -> dict:
    spans: tuple[list[list[int]], list[list[int]]] = ([], [])
    if kind == "changed":
        spans = word_spans(before, after)
    return {
        "kind": kind,
        "before": before,
        "after": after,
        "beforeSpans": spans[0],
        "afterSpans": spans[1],
        "block": -1,
    }


def rows(before: str, after: str) -> list[dict]:
    """The two texts lined up row for row (see the module's docstring).

    Each row: {"kind", "before", "after", "beforeSpans", "afterSpans",
    "block"}; "before"/"after" is "" on a filler row, the spans are set on
    changed rows only, and "block" is the index of the change block the row
    is in (-1 on a same row). Rows next to each other that aren't "same"
    are one block.
    """
    old = (before or "").splitlines()
    new = (after or "").splitlines()
    matcher = difflib.SequenceMatcher(None, old, new, autojunk=False)
    out: list[dict] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            out.extend(_row("same", line, line) for line in old[i1:i2])
            continue
        # A replaced run: its lines pair up in order as changed rows; the
        # longer side's extra lines face filler rows.
        paired = min(i2 - i1, j2 - j1)
        for k in range(paired):
            out.append(_row("changed", old[i1 + k], new[j1 + k]))
        out.extend(_row("removed", before=line) for line in old[i1 + paired : i2])
        out.extend(_row("added", after=line) for line in new[j1 + paired : j2])
    block = -1
    previous_same = True
    for row in out:
        if row["kind"] == "same":
            previous_same = True
            continue
        if previous_same:
            block += 1
        previous_same = False
        row["block"] = block
    return out


def blocks(diff_rows: list[dict]) -> list[int]:
    """The first row index of each change block, in order."""
    starts: list[int] = []
    seen = -1
    for index, row in enumerate(diff_rows):
        if row.get("block", -1) > seen:
            seen = row["block"]
            starts.append(index)
    return starts
