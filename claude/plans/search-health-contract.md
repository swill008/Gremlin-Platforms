# Contract: Search layout, Health, Turn displays off now (2026-11-22)

User: "build it all now" (1.1.1). Spec: 01 S196 (Search layout), 01 S197
(Health), 12 S40 (Turn displays off now). Drawings agreed in the chat
(Search alone; Health in Search's layout with the Why panel).

## 1. Health core (owner: HCORE: new `gremlin/health.py`, `gremlin/search_index.py`, tests)
- `search_index.SearchRow` loses `not_found`, `why`, `used_twice`, `plugged`;
  `mark_used_twice` and the plugged lookup leave the index.
- `gremlin/health.py`:
  ```python
  CHECKS = ("notFound", "usedTwice", "noBindings", "notPlugged")   # order shown
  LABELS = {"notFound": "Binding output not found", "usedTwice": "Used twice",
            "noBindings": "No bindings", "notPlugged": "Not plugged in"}
  @dataclass(frozen=True) class Finding: check: str; why: str; fix: str
  def results(rows=None) -> dict[row_key, tuple[Finding, ...]]  # one copy, cached per index version
  def findings(row) -> tuple[Finding, ...]
  def counts(scope_rows) -> dict[str, int]
  def broken_count() -> int           # notFound in the open profile (toolbar)
  changed: a Qt signal or callback list (results recomputed when the index changes)
  ```
  notFound/why come from gremlin/references.py (its owner); usedTwice = the
  rule moved from the index; notPlugged = the device list (library rows never);
  noBindings = no action. `fix` = the Why panel's "what you can do" text per check.
  `row_key` = a stable key of a SearchRow (pick one; report it).

## 2. Search model (owner: SMODEL: `gremlin/ui/search_model.py` + its tests)
- Remove HEALTH_FILTERS, health counts and tags; nothing in Search reads health.
- Recent searches for the drop-down (existing recent list + clearRecent).
- Expose what the QML needs for the drop-down (recent when box empty, suggestions while typing).

## 3. Search window (owner: SQML: `qml/DialogSearch.qml`, `qml/search/*.qml`, window tests)
- S196: Listen first (left of the box); suggestion tick under the bar; recent
  searches in the drop-down with Clear; welcome panel only when nothing typed
  and no results; fixed Input/Mode widths (Layout.minimumWidth = preferred);
  action text cut in the middle; Details title at top; sidebar names wrap; no
  health UI.
- The result row component gets a property `showStatus` (default false): when
  true it shows the ⚠ in the action and the "Not plugged in" chip from
  properties the caller passes (`notFound`, `why`, `notPlugged`). Health uses it.

## 4. Health window (owner: HUI: new `gremlin/ui/health_model.py`, new `qml/DialogHealth.qml`, tests)
- S197 layout as drawn: sidebar (Look in: All profiles / This profile only;
  the four checks with counts from health.counts), grouped list using
  qml/search/SearchResultRow.qml with showStatus true, hover reason, Why panel
  (reason + fix text, links), right-click menu (Open, Change target…, Remove
  binding…, Copy as text) through gremlin/binding_edit.py, multi-select
  (Ctrl/Shift), one Undo for a group change (list of binding_edit Undo records).
- Register the window as a command `tools.health` (find how `tools.search` is
  registered) so the toolbar and menus can open it.

## 5. Toolbar (owner: TBAR: `qml/Main.qml` toolbar part only, the toolbar's model if any, tests)
- A **Health** button after Search: heartbeat icon (Style colours: red with the
  count from health.broken_count when > 0, gray and no number at 0), opens
  `tools.health`; tooltip "N binding outputs not found in this profile" / "No
  problems found".

## 6. Turn displays off now (owner: SSM: `gremlin/screen_saver_mode.py`, `test/unit/test_ssm_core.py`)
- S40: until displays off and 2 s after, mouse movement and program input
  don't cancel or wake; key press, click, wheel do (use InputClock.last_press).

## 7. Tests (owner: E2E: new end-to-end test files)
- Health real path (unplugged device to missing vJoy: count 1 on toolbar, row
  in Health with Why, fix via Change target, count 0); Search shows no health.

## 8. Docs (owner: DOCS: Help, glossary, map, release notes, to-do)
