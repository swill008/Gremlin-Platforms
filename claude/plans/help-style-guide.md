# Help style guide and page template (APPROVED 2026-11-22, user: 1a)

From the Help review (claude/audits/2026-11-22-help-review/). User chose
method 1a (2026-11-22): style guide -> template -> one sample page -> the
other pages -> automatic check -> fresh-reader testing.

## 1. Voice

- Talk to the reader as **you**. Present tense, active voice: "Click Apply.
  Windows asks for permission once." Not "Permission is requested."
- A friendly expert sitting next to the reader: plain words, no showing off,
  no jokes.
- US English (color, behavior), as the glossary says.

## 2. Length

- Sentences: aim for under 20 words; never over 30.
- Paragraphs: at most 3 sentences.
- Bullets: one idea each, under 25 words. More detail goes in a nested
  bullet, not a longer sentence.
- A topic that needs more than about 15 bullets becomes two topics.

## 3. Words

- Screen names exactly as on screen (glossary), in **bold** the first time in
  a topic only. Menus: **Tools › Drivers**. The "›" sign only for menu paths.
- Never in Help: spec or decision numbers (S187, D-01-...), code or file
  names (unless the reader needs them, e.g. the logs folder), internal words
  (wire, fires, latches, cloak, snapshot, bus, claim, container action,
  instance, module file, .json), test notes ("checked on an LG OLED").
- A technical word the reader can't avoid is explained once, in plain words,
  where it first appears: "vJoy (a virtual joystick driver games can read)".
- Every choice in a list says what it does, not only its name.
- No full dialog texts quoted: name the box and its choices ("A box asks
  whether to stop Run first: **Yes** or **No**.").
- No version numbers in examples unless the version matters.

## 4. Facts

- Describe what the reader sees and does, never how the code does it.
- A rule is explained once; other places link to it ("See **Run and Stop**").
- When unsure whether Help matches the program: check the spec (program map)
  and the program; the Help follows the screen.

## 4a. Links (user 2026-11-22: "within reason ... not too many that it's difficult to read")

- A window, menu item, button or option that exists in the program gets a
  **Show me ›** or **Open ›** link the first time it is named in a topic,
  not every time.
- At most one link per sentence or step.
- A list where every item would get a link (e.g. the toolbar buttons) gets
  none per item; one link after the list instead, or a table.
- The installer (setup) has no links of its own; point to the same control
  in the program (e.g. **Tools › Drivers** Open ›).

## 5. Page template (every topic)

1. **Heading**: the task or the thing, e.g. "Set up vJoy devices".
2. **What it's for**: one or two sentences.
3. **How to**: numbered steps for the common tasks (one action per step).
4. **What you see**: the controls, as a short list or a two-column table
   (control | what it does).
5. **Good to know**: exceptions, limits and tips, as short bullets.

Sections 3-5 are left out when empty. Links ("Open ›", "Show me ›") go at the
end of the step or bullet they belong to.

## 6. Look (from look.md)

- Reading width: `_body` maximum width 650 dp in qml/DialogHelp.qml (user
  2026-11-22: "maybe 650"; about 85 characters at 15 px).
- Subheadings (`<h4>`, used 168 times) styled 1.2 x body size with space
  above and below; the unused `h3` rule removed.
- Fewer bold words, so headings stand out (3,095 `<b>` today).
- Space between list items.
- Dark-theme link colour with enough contrast (e.g. #7C9BFF).
- Body text the program's size (15 px, not 14).
- Tables styled (header row, cell padding); the scroll bar visible when a
  page continues; "Show me ›" kept on one line; the place line not repeating
  the title.

## 7. Automatic check (step 4, a guard test)

Fails when Help has: a sentence over 30 words; a paragraph over 3 sentences;
a spec or decision number; a word on the "never in Help" list or a glossary
"words to avoid" entry; "›" outside a menu path.

## Decisions (user 2026-11-22)

1. Axis names in Help: the long names **Slider 1** and **Slider 2**; where
   the tick boxes are described, mention once that they read S1 and S2 (2a).
2. Topics about older profiles are removed (3a; the program is unreleased).
3. Glossary rows that differ from the screen: Help follows the screen; the
   glossary row is corrected in the same batch and reported.
4. 1.1.1 is released after the Help rewrite.
5. Screen labels and glossary terms are always allowed in Help (user
   2026-11-22: "approved", 1a). The "never in Help" list (section 3) bans
   those words only as loose internal jargon: e.g. **Module File** (a box on
   screen), "(not claimed)", **Wires**, "Autosave: module file deleted" and
   the glossary term "module file" stay.
