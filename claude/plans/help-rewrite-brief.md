# Help rewrite: shared brief for the page writers (2026-11-22)

Approved: claude/plans/help-style-guide.md (follow it exactly, incl. 4a links
and the Decisions). Model page: qml/help/getting_started.js (rewritten
07:05-07:12 and approved by the user). Findings with rewrites per file:
claude/audits/2026-11-22-help-review/h1.md ... h7.md (check any rewrite marked
"needs checking" against claude/program-map/ before using it; the spec decides
facts; Help follows the screen).

Each writer owns only its file(s). Keep the file's data structure and every
topic/anchor id other files link to (grep qml/help/*.js, qml/help_links.js,
qml/*.qml and test/ for the ids); new topics get new ids. Use only markup
qml/DialogHelp.qml renders (h4, b, i, ul/ol/li, table, code, a href with
topic:/show:/open:). Remove older-profile topics (Decision 2). Glossary
mismatches: don't edit claude/glossary.md; list them in your report.

Tests: run test/unit/test_help_guide.py, test_help_links.py,
test_help_links_resolve.py, test_help_search.py, test_help_topics_script.py,
test_glossary_words.py and any test that greps your file's text (grep test/
for a distinctive phrase or your topic ids), with a temp USERPROFILE and the
Poetry venv Python directly. Agent CHECK is adding the automatic style check
(test/unit/test_help_style.py) now; run it when it exists and fix your text
until it passes. Don't weaken tests; report a test that blocks the guide.
