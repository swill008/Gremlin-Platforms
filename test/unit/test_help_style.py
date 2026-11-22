# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The automatic Help check (claude/plans/help-style-guide.md section 7):
every topic's visible text keeps to the length, word and "›" rules. One test
per chapter file, so each writer sees only their own file's failures; each
failure names the file, the topic id and the offending text."""

from __future__ import annotations

import functools
import re

import pytest
from PySide6 import QtCore

from test.unit import help_book
from test.unit.help_book import ROOT as _ROOT

_MAX_WORDS = 30  # style guide 2: never over 30 words
_MAX_SENTENCES = 3  # style guide 2: paragraphs at most 3 sentences


def _chapter_files() -> dict[str, str]:
    """{chapter id: file name} of every chapter file in qml/help."""
    files = {}
    for path in sorted((_ROOT / "qml" / "help").glob("*.js")):
        source = path.read_text(encoding="utf-8")
        match = re.search(r'var chapter = \{ id: "([^"]+)"', source)
        if match:
            files[match.group(1)] = path.name
    return files


_FILES = _chapter_files()


# --- Visible text -------------------------------------------------------

_LINK_TEXT = re.compile(r"<a\b[^>]*>.*?</a>", re.S)


def _visible(markup: str) -> str:
    return re.sub(r"\s+", " ", help_book.text(markup)).strip()


def blocks(body: str, tag: str) -> list[str]:
    """Visible text of each <tag> block, link text left out, nested lists
    left out of their parent item."""
    body = _LINK_TEXT.sub(" ", body)
    out = []
    for match in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", body, re.S):
        inner = match.group(1)
        if tag == "li":
            inner = re.split(r"<[ou]l\b", inner, maxsplit=1)[0]
        out.append(_visible(inner))
    return [b for b in out if b]


# A full stop that doesn't end a sentence: abbreviations, numbers, file
# names. "…" inside a label (Module Setup…) never ends one.
_ABBREVIATIONS = re.compile(r"\b(e\.g|i\.e|etc|vs|approx)\.$", re.I)


def sentences(text: str) -> list[str]:
    parts = []
    start = 0
    for match in re.finditer(r"[.!?](?=[\"')\]]?(?:\s+[\"'(]?[A-Z0-9]|\s*$))", text):
        piece = text[start:match.end()]
        if _ABBREVIATIONS.search(piece):
            continue
        parts.append(piece.strip())
        start = match.end()
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    return [p for p in parts if re.search(r"\w", p)]


def words(sentence: str) -> int:
    return len([w for w in sentence.split() if re.search(r"\w", w)])


# --- Rules --------------------------------------------------------------

# Decision 1: where the vJoy tick boxes are described, Help may say once that
# Slider 1 and Slider 2 read S1 and S2. Only the pair "S1 and S2" (or "S1 /
# S2", "S1, S2", "S1 or S2") counts, and only in a sentence about Slider or
# the tick boxes; S1 alone, S2 alone or S187 stay spec numbers.
_AXIS_PAIR = re.compile(r"\bS1\b\s*(?:and|or|/|,)\s*\bS2\b")
_AXIS_CONTEXT = re.compile(r"\bSlider\b|\btick box", re.I)


def strip_axis_names(text: str) -> tuple[str, int]:
    """(text with the allowed "S1 and S2" mentions blanked, how many)."""
    count = 0
    out = []
    for sentence in sentences(text) or [text]:
        if _AXIS_CONTEXT.search(sentence):
            sentence, n = _AXIS_PAIR.subn("Slider pair", sentence)
            count += n
        out.append(sentence)
    return " ".join(out), count


_SPEC_NUMBER = re.compile(r"\b[SQ]\d+[a-z]?\b|\bD-[A-Z0-9]+-[A-Z0-9-]*")

# Style guide 3: internal words never in Help. (pattern, what it stands for)
_NEVER = [
    (r"\bwir(e|es|ed|ing)\b", "wire"),
    (r"\bfire[sd]\b", "fires"),
    (r"\blatch(es|ed|ing)?\b", "latches"),
    (r"\bcloak(s|ed|ing)?\b", "cloak"),
    (r"\bsnapshots?\b", "snapshot"),
    (r"\bbus(es)?\b", "bus"),
    (r"\b(un)?claim(s|ed|ing)?\b", "claim"),
    (r"\bcontainer actions?\b", "container action"),
    (r"\binstances?\b", "instance"),
    (r"\bmodule files?\b", "module file"),
    (r"\.json\b", ".json"),
    (r"\bchecked on\b", "test note (checked on ...)"),
]
_NEVER_RE = [(re.compile(p, re.I), name) for p, name in _NEVER]
# The on-screen phrase the Map to vJoy box shows (glossary): allowed.
_ON_SCREEN_CLAIM = re.compile(r"\(not claimed\)")


def _glossary_avoid() -> list[str]:
    """The glossary's "Instead of" column, as phrases Help can check.

    Left out, because a plain match would flag good text: entries limited to
    a context by a note in brackets ("Configuration (for the page)"), entries
    that are a "Use" word elsewhere in the glossary or on screen (Help follows
    the screen, Decision 3), and single ordinary words (Edit, Find, Delay):
    a single word is kept only when it can't be plain English (an inner
    capital, a digit, or one of the coined words below)."""
    coined = {
        "unmapped", "unbound", "watchdog", "vignette", "sniffer", "desync",
        "whitelist", "blacklist", "zeroconf", "bonjour", "powercfg", "daemon",
        "systray", "typeahead", "autocomplete", "changelog", "untracked",
        "replug", "re-enumerate", "re-enumerated", "remapped", "dest",
        "autostart", "dill",
    }
    glossary = (_ROOT / "claude" / "glossary.md").read_text(encoding="utf-8")
    rows = [line.split("|") for line in glossary.splitlines() if line.startswith("|")]
    rows = [r for r in rows if len(r) >= 5 and not set(r[1].strip()) <= {"-"}]
    use = " ".join(r[-3] for r in rows)
    screen = _screen_text()
    phrases = set()
    for row in rows:
        cell = row[-2]
        cell = re.sub(r"\[[^\]]*\]", "", cell)
        for raw in re.split(r",|/(?![^(]*\))|\+", cell):
            raw = raw.strip()
            if not raw or "(" in raw or "*" in raw or "`" in raw:
                continue
            phrase = raw.strip("\"' .").rstrip("…").strip()
            if len(phrase) < 3 or not re.search(r"[A-Za-z]", phrase):
                continue
            if " " not in phrase:
                plain = re.fullmatch(r"[A-Za-z][a-z]+", phrase)
                if plain and phrase.casefold() not in coined:
                    continue
            known = use + "\n" + screen
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", known, re.I):
                continue
            phrases.add(phrase)
    return sorted(phrases)


def _screen_text() -> str:
    """Every string the program shows (QML, JavaScript and Python outside
    the Help book, and setup)."""
    parts = []
    for folder, pattern in (("qml", "*.qml"), ("qml", "*.js"), ("gremlin", "*.py"),
                            ("action_plugins", "*.py"), ("action_plugins", "*.qml")):
        for path in (_ROOT / folder).rglob(pattern):
            if "help" in path.parts:
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            parts += re.findall(r'"([^"\n]*\s[^"\n]*)"', source)
    setup = _ROOT / "installer" / "gremlin_platforms.iss"
    parts.append(setup.read_text(encoding="utf-8"))
    return "\n".join(parts)


# "›" belongs to menu paths only: a bold path (<b>Tools › Drivers</b>), the
# link texts "Show me ›" / "Open ›", or a later plain mention of a path that
# is bold earlier in the topic (bold the first time only, guide 3).
_BOLD = re.compile(r"<b>(.*?)</b>", re.S)


def stray_arrows(body: str) -> list[str]:
    # Bold words joined by › (<b>Row</b> › <b>Clear Name</b>) are one path.
    body = re.sub(r"</b>\s*›\s*<b>", " › ", body)
    bold_paths = [_visible(b) for b in _BOLD.findall(body) if "›" in b]
    rest = _LINK_TEXT.sub(" ", body)
    rest = _BOLD.sub(lambda m: " " if "›" in m.group(1) else m.group(0), rest)
    rest = re.sub(r"\b(Show me|Open) ›", " ", rest)
    text = _visible(re.sub(r"<[^>]+>", " ", rest))
    stray = []
    for match in re.finditer(r"›", text):
        before = re.findall(r"\S+", text[:match.start()])
        after = re.findall(r"\S+", text[match.end():])
        left = before[-1].strip(".,;:()") if before else ""
        right = after[0].strip(".,;:()") if after else ""
        pair = f"{left} › {right}"
        if any(pair.strip() in path for path in bold_paths):
            continue
        stray.append(text[max(0, match.start() - 30):match.end() + 30])
    return stray


@functools.lru_cache(maxsize=1)
def _screen_literals() -> frozenset[str]:
    """Every string literal the program's own code holds (QML, JavaScript and
    Python outside the Help book, and setup), to find on-screen labels."""
    parts = []
    for folder, pattern in (("qml", "*.qml"), ("qml", "*.js"), ("gremlin", "*.py"),
                            ("action_plugins", "*.py"), ("action_plugins", "*.qml")):
        for path in (_ROOT / folder).rglob(pattern):
            if "help" in path.parts:
                continue
            source = path.read_text(encoding="utf-8", errors="replace")
            parts += re.findall(r'"((?:[^"\\\n]|\\.)+)"', source)
            parts += re.findall(r"'((?:[^'\\\n]|\\.)+)'", source)
    setup = (_ROOT / "installer" / "gremlin_platforms.iss").read_text(encoding="utf-8")
    parts += re.findall(r"=([^\n]+)", setup)  # its [Messages] and [CustomMessages]
    return frozenset(p.strip().rstrip(".:…").strip() for p in parts)


@functools.lru_cache(maxsize=1)
def _glossary_terms() -> tuple[str, ...]:
    """The glossary's approved words: every bold term in its "Use" and core
    "Term" / "Meaning" columns (never the "Instead of" column)."""
    glossary = (_ROOT / "claude" / "glossary.md").read_text(encoding="utf-8")
    terms = set()
    for line in glossary.splitlines():
        cells = line.split("|")
        if not line.startswith("|") or len(cells) < 4:
            continue
        for cell in cells[1:3]:
            for bold in re.findall(r"\*\*(.+?)\*\*", cell):
                for term in bold.split(" / "):
                    term = term.strip().rstrip("…").strip()
                    if len(term) >= 3:
                        terms.add(term)
    return tuple(sorted(terms, key=len, reverse=True))


def allowed_words_masked(body: str, text: str, screen: frozenset[str],
                         terms: tuple[str, ...]) -> str:
    """The text with screen labels and glossary terms blanked (Decision 5):
    bold or quoted text that is a whole string the program shows (trailing
    "…", ":" and "." aside), and every approved glossary term (with -s, -es,
    -ed, -ing). The same length, so places stay put."""
    labels = [_visible(b) for b in _BOLD.findall(body)]
    labels += [a or b for a, b in re.findall(r'"([^"]+)"|“([^”]+)”', text)]
    labels = [lbl.strip().rstrip(".:,;…").strip() for lbl in labels]
    on_screen = {lbl for lbl in labels if len(lbl) >= 3 and lbl in screen}

    def blank(match: re.Match[str]) -> str:
        return "▫" * len(match.group(0))

    for label in sorted(on_screen, key=len, reverse=True):
        text = re.sub(re.escape(label), blank, text)
    for term in terms:
        text = re.sub(rf"(?<!\w){re.escape(term)}(?:s|es|ed|d|ing)?(?!\w)",
                      blank, text, flags=re.I)
    return text


def check_topic(topic: dict, avoid: list[str] | None = None,
                screen: frozenset[str] | None = None,
                terms: tuple[str, ...] | None = None) -> list[str]:
    """Every style failure of one topic, as "rule: text"."""
    screen = _screen_literals() if screen is None else screen
    terms = _glossary_terms() if terms is None else terms
    body = topic["body"]
    found = []
    for tag in ("p", "li", "td", "th"):
        for block in blocks(body, tag):
            for sentence in sentences(block):
                if words(sentence) > _MAX_WORDS:
                    found.append(f"sentence over {_MAX_WORDS} words "
                                 f"({words(sentence)}): {sentence!r}")
            if tag == "p" and len(sentences(block)) > _MAX_SENTENCES:
                found.append(f"paragraph over {_MAX_SENTENCES} sentences "
                             f"({len(sentences(block))}): {block[:80]!r}")
    for where, text in (("title", topic["title"]), ("body", _visible(body))):
        text, pairs = strip_axis_names(text)
        if pairs > 1:
            found.append(f"S1 and S2 named {pairs} times (once only, Decision 1)")
        for match in _SPEC_NUMBER.finditer(text):
            found.append(f"spec or decision number in {where}: {match.group(0)!r}")
        clean = allowed_words_masked(body if where == "body" else "",
                                     _ON_SCREEN_CLAIM.sub(" ", text), screen, terms)
        for pattern, name in _NEVER_RE:
            for match in pattern.finditer(clean):
                found.append(f"never-in-Help word ({name}) in {where}: "
                             f"{_around(text, match)!r}")
    for phrase in avoid or []:
            for match in re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
                found.append(f"glossary word to avoid ({phrase}) in {where}: "
                             f"{_around(text, match)!r}")
    for stray in stray_arrows(body):
        found.append(f"'›' outside a menu path: {stray!r}")
    return found


def _around(text: str, match: re.Match[str]) -> str:
    return text[max(0, match.start() - 25):match.end() + 25]


# --- The rules on small samples -----------------------------------------


def _topic(body: str, title: str = "Sample") -> dict:
    return {"id": "sample", "title": title, "body": body}


def test_sentence_and_paragraph_lengths() -> None:
    long = "<p>" + " ".join(["word"] * 31) + ".</p>"
    assert any("over 30 words (31)" in f for f in check_topic(_topic(long)))
    ok = "<p>" + " ".join(["word"] * 30) + ".</p>"
    assert check_topic(_topic(ok)) == []
    # Link text and markup don't count as words.
    linked = ("<p>" + " ".join(["word"] * 28)
              + ' <b>Tools › Drivers</b> <a href="open:x">Open ›</a>.</p>')
    assert check_topic(_topic(linked)) == []
    four = "<p>One. Two is here. Three, e.g. this. Four.</p>"
    assert any("over 3 sentences (4)" in f for f in check_topic(_topic(four)))
    assert check_topic(_topic("<p>One. Two. Three.</p>")) == []
    # A label's "…" and a decimal don't end a sentence.
    assert sentences("Choose Save Diagnostics… and wait 0.5 s. Done.") == [
        "Choose Save Diagnostics… and wait 0.5 s.", "Done."]
    # A bullet is checked for length, not for its sentence count.
    assert check_topic(_topic("<ul><li>A. B. C. D.</li></ul>")) == []


def test_spec_numbers_and_the_slider_names() -> None:
    for bad in ("See S187.", "Decided in Q11.", "Per D-01-TRACE it works.",
                "S1 is a spec number here.", "The S2 box."):
        assert any("spec or decision number" in f
                   for f in check_topic(_topic(f"<p>{bad}</p>"))), bad
    allowed = ("<p>The tick boxes for Slider 1 and Slider 2 read "
               "<b>S1</b> and <b>S2</b>.</p>")
    assert check_topic(_topic(allowed)) == []
    # The pair outside a Slider or tick-box sentence is still caught.
    assert check_topic(_topic("<p>Rows S1 and S2 differ.</p>"))
    twice = allowed + "<p>On a tick box, S1 / S2 again.</p>"
    assert any("2 times" in f for f in check_topic(_topic(twice)))


def test_never_in_help_words() -> None:
    # Loose jargon; the sample screen and glossary hold none of it.
    for bad in ("The wire carries it.", "The action fires.", "It latches.",
                "HidHide's cloak.", "A snapshot.", "The bus is off.",
                "Claim the input.", "Inputs you claimed.", "A container action.",
                "One instance.", "The module file.", "Open profile.json.",
                "Checked on an LG OLED.", "Wires go here."):
        found = check_topic(_topic(f"<p>{bad}</p>"), screen=frozenset(), terms=())
        assert any("never-in-Help" in f for f in found), bad
    # The on-screen phrase and words that only contain the letters pass.
    ok = "<p>The box shows vJoy 1 (not claimed). Install ViGEmBus.</p>"
    assert check_topic(_topic(ok), screen=frozenset(), terms=()) == []


def test_screen_labels_and_glossary_terms_are_allowed() -> None:
    """Decision 5: on-screen labels (bold or quoted) and the glossary's
    approved terms stay; the same words as loose jargon don't."""
    screen = frozenset({"Module File", "Wires", "Wires in these modes",
                        "Autosave: module file deleted",
                        "Module file damaged – inputs blocked"})
    for ok in ("<p>The <b>Module File</b> box.</p>",
               "<p>Untick <b>Wires</b>.</p>",
               '<p>The list "Wires in these modes" shows them.</p>',
               '<p>It is named "Autosave: module file deleted".</p>',
               '<p>The card says "Module file damaged – inputs blocked".</p>'):
        assert check_topic(_topic(ok), screen=screen, terms=()) == [], ok
    # Jargon next to a label is still caught.
    found = check_topic(_topic("<p><b>Wires</b>: the wire fires.</p>"),
                        screen=screen, terms=())
    assert len([f for f in found if "never" in f]) == 2
    # A quoted or bold text that isn't on screen gives no pass.
    assert check_topic(_topic('<p>A "module file" here.</p>'), screen=screen, terms=())
    # Glossary terms, in any form.
    terms = ("module file", "Claim")
    ok = "<p>Each module file claims inputs. A claimed input; claim it.</p>"
    assert check_topic(_topic(ok), screen=frozenset(), terms=terms) == []
    assert check_topic(_topic("<p>A snapshot.</p>"), screen=frozenset(), terms=terms)
    # The real glossary and screen hold the user's examples.
    assert "module file" in [t.casefold() for t in _glossary_terms()]
    for label in ("Module File", "Wires in these modes",
                  "Autosave: module file deleted",
                  "Module file damaged – inputs blocked"):
        assert label in _screen_literals(), label


def test_glossary_words_to_avoid() -> None:
    avoid = _glossary_avoid()
    assert "Auto Mapper" in avoid and "Unmapped" in avoid
    assert "Edit" not in avoid  # an ordinary word and a real menu
    assert "No actions" not in avoid  # a "Use" word
    found = check_topic(_topic("<p>Open the Auto Mapper.</p>"), avoid)
    assert any("Auto Mapper" in f for f in found)


def test_arrow_only_in_menu_paths() -> None:
    ok = ('<p>Choose <b>Tools › Drivers</b> <a href="open:x">Open ›</a>. Later, '
          'Tools › Drivers again. <a href="show:y">Show me ›</a></p>')
    assert check_topic(_topic(ok)) == []
    joined = "<p>Choose <b>Row</b> › <b>Clear Name</b>. Then Row › Clear Name.</p>"
    assert check_topic(_topic(joined)) == []
    for bad in ("<p>Stick › vJoy › game.</p>",
                "<p><b>Tools › Drivers</b>, then Home › Cards.</p>"):
        assert any("outside a menu path" in f for f in check_topic(_topic(bad))), bad


# --- The Help book ------------------------------------------------------


@pytest.fixture(autouse=True)
def _book(qapp: QtCore.QCoreApplication) -> None:
    help_book.load()


def test_every_chapter_file_is_checked() -> None:
    chapters = {c["id"] for c in help_book.load()[0]}
    assert chapters == set(_FILES), "a chapter without its file (or the reverse)"
    assert len(_FILES) >= 10


@pytest.mark.parametrize("chapter", sorted(_FILES), ids=lambda c: _FILES[c])
def test_help_file_keeps_to_the_style_guide(chapter: str) -> None:
    avoid = _glossary_avoid()
    topics = help_book.chapter_topics(chapter)
    assert topics
    failures = [
        f"qml/help/{_FILES[chapter]} [{topic['id']}] {failure}"
        for topic in topics
        for failure in check_topic(topic, avoid)
    ]
    assert failures == [], f"{len(failures)} style failures:\n" + "\n".join(failures)

