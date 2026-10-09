// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Modes.

.pragma library

var chapter = { id: "modes", title: "Modes" }

function topics() {
    return [
        {
            id: "modes-modes",
            section: "Modes",
            title: "Modes",
            body: "<p>A mode is a set of actions. The same button can do different things in different modes.</p>"
                + "<ul>"
                + "<li>A mode can inherit from a parent: anything it does not map itself uses the parent's actions.</li>"
                + "<li>One mode runs at a time. The <b>Mode</b> box shows it (see <a href=\"topic:modes-mode-box\">Choose the mode you edit and run</a>).</li>"
                + "<li>The <b>Change Mode</b> action switches mode while the profile runs.</li>"
                + "<li>Modes are part of the profile; save the profile to keep them.</li>"
                + "</ul>",
            related: ["modes-manage", "modes-mode-box", "configuration-actions-change-mode", "options-profile-profile-settings"]
        },
        {
            id: "modes-manage",
            section: "Modes",
            title: "Add, rename and remove modes",
            body: "<p><b>Manage Modes</b> is where you add, rename and remove modes and set their parents.</p>"
                + "<ol>"
                + "<li>Choose <b>Manage Modes</b> on the toolbar, or <b>Tools › Mapping › Manage Modes</b>.</li>"
                + "<li>Add, rename or remove a mode.</li>"
                + "<li>Set <b>Inherits from</b> to give a mode a parent.</li>"
                + "</ol>"
                + "<h4>Good to know</h4>"
                + "<ul>"
                + "<li>Deleting a mode removes its actions too.</li>"
                + "<li><b>Undo Delete Mode</b> brings back the mode deleted last, with its actions, while the same profile is open.</li>"
                + "</ul>",
            related: ["modes-modes", "modes-mode-box"]
        },
        {
            id: "modes-mode-box",
            section: "Modes",
            title: "Choose the mode you edit and run",
            body: "<p>The <b>Mode</b> box, in the bar under the toolbar, is the mode you edit and the mode that runs.</p>"
                + "<ul>"
                + "<li>While the profile is stopped, it picks the mode you edit and the mode <b>Run</b> starts in.</li>"
                + "<li>While the profile runs, it shows the mode that runs; picking another mode there switches the running profile to it.</li>"
                + "<li>Actions you add belong to the mode shown in the Mode box.</li>"
                + "</ul>"
                + "<h4>Good to know</h4>"
                + "<ul><li>The mode a profile opens in when it is loaded is its <b>Startup Mode</b> (see <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>).</li></ul>",
            related: ["modes-modes", "getting-started-run", "options-profile-profile-settings"]
        },

        {
            id: "modes-q-button-does-nothing",
            section: "Common questions",
            title: "Why does a button do nothing in one mode?",
            body: "<p>Only the running mode's actions, and its parents', run. Check the mode in the <b>Mode</b> box and its parent. See <a href=\"topic:modes-modes\">Modes</a>.</p>",
            related: ["modes-modes", "getting-started-nothing-reaches-vjoy"]
        },
        {
            id: "modes-q-undo-delete",
            section: "Common questions",
            title: "I deleted a mode. Can I get it back?",
            body: "<p>Yes, while the same profile is open: <b>Undo Delete Mode</b> brings it back with its actions. See <a href=\"topic:modes-manage\">Add, rename and remove modes</a>.</p>",
            related: ["modes-manage"]
        },
        {
            id: "modes-q-start-mode",
            section: "Common questions",
            title: "How do I choose the mode a profile starts in?",
            body: "<p><b>Run</b> starts in the mode shown in the <b>Mode</b> box; loading a profile uses its <b>Startup Mode</b>. See <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>.</p>",
            related: ["modes-mode-box", "options-profile-profile-settings"]
        }
    ]
}
