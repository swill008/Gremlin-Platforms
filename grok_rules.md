# grok_rules — JoystickGremlin_ (swill008)

Read this file **first** on every new chat about this project. Do not re-ask settled decisions. Do not reopen parked topics unless the user names them.

Repo: `swill008/JoystickGremlin_`
Run: `poetry run python joystick_gremlin.py`
GitHub: all pushes use the user's PAT. Skip size checks. Never commit secrets/PAT.

Core QML: `qml/VkbRigEditor.qml`, `qml/VkbRigFace.qml`, `qml/DialogJoystickButtonMap.qml`

---

## 1. Handoffs

When the user opens a new chat or asks for a handoff:

1. Entire handoff in **one** markdown `text` code fence (copy/paste). Never prose-only.
2. Include: repo, files, current task, settled decisions, parked topics, next action, picture rules.
3. After writing the fence, stop. Wait for them to paste it elsewhere or say GO.

---

## 2. Pictures

This Grok **Build / coding-agent** UI often does **not** show Imagine output. Generation can succeed on disk while the user sees nothing. `render_file` / grok XML showed **raw tags**.

1. Generate **one** image at a time with `imagine_text_to_image`.
2. Ask: **saw it** / **blank**.
3. If blank: one `search_images` + `render_searched_image` test.
4. If still blank: **stop generating**. Implement in the live Gremlin editor.
5. **Never** use `render_file` for pictures.
6. Do not invent a VKB / controller photo. User's live shot is the only hardware reference.

---

## 3. Button-map editor — settled behavior (do not regress)

**Truth**
- Save writes a **control.hardware** profile and **is** the live-map source of truth.
- Cancel / close with unsaved edits: warn. If already saved, no warn.
- File menu: Edit Mapping, Save, Cancel, **Exit**. No standalone Edit button.

**Viewport**
- Wheel zoom, smooth, about −50% to +500%.
- Pan: existing pan (middle / whatever is current). **Auto-pan / edge-scroll: removed. Do not bring it back.**
- Grid: on/off/size under **View → Grid**. Snap to grid and to entities.
- Child windows stay up if the main Gremlin window is minimized.

**Chips**
- Full hardware name in the system; **friendly name** shown.
- Filter reservoir by friendly **and** hardware name. Filter box has X + Reset.
- Reservoir: floating pool in the bottom area, resizable, no zoom/click-through when pointer is over it. Drag chips out onto the map. Not a menu.
- Reset map: chips return to reservoir. **Does not** break live illumination when the stick is pressed.
- Chip look: size, shape (round/square), hollow/filled, color, highlight color. Same rules for hotspots.
- Selection ring: **same 4px yellow ring on the chip itself for every chip**, including group members. No wrap box. No special-case chip.
- No pre-applied centering, min-width, or padding. **Align left/center/right is menu-only.** Default align is **left**.
- Delete Chip: works on a **single** chip (returns it to reservoir). **Greyed out on a group.** Delete key uses the **same** path as the context item (delete chip or break group).

**Groups**
- Group / ungroup freely. Context: Group, Break group.
- Single is **above** Group in the context menu.
- After ungroup, **clear selection** so members are immediately independently draggable (no extra click-off).
- Grouping 2+ chips: collapse to **one** leader (remove extras).
- While grouped, right-click **Edit group** to move members inside the group.
- 5-ways are a **group**. Do not split them by default. Do **not** hard-code a special 5-way stack layout in render (that exploded stacks). Treat members like any grouped chips; layout is plus/card via group layout, not a hidden kind.

**Leaders**
- Free-form: add/edit/delete/move, spine points, mix curved + straight in one leader.
- Detach/reattach to any entity. Multiple leaders to one element; branch from an orphan.
- Context: Delete spline **above** Delete leader.
- Horizontal leaders closer to grips when laying out.

**Draw**
- Context root submenu **Draw**: boxes, circles, triangles, diamonds, ellipses, free-drag, snap to entities, rotation, fill, color, transparency, z-order.

**Menus**
- One primary right-click menu for all cases (empty / chip / group / leader). Nested: Single, Group, Draw, Delete.
- Context menu is **draggable from any non-control area** (not only a corner). Remember size. Options: context menu size in px. Resize handles. Flickable must not steal drag (interactive false + wheel).
- Main MenuBar always visible on the mapper: **File, Edit, View, Help**. Flattened: Options / Session / Group etc. sit under Menu, not a third layer. Grid under View.
- Help: editor instructions.

**Undo**
- Snapshot history. Undo = **last action only**, not the whole session. Context: Undo. Guard with `_restoring` so restore does not re-record.

**QML landmines already hit**
- Do not name a signal the same as a property-change signal (`histChanged` → `historyChanged`).
- Do not assign `implicitHeight` on items where it is read-only.
- Do not call functions on the editor from Face during load if they are not functions (`bump`).
- Avoid Binding-target overwrite; don't overwrite bound properties from elsewhere.

---

## 4. Current task — 5-way presentation (2026-09-18)

Problem: five stacked chips repeating the long device name.

| ID | Layout | Notes |
|----|--------|--------|
| **A** | Plus cluster | Short roles in a cross: Up / Left / Push / Right / Down. Group title once. One leader. **Recommended default.** |
| B | Mini hat widget | U/D/L/R/C glyph. New control type. Later. |
| C | Named card | Header `HEAD 5-WAY`, members = role only. Fastest. |
| D | Radial leaders | Skip as default (three hats collide). |

Next: generate **A** once. If the user cannot see the picture, **implement A in the editor**.

Prompt for A: dark HUD, VKB EVO head, red button + 5-way hat, plus cluster of 5 navy pills (Up/Left/Push/Right/Down), caption Head 5-way, one white leader to a blue hotspot on the hat. 16:9.

---

## 5. Parked — Windows volume knob (do not start unless asked)

Device does **not** appear in `joy.cpl`. It is HID Consumer Control (page 0x0C), not DirectInput. GremlinEx will not import it as a joystick. GremlinEx hid.py only keeps Usage 4/5 on page 1.

Paths if resumed:
- Keyboard listen of Volume Up/Down/Mute: leaky, OS volume still moves, not unique to this device.
- hidapi by VID/PID (Octavi IFR1 pattern in GremlinEx) → vJoy pulses. Hide OS with HidHide if listed, else Interception for that hardware ID, else Zadig WinUSB.
- Hardware HID Remapper (Pi Pico): cleanest hide.

Need VID/PID before coding. Encoder ticks are relative, not an analog axis.

---

## 6. Working style

- User said GO / stop asking during a phase: implement, don't quiz.
- Product photos when hardware is discussed (if pictures work).
- Prefer editing existing QML over new files.
- After a batch of editor changes, push with PAT.
