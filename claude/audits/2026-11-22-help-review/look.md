# Help review: how it looks (agent LOOK, 2026-11-22)

Read-only review of how the in-program Help looks and scans on screen (not
its wording). Pictures were taken off-screen (Qt offscreen platform, 1600 x 1000
screen, 100% UI scale, dark theme, stand-in hardware, temp user folder) with
the Help window at its default 980 x 680 size unless noted. No program file
was changed.

Pictures (in `pictures/`):

| File | Shows |
|---|---|
| 01-getting-started-first-setup.png | Numbered steps, "Good to know", Related topics |
| 02-getting-started-main-window.png | Long bullets full of inline "Show me ›" links |
| 03-tools-drivers.png | A long topic (about 4 screens), h4 subheadings |
| 07-tools-drivers-scrolled.png | The same topic further down: long bullets |
| 04-osc-patterns-table.png | A table and code text |
| 05-options.png | Steps and bullets with many bold words; contents list cut short |
| 06-main-window-wide-1560.png | Help window at 1560 x 960: very long lines |
| 08-search-vjoy.png | Search: match highlights and per-topic counts |

Measured: the reading column is 612 px wide at the default size (about 88 to
92 characters per line at 14 px Segoe UI) and 1192 px when the window is
widened (about 190 to 200 characters per line). Contrast in the dark theme:
body text `fg` #E4E4E7 on `bgPage` #111113 is 14.9:1 (good); links and
section labels use the accent #3E65FF (sampled from the picture), 4.05:1 on
`bgPage`, which is under the 4.5:1 that normal-size text needs.

## Top 5 problems

1. **No limit on reading width.** Lines run to about 90 characters at the
   default size and about 200 when the window is widened or maximised (picture
   06). Comfortable reading is 60 to 75 characters.
2. **Subheadings don't look like headings.** Topic subheadings are `<h4>`
   (168 of them), which Qt draws bold at body size, so "What each row says"
   looks the same as the bold UI names in the text around it (pictures 03, 07).
   The style block in DialogHelp.qml styles `h3`, which no page uses.
3. **Link blue is too dark on the dark page.** #3E65FF on #111113 is 4.05:1,
   used for every link, every "Open ›"/"Show me ›" and the 11 px section labels
   in the contents list (pictures 01, 05).
4. **Dense text: no space between list items, default line height, heavy
   bold.** Long bullets (Drivers, The main window, Options) run together into
   a wall; 3,095 `<b>` across the book means some paragraphs have six or more
   bold runs in three lines, so nothing stands out (pictures 02, 05, 07).
5. **No sign that a topic goes on, and long topics have no map.** The
   vertical scroll bar only appears while scrolling (Universal style,
   `AsNeeded`), so a topic cut at the bottom (picture 02: Related topics cut
   through the middle of a line) gives no cue. The Drivers topic is about
   1,950 px tall (4 screens) with 4 subheadings and no way to jump to one.

## Findings

| # | Where | Problem | Suggested change | Severity | Picture |
|---|---|---|---|---|---|
| 1 | qml/DialogHelp.qml:836-844 (`_bodyColumn`, `_body`) | Reading width follows the window: ~90 characters by default, ~200 when wide. | Give `_body` (and the Related block) `Layout.maximumWidth: Style.dp(640)` so a line is at most about 75 to 80 characters at 15 px; leave the rest of the panel empty (or centre the column). | high | 06, 02 |
| 2 | qml/DialogHelp.qml:391-392 (the `css` string in `_shown`) | The rule styles `h3 { margin-top: 14px }`, but every page uses `<h4>` (168 uses, 0 `<h3>`); `h4` renders bold at body size with Qt's default margins, so subheadings blend with bold body words. | Replace with `h4 { font-size: <1.2 x body>px; margin-top: 18px; margin-bottom: 6px; color: <Style.fgStrong>; }` built from `Style.dp()`; remove the unused `h3` rule. | high | 03, 07 |
| 3 | qml/Style.qml:13 (`accent` = Universal.accent) used by DialogHelp.qml:391 (link CSS), :696 (section labels), :898 (Related links) | Accent #3E65FF is 4.05:1 on `bgPage` #111113: under 4.5:1 for 14 px text; worse for 11 px section labels. | Add a dark-theme link colour token in Style.qml (for example `link: "#7C9BFF"`, 7.2:1, or `#8AA6FF`, 8.1:1; light theme keeps its own) and use it for the `a {}` colour, section labels and Related links; keep `accent` for the selected-row fill. | high | 01, 05 |
| 4 | qml/DialogHelp.qml:391 (css) | List items have no space between them and lines use Qt's default leading, so long bullets merge (Drivers has bullets of 5 to 9 lines). | Add `li { margin-bottom: 6px; }` and `p, li { line-height: 135%; }` to the style block (Qt rich text accepts `line-height` as a percentage on block elements; check it renders, else set it per element in the decorate pass). | high | 07, 02, 05 |
| 5 | qml/help/*.js (3,095 `<b>`), e.g. tools.js Drivers topic, options_profile.js "Options" | Bold marks every UI name, every value and the run-in labels, so a paragraph has 6+ bold runs (picture 07: "Repair Now or Repair Later: Repair Now ... Repair Later ... lost in the vJoy update ... Repair"). Headings and the one key term stop standing out. | Content rule for the wording agents: bold a UI name only on its first mention in a topic, and only the run-in label of a bullet ("General:"); values and repeats stay plain. Optional style: render `<b>` as weight 600 in `fgStrong` rather than full bold. | medium | 07, 05 |
| 6 | qml/DialogHelp.qml:834 (`ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }`) | In the Universal style the bar is hidden until scrolled, so a topic that continues below shows no cue (picture 02 cuts Related topics mid-line). Same for the contents list at :604. | `policy: ScrollBar.AlwaysOn` when `_bodyFlick.contentHeight > _bodyFlick.height` (and the same for `_list`), or a 24 dp fade from `bgPage` at the bottom edge of the body panel. | medium | 02, 03 |
| 7 | qml/help/tools.js `tools-drivers` (and other long topics with 3+ `<h4>`) | ~1,950 px tall (4 screens at default size) with 4 subheadings and no way to jump to one. | Have DialogHelp build a short "On this page" line of links from the topic's `<h4>` texts when there are 3 or more (one shared owner, no page edits), or split the topic. | medium | 03, 07 |
| 8 | qml/help/*.js inline `Show me ›` / `Open ›` (173 across the book); qml/DialogHelp.qml:393 (`_shown`) | The two-word link breaks across lines ("Show / me ›", "Input Tester Show / me ›") and, nine to a bullet, turns The main window's Toolbar bullet into a blue-and-white patchwork. | In `_shown`, replace the link text's spaces with `&nbsp;` (one shared pass, not per page). Content suggestion: turn the Toolbar bullet into a two-column table (Button / What it does) with one "Show me ›" per row. | medium | 02, 06 |
| 9 | qml/DialogHelp.qml:792 (`topicPlace`) | Breadcrumb repeats itself when the section has the chapter's name: "Getting started › Getting started", "OSC › OSC". | Show only the chapter when `section === chapter`. | low | 01, 02, 06 |
| 10 | qml/help/osc.js:35-47 (`_table`), device_bindings_actions.js:287, :302, :313, tools.js:584 | Tables stretch over the whole column with no rule under the header and 3 px padding; the Example column is pushed to the far right, far from its row (picture 04). Each table builds its own markup; tools.js:584 has no `align`/padding at all. | One shared table look in the style block: `table { margin-top: 8px; margin-bottom: 8px; } th { background-color: <bgRaised>; } td, th { padding: 4px 10px; }` plus `cellspacing="0"` and `border-bottom` on `th`; give tables a natural width (no full width). Pages keep plain `<table>`. | medium | 04 |
| 11 | qml/DialogHelp.qml:391 (css), qml/help/*.js `<code>` (147) | `<code>` falls back to Qt's default fixed font, which drew as a narrow, hard-to-read face in the pictures ("/deck/*", "/{fire,jump}"); it may differ on a real screen. | `code { font-family: "<Style.monoFont>"; }` (Consolas) in the style block, and a faint background (`bgRaised`). | low (check on a real screen) | 04 |
| 12 | qml/DialogHelp.qml:853 (`font.pixelSize: Style.dp(14)`), :727 (topic rows 13), :697 (section labels 11) | Help body text is 14 px while the program's own text is 15 px (`Style.fontSize`, Style.qml:205); contents rows are 13 and section labels 11. | Body `Style.fontSize` (15); topic rows 14; section labels 12. Title 22 and chapter band 16 can stay (title is then about 1.45 x body, h4 at 1.2 x). | medium | 01 |
| 13 | qml/DialogHelp.qml:721-728 (topic label `elide: Text.ElideRight`), :90 (default list width 290 dp) | Long topic titles are cut: "How do I get back an earlier version of a...", "Why is there a red frame around every w...", "Why does my screen never turn off or st..." (Common questions read worst cut). | Let topic rows wrap (`wrapMode: Text.WordWrap`, no elide, row height from the label) or show the full title as a tooltip on hover; or default the list to 320 dp. | medium | 05, 08 |
| 14 | qml/DialogHelp.qml:839 (`_bodyColumn` spacing 10), :896-899 (Related links) | Related topics links sit 10 dp apart while body list items have 0, so the Related block looks looser than the text above it; it also starts with only a hairline and a bold label. | Related links 4 dp apart (a nested `ColumnLayout { spacing: Style.dp(4) }`) and render them as bullet-like rows; keep the 1 px line. | low | 01, 06 |
| 15 | qml/help/*.js "Good to know" (`<h4>Good to know</h4>` followed by a one-item `<ul>`) | Many topics end with a heading for a single bullet; with h4 at body size it reads as a stray bold line, and at a page break it is left alone at the bottom (picture 04). | Content suggestion: when there is one item, fold it into the text; keep the heading for 2+ items. Finding 2's h4 style also fixes how it looks. | low | 01, 04 |

## What works

- Contrast of body text in the dark theme is very good (14.9:1).
- The topic title (22 px bold) and the breadcrumb above it make the place clear.
- Chapter bands (accent bar, 16 px bold) and the uppercase section labels give
  the contents list a clear three-level shape; folding keeps it short.
- Search shows a count per topic in the list and "k of n" with previous/next;
  the current match is a stronger orange than the other matches (picture 08).
- Numbered steps use `<ol>` and the indent of lists is right.
