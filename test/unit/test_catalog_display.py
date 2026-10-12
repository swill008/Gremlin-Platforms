# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only
# Device-Configuration-Macro Change — Configuration display panel.
# Since D-05-CFG-PAGE (05 S121-S131): the Device Bindings page is
# DeviceBindingsPage.qml on the shared base and its Appearance is the one
# shared list Appearance (ListAppearancePanel.qml, program settings, S125).

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PAGE = _ROOT / "qml/DeviceBindingsPage.qml"
_PANEL = _ROOT / "qml/ListAppearancePanel.qml"
_PART = _ROOT / "qml/PageAppearance.qml"
_MENU = _ROOT / "qml/control_menu.js"
_PANE = _ROOT / "qml/ActionPane.qml"
_TREE = _ROOT / "qml/ControlTree.qml"
_MAIN = _ROOT / "qml/Main.qml"
_MM = _ROOT / "gremlin/ui/module_model.py"


def test_main_has_catalog_display_button() -> None:
    text = _MAIN.read_text(encoding="utf-8")
    # The Output View keeps its own Appearance in Main's header.
    assert "property bool outputViewPanel: true" in text
    assert 'text: outputViewPanel ? "Hide Appearance" : "Appearance…"' in text
    assert "property string lastSaveText" in text
    assert "function onSaveNoted" in text
    assert "showPanel: _root.outputViewPanel" in text
    assert "_root.outputViewPanel = false" in text
    assert "rememberDisplayPanel()" in text
    # The Device Bindings page's button is on its own bar under the toolbar
    # (01 S58a); its open state is the page's, one for every device (S125).
    assert "catalogPanel" not in text
    # The bar and the open state come from the shared PageAppearance part
    # (to-do 91); the page gives its key and button name.
    page = _PAGE.read_text(encoding="utf-8")
    use = page[page.index("PageAppearance {") :]
    use = use[: use.index("}")]
    assert 'buttonName: "deviceBindingsAppearanceButton"' in use
    assert 'pageKey: "device-bindings"' in use
    assert "readonly property Component pageBar: _appear.pageBar" in page
    part = _PART.read_text(encoding="utf-8")
    bar = part[part.index("property Component pageBar") :]
    bar = bar[: bar.index("onClicked")]
    assert "objectName: _part.buttonName" in bar
    assert 'text: _part.displayOpen ? "Hide Appearance" : "Appearance…"' in bar
    assert '_openPlace.setDisplayPanelOpen(pageKey, "page", displayOpen)' in part
    assert 'displayOpen = _openPlace.displayPanelOpen(pageKey, "page")' in part


def test_binding_targets_list_destinations() -> None:
    # The row bindings (05 S142): one box per destination.
    src = (_ROOT / "gremlin/ui/binding_catalog.py").read_text(encoding="utf-8")
    start = src.index("def binding_targets")
    end = src.index("# --- The edit lock")
    ns: dict = {}
    exec(src[start:end], ns)
    boxes = ns["binding_targets"](
        [
            ("map-to-vjoy", "Map to vJoy", "vJoy 3 · Button 9"),
            ("map-to-vjoy", "Map to vJoy", "vJoy 3 · Button 10"),
        ]
    )
    assert boxes == ["vJoy 3 · Button 9", "vJoy 3 · Button 10"]
    qml = _PAGE.read_text(encoding="utf-8")
    py = src + (_ROOT / "gremlin/ui/hardware_layout.py").read_text(encoding="utf-8")
    # The quick editor and its row refresh are gone (05 Q18).
    assert "function openSequence" not in qml
    assert "noteOpenRow" not in qml
    assert "def refreshOpenRow" not in py
    assert "def noteOpenRow" not in py
    assert "def sequences_for_item" in py
    assert "def writeSimpleMap" not in py  # unused, removed in Phase 5
    # A row opens the shared pane (S126).
    assert "function openInput(key, title)" in qml
    assert "function openAction(key, seq, title)" in qml
    main = _MAIN.read_text(encoding="utf-8")
    assert "DialogActionEditor.qml" not in main
    assert "addAction: function() { addAction(_menuKey, _menuTitle) }" in qml
    assert 'M.action("Add Action"' in _MENU.read_text(encoding="utf-8")
    assert "_hold_reload" not in py
    assert "setHoldReload" not in qml
    assert "signal.inputItemChanged.connect(self.reload)" not in py
    assert "def binding_targets" in py
    assert "def action_summary" not in py
    # The shared Appearance panel (S125).
    assert 'title: "Device Bindings — Appearance"' in qml
    text = _PANEL.read_text(encoding="utf-8")
    assert 'text: "Open All"' in text
    assert 'text: "Close All"' in text
    assert 'text: "Save\\nAppearance"' in text
    assert 'text: "Reset\\nAppearance"' in text
    # CF-Q4: no Copy Appearance from another module.
    assert "Copy Appearance" not in text and "Copy Appearance" not in qml
    assert "id: _savedToast" in text
    assert "CloseOnPressOutside" in text
    assert 'title: "Group"' in text
    assert 'text: "Space inside the group"' in text
    assert 'title: "Parent Row"' in text
    assert 'title: "Action Row"' in text
    assert 'title: "Selection"' in text
    output = (_ROOT / "qml/OutputModuleView.qml").read_text(encoding="utf-8")
    assert 'text: "Output View — Appearance"' in output
    assert 'title: "Screen"' in output
    assert 'title: "Pads"' in output
    assert 'title: "Colors"' in output
    assert "onClicked: resetView()" in output
    assert "onClicked: saveView()" in output
    assert 'text: "Save\\nAppearance"' in output
    assert "Save with module" not in output
    assert 'title: "SCREEN"' not in output
    assert 'title: "Text"' in text
    assert 'title: "Shown"' in text
    assert 'text: "Show LED dots"' in text
    assert 'text: "Left"' in text
    assert 'text: "Right"' in text
    assert 'model: ["Same on all sides", "Each side"]' in text
    assert "ColorDialog" in text
    assert "signal closed()" in text


def test_reset_does_not_save() -> None:
    text = _PANEL.read_text(encoding="utf-8")
    chunk = text[text.find("function reset()") : text.find("function requestClose")]
    assert chunk
    assert "setListAppearance" not in chunk
    assert "Options have been reset" in chunk
    assert "applyDisplayDefaults()" in chunk


def test_save_writes_catalog_not_view() -> None:
    # The Appearance is kept in program settings, one per page (CF-Q4, AP2
    # (b)): Save writes this page's there, never into a module file.
    text = _PANEL.read_text(encoding="utf-8")
    save = text[text.find("function save()") : text.find("function reset()")]
    assert "_place.setListAppearance(pageKey," in save
    assert "required property string pageKey" in text
    page = _PAGE.read_text(encoding="utf-8")
    panel = page[page.index("PageAppearance {") :]
    assert 'pageKey: "device-bindings"' in panel[: panel.index("}")]
    assert "saveViewConfig" not in save and "saveCatalogConfig" not in save
    mm = _MM.read_text(encoding="utf-8")
    assert 'doc["catalog"]' not in mm
    assert "_DEFAULT_CATALOG" not in mm
    assert "def catalogConfigJson" not in mm
    assert "def saveCatalogConfig" not in mm
    assert "copyCatalogFrom" not in mm


def test_zero_padding_survives_load() -> None:
    def num_val(v: object, d: float) -> float:
        if v is None or v == "":
            return d
        try:
            n = float(v)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            return d
        return int(n) if n == int(n) else n

    assert num_val(0, 8) == 0
    assert num_val(None, 8) == 8
    text = _PANEL.read_text(encoding="utf-8")
    assert "v.listPad ||" not in text
    assert "numVal(v.listPad, 0)" in text
    assert "numVal(v.parentPadLeft, 24)" in text


def _box(total: int, indent: int, align: str, pct: int) -> tuple[int, int]:
    """ControlTree's row box (boxX, boxWidth): the room after the indent,
    pct of it wide, placed left, centred or right."""
    room = max(0, total - indent)
    width = round(room * max(1, min(100, pct)) / 100)
    spare = room - width
    if align == "center":
        return indent + round(spare / 2), width
    if align == "right":
        return indent + spare, width
    return indent, width


def test_leaf_geometry_left_center_right() -> None:
    # Action rows: alignment and width % (AP3 (b), on the shared tree).
    total = 1000
    assert _box(total, 32, "left", 100) == (32, 968)
    assert _box(total, 32, "left", 50) == (32, 484)
    assert _box(total, 32, "center", 50) == (274, 484)
    assert _box(total, 32, "right", 50) == (516, 484)
    tree = _TREE.read_text(encoding="utf-8")
    assert "function boxX(kind, total)" in tree
    assert "function boxWidth(kind, total)" in tree
    assert 'property string childAlign: "left"' in tree
    assert "property int childWidthPct: 100" in tree
    assert 'var pct = kind === "parent" ? parentWidthPct : childWidthPct' in tree
    panel = _PANEL.read_text(encoding="utf-8")
    assert 'property string childAlign: "left"' in panel
    assert "property int childWidthPct: 100" in panel
    assert '"childAlign": childAlign' in panel
    assert "childAlign = alignVal(v.childAlign)" in panel
    page = _PAGE.read_text(encoding="utf-8")
    assert "childAlign: _appear.childAlign" in page
    assert "childWidthPct: _appear.childWidthPct" in page


def test_parent_geometry_defaults_full_width() -> None:
    # Input rows: full width, on the left, unless set (AP3 (b)); Space
    # between groups above each group after the first.
    total = 1000
    assert _box(total, 16, "left", 100) == (16, 984)
    assert _box(total, 0, "left", 100) == (0, 1000)
    assert _box(total, 0, "center", 80) == (100, 800)
    assert _box(total, 40, "right", 50) == (520, 480)
    tree = _TREE.read_text(encoding="utf-8")
    assert 'property string parentAlign: "left"' in tree
    assert "property int parentWidthPct: 100" in tree
    assert "property int groupSpacing: 0" in tree
    assert 'rowKind === "group" && index > 0) ? Style.dp(_tree.groupSpacing)' in tree
    panel = _PANEL.read_text(encoding="utf-8")
    assert 'property string parentAlign: "left"' in panel
    assert "property int parentWidthPct: 100" in panel
    assert 'text: "Space between groups"' in panel
    assert "groupSpacing = numVal(v.groupSpacing, 0)" in panel
    page = _PAGE.read_text(encoding="utf-8")
    assert "parentAlign: _appear.parentAlign" in page
    assert "parentWidthPct: _appear.parentWidthPct" in page
    assert "groupSpacing: _appear.groupSpacing" in page


def test_actions_open_in_the_shared_pane() -> None:
    qml = _PAGE.read_text(encoding="utf-8")
    assert "function openAction(key, seq, title)" in qml
    assert "addAction: function() { addAction(_menuKey, _menuTitle) }" in qml
    assert 'M.action("Add Action"' in _MENU.read_text(encoding="utf-8")
    assert 'text: "Close pane after OK"' in _PANE.read_text(encoding="utf-8")


def test_photo_lookup_does_not_copy_another_device() -> None:
    root = Path(__file__).resolve().parents[2]
    text = root.joinpath("gremlin/ui/hardware_profile.py").read_text(encoding="utf-8")
    registry = root.joinpath("gremlin/modules/registry.py").read_text(encoding="utf-8")
    # No name-slug lookup that could land on another device's file (03 S130).
    assert "def resolve_module_slug" not in registry
    assert "for folder in _maps_dir().iterdir()" not in text
    # Which folder and pictures a device uses is the module store's
    # (store.device_dir / store.pictures_dir, GL-067); the guard test
    # test_module_store_only keeps callers from building module paths.
    copy = text[text.find("def copyImage") : text.find("# --- a missing picture")]
    assert copy
    # Import Image keeps the picture in the edit (07 S107): nothing is
    # copied into a device folder or written to a module file here.
    assert "self._stage(" in copy
    assert "write_bytes" not in copy and "update_path" not in copy
    photo = text[text.find("def _photo_url") : text.find("def _want_device_photo")]
    assert photo
    # The photo comes from the device's own pictures/ only (07 S11).
    # Old: profilePhotoUrl checked "path.resolve().parent != own.resolve()";
    # the check now lives in _photo_url (D-03-DEVICE-IMAGE precedence).
    assert "found.resolve().parent == own.resolve()" in photo
