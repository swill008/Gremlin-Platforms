// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Home and devices (cards, devices, modules, Device Pack,
// deleted devices).

.pragma library

var chapter = { id: "home-devices", title: "Home and devices" }

function topics() {
    return [
        {
            id: "home-devices-home",
            section: "Home",
            title: "Home and its cards",
            body: "<p><b>Home</b> <a href=\"open:view.home\">Open ›</a> shows one card per device: your physical devices, the <b>Keyboard</b>, <b>OSC</b>, each vJoy device, the Xbox controller, and the <b>Logical Device</b> once it has a module file.</p>"
                + "<ul>"
                + "<li>Double-click a card, or select it and press <b>Enter</b>, to open its Configuration page (or <b>Output View</b> for an output).</li>"
                + "<li>The arrow keys move between cards.</li>"
                + "<li>Right-click a card for its menu (see <a href=\"topic:home-devices-card-menu\">Card menus</a>).</li>"
                + "<li><b>Compact view</b> and <b>Layout</b> (<b>Single list</b>, <b>Side by side</b> or <b>Stacked</b>; also <b>View › Home Layout</b> <a href=\"show:menu/View/Home Layout\">Show me ›</a>) change how the cards are laid out.</li>"
                + "<li>Right-click empty space for <b>Unhide All Cards</b>, <b>Reset All Card Sizes</b>, <b>Hidden Cards</b> and <b>Layout</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>A connected device without a module shows as a card without a module when <b>Show devices without a module</b> <a href=\"show:option/Show devices without a module\">Show me ›</a> is on in <b>Options</b> (<b>Home</b>).</li></ul>",
            related: ["home-devices-card-text", "home-devices-arrange-cards", "home-devices-card-menu", "configuration-actions-configuration-page"]
        },
        {
            id: "home-devices-card-text",
            section: "Home",
            title: "What a card shows",
            body: "<p>Each card sums up its device, top to bottom.</p>"
                + "<ul>"
                + "<li>The device photo (left out in <b>Compact view</b>) and the device name.</li>"
                + "<li>Its status and bus, for example <b>Connected</b>, <b>Virtual</b> or <b>No module</b>. A vJoy device another program holds shows \"In use by another program\".</li>"
                + "<li>The claimed buttons, axes and hats, in words (\"1 hat\", \"2 hats\").</li>"
                + "<li>On output cards only, <b>Driven by: [device]</b>: the input devices whose actions send to it, or <b>Driven by: [nothing]</b>. It follows your action edits within a moment. The <b>Output View</b> header shows the same line.</li>"
                + "<li>The <b>last:</b> line: the latest input the input module passed, or on an output card the latest output sent while the profile runs. It uses the friendly name; hover for the hardware name.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>A card whose module file can't be read says \"Module file damaged – inputs blocked\" in red. See <a href=\"topic:home-devices-damaged-file\">Fix a damaged module file</a>.</li></ul>",
            related: ["home-devices-home", "home-devices-input-modules", "home-devices-damaged-file", "configuration-actions-output-view"]
        },
        {
            id: "home-devices-arrange-cards",
            section: "Home",
            title: "Arrange and resize cards",
            body: "<p>Put the cards in the order and size you like. Both are kept between sessions.</p>"
                + "<ul>"
                + "<li>To move a card, drag it to its new place.</li>"
                + "<li>To resize a card, drag its edge or corner.</li>"
                + "<li>To group cards, Shift-click them, then right-click and choose <b>Stack Selected Cards</b>. Cards in a stack share one size.</li>"
                + "<li>To undo a size, right-click the card and choose <b>Reset Size</b>, or right-click empty space and choose <b>Reset All Card Sizes</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Unplugged and hidden cards keep their places. A renamed stick takes its old card's place.</li>"
                + "<li>When you delete a device, its place goes too.</li>"
                + "</ul>",
            related: ["home-devices-home", "home-devices-card-menu", "home-devices-hidden-cards"]
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
                + "<li>Right-click the card and choose <b>Device</b> › <b>Delete Device</b>. A first window says what goes; choose <b>Continue</b>.</li>"
                + "<li>The question \"Delete &lt;name&gt;?\" starts \"An autosave is kept in the Device Library first.\" and ends \"You can restore it from Tools › History.\" Choose the red <b>Delete Device</b>. <b>Cancel</b>, <b>Enter</b> and <b>Esc</b> keep the device.</li>"
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
                + "<li>Choose <b>Tools › Device Setup › Device Library…</b> <a href=\"open:tools.deviceLibrary\">Open ›</a>.</li>"
                + "<li>Pick the stick's autosave.</li>"
                + "<li>Choose <b>Copy to Another Stick…</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>A saved setup can also be exported as a Device Pack and imported with <b>Tools › Device Setup › Device Pack</b> <a href=\"open:tools.devicePack\">Open ›</a>.</li></ul>",
            related: ["home-devices-delete-device", "home-devices-module-files", "home-devices-device-pack"]
        },

        {
            id: "home-devices-identical",
            section: "Devices",
            title: "Identical devices",
            body: "<p>Two devices of the same make get names of their own, so each has its own module file, card, Button Map and calibration.</p>"
                + "<ul>"
                + "<li>The device the existing module file belongs to keeps the plain name. The second is named \"&lt;name&gt; (2)\", a third \"&lt;name&gt; (3)\".</li>"
                + "<li>Each name stays with its device, whichever port it uses and in every session.</li>"
                + "<li>A \"(2)\" device plugged in on its own is still \"(2)\".</li>"
                + "<li>A device with no twin is never renamed.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>To tell the two apart, compare their Joystick ID and Device ID in <b>Tools › Device Setup › Device Information</b> <a href=\"open:tools.deviceInfo\">Open ›</a>.</li></ul>",
            related: ["tools-device-information", "home-devices-module-files", "tools-q-identical-sticks"]
        },
        {
            id: "home-devices-unplugged",
            section: "Devices",
            title: "When a device is unplugged",
            body: "<p>Unplugging a stick is safe, also while the profile runs.</p>"
                + "<ul>"
                + "<li>Every button it held is let go and every hat is centred, as if you had let go yourself.</li>"
                + "<li>Every action that reads one of its axes reads it centred.</li>"
                + "<li>Its actions stay in the profile, and its card stays on Home.</li>"
                + "<li>Module Setup keeps your work on screen, but <b>Save Module</b> is refused until the stick is plugged in again. Nothing is saved meanwhile.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When the stick is back, Save works with the work on screen kept.</li>"
                + "<li>The Keyboard, OSC and Xbox are never blocked.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "getting-started-device-missing", "getting-started-what-stop-releases"]
        },
        {
            id: "home-devices-vjoy-left-out",
            section: "Devices",
            title: "vJoy devices left out at start",
            body: "<p>A vJoy device with a set-up problem is left out, and the program starts without it. The other vJoy devices work.</p>"
                + "<ul>"
                + "<li>A vJoy device is left out when it has discrete hats, Windows doesn't list it, or two are set up alike.</li>"
                + "<li>Once the main window is up, a message says which ones, why, and how to fix each (\"Gremlin-Platforms is running without vJoy 2.\"). It shows again only when that changes, for example when a device is plugged in.</li>"
                + "<li>Fix the vJoy set-up as the message says, then restart the program.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Device Information</b> <a href=\"open:tools.deviceInfo\">Open ›</a> still lists a left-out vJoy device, marked \"left out (see message)\", and the program's own Xbox pads, marked \"this program's Xbox pad\".</li>"
                + "<li>A vJoy device that another program holds shows \"In use by another program\" on its card. The program tells you once per Run and tries again every 3 seconds.</li>"
                + "</ul>",
            related: ["getting-started-nothing-reaches-vjoy", "home-devices-vjoy-output", "tools-device-information"]
        },
        {
            id: "home-devices-record-input",
            section: "Devices",
            title: "Record an input by pressing it",
            body: "<p>Where a page has a red record button (for example <b>Add Key</b> on the Keyboard page, or <b>Record Inputs</b> in a macro or condition), you can pick an input by pressing it.</p>"
                + "<ol>"
                + "<li>Choose the record button. \"Waiting for user input. Hold ESC to abort.\" shows.</li>"
                + "<li>Press the button or key, move the axis, or push the hat.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>For one input, it ends at the first press. For several, it ends at the first release.</li>"
                + "<li>An axis counts only after a big enough move; a hat only when pushed off centre.</li>"
                + "<li>The Logical Device and the program's own virtual buttons are ignored.</li>"
                + "<li>To cancel, hold <b>Esc</b> for 1 second. A short tap does not cancel.</li>"
                + "</ul>",
            related: ["configuration-actions-keyboard-page", "configuration-actions-macro", "configuration-actions-condition"]
        },

        {
            id: "home-devices-input-modules",
            section: "Modules",
            title: "Set up an input module",
            body: "<p>An input module decides which controls of a physical device exist for Gremlin-Platforms. Only claimed controls reach your actions, the viewers and the Auto Mapper.</p>"
                + "<ol>"
                + "<li>Open it from the card menu (<b>Module</b> › <b>Module Setup…</b>) or <b>Tools › Device Setup › Input Module Setup</b> <a href=\"open:tools.configureInput\">Open ›</a>.</li>"
                + "<li>Press a control on the device to claim it, or tick it. Untick a control to release it.</li>"
                + "<li>Give a control a <b>Friendly name</b> if you like.</li>"
                + "<li>Choose <b>Save Module</b> to write the module file, or <b>Cancel</b> to discard.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li><b>Undo</b> and <b>Redo</b> (<b>Ctrl+Z</b>, <b>Ctrl+Y</b>) step back through the ticks and names until you open another device.</li>"
                + "<li><b>Keyboard</b> is an input module too. Press a key that isn't listed to add it, ticked; the empty list says \"Press a key to add it.\". Key bindings only fire for keys it claims. Until you save a choice, every key is claimed. Typing in Windows and games is never affected.</li>"
                + "<li>A module saved while the profile runs applies at once.</li>"
                + "<li>Save is refused while the stick is unplugged (see <a href=\"topic:home-devices-unplugged\">When a device is unplugged</a>).</li>"
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
                + "<li>Open it from the card menu (<b>Module</b> › <b>Module Setup…</b>) or <b>Tools › Device Setup › Output Module Setup</b> <a href=\"open:tools.configureOutput\">Open ›</a>.</li>"
                + "<li>Tick the axes, buttons and hats you will use.</li>"
                + "<li>Choose <b>Save Module</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The vJoy driver sets the maximum; the output module sets what Gremlin-Platforms may use.</li>"
                + "<li>A wire to an output that is not claimed sends nothing. It is kept, and shown as <b>(not claimed)</b>. Claim the output to make it work.</li>"
                + "<li>A module saved while the profile runs applies at once.</li>"
                + "<li>A profile with Map to vJoy actions opens on a PC without vJoy, and keeps those actions.</li>"
                + "<li>A vJoy device set to <b>Input</b> under <b>vJoy Behavior</b> in <b>Profile Settings</b> <a href=\"open:view.settings\">Open ›</a> is listed with the physical devices, and is not offered under <b>vJoy Initial Values</b>.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "home-devices-xbox-output", "home-devices-vjoy-left-out", "getting-started-nothing-reaches-vjoy"]
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
                + "<p>Its page (double-click the card) shows which inputs drive each control. The <b>Xbox Viewer</b> <a href=\"open:tools.xboxViewer\">Open ›</a> shows the live pad.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The pad appears when a Map to Xbox action first sends while the profile runs, and is removed when the profile stops.</li>"
                + "<li>The pad number comes from the module's name: Xbox 360 Controller is pad 1.</li>"
                + "<li>The page and the Xbox Viewer check the driver at their top: <b>ViGEmBus driver found</b> with its version, or what is wrong and what to do. <b>Get ViGEmBus</b> opens the Nefarius releases page; <b>Test ViGEmBus</b> opens Windows Game Controllers.</li>"
                + "</ul>",
            related: ["configuration-actions-map-to-xbox", "home-devices-vjoy-output", "tools-viewers", "getting-started-xbox-does-nothing"]
        },
        {
            id: "home-devices-module-files",
            section: "Modules",
            title: "Module files",
            body: "<p>Each device has its own module file, found by the device first and then by its name. It holds the device's claims, friendly names, picture, Button Map layout, Appearance and calibration.</p>"
                + "<p>In Input or Output Module Setup, <b>Module File</b> shows the <b>Current file</b>, with \"(not saved yet)\" when it doesn't exist yet, and offers:</p>"
                + "<ul>"
                + "<li><b>Import from</b>: copy another file into this device's file (see <a href=\"topic:home-devices-import-module-file\">Import a module file</a>).</li>"
                + "<li><b>Browse for File</b> and <b>Open Modules Folder</b>.</li>"
                + "<li><b>Delete File</b>: it asks \"Delete &lt;file&gt;?\", ending \"You can restore it from Tools › History.\" Choose the red <b>Delete File</b>; <b>Cancel</b>, <b>Enter</b> and <b>Esc</b> keep the file. An autosave is kept (see <a href=\"topic:home-devices-backups\">Deleted devices and backups</a>).</li>"
                + "</ul>"
                + "<p>The message line under them says what an import, its Undo or Delete File did: plain when it worked, red when it failed.</p>"
                + "<p><b>Import Image…</b> sets the device picture.</p>"
                + "<h4>Good to know</h4>"
                + "<ul><li>When the stick still opens a file of another name, a note says so; import that file to copy it here.</li>"
                + "<li><b>Browse for File</b> opens in the folder you last picked a module file from; <b>Import Image…</b> opens in the folder you last picked a picture from.</li></ul>",
            related: ["home-devices-import-module-file", "home-devices-damaged-file", "getting-started-saved-where", "home-devices-device-pack"]
        },
        {
            id: "home-devices-import-module-file",
            section: "Modules",
            title: "Import a module file",
            body: "<p><b>Import from</b> copies a chosen module file into this device's file. The chosen file stays where it is.</p>"
                + "<ol>"
                + "<li>In Module Setup, open <b>Module File</b>.</li>"
                + "<li>Choose a file under <b>Import from</b>, or <b>Browse for File</b>. With unsaved ticks, it asks first.</li>"
                + "<li>Read the message line under <b>Module File</b>: it says what was imported. Its <b>Undo</b> link puts the previous file back.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The <b>Undo</b> link lasts until the next message, until you close the message with its ×, or until you close the window; then the import is kept.</li>"
                + "<li>Only the controls this device has are kept; the message names the ones left out. This device's picture and the profile's wires stay as they are.</li>"
                + "<li>It is refused for a file that can't be read or isn't a module file, a vJoy file onto a stick or a stick file onto a vJoy, a device that isn't connected, and a current file that can't be read.</li>"
                + "<li>The previous file is kept in the imported folder.</li>"
                + "<li>A failed import or Undo shows its message in red.</li>"
                + "</ul>",
            related: ["home-devices-module-files", "home-devices-backups"]
        },
        {
            id: "home-devices-damaged-file",
            section: "Modules",
            title: "Fix a damaged module file",
            body: "<p>A module file that can't be read is never treated as empty, so nothing in it is lost. Until you fix it, the device's inputs are blocked.</p>"
                + "<ul>"
                + "<li>Its card says \"Module file damaged – inputs blocked\" in red.</li>"
                + "<li>Every save into the file is refused, including Module Setup, the Button Map and a Device Pack import.</li>"
                + "</ul>"
                + "<p>To set the device up again:</p>"
                + "<ol>"
                + "<li>Right-click the card and choose <b>Start Fresh…</b> (under <b>Device</b>). It asks first.</li>"
                + "<li>Set the device up again in Module Setup.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>Start Fresh keeps the damaged file as a copy named &lt;name&gt;.json.bad-&lt;date&gt;. If it can't be moved, it says so.</li></ul>",
            related: ["home-devices-module-files", "home-devices-card-text", "home-devices-backups"]
        },
        {
            id: "home-devices-device-pack",
            section: "Modules",
            title: "Share a setup with a Device Pack",
            body: "<p><b>Tools › Device Setup › Device Pack</b> <a href=\"open:tools.devicePack\">Open ›</a> shares a working copy of a device's setup as a zip.</p>"
                + "<ol>"
                + "<li>On the <b>Export</b> tab, pick the device. It opens on the first device that can be exported.</li>"
                + "<li>Untick modes under <b>Wires in these modes</b> to leave them out.</li>"
                + "<li>Fill in <b>Made by</b> and <b>Note</b>; they are shown to whoever imports the pack.</li>"
                + "<li>Choose <b>Export…</b> and pick where to save it. The chooser opens in the folder you last used for a Device Pack. <b>Show Folder</b> then opens that folder.</li>"
                + "</ol>"
                + "<p>The pack holds the device's module file, pictures, and its wires (with their actions and the output modules they send to).</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The pack is written in the background. The window stays usable and shows <b>Exporting…</b>; one export runs at a time.</li>"
                + "<li>A device with no module file yet can't be exported (\"This device has no module file yet.\"). One whose file can't be read shows \"(file damaged)\".</li>"
                + "<li>Save the pack outside the modules folder. A name without .zip gets .zip.</li>"
                + "</ul>",
            related: ["home-devices-device-pack-import", "home-devices-module-files", "home-devices-backups"]
        },
        {
            id: "home-devices-device-pack-import",
            section: "Modules",
            title: "Put a Device Pack on a device",
            body: "<p>Import puts a pack's setup on one of your devices.</p>"
                + "<ol>"
                + "<li>In <b>Device Pack</b> <a href=\"open:tools.devicePack\">Open ›</a>, open the <b>Import</b> tab and choose <b>Choose Zip…</b>.</li>"
                + "<li>Pick the device under <b>Put this pack on</b>.</li>"
                + "<li>Tick the pieces to bring in. Import adds the pack's checked controls and never unchecks one you have. Other pieces replace only what they hold, and each ticked mode under <b>Wires</b> replaces the device's wires in that mode. Other modes and devices are left alone.</li>"
                + "<li>Choose <b>Import</b>, read the warning, then choose <b>Replace</b>. The message line says what was imported, with an <b>Undo Import</b> link.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Missing modes are created under their parent, or under Default when the parent isn't here. Tick <b>Create the missing Logical Device inputs</b> to add the ones its wires need.</li>"
                + "<li>Refused: a stick pack onto a vJoy or the other way round, a damaged module file (use <b>Start Fresh…</b> first), and a pack from a newer version.</li>"
                + "<li>If it fails partway, everything it did is undone and it says so.</li>"
                + "<li><b>Undo Import</b> (the button or the link) puts back the files, pictures and wires, and removes the modes and Logical Device inputs it created. It lasts until you import again, open another pack, or close the window. With another profile open, only the files go back.</li>"
                + "</ul>",
            related: ["home-devices-device-pack", "home-devices-damaged-file", "device-library-import"]
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
        },
        {
            id: "home-devices-q-two-same",
            section: "Common questions",
            title: "Why is my stick called \"(2)\"?",
            body: "<p>You have two of the same device, and each gets its own name. See <a href=\"topic:home-devices-identical\">Identical devices</a>.</p>",
            related: ["home-devices-identical"]
        },
        {
            id: "home-devices-q-cannot-save-module",
            section: "Common questions",
            title: "Why won't Module Setup save?",
            body: "<p>The stick is unplugged, or its module file is damaged. See <a href=\"topic:home-devices-unplugged\">When a device is unplugged</a> and <a href=\"topic:home-devices-damaged-file\">Fix a damaged module file</a>.</p>",
            related: ["home-devices-unplugged", "home-devices-damaged-file"]
        }
    ]
}
