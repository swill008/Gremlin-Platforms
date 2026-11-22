# Fresh reader FR5 (2026-11-22)

Help only (qml/help/*.js). Tasks: hide the real stick from a game; check it with
the Input Tester; turn on Screen Saver Mode and try it with Test now.

## Task 1: hide the real stick from the game

Could do it: **with guesses**

Steps (from tools-hidhide, reached via getting-started "A game sees both the stick and vJoy" and tools-q-game-sees-both):
1. Tools › Device Setup › HidHide (Open ›).
2. Turn on Gremlin-Platforms controls HidHide.
3. Turn on HidHide Enabled.
4. Tick the stick (it dims, marked HIDDEN).
5. Choose Allow list or Block list; add the game with Add Program (guess: Block list, see problem 1).
6. Test HidHide (Windows Game Controllers panel): the stick should be missing.
7. Start the game afterwards (tools-hidhide-timing).

Problems:
1. **Two topics disagree on the list (blocker).** tools.js `tools-hidhide` step 5: "Choose Allow list or Block list, and add your game with Add Program." But `tools-q-game-sees-both`: "With Allow list, the game must not be on it". Allow list + adding the game, as the how-to says, lets the game see the stick. Fix: in the how-to, say which to pick and what to add for each: "Block list: add your game. Allow list: leave the game off; only programs that must see the stick go on it (this program always sees it)." Recommend one as the default.
2. **Guess: which list to pick.** `tools-hidhide` defines both lists, but never recommends one for the normal case "hide my stick from my game". Fix: one sentence recommending a choice, with the reason.
3. **Test HidHide only covers Allow list.** `tools-hidhide` step 6: "With Allow list, a hidden device should be missing there." With Block list, what should I see? Fix: add "With Block list, the panel still shows it (the panel isn't on the list); use the Input Tester instead."
4. Slow to read: the how-to is fine, but the warning that matters most (start the game after the change) is in a separate topic. A one-line warning is in step 7. OK.

## Task 2: check it worked, with the Input Tester

Could do it: **with guesses**

Steps (tools-input-tester):
1. HidHide page, with Gremlin-Platforms controls HidHide on.
2. Add Input Tester to the list.
3. Choose Input Tester (page or toolbar).
4. Read the top line: Pass or Problem. Rows: the stick should read "Hidden from programs".
5. If HidHide changed after the tester started, choose Restart tester.

Problems:
5. **Same Allow/Block conflict again.** `tools-input-tester`: "Put it on HidHide's list like your game". With Allow list, the game must not be on the list (problem 1), and a listed tester would see the hidden stick. Fix: "Add Input Tester to the list puts it where your game is: on a Block list, or left off an Allow list" (whatever the button really does), and say the button handles both.
6. **Button missing from the page topic.** `tools-hidhide` "What you see" lists Input Tester and Last Status, but not Add Input Tester to the list, nor Update path. I have to read the tester topic to learn the page has it. Fix: add both to the page's "What you see".
7. **Two names for one button.** `tools-hidhide-timing`: "The page offers Restart Input Tester." `tools-input-tester`: "Choose Restart tester". Are they the same button in two places? Fix: use one name, or say where each is.
8. Guess: `tools-input-tester` "Opened on its own, the tester shows what it sees without a Pass or Problem." and getting-started says it has no Start menu entry. Fine, but the Tools › Viewers menu path (getting-started, tools menu) is a third way to open it that the tester topic doesn't mention. Minor: list all three ways once.
9. Rows topic is clear (the verdict table is good). `tools-input-tester-rows` red-row fix "Tick it on the HidHide page, then choose Restart tester." works.

## Task 3: turn on Screen Saver Mode and try it with Test now

Could do it: **with guesses**

Steps:
1. Tools › Screen Saver Mode… (Open ›), turn on Screen Saver Mode (`tools-screen-saver-mode`).
2. Wake PC tab: press a key and click the mouse so they tick (`tools-screen-saver-wake-pc`).
3. Press Test now (found only in `tools-screen-saver-awake`); wait out the 5-second countdown (Cancel test (N) stops it).
4. Press a key or move the mouse to come back.

Problems:
10. **Test now is buried in the wrong topic.** The main topic `tools-screen-saver-mode` never mentions it; it is step 3 of `tools-screen-saver-awake` ("Find what keeps the PC awake"), a title I would not open to try the feature. Fix: add a last how-to step to `tools-screen-saver-mode`: "To try it now, press Test now (5-second countdown)."
11. **Guess: what Test now does.** `tools-screen-saver-awake`: "runs the real sequence after a 5-second countdown". Which sequence: the screen saver, then displays off? Does it switch off the devices marked Switch off? Does it honour the waits or skip them? How do I end it? Fix: one line: what happens in order, and "press a key or move the mouse to end it".
12. **Guess: does Test now need setup first?** `tools-screen-saver-wake-pc`: "With nothing ticked, neither timer runs." This is in a sub-topic; step 3 of the main topic doesn't say it is required. Does Test now also need a ticked device, and does it work with the mode switched off? Fix: in the main how-to, step 3: "Tick at least one, or nothing runs"; under Test now say whether it needs the mode on and a ticked device.
13. Guess: which tab holds Test now (Settings? a status area?). `tools-screen-saver-awake` says only "Open Tools › Screen Saver Mode…". Fix: name the tab or area.
14. Slow to read: `tools-screen-saver-mode` "Good to know" has 13 items; the one I needed (Test now) isn't among them.

## Top 3 problems

1. Allow list vs game on the list: `tools-hidhide` step 5 ("add your game with Add Program" under either list) contradicts `tools-q-game-sees-both` ("With Allow list, the game must not be on it"); `tools-input-tester` repeats it ("Put it on HidHide's list like your game"). Following the how-to with Allow list leaves the stick visible.
2. Test now is only in `tools-screen-saver-awake`, not in the main Screen Saver Mode topic, and what it does ("the real sequence") and how to end it are not explained.
3. The HidHide page topic doesn't list Add Input Tester to the list or Update path, and the restart button has two names (Restart Input Tester / Restart tester).
