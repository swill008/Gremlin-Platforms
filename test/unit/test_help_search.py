# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""qml/help_search.js, the Help search logic (01 S137, D-01-GUIDE-SEARCH):
all words in any order, match counts, and highlighting that never breaks a
tag or an entity. Runs the real script in a QJSEngine."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PySide6 import QtCore, QtQml

_SCRIPT = Path(__file__).resolve().parents[2] / "qml" / "help_search.js"


def _js(call: str) -> object:
    source = "\n".join(
        "" if line.startswith(".") else line
        for line in _SCRIPT.read_text(encoding="utf-8").splitlines()
    )
    engine = QtQml.QJSEngine()
    result = engine.evaluate(source + "\nJSON.stringify(" + call + ")", str(_SCRIPT))
    assert not result.isError(), result.toString()
    return json.loads(result.toString())


def _q(value: object) -> str:
    return json.dumps(value)


_TOPICS = [
    {
        "title": "Rename a device",
        "body": "<p>Select a device, then choose <b>Rename…</b>.</p>",
    },
    {
        "title": "Undo a change",
        "body": "<p>Choose <b>Edit › Undo</b> or press <b>Ctrl+Z</b>.</p>",
    },
    {
        "title": "Modes",
        "body": "<p>A mode holds its own actions &amp; device settings.</p>",
    },
]


def _spans(html: str) -> list[str]:
    return re.findall(
        r'<span style="background-color:([^";]+)[^"]*">(.*?)</span>', html
    )


def _strip_spans(html: str) -> str:
    return re.sub(r'<span style="[^"]*">|</span>', "", html)


def test_words(qapp: QtCore.QCoreApplication) -> None:
    assert _js('words("  Rename   DEVICE ")') == ["rename", "device"]
    assert _js('words("   ")') == []
    assert _js('words("")') == []


def test_plain_removes_tags_and_decodes_entities(qapp: QtCore.QCoreApplication) -> None:
    text = _js(
        _q_call(
            "plain",
            "<p>Actions &amp; <b>device</b>&nbsp;&quot;x&quot; &#169;</p><p>Two</p>",
        )
    )
    assert "<" not in text and "&amp;" not in text
    assert "Actions & device" in text
    assert '"x"' in text and "©" in text
    # A block tag stands for a space, so words don't run together.
    assert "Two" in text and "©Two" not in text


def _q_call(name: str, *args: object) -> str:
    return name + "(" + ", ".join(_q(a) for a in args) + ")"


def test_count_needs_every_word(qapp: QtCore.QCoreApplication) -> None:
    topic = _TOPICS[0]
    # "device" twice (title + body), "rename" twice (title + bold label).
    assert _js(f"countIn({_q(topic)}, words('device rename'))") == 4
    assert _js(f"countIn({_q(topic)}, words('RENAME device'))") == 4
    # One word missing: no match at all.
    assert _js(f"countIn({_q(topic)}, words('rename mode'))") == 0


def test_filter_keeps_topic_order_and_blank_means_no_filter(
    qapp: QtCore.QCoreApplication,
) -> None:
    assert _js(_q_call("filter", _TOPICS, "device")) == [
        {"index": 0, "count": 2},
        {"index": 2, "count": 1},
    ]
    assert _js(_q_call("filter", _TOPICS, "choose")) == [
        {"index": 0, "count": 1},
        {"index": 1, "count": 1},
    ]
    assert _js(_q_call("filter", _TOPICS, "   ")) == []
    assert _js(_q_call("filter", _TOPICS, "zebra")) == []
    # Entities are searched as the reader sees them.
    assert _js(_q_call("filter", _TOPICS, "actions & device")) == [
        {"index": 2, "count": 3}
    ]
    assert _js(_q_call("filter", _TOPICS, "amp")) == []


def test_highlight_marks_every_match_and_the_current_one(
    qapp: QtCore.QCoreApplication,
) -> None:
    html = "<p>Device one, <b>device</b> two, DEVICE three.</p>"
    out = _js(_q_call("highlight", html, "device", 1, "#111111", "#222222"))
    assert out["total"] == 3
    spans = _spans(out["html"])
    assert [colour for colour, _ in spans] == ["#111111", "#222222", "#111111"]
    assert [word for _, word in spans] == ["Device", "device", "DEVICE"]
    # The current one sits inside the <b>, not around it.
    assert '<b><span style="background-color:#222222">device</span></b>' in out["html"]
    assert _strip_spans(out["html"]) == html


def test_highlight_never_breaks_tags_or_entities(qapp: QtCore.QCoreApplication) -> None:
    html = (
        '<p>Use <a href="topic:span-b">&quot;b&quot; &amp; amp</a> '
        "<b>bold</b> &lt;b&gt;</p>"
    )
    # "b" is in tag names, an attribute and entities' names; "amp" and
    # "quot" are entity names. Only visible text is marked.
    out = _js(_q_call("highlight", html, "b amp quot", 0))
    assert _strip_spans(out["html"]) == html
    # Visible: "b" in "b" (quoted), "amp", "bold", "<b>" -> 4 matches.
    assert out["total"] == 4
    for colour, inner in _spans(out["html"]):
        assert "<" not in inner and ">" not in inner
    # The quoted b keeps its entities whole around the span.
    assert '&quot;<span style="background-color:orange">b</span>&quot;' in out["html"]
    # A decoded entity matched is wrapped whole.
    out = _js(_q_call("highlight", "<p>Tom &amp; Jerry</p>", "&", 0))
    assert out["total"] == 1
    assert ">&amp;</span>" in out["html"]
    assert _strip_spans(out["html"]) == "<p>Tom &amp; Jerry</p>"


def test_highlight_across_tags_counts_once(qapp: QtCore.QCoreApplication) -> None:
    html = "<p>Re<b>name</b> it</p>"
    out = _js(_q_call("highlight", html, "rename", 0, "#111111", "#222222"))
    assert out["total"] == 1
    assert _spans(out["html"]) == [("#222222", "Re"), ("#222222", "name")]
    assert _strip_spans(out["html"]) == html


def test_highlight_blank_text_changes_nothing(qapp: QtCore.QCoreApplication) -> None:
    html = "<p>Anything</p>"
    assert _js(_q_call("highlight", html, " ", 0)) == {"html": html, "total": 0}
    out = _js(_q_call("highlight", html, "zebra", 0))
    assert out == {"html": html, "total": 0}
