# Button Map — Help

This note matches the editor. It is not limited to one stick. File → Save writes the layout to that device’s module file. A successful save says “Saved to the module file.” Moving a chip does not change the action bound to that control.

## Overview

Button Map is a picture of the selected device. Each chip marks one control. **File → Edit Mapping** starts an edit. The live view uses the same layout, and a press still lights the matching chip.

**File → Save** writes this device’s module file. **File → Cancel** drops the edit. Closing with unsaved work asks first.

## File

| Command | Function |
|---|---|
| Edit Mapping | Start the editor |
| Save | Write this device’s module file |
| Cancel | Leave without writing |
| Reset layout | Send every chip back to the pool. Inputs still light |
| Choose background… | Pick a photo under the map |
| Clear image | Restore the picture from the module |
| Exit | Close the window. Unsaved work still asks |

## Edit menu

| Command | Function |
|---|---|
| Undo / Redo | Layout history for this session (Ctrl+Z / Ctrl+Y) |
| Duplicate | Copy the selection, offset so it does not stack (Ctrl+D) |
| Copy / Paste | Clipboard of chips, groups, and frames (Ctrl+C / Ctrl+V) |

## View, zoom, pan

- Scroll wheel zooms about 50%–400%. Middle-button drag pans.
- **View → Reset view** returns 100% and centered.
- A resize or photo reload keeps a valid zoom. It only recenters when zoom or pan is broken.
- **View → Grid → Show grid** — overlay. Saved with the map.
- **Snap to grid** — drag onto grid points. Size 4 / 8 / 16 / 32.
- **Snap to entities** — snap to other chips, hots, frames.
- **Alt** while dragging skips snap.

## Reservoir

The pool lists chips not on the map. Filter by friendly or hardware name. X or Reset clears the filter.

Drag a chip from the pool onto the photo to place it. Resize the pool; the map does not zoom while the pointer is over the pool.

Empty photo right-click is **Draw** only — chips come from the pool.

## Chips

Left-drag moves the chip. The hotspot (dot on the photo) is the hardware contact — drag it separately.

**Right-click → Chip**

| Item | Function |
|---|---|
| Rename | Friendly label. Empty name falls back to the hardware / system name |
| Font size | Label size |
| Size / Round / Square / Filled / Hollow | Chip body |
| Fill… / Outline… / Text… | Idle colors (HSV picker) |
| Pressed fill / outline / text | Live highlight colors |
| Highlight on press | Live fill when the stick is down |
| Reset this cell | Drop member style overrides (Edit group only) |
| Delete chip | Return to the reservoir |

Delete / Backspace on a single chip also returns it to the pool. Yellow ring is selection.

Hotspot (photo input) and Leader End (wire stop) are first-level menus, not under Chip.

## Hotspot

Hotspot is the input on the photo — the control you press — not the chip label.

| Item | Function |
|---|---|
| Size | Dot diameter |
| Round / Square | Dot shape |
| Filled / Hollow | Dot fill |
| Color… | HSV picker for the photo dot only |

## Leader End

Leader End is where the wire stops. It is not the hotspot fill.

| Item | Function |
|---|---|
| Detach chip end | Free the terminus on the pill |
| Detach hotspot end | Free the terminus on the photo |
| Reconnect to this chip | Snap the chip-side end back |
| Reconnect to this hotspot | Snap the photo-side end back |

Leader still owns line color, weight, extra leaders, and curve.

## Groups

Shift-click or rubber-band two or more chips, then **Group → Group selected** (Ctrl+G). Extra leaders drop; one remains.

**Break group** (Ctrl+Shift+G) or Delete on a group splits members back to singles.

**Edit group** unlocks that group only. Other groups stay locked.

- Double-click or right-click a member to target it.
- Drag that member to offset it.
- Chip style writes to that member only.
- Double-click the member again to rename it.
- **Done editing group** or Esc ends the session.
- Double-click empty photo ends edit and clears the selection.

Saved group style profiles are not in yet. Each group keeps its own format and overrides.

## Format and Align

Format and Align are first-level drawers, not inside Group.

**Format → 5-Way** (five-member hat groups only)

| Theme | What it draws |
|---|---|
| Plus cluster | Up / Left / Push / Right / Down cross. Group name once. One leader |
| Mini hat | Compact U/D/L/R/C glyph |
| Named card | Header plus role-only rows |
| Radial leaders | Spokes from the group (can crowd three hats on this grip) |

Picking the theme that is already on **re-applies** it: stock layout, cell offsets and style overrides cleared, names kept.

**Clear Format** sits under Undo/Redo on a group click, and also in Format → Clear Format. It strips the 5-Way theme and every cell override (size, shape, colors, offsets). Names, Align, and the group stay. Enabled when a theme or any cell override exists.

**Align** left / center / right / Free layout — only when the target is a group.

Format is presentation. Hardware ids stay grouped. Save writes the layout to this device’s module file.

## Context menu

The first screen follows the click target.

| Click | First screen |
|---|---|
| Group | Undo, Redo, Clear Format (theme or cell overrides), then Chip / Group / Format / Align / Leader / Draw |
| Leader or spine handle | Undo, Redo, Clear Format if the line belongs to a group, then Add spine, Convert spine, Delete selected spine, Clear spines, then the family drawers |
| Chip / group | Undo, Chip, Hotspot, Leader End, Group, Format, Align, Leader, Draw |
| Empty photo | Undo and Draw |

Gray items are gated: no selection, not a group, not a 5-way, or no spines.

## Leaders

A leader is the line from chip (or group) to the hotspot.

| Gesture | Function |
|---|---|
| Click the line | Select only. Does not add a spine |
| Drag a segment | Plant a **curved** spine at the grab point; the handle follows the drag |
| Click a handle | Select it (orange) |
| Short right-click on a handle | Menu. **Convert spine** flips curved ↔ straight (no check mark). **Delete selected spine** removes that handle |
| Hold right-click ~½ s on a handle | Delete that handle. No menu |

**First menu on a line or handle:** Add spine, Convert spine, Delete selected spine, Clear spines. Convert and Delete need a selected handle. Convert is a plain action — no check mark.

**Leader submenu:** Color…, Weight 0.8–4.0, Add straight / curved spine, This segment or All segments Curved / Straight, Add leader, Branch from this end, Attach (detach / reconnect chip or hotspot ends), Clear all spines, Delete spine, Delete leader.

Spines show only while Edit Mapping is on. The chip-to-hotspot line stays in the live map.

## Draw

**Right-click → Draw.**

- **Around selection** — rectangle, rounded, ellipse, triangle, or diamond around selected chips; it moves with them.
- **Free drag** — pick a shape, drag on empty photo. Shift locks aspect. Esc or Cancel tool drops the tool. Yellow **Drawing** in the toolbar means a tool is armed.
- Corner handles resize. Detach from chips turns an around-frame into a free frame.
- Shape, Padding, Rotate (0/90/180/270, ±15), Filled / Hollow, Fill color…, Stroke color…, Stroke width, Opacity.
- Bring forward / Send back. Hollow frames click through to chips inside.

## Select and move

Click selects. Shift-click or Ctrl-click toggles. Drag empty glass to rubber-band.

Arrows nudge 1 px. Shift+arrows nudge by the grid size.

## Keyboard

| Key | Function |
|---|---|
| Ctrl+S | Save |
| Ctrl+Z | Undo |
| Ctrl+Y or Ctrl+Shift+Z | Redo |
| Ctrl+D | Duplicate |
| Ctrl+C / Ctrl+V | Copy / Paste |
| Ctrl+G | Group |
| Ctrl+Shift+G | Break group |
| Delete / Backspace | Chip to pool, break group, or delete selected spine |
| Arrows | Nudge 1 px |
| Shift+Arrows | Grid nudge |
| Esc | Cancel draw tool / end group edit / cancel rename |
| F1 | This help |
| Alt while dragging | Skip snap |
| Shift while drawing | Lock aspect |

## Save and live map

Save writes the layout to this device’s module file. That includes the chips, the photo, and the grid settings.

The live view still lights the control that is pressed. Chip names and colors are layout only. They do not change the actions in the profile.
