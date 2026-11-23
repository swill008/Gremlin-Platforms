// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Home and devices (cards, devices, modules, Export / Import Device,
// deleted devices). Written to claude/plans/help-style-guide.md: each topic
// opens with what it's for, then "How to", "What you see" and "Good to know"
// (empty sections left out).

.pragma library

var chapter = { id: "home-devices", title: "Home and devices" }

function topics() {
    return [
        {
            id: "home-devices-home",
            section: "Home",
            title: "Home and its cards",
            body: "<p><b>Home</b> <a href=\"open:view.home\">Open ›</a> shows one card for each device. Your sticks, the <b>Keyboard</b>, <b>OSC</b>, each vJoy device, the Xbox controller and the <b>Logical Device</b> each have one.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>To open a device's page, double-click its card, or select it and press <b>Enter</b>. Input devices open <b>Device Bindings</b>; outputs open their <b>Output View</b>.</li>"
                + "<li>To move between cards, use the arrow keys.</li>"
                + "<li>To see a card's commands, right-click it (see <a href=\"topic:home-devices-card-menu\">Card menus</a>).</li>"
                + "<li>To take back a change to the cards, press <b>Ctrl+Z</b> (<b>Undo</b>). <b>Ctrl+Y</b> (<b>Redo</b>) puts it back again.</li>"
                + "</ul>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Compact view</b> makes each card a short row. It is also in Options. <a href=\"show:option/Compact view\">Show me ›</a></li>"
                + "<li><b>Layout</b> picks <b>Single list</b>, <b>Side by side</b> or <b>Stacked</b>. It is also in <b>View › Home Layout</b>. <a href=\"show:menu/View/Home Layout\">Show me ›</a></li>"
                + "<li>Right-click empty space for <b>Unhide All Cards</b>, <b>Reset All Card Sizes</b>, <b>Hidden Cards</b> and <b>Layout</b>.</li>"
                + "<li><b>Undo</b> and <b>Redo</b> also sit beside the title of every right-click menu on Home.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Undo covers card sizes, order and stacks, <b>Reset Card Layout</b>, card pictures, Compact view, Layout and the line between the lists.</li>"
                + "<li><b>Ctrl+Shift+Z</b> also works as Redo.</li>"
                + "<li>Home keeps about 50 Undo steps until you close the program. Loading another profile clears them.</li>"
                + "<li><b>Delete Device</b> can't be undone here; use <b>Tools › History</b> instead.</li>"
                + "<li>Turn on <b>Show devices without a module</b> to see a card for every connected device, even one you haven't set up yet. <a href=\"show:option/Show devices without a module\">Show me ›</a></li>"
                + "</ul>",
            related: ["home-devices-card-text", "home-devices-arrange-cards", "home-devices-card-menu", "device-bindings-actions-device-bindings-page"]
        },
        {
            id: "home-devices-card-text",
            section: "Home",
            title: "What a card shows",
            body: "<p>Each card sums up its device, from top to bottom.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>A picture and the device name. The picture is the device image you added, or else one made from the device map's background.</li>"
                + "<li>In <b>Compact view</b> the picture is a small thumbnail on the left. A device with no picture shows its icon there.</li>"
                + "<li>Its status, for example <b>Connected</b>, <b>Virtual</b> or <b>No module</b>.</li>"
                + "<li>The buttons, axes and hats ticked in its module, in words (\"1 hat\", \"2 hats\").</li>"
                + "<li>On output cards only, <b>Driven by: [device]</b>: the input devices whose actions send to it. With none, it reads <b>Driven by: [nothing]</b>.</li>"
                + "<li>The <b>last:</b> line: the last control you used. On an output card, it is the last thing sent while the profile runs.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The Driven by line updates as soon as you change an action. The <b>Output View</b> header shows the same line.</li>"
                + "<li>The last: line uses the control's friendly name. Hover it for the device's own name for that control.</li>"
                + "<li>A vJoy card that another program holds says \"In use by another program\".</li>"
                + "<li>The OSC card shows its server instead of a status, for example \"Listening on all addresses, port 8001\". See <a href=\"topic:osc-card-line\">The OSC card on Home</a>.</li>"
                + "<li>A card whose module file can't be read says \"Module file damaged – inputs blocked\" in red. See <a href=\"topic:home-devices-damaged-file\">Fix a damaged module file</a>.</li>"
                + "<li>A red outline and \"⚠ n binding outputs not found\" mean some actions send to an output that isn't there. The output is missing or switched off.<ul>"
                + "<li>Hover the warning to see which ones: the first 10, then \"… and n more\".</li>"
                + "<li>To fix them, open the device's page and pick another output in each action.</li>"
                + "<li>Tick <b>Binding output not found</b> in the page's Find bar to list them.</li>"
                + "<li>To see them across devices and fix several at once, use Health. See <a href=\"topic:tools-health\">Find problems with Health</a>.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["home-devices-home", "home-devices-input-modules", "home-devices-damaged-file", "device-bindings-actions-output-view"]
        },
        {
            id: "home-devices-arrange-cards",
            section: "Home",
            title: "Arrange and resize cards",
            body: "<p>Put the cards in the order and size you like. Home keeps both between sessions.</p>"
                + "<h4>How to</h4>"
                + "<ul>"
                + "<li>To move a card, drag it and drop it where the line shows.</li>"
                + "<li>To resize a card, drag its right edge, its bottom edge or its bottom-right corner.</li>"
                + "<li>To select several cards, Shift-click them, or drag a box over empty space.</li>"
                + "<li>To add to a selection, hold <b>Shift</b> while you drag. To clear it, click empty space or press <b>Esc</b>.</li>"
                + "<li>To stack cards, select them, right-click one and choose <b>Stack Selected Cards</b> (under <b>Cards</b>).</li>"
                + "<li>To take a card out of a stack, right-click it and choose <b>Unstack</b>. <b>Unstack All</b> breaks up the whole stack.</li>"
                + "<li>To put a card back to its default size, right-click it and choose <b>Reset Size</b>.</li>"
                + "</ul>"
                + "<h4>What you see</h4>"
                + "<table>"
                + "<tr><th>Command</th><th>What it does</th></tr>"
                + "<tr><td><b>Hide Selected Cards</b></td><td>Hides every selected card.</td></tr>"
                + "<tr><td><b>Reset Size of Selected Cards</b></td><td>Puts every selected card back to its default size.</td></tr>"
                + "<tr><td><b>Reset All Card Sizes</b></td><td>Puts every card back to its default size.</td></tr>"
                + "<tr><td><b>Reset Card Layout</b></td><td>Clears this card's size and its stack (under <b>Device</b>).</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>While you drag, a picture of the card follows the pointer, and the other cards stay put. Dragging never stacks cards.</li>"
                + "<li>A box you drag selects every card it touches. Touching part of a stack selects the whole stack.</li>"
                + "<li>Dragging a box doesn't scroll the page. Use the wheel or the scroll bar, or move the box to the top or bottom edge.</li>"
                + "<li>Only cards of the same kind stack: inputs with inputs, outputs with outputs. Click a stacked card to bring it to the top.</li>"
                + "<li>A card has a smallest and a largest size. Cards in a stack share one size.</li>"
                + "<li><b>Reset All Card Sizes</b> is also in Options. It changes only sizes: stacks, order and hidden cards stay. <a href=\"show:option/Reset card sizes\">Show me ›</a></li>"
                + "<li>Unplugged and hidden cards keep their places. If a stick's name changes, its card keeps the same place.</li>"
                + "<li>When you delete a device, its place goes too.</li>"
                + "<li><b>Undo</b> (<b>Ctrl+Z</b>) puts back a move, a size, a stack or a layout change.</li>"
                + "</ul>",
            related: ["home-devices-home", "home-devices-card-menu", "home-devices-hidden-cards"]
        },
        {
            id: "home-devices-card-menu",
            section: "Home",
            title: "Card menus",
            body: "<p>Right-click a card to see every command for that device. Right-clicking a card also selects it. If several cards are selected, they stay selected, so a command can act on all of them.</p>"
                + "<h4>What you see</h4>"
                + "<table>"
                + "<tr><th>Part of the menu</th><th>What it holds</th></tr>"
                + "<tr><td>Beside the title</td><td><b>Undo</b> and <b>Redo</b>, for changes to the cards.</td></tr>"
                + "<tr><td>At the top</td><td><b>Open Device Bindings</b> (<b>Output View</b> on an output card), <b>Device Mapping Editor</b> and <b>Hide Card</b>.</td></tr>"
                + "<tr><td><b>Module</b></td><td><b>Module Setup…</b> (<b>Xbox Setup…</b> on the Xbox card), <b>Auto Mapping Tool</b> and <b>Calibration</b>.</td></tr>"
                + "<tr><td><b>View</b></td><td><b>vJoy Viewer</b>, <b>Device Information</b> and <b>Search this device</b>.</td></tr>"
                + "<tr><td><b>Cards</b></td><td>Stacking, hiding and sizes (see <a href=\"topic:home-devices-arrange-cards\">Arrange and resize cards</a>).</td></tr>"
                + "<tr><td><b>Device</b></td><td>The device's setup, pictures and files (below).</td></tr>"
                + "</table>"
                + "<p>The <b>Device</b> part holds:</p>"
                + "<ul>"
                + "<li><b>Start Fresh…</b>: sets up a device whose module file is damaged.</li>"
                + "<li><b>Copy Setup to Another Stick…</b>, <b>Swap with Another Stick…</b> and <b>Change vJoy Output…</b>: open the <b>Device Library</b> on that stick.</li>"
                + "<li><b>Add Image…</b>, <b>Change Image…</b> and <b>Remove Image</b>: the card's picture (see below).</li>"
                + "<li><b>Export Device…</b> and <b>Import Device…</b>: share a device (see <a href=\"topic:home-devices-device-pack\">Share a device</a>).</li>"
                + "<li><b>Reset Card Layout</b>: clears the card's size and its stack.</li>"
                + "<li><b>Delete Device</b>: see <a href=\"topic:home-devices-delete-device\">Delete a device</a>.</li>"
                + "</ul>"
                + "<p>Each card shows only the items that apply to it. A stick's card has them all. The others leave these out:</p>"
                + "<table>"
                + "<tr><th>Card</th><th>Left out</th></tr>"
                + "<tr><td>vJoy</td><td>Calibration, the stick items, the picture items, Delete Device</td></tr>"
                + "<tr><td>Xbox</td><td>Module Setup (it has Xbox Setup instead), Auto Mapping Tool, Calibration, vJoy Viewer, Device Information, the stick items, the picture items, Delete Device</td></tr>"
                + "<tr><td>Keyboard, OSC</td><td>Auto Mapping Tool, Calibration, Device Information, the stick items</td></tr>"
                + "<tr><td>Logical Device</td><td>Module Setup, Auto Mapping Tool, Calibration, Device Information, the stick items</td></tr>"
                + "</table>"
                + "<p>The stick items are Copy Setup to Another Stick…, Swap with Another Stick… and Change vJoy Output…. Start Fresh shows only for a damaged module file.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>To give a card a picture, right-click it and choose <b>Add Image…</b> (under <b>Device</b>).</li>"
                + "<li>To change it later, choose <b>Change Image…</b>. To take it off, choose <b>Remove Image</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Remove Image doesn't ask. Press <b>Ctrl+Z</b> on Home, or use <b>Tools › History</b> <a href=\"open:tools.history\">Open ›</a>, to get the picture back.</li>"
                + "<li>On a stick, the Keyboard or OSC, the picture is the <b>device image</b>. You can also set it in the <b>Device Image</b> box in Module Setup.</li>"
                + "<li>The device image shows on the card, in Module Setup and in the Device Library. It shows ahead of the picture made from the device map's background.</li>"
                + "<li>The device image is not part of the device map.</li>"
                + "<li>vJoy and Xbox cards can't have a picture.</li>"
                + "</ul>",
            related: ["home-devices-home", "home-devices-delete-device", "home-devices-input-modules", "getting-started-menus"]
        },
        {
            id: "home-devices-hidden-cards",
            section: "Home",
            title: "Hide and unhide cards",
            body: "<p>Hiding a card only takes it off Home. Windows and games still see the device; to hide it from games, use <a href=\"topic:tools-hidhide\">HidHide</a>.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>To hide a card, right-click it and choose <b>Hide Card</b>. To hide several, select them and choose <b>Hide Selected Cards</b>.</li>"
                + "<li>To bring one back, right-click empty space on Home and open <b>Hidden Cards</b>. Click the card you want back.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li><b>Unhide All Cards</b> in the same menu brings them all back.</li></ul>",
            related: ["home-devices-home", "tools-hidhide"]
        },
        {
            id: "home-devices-delete-device",
            section: "Home",
            title: "Delete a device",
            body: "<p><b>Delete Device</b> removes a device's module file, its pictures and its actions in every mode. A copy is kept first, so you can get it back.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Stop the profile. Delete Device is refused while the profile runs.</li>"
                + "<li>Right-click the card and choose <b>Delete Device</b> (under <b>Device</b>).</li>"
                + "<li>A window lists what will be removed. Choose <b>Continue</b>.</li>"
                + "<li>Choose the red <b>Delete Device</b> to confirm. <b>Cancel</b> or <b>Esc</b> keeps the device.</li>"
                + "<li>Save the profile. Its actions were removed from the open profile, so it now has unsaved changes.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>An autosave of the device is always kept in the <b>Device Library</b> first, marked <b>Deleted</b>. If it can't be saved, nothing is deleted.</li>"
                + "<li>The autosave holds the module file, the pictures and the actions in every mode. See <a href=\"topic:home-devices-backups\">Deleted devices and backups</a>.</li>"
                + "<li>The device's Device Bindings page, Device Mapping Editor and Module Setup close without asking.</li>"
                + "<li>A device still plugged in keeps its card, without a module. The card of an unplugged device goes.</li>"
                + "<li>A module file another device uses stays; only this device's actions go. The last message says what was kept.</li>"
                + "</ul>",
            related: ["home-devices-backups", "home-devices-card-menu"]
        },
        {
            id: "home-devices-backups",
            section: "Home",
            title: "Deleted devices and backups",
            body: "<p>Delete Device, Delete File, an import and Start Fresh each keep a copy first. You can get your setup back from it.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li><b>Delete Device</b> keeps an autosave of the stick in the <b>Device Library</b> (see <a href=\"topic:home-devices-delete-device\">Delete a device</a>).</li>"
                + "<li><b>Delete File</b> in Module Setup asks first and keeps an autosave of the module file in the Device Library. If it can't keep one, nothing is deleted.</li>"
                + "<li>An import over an existing device keeps the old module file in an \"imported\" folder inside the device folder.</li>"
                + "<li><b>Start Fresh…</b> moves a damaged module file aside and keeps it as a copy.</li>"
                + "</ul>"
                + "<h4>How to</h4>"
                + "<p>To put a deleted stick's setup on another stick:</p>"
                + "<ol>"
                + "<li>Choose <b>Tools › Device Setup › Device Library…</b> <a href=\"open:tools.deviceLibrary\">Open ›</a>.</li>"
                + "<li>Pick the stick's autosave.</li>"
                + "<li>Choose <b>Copy to Another Stick…</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Delete File keeps the device's pictures.</li>"
                + "<li>The Device Library keeps the newest autosaves for each stick and drops older ones. <b>Keep This Autosave</b> makes one yours, so it is never dropped.</li>"
                + "<li>You can also export a saved setup as a device file and import it in <b>Tools › Device Setup › Export / Import Device</b> <a href=\"open:tools.devicePack\">Open ›</a>.</li>"
                + "</ul>",
            related: ["home-devices-delete-device", "home-devices-module-files", "home-devices-device-pack"]
        },

        {
            id: "home-devices-identical",
            section: "Devices",
            title: "Identical devices",
            body: "<p>Two devices of the same make each get a name of their own. Each then has its own module file, card, device map and calibration.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>The first one keeps the plain name. The second is called \"&lt;name&gt; (2)\", the third \"&lt;name&gt; (3)\".</li>"
                + "<li>Each name stays with its device, whichever port it uses, in every session.</li>"
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
            body: "<p>Unplugging a stick is safe, even while the profile runs.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Its buttons are released, its hats centered and its axes read as centered, as if you had let go.</li>"
                + "<li>Its actions stay in the profile, and its card stays on Home.</li>"
                + "<li>Module Setup keeps your changes on screen, but <b>Save Module</b> is refused until you plug the stick in again.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When the stick is back, Save Module works, with your changes still on screen.</li>"
                + "<li>Keyboard, OSC and Xbox setups can be saved at any time.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "getting-started-device-missing", "getting-started-what-stop-releases"]
        },
        {
            id: "home-devices-vjoy-left-out",
            section: "Devices",
            title: "vJoy devices left out at start",
            body: "<p>A vJoy device with a setup problem is left out, and the program starts without it. The other vJoy devices work.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Once the main window is up, a message names each left-out device, says why, and how to fix it.</li>"
                + "<li>It shows again only when that changes, for example when a device is plugged in.</li>"
                + "</ul>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Fix the vJoy setup as the message says.</li>"
                + "<li>Restart the program.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A vJoy device is left out when Windows doesn't list it, or when it uses 8-way (discrete) hats.</li>"
                + "<li>It is also left out when two vJoy devices have the same number of axes, buttons and hats, so the program can't tell them apart.</li>"
                + "<li><b>Device Information</b> <a href=\"open:tools.deviceInfo\">Open ›</a> still lists a left-out device, marked \"left out (see message)\".</li>"
                + "<li>A vJoy device another program holds shows \"In use by another program\" on its card. The program tells you once per Run and tries again every 3 seconds.</li>"
                + "</ul>",
            related: ["getting-started-nothing-reaches-vjoy", "home-devices-vjoy-output", "tools-device-information"]
        },
        {
            id: "home-devices-record-input",
            section: "Devices",
            title: "Record an input by pressing it",
            body: "<p>Some pages have a red record button, for example <b>Add Key</b> on the Keyboard page or <b>Record Inputs</b> in a macro or condition. It lets you pick an input by pressing it.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Click the record button. The program waits for your input.</li>"
                + "<li>Press the button or key, move the axis, or push the hat.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>When you record one input, it stops at the first press.</li>"
                + "<li>When you record several, it stops at the first release.</li>"
                + "<li>An axis counts only after a big enough move. A hat counts only when pushed off center.</li>"
                + "<li>The Logical Device and the program's own virtual buttons are ignored.</li>"
                + "<li>To cancel, hold <b>Esc</b> for 1 second. A short tap does not cancel.</li>"
                + "</ul>",
            related: ["device-bindings-actions-keyboard-page", "device-bindings-actions-macro", "device-bindings-actions-condition"]
        },

        {
            id: "home-devices-input-modules",
            section: "Modules",
            title: "Set up an input module",
            body: "<p>An input module tells the program which controls on a device you use. Only the ticked controls reach your actions, the viewers and the Auto Mapping Tool.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the card and choose <b>Module Setup…</b> (under <b>Module</b>).</li>"
                + "<li>Press a control on the device to tick it, or tick it yourself. Untick a control you don't use.</li>"
                + "<li>Give a control a <b>Friendly name</b> if you like.</li>"
                + "<li>Choose <b>Save Module</b> to keep your changes, or <b>Cancel</b> to drop them.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Module Setup also opens from <b>Tools › Device Setup › Input Module Setup</b>. <a href=\"open:tools.configureInput\">Open ›</a></li>"
                + "<li><b>Undo</b> and <b>Redo</b> (<b>Ctrl+Z</b>, <b>Ctrl+Y</b>) step through the ticks and names, up to 100 steps, until you open another device.</li>"
                + "<li>A friendly name is kept only for a ticked control.</li>"
                + "<li>If you have unsaved changes, Cancel or closing the window asks first. So does closing the program.</li>"
                + "<li><b>Esc</b> and <b>Enter</b> do nothing in Module Setup, because sticks can send them.</li>"
                + "<li>A module saved while the profile runs applies at once.</li>"
                + "<li>Save Module is refused while the stick is unplugged (see <a href=\"topic:home-devices-unplugged\">When a device is unplugged</a>).</li>"
                + "<li>A stick's calibration is kept in its input module (see <a href=\"topic:tools-calibration\">Calibrate axes</a>).</li>"
                + "<li><b>Keyboard</b> is an input module too:<ul>"
                + "<li>Until you save it, every key counts as ticked.</li>"
                + "<li>Press a key that isn't listed to add it, ticked.</li>"
                + "<li>Key actions run only for ticked keys.</li>"
                + "<li>Your typing in Windows and games is never affected.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["home-devices-vjoy-output", "home-devices-module-files", "tools-calibration", "getting-started-key-does-not-fire", "home-devices-xbox-input"]
        },
        {
            id: "home-devices-xbox-input",
            section: "Modules",
            title: "Use an Xbox pad as an input",
            body: "<p>A real Xbox pad plugged into this PC is an input device, like a stick. It has its own card and input module.</p>"
                + "<h4>What you see</h4>"
                + "<table>"
                + "<tr><th>Control</th><th>Numbers</th></tr>"
                + "<tr><td>Axes</td><td>1 left stick left/right, 2 left stick up/down, 4 right stick left/right, 5 right stick up/down, 7 left trigger, 8 right trigger</td></tr>"
                + "<tr><td>Buttons</td><td>1 A, 2 B, 3 X, 4 Y, 5 LB, 6 RB, 7 View, 8 Menu, 9 left stick click, 10 right stick click</td></tr>"
                + "<tr><td>Hat 1</td><td>The D-pad</td></tr>"
                + "</table>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Each trigger is its own axis.</li>"
                + "<li>The <b>Xbox</b> button and the <b>Share</b> button aren't available: the program doesn't receive them.</li>"
                + "<li>If a pad's Xbox connection stops answering, the pad can switch to an older layout with other numbers. The program treats this like unplugging and plugging the pad back in.</li>"
                + "<li>A running profile then does what <b>Device change behavior</b> in Options says. <a href=\"show:option/Device change behavior\">Show me ›</a></li>"
                + "<li>The system log and the Trace tab say the pad <b>changed layout</b>, with its axes and buttons before and after.</li>"
                + "<li>This topic is about a pad you hold. The program's own Xbox controller is an output; see <a href=\"topic:home-devices-xbox-output\">Xbox output module</a>.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "home-devices-xbox-output"]
        },
        {
            id: "home-devices-vjoy-output",
            section: "Modules",
            title: "Set up a vJoy output module",
            body: "<p>Each vJoy device has an output module. Only the outputs ticked there are sent to vJoy.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the vJoy card and choose <b>Module Setup…</b> (under <b>Module</b>).</li>"
                + "<li>Tick the axes, buttons and hats you will use.</li>"
                + "<li>Choose <b>Save Module</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>It also opens from <b>Tools › Device Setup › Output Module Setup</b>. <a href=\"open:tools.configureOutput\">Open ›</a></li>"
                + "<li>Saving an output module also saves the profile, if the profile has a file. If it has unfinished actions, it isn't saved and the window tells you.</li>"
                + "<li>The vJoy driver sets the most a device can have. The output module sets what the program may use.</li>"
                + "<li>An action that sends to an output that isn't ticked sends nothing. It is kept and marked <b>(not claimed)</b>; tick the output to make it work.</li>"
                + "<li>A module saved while the profile runs applies at once.</li>"
                + "<li>A profile with Map to vJoy actions opens on a PC without vJoy, and keeps those actions.</li>"
                + "<li>A vJoy device set to <b>Input</b> under <b>vJoy Behavior</b> in <b>Profile Settings</b> (its <b>vJoy</b> section) is listed with your sticks. <a href=\"open:tools.profileSettings\">Open ›</a></li>"
                + "<li>Such a device is not offered under <b>vJoy Initial Values</b>.</li>"
                + "</ul>",
            related: ["home-devices-input-modules", "home-devices-xbox-output", "home-devices-vjoy-left-out", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "home-devices-xbox-output",
            section: "Modules",
            title: "Xbox output module",
            body: "<p>The program's Xbox pads are virtual Xbox 360 pads from the <b>ViGEmBus</b> driver. Each pad passes every control straight to the driver, so there is nothing to tick. One Xbox card on Home stands for all of them.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>To set how many pads are on, right-click the Xbox card and choose <b>Xbox Setup…</b>.</li>"
                + "<li>Set the <b>Number of Xbox pads</b>, 1 to 4, and choose <b>OK</b>. <b>Cancel</b> leaves it as it was.</li>"
                + "<li>To send to a pad, choose <b>Add Action</b> on an input's row on the Device Bindings page.</li>"
                + "<li>Choose <b>Map to Xbox</b>.</li>"
                + "</ol>"
                + "<h4>What you see</h4>"
                + "<p>Double-click the Xbox card for its <b>Output View</b>. <a href=\"open:view.xboxOutput\">Open ›</a> It has:</p>"
                + "<ul>"
                + "<li>One section for each pad that is on and has a Map to Xbox action. Click a heading to fold it.</li>"
                + "<li>The section heading names the pad, the devices that drive it and how many controls are bound.</li>"
                + "<li>In each section: the pad's picture, lit from what is sent to it, then the <b>Mapped axes</b> and <b>Mapped buttons</b> rows.</li>"
                + "<li>Then the pad's controls, Left Stick X to DPad. Under each, a line for each input that sends to it, such as <i>VKBsim Gladiator EVO R · Button 1</i>.</li>"
                + "<li>At the top, <b>Find</b>, the type filter and <b>Show only bound controls</b>. They narrow every pad's list.</li>"
                + "<li>While the profile runs, sticks and triggers show a live bar, and buttons and the D-pad a lit dot.</li>"
                + "<li>When the ViGEmBus driver is missing, a red line at the top says so, with <b>Open Xbox Setup</b>.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Pad 1 is <b>Xbox 360 Controller</b>; pads 2-4 are Xbox 360 2, Xbox 360 3 and Xbox 360 4.</li>"
                + "<li>If you lower the number while a pad you turn off still has Map to Xbox actions, Xbox Setup lists them and asks first.<ul>"
                + "<li><b>Yes</b> keeps them, marked with a red ⚠, until you move them to a pad that is on or raise the number again.</li>"
                + "</ul></li>"
                + "<li>Xbox Setup checks the driver: <b>ViGEmBus driver found</b> with its version, or what is wrong and what to do.</li>"
                + "<li>In Xbox Setup, <b>Open Drivers</b> opens <b>Tools › Drivers</b>, which installs the driver (see <a href=\"topic:tools-drivers\">Drivers</a>). <b>Test ViGEmBus</b> opens Windows Game Controllers.</li>"
                + "<li>You can also send to a pad from a Logical Device control: right-click it and choose <b>Add Action</b>.</li>"
                + "<li>A pad appears when a Map to Xbox action first sends to it while the profile runs. It goes when the profile stops. A pad that is off in Xbox Setup is never sent to.</li>"
                + "<li>Each section opens the first time, and the program remembers which ones you fold. With no pad bound yet, the page says so.</li>"
                + "<li>Use the arrow beside a control to show or hide its input lines. The type filter offers Sticks, Triggers, Buttons and D-Pad.</li>"
                + "<li><b>Show only bound controls</b> is ticked at first, and the program remembers your choice.</li>"
                + "<li><b>Appearance…</b> on the bar under the toolbar changes how the list looks; its <b>Live</b> section turns the bars and dots on or off.</li>"
                + "<li>The section headings look like the list's group rows. <b>Group</b> in Appearance changes them; <b>Space between groups</b> sets the space between pads.</li>"
                + "</ul>",
            related: ["device-bindings-actions-map-to-xbox", "home-devices-vjoy-output", "tools-viewers", "getting-started-xbox-does-nothing"]
        },
        {
            id: "home-devices-module-files",
            section: "Modules",
            title: "Module files",
            body: "<p>Each device has its own module file, kept apart from your profiles. It holds the device's ticked controls, friendly names, picture, device map, Appearance and calibration.</p>"
                + "<h4>What you see</h4>"
                + "<p>In Module Setup, the <b>Module File</b> part shows the <b>Device folder</b>. It reads \"(not saved yet)\" until the file exists. It offers:</p>"
                + "<table>"
                + "<tr><th>Control</th><th>What it does</th></tr>"
                + "<tr><td><b>Import from</b></td><td>Copies another file into this device's file (see <a href=\"topic:home-devices-import-module-file\">Import a module file</a>).</td></tr>"
                + "<tr><td><b>Browse for File</b></td><td>Picks a file to import from anywhere.</td></tr>"
                + "<tr><td><b>Open Modules Folder</b></td><td>Opens the folder that holds every device folder.</td></tr>"
                + "<tr><td><b>Delete File</b></td><td>Asks first; confirm with the red <b>Delete File</b>. An autosave is kept (see <a href=\"topic:home-devices-backups\">Deleted devices and backups</a>).</td></tr>"
                + "</table>"
                + "<p>A message line under them says what an import, its Undo or Delete File did. It is plain when it worked and red when it failed.</p>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>For an input device, the <b>Device Image</b> box sets the device image: <b>Add Image…</b> (or <b>Change Image…</b>) and <b>Remove Image</b>.</li>"
                + "<li>The device image shows ahead of the picture made from the device map's background. Nothing changes until you choose <b>Save Module</b>.</li>"
                + "<li>For a vJoy output, <b>Import Image…</b> adds a picture at the bottom of the device map's background.</li>"
                + "<li>When the stick still opens a file of another name, a note says so. Import that file to copy it here.</li>"
                + "<li>Browse for File opens in the folder you last picked a module file from. Add Image… and Import Image… open in the folder you last picked a picture from.</li>"
                + "</ul>",
            related: ["home-devices-import-module-file", "home-devices-damaged-file", "getting-started-saved-where", "home-devices-device-pack"]
        },
        {
            id: "home-devices-import-module-file",
            section: "Modules",
            title: "Import a module file",
            body: "<p><b>Import from</b> copies a module file you choose into this device's file. The file you choose stays where it is.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In Module Setup, open <b>Module File</b>.</li>"
                + "<li>Choose a file under <b>Import from</b>, or choose <b>Browse for File</b>. With unsaved ticks, it asks first.</li>"
                + "<li>Read the message line under Module File: it says what was imported.</li>"
                + "<li>To take the import back, click the message's <b>Undo</b> link. The previous file comes back.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>The Undo link lasts until the next message, until you close the message with its ×, or until you close the window.</li>"
                + "<li>Only the controls this device has are kept. The message names the ones left out.</li>"
                + "<li>This device's picture and your actions stay as they are.</li>"
                + "<li>The previous file is kept in the \"imported\" folder inside the device folder.</li>"
                + "<li>A failed import or Undo shows its message in red.</li>"
                + "<li>An import is refused for:<ul>"
                + "<li>A file that can't be read, or isn't a module file.</li>"
                + "<li>A vJoy file onto a stick, or a stick file onto a vJoy.</li>"
                + "<li>A device that isn't connected.</li>"
                + "<li>A current file that can't be read.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["home-devices-module-files", "home-devices-backups"]
        },
        {
            id: "home-devices-damaged-file",
            section: "Modules",
            title: "Fix a damaged module file",
            body: "<p>A module file that can't be read is never overwritten, so nothing in it is lost. Until you fix it, the device's inputs are blocked.</p>"
                + "<h4>What you see</h4>"
                + "<ul>"
                + "<li>Its card says \"Module file damaged – inputs blocked\" in red.</li>"
                + "<li>Every save into the file is refused: Module Setup, the Device Mapping Editor and Export / Import Device.</li>"
                + "</ul>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>Right-click the card and choose <b>Start Fresh…</b> (under <b>Device</b>). It asks first.</li>"
                + "<li>Set the device up again in Module Setup.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul><li>Start Fresh keeps the damaged file as a copy, with \"bad\" and the date added to its name. If it can't move the file, it says so.</li></ul>",
            related: ["home-devices-module-files", "home-devices-card-text", "home-devices-backups"]
        },
        {
            id: "home-devices-device-pack",
            section: "Modules",
            title: "Share a device with Export / Import Device",
            body: "<p><b>Tools › Device Setup › Export / Import Device</b> <a href=\"open:tools.devicePack\">Open ›</a> saves a copy of a device's setup as one device file (.gmap). Someone else can import it. The Device Library can share the same file; see <a href=\"topic:device-library-share-which\">Which way to share?</a></p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>On the <b>Export</b> tab, pick the device.</li>"
                + "<li>Under <b>Wires in these modes</b>, untick the modes to leave out. These are the device's actions in each mode.</li>"
                + "<li>Fill in <b>Made by</b> and <b>Note</b>. Whoever imports the file sees them.</li>"
                + "<li>Choose <b>Export…</b> and pick where to save it.</li>"
                + "<li>To find the file later, choose <b>Show Folder</b>.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A card's <b>Export Device…</b> opens this window on the Export tab, with that device picked. Otherwise it opens on the first device that can be exported.</li>"
                + "<li>The file holds the device folder (its module file and pictures) and its actions in the ticked modes.</li>"
                + "<li>It also holds the output modules those actions send to, with their pictures.</li>"
                + "<li>The file is written in the background. The window stays usable and shows <b>Exporting…</b>; one export runs at a time.</li>"
                + "<li>The file chooser opens in the folder you last used for a device file.</li>"
                + "<li>A device with no module file yet can't be exported. One whose file can't be read shows \"(file damaged)\".</li>"
                + "<li>Save the file outside the modules folder. A name without .gmap gets .gmap added.</li>"
                + "</ul>",
            related: ["home-devices-device-pack-import", "home-devices-module-files", "home-devices-backups", "device-library-share-which"]
        },
        {
            id: "home-devices-device-pack-import",
            section: "Modules",
            title: "Import a device file",
            body: "<p>Import brings a device file (.gmap) in, either as a new device or onto one of your devices.</p>"
                + "<h4>How to</h4>"
                + "<ol>"
                + "<li>In <b>Export / Import Device</b> <a href=\"open:tools.devicePack\">Open ›</a>, open the <b>Import</b> tab and choose <b>Choose File…</b>.</li>"
                + "<li>Choose <b>As a new device</b>, or <b>Onto an existing device</b> and pick the device under <b>Put it on</b>.</li>"
                + "<li>Tick the parts to bring in.</li>"
                + "<li>Choose <b>Import</b>, read the warning, then confirm.</li>"
                + "<li>Read the message line: it says what was imported, with a <b>Restore Import</b> link.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>A card's <b>Import Device…</b> opens the Import tab with that device suggested.</li>"
                + "<li>As a new device makes a new device folder from the file. A name already taken gets \"(2)\".</li>"
                + "<li>If the file's device isn't here yet, As a new device is already selected.</li>"
                + "<li>Onto an existing device:<ul>"
                + "<li>Import adds the file's checked controls and never unchecks one of yours.</li>"
                + "<li>Each ticked mode under <b>Wires</b> replaces the device's actions in that mode.</li>"
                + "<li>Other parts replace only what they hold. Other modes and devices are left alone.</li>"
                + "<li><b>Device image</b> (ticked at first) brings the file's device image. Untick it to keep yours.</li>"
                + "</ul></li>"
                + "<li>Missing modes are made under their parent, or under Default when the parent isn't here.</li>"
                + "<li>Tick <b>Create the missing Logical Device inputs</b> to add the ones the file's actions need.</li>"
                + "<li>An import is refused for:<ul>"
                + "<li>A stick's file onto a vJoy, or a vJoy's file onto a stick.</li>"
                + "<li>A damaged module file (use <b>Start Fresh…</b> first).</li>"
                + "<li>A file made by a newer version of the program. The message names that version; update the program to import it.</li>"
                + "<li>A file that unpacks to more than 64 MB. The message gives its size.</li>"
                + "</ul></li>"
                + "<li>A file that can't be read shows the reason. The log has the details.</li>"
                + "<li>If an import fails partway, everything it did is undone, and the message says so.</li>"
                + "<li><b>Restore Import</b> (the button or the link) puts the device back as it was before the import.<ul>"
                + "<li>Onto an existing device, it restores the files, pictures and actions, and removes the modes and inputs the import added.</li>"
                + "<li>As a new device, it removes the new device.</li>"
                + "<li>With another profile open, only the files are restored.</li>"
                + "<li>It lasts until you import the file again, open another file, or close the window.</li>"
                + "</ul></li>"
                + "</ul>",
            related: ["home-devices-device-pack", "home-devices-damaged-file", "device-library-import"]
        },

        {
            id: "home-devices-q-card-missing",
            section: "Common questions",
            title: "Where did my device's card go?",
            body: "<p>It may be hidden. Right-click empty space on Home and open <b>Hidden Cards</b>. See <a href=\"topic:home-devices-hidden-cards\">Hide and unhide cards</a>.</p>"
                + "<p>A device without a module shows only when <b>Show devices without a module</b> is on. See <a href=\"topic:home-devices-home\">Home and its cards</a>.</p>",
            related: ["home-devices-hidden-cards", "getting-started-device-missing"]
        },
        {
            id: "home-devices-q-input-missing",
            section: "Common questions",
            title: "Why doesn't an input show on the Device Bindings page?",
            body: "<p>Only the inputs ticked in the device's input module show. Tick it in Module Setup. See <a href=\"topic:home-devices-input-modules\">Set up an input module</a>.</p>",
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
            body: "<p>That output isn't ticked in its output module, so nothing is sent to it. See <a href=\"topic:home-devices-vjoy-output\">Set up a vJoy output module</a>.</p>",
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
