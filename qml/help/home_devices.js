// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Home and devices (cards, modules, Device Pack, deleted devices).

.pragma library

var chapter = { id: "home-devices", title: "Home and devices" }

function topics() {
    return [
        {
            id: "home-devices-home",
            section: "Home",
            title: "Home and its cards",
            body: "<p>Home shows one card per device: your physical devices, the <b>Keyboard</b>, <b>OSC</b>, each vJoy device, the Xbox controller, and the <b>Logical Device</b> once it has a module file.</p>"
                + "<ul>"
                + "<li>Double-click a card to open its Configuration page (or <b>Output View</b> for an output).</li>"
                + "<li>Right-click a card for its menu (see <a href=\"topic:home-devices-card-menu\">Card menus</a>).</li>"
                + "<li>Each card's <b>last:</b> line shows the latest input it passed or output it sent.</li>"
                + "<li>To group cards, Shift-click them, then choose <b>Stack Selected Cards</b>.</li>"
                + "<li><b>Compact view</b> and <b>Layout</b> (<b>Single list</b>, <b>Side by side</b> or <b>Stacked</b>; also <b>View › Home Layout</b>) change how the cards are laid out.</li>"
                + "<li>Right-click empty space for <b>Unhide All Cards</b>, <b>Reset All Card Sizes</b>, <b>Hidden Cards</b> and <b>Layout</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>A connected device without a module shows as a card without a module when <b>Show devices without a module</b> is on in <b>Options</b> (<b>Home</b>).</li></ul>",
            related: ["home-devices-card-menu", "home-devices-hidden-cards", "configuration-actions-configuration-page", "configuration-actions-output-view"]
        },
        {
            id: "home-devices-card-menu",
            section: "Home",
            title: "Card menus",
            body: "<p>A card's right-click menu holds every command for that device. The card shows as picked first, as a click does; a card in a Shift selection keeps the selection, for items that act on all of it.</p>"
                + "<ul>"
                + "<li>At the top: <b>Open Configuration</b> (<b>Output View</b> on an output card), <b>Button Map</b> and <b>Hide Card</b>.</li>"
                + "<li><b>Module</b>: <b>Module Setup…</b>, <b>Auto Mapper</b>, <b>Calibration</b>.</li>"
                + "<li><b>View</b>: the <b>vJoy Viewer</b> or <b>Xbox Viewer</b>, <b>Device Information</b>.</li>"
                + "<li><b>Cards</b>: <b>Stack Selected Cards</b>, <b>Unstack</b>, <b>Unstack All</b>, <b>Reset Size</b>, <b>Reset All Card Sizes</b>.</li>"
                + "<li><b>Device</b>: <b>Start Fresh…</b> (for a damaged module file), <b>Copy Setup to Another Stick…</b>, <b>Swap with Another Stick…</b> and <b>Change vJoy Output…</b> (they open the <b>Device Library</b> on that stick), <b>Reset Card Layout</b> (clears its size and stacking) and <b>Delete Device</b>.</li>"
                + "</ul>"
                + "<p>Items that don't apply to a card are left out:</p>"
                + "<ul>"
                + "<li>vJoy cards have no Calibration, Copy Setup to Another Stick…, Swap with Another Stick…, Change vJoy Output… or Delete Device.</li>"
                + "<li>The Xbox card has no Module Setup, Auto Mapper, Calibration, Device Information, Copy Setup to Another Stick…, Swap with Another Stick…, Change vJoy Output… or Delete Device.</li>"
                + "<li>The Keyboard and OSC cards have no Auto Mapper, Calibration, Device Information, Copy Setup to Another Stick…, Swap with Another Stick… or Change vJoy Output….</li>"
                + "<li>The Logical Device card has no Module Setup, Auto Mapper, Calibration, Device Information, Copy Setup to Another Stick…, Swap with Another Stick… or Change vJoy Output….</li>"
                + "</ul>",
            related: ["home-devices-home", "home-devices-delete-device", "home-devices-input-modules", "getting-started-menus"]
        },
        {
            id: "home-devices-hidden-cards",
            section: "Home",
            title: "Hide and unhide cards",
            body: "<p>Hiding a card only takes it off Home. It does not hide the device from Windows or games; use HidHide for that.</p>"
                + "<ol>"
                + "<li>To hide a card, right-click it and choose <b>Hide Card</b>.</li>"
                + "<li>To bring one back, right-click empty space on Home and open <b>Hidden Cards</b>. It lists each hidden card; click one to unhide it.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>Unhide All Cards</b> brings them all back.</li></ul>",
            related: ["home-devices-home", "tools-hidhide"]
        },
        {
            id: "home-devices-delete-device",
            section: "Home",
            title: "Delete a device",
            body: "<p><b>Delete Device</b> removes a device's module file, its pictures and its actions in every mode.</p>"
                + "<ol>"
                + "<li>Stop the profile. Delete Device is refused while the profile runs.</li>"
                + "<li>Right-click the card and choose <b>Device</b> › <b>Delete Device</b>. It asks twice.</li>"
                + "<li>Save the profile to keep the change. The actions are removed from the open profile, which is left with unsaved changes.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An autosave of the stick (\"Autosave: stick deleted\") is always kept in the <b>Device Library</b> first: its module file, its pictures and its bindings in every mode. If the autosave can't be written or read back, nothing is deleted.</li>"
                + "<li>The stick then shows in the Device Library as <b>Deleted</b>.</li>"
                + "</ul>",
            related: ["home-devices-backups", "home-devices-card-menu"]
        },
        {
            id: "home-devices-backups",
            section: "Home",
            title: "Deleted devices and backups",
            body: "<p>Nothing is thrown away for good. The copies stay until you delete them yourself.</p>"
                + "<ul>"
                + "<li><b>Delete Device</b> keeps an autosave of the stick in the <b>Device Library</b> (see <a href=\"topic:home-devices-delete-device\">Delete a device</a>).</li>"
                + "<li><b>Delete File</b> in Module Setup asks first and keeps an autosave of the module file in the Device Library (\"Autosave: module file deleted\"); if it can't be kept, nothing is deleted. The device's pictures stay.</li>"
                + "<li><b>Device Pack</b> import and Module Setup's <b>Import from</b> keep the file they replace in the imported folder inside the modules folder.</li>"
                + "<li><b>Start Fresh…</b> moves a damaged module file aside and keeps it as a copy.</li>"
                + "</ul>"
                + "<p>To put a deleted stick's setup on another stick:</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › Device Library…</b>.</li>"
                + "<li>Pick the stick's autosave.</li>"
                + "<li>Choose <b>Copy to Another Stick…</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>A saved setup can also be exported as a Device Pack and imported with <b>Tools › Device Setup › Device Pack</b>.</li></ul>",
            related: ["home-devices-delete-device", "home-devices-module-files", "home-devices-device-pack"]
        },

        {
            id: "home-devices-input-modules",
            section: "Modules",
            title: "Set up an input module",
            body: "<p>An input module decides which controls of a physical device exist for Gremlin-Platforms. Only claimed controls reach your actions, the viewers and the Auto Mapper.</p>"
                + "<ol>"
                + "<li>Open it from the card menu (<b>Module</b> › <b>Module Setup…</b>) or <b>Tools › Device Setup › Input Module Setup</b>.</li>"
                + "<li>Press a control on the device to claim it, or tick it. Untick a control to release it.</li>"
                + "<li>Give a control a <b>Friendly name</b> if you like.</li>"
                + "<li>Choose <b>Save Module</b> to write the module file, or <b>Cancel</b> to discard.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Undo</b> and <b>Redo</b> (<b>Ctrl+Z</b>, <b>Ctrl+Y</b>) step back through the ticks and names until you open another device.</li>"
                + "<li><b>Keyboard</b> is an input module too. Key bindings only fire for keys it claims. Until you save a choice, every key is claimed. Typing in Windows and games is never affected.</li>"
                + "<li>Calibration for a stick is stored in its input module (see <a href=\"topic:tools-calibration\">Calibrate axes</a>).</li>"
                + "</ul>",
            related: ["home-devices-vjoy-output", "home-devices-module-files", "tools-calibration", "getting-started-key-does-not-fire"]
        },
        {
            id: "home-devices-vjoy-output",
            section: "Modules",
            title: "Set up a vJoy output module",
            body: "<p>Each vJoy device has an output module. It is the firewall in front of the vJoy driver: only outputs it claims are sent.</p>"
                + "<ol>"
                + "<li>Open it from the card menu (<b>Module</b> › <b>Module Setup…</b>) or <b>Tools › Device Setup › Output Module Setup</b>.</li>"
                + "<li>Tick the axes, buttons and hats you will use.</li>"
                + "<li>Choose <b>Save Module</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The vJoy driver sets the maximum; the output module sets what Gremlin-Platforms may use.</li>"
                + "<li>A wire to an output that is not claimed sends nothing. It is kept, and shown as <b>(not claimed)</b> on the Configuration page, Button Map chips, the viewers and in Map to vJoy, and the log notes it once. Claim the output to make it work.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "home-devices-xbox-output", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "home-devices-xbox-output",
            section: "Modules",
            title: "Xbox output module",
            body: "<p>The Xbox controller (<b>Xbox 360 Controller</b>, pad 1) is a virtual Xbox 360 pad provided by the <b>ViGEmBus</b> driver. Its output module passes every control straight to the driver; there is nothing to claim.</p>"
                + "<p>To send to it:</p>"
                + "<ol>"
                + "<li>Choose <b>Add Action</b> on the input's row on the Configuration page (or right-click a Logical Device control and choose <b>Add Action</b>).</li>"
                + "<li>Choose <b>Map to Xbox</b>.</li>"
                + "</ol>"
                + "<p>Its page (double-click the card) shows which inputs drive each control. The <b>Xbox Viewer</b> shows the live pad.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The pad appears when a Map to Xbox action first sends while the profile runs, and is removed when the profile stops.</li>"
                + "<li>The page and the Xbox Viewer check the driver at their top, as HidHide does: <b>ViGEmBus driver found</b> with its version, or what is wrong (not installed, installed but not running, ViGEmClient.dll missing) and what to do. The check shows even when nothing is mapped to Xbox yet.</li>"
                + "<li><b>Get ViGEmBus</b> opens the Nefarius releases page; <b>Test ViGEmBus</b> opens Windows Game Controllers, where the pad shows while the profile runs.</li>"
                + "</ul>",
            related: ["configuration-actions-map-to-xbox", "home-devices-vjoy-output", "tools-viewers", "getting-started-xbox-does-nothing"]
        },
        {
            id: "home-devices-module-files",
            section: "Modules",
            title: "Module files",
            body: "<p>Each device has its own module file, found by the device first and then by its name. It holds the device's claims, friendly names, picture, Button Map layout, Appearance and calibration.</p>"
                + "<p>In Input or Output Module Setup, <b>Module File</b> shows the current file and offers:</p>"
                + "<ul>"
                + "<li><b>Import from</b>: copy another file into this device's file.</li>"
                + "<li><b>Browse for File</b> and <b>Open Modules Folder</b>.</li>"
                + "<li><b>Delete File</b> (an autosave is kept; see <a href=\"topic:home-devices-backups\">Deleted devices and backups</a>).</li>"
                + "</ul>"
                + "<p><b>Import Image…</b> sets the device picture.</p>",
            related: ["getting-started-saved-where", "home-devices-device-pack", "home-devices-backups"]
        },
        {
            id: "home-devices-device-pack",
            section: "Modules",
            title: "Share a setup with a Device Pack",
            body: "<p><b>Tools › Device Setup › Device Pack</b> shares a working copy of a device's setup as a zip.</p>"
                + "<p>To export a pack:</p>"
                + "<ol>"
                + "<li>Choose <b>Export</b>. The pack holds the device's module file, pictures, and its wires (with their actions and the output modules they send to).</li>"
                + "<li>Untick modes under <b>Wires in these modes</b> to leave them out.</li>"
                + "<li>Fill in <b>Made by</b> and <b>Note</b>; they are shown to whoever imports the pack.</li>"
                + "<li>After saving, <b>Show Folder</b> opens where it was saved.</li>"
                + "</ol>"
                + "<p>To import a pack:</p>"
                + "<ol>"
                + "<li>Choose <b>Import</b> and pick the device under <b>Put this pack on</b>.</li>"
                + "<li>Tick the pieces to bring in. Import adds the pack's checked controls to the ones checked here; none are unchecked. The other ticked pieces replace only what they hold (a control's name, an axis's calibration, the map), and each ticked mode under <b>Wires</b> replaces the device's wires and actions in that mode. Other modes and other devices are left alone.</li>"
                + "<li>Read the warning before anything changes: it lists what will be added and replaced, any controls the device doesn't have (left out), and wires to Logical Device inputs that don't exist here, which it can create.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An output put on another vJoy (an output's name box) takes its wires with it. Modes are created under their parent from the pack.</li>"
                + "<li>If a driver the pack's wires need isn't found (vJoy, a vJoy device, or the Xbox driver ViGEmBus), the import screen says so as soon as the pack is opened, and the warning says it again.</li>"
                + "<li><b>Map settings</b> holds <b>Map view</b> (pan, zoom, grid and guides) and <b>Print area and print settings</b>; both are unticked unless you tick them. The device photo comes with where it sits on the map.</li>"
                + "<li>The previous module file is kept in the imported folder, and the profile changes on disk only when you save it.</li>"
                + "<li><b>Undo Import</b> puts the last import back until you import again, open another pack, or close the window. If a file the import wrote was saved again since, it asks first, because those later changes are lost.</li>"
                + "<li>A pack made by a newer version of the program is refused.</li>"
                + "</ul>",
            related: ["home-devices-module-files", "home-devices-backups"]
        },

        {
            id: "home-devices-q-card-missing",
            section: "Common questions",
            title: "Where did my device's card go?",
            body: "<p>It may be hidden. Right-click empty space on Home and open <b>Hidden Cards</b>. See <a href=\"topic:home-devices-hidden-cards\">Hide and unhide cards</a>.</p>",
            related: ["home-devices-hidden-cards", "getting-started-device-missing"]
        },
        {
            id: "home-devices-q-input-missing",
            section: "Common questions",
            title: "Why doesn't an input show on the Configuration page?",
            body: "<p>Only claimed inputs show. Claim it in the device's input module. See <a href=\"topic:home-devices-input-modules\">Set up an input module</a>.</p>",
            related: ["home-devices-input-modules"]
        },
        {
            id: "home-devices-q-get-deleted-back",
            section: "Common questions",
            title: "Can I get a deleted device back?",
            body: "<p>Yes. An autosave is kept in the Device Library first. See <a href=\"topic:home-devices-backups\">Deleted devices and backups</a>.</p>",
            related: ["home-devices-backups"]
        },
        {
            id: "home-devices-q-not-claimed",
            section: "Common questions",
            title: "What does \"(not claimed)\" mean?",
            body: "<p>The output module doesn't claim that output, so nothing is sent to it. See <a href=\"topic:home-devices-vjoy-output\">Set up a vJoy output module</a>.</p>",
            related: ["home-devices-vjoy-output"]
        }
    ]
}
