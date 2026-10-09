// -*- coding: utf-8; -*-
// SPDX-License-Identifier: GPL-3.0-only

// Help chapter: Modes.

.pragma library

var chapter = { id: "modes", title: "Modes" }

function _good(items) {
    return "<h4>Good to know</h4><ul><li>" + items.join("</li><li>") + "</li></ul>"
}

// Where Manage Modes is: the mode bar button and the Tools menu item.
var _manageModes = "<b>Manage Modes</b> <a href=\"show:modebar/Manage Modes\">Show me ›</a>"

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
                + "</ul>"
                + _good([
                    "A profile always has at least one mode.",
                    "When Change Mode goes back to a mode already in the list of modes you came through, <b>Mode cycle resolution</b> <a href=\"show:option/Mode cycle resolution\">Show me ›</a> decides where you land: <b>Oldest</b> or <b>Newest</b>."
                ]),
            related: ["modes-manage", "modes-mode-box", "configuration-actions-change-mode", "options-profile-profile-settings"]
        },
        {
            id: "modes-manage",
            section: "Modes",
            title: "Add, rename and remove modes",
            body: "<p>" + _manageModes + " is where you add, rename and remove modes and set their parents.</p>"
                + "<ol>"
                + "<li>Choose " + _manageModes + " on the mode bar, or <b>Tools › Mapping › Manage Modes</b> <a href=\"show:menu/Tools/Mapping/Manage Modes\">Show me ›</a>.</li>"
                + "<li>Choose <b>Add Mode</b>, or the pencil beside a mode to rename it.</li>"
                + "<li>Set <b>Inherits from</b> to give a mode a parent. <b>(none)</b> makes it a top-level mode.</li>"
                + "</ol>"
                + _good([
                    "A name can't be blank or match another mode's name, ignoring capitals and spaces. A mode can change the capitals of its own name.",
                    "Modes are listed alphabetically, ignoring capitals.",
                    "A mode can inherit from any mode except itself and the modes under it.",
                    "Renaming a mode also updates the <b>Change Mode</b> actions and the <b>Startup Mode</b> that name it.",
                    "You can change modes while the profile runs. Renamed and deleted modes change at once; added modes and new parents take effect the next time it starts."
                ]),
            related: ["modes-delete", "modes-modes", "modes-mode-box"]
        },
        {
            id: "modes-delete",
            section: "Modes",
            title: "Delete a mode",
            body: "<p>Deleting a mode removes it and its bindings from the profile.</p>"
                + "<ol>"
                + "<li>Open " + _manageModes + ".</li>"
                + "<li>Choose the bin beside the mode.</li>"
                + "<li>The question \"Delete mode Combat?\" says how many bindings go with it. Choose the red <b>Delete Mode</b>.</li>"
                + "</ol>"
                + _good([
                    "Modes under it move up one level and keep their bindings.",
                    "If the <b>Startup Mode</b> named it, Startup Mode goes back to <b>Last Active</b>.",
                    "An action editor open in that mode closes, with a notice.",
                    "The last mode can't be deleted.",
                    "<b>Cancel</b> has the focus: <b>Enter</b> and <b>Esc</b> both cancel, so only a click on <b>Delete Mode</b> deletes.",
                    "To take a delete back, choose <b>Undo</b> (Undo Delete Mode) at the bottom of Manage Modes; see <a href=\"topic:modes-undo-delete\">Bring back a deleted mode</a>."
                ]),
            related: ["modes-undo-delete", "modes-manage", "options-profile-profile-settings"]
        },
        {
            id: "modes-undo-delete",
            section: "Modes",
            title: "Bring back a deleted mode",
            body: "<p>Undo Delete Mode is the <b>Undo</b> button at the bottom of " + _manageModes + ". It brings back the mode you deleted last. Choose it again to bring back the one before.</p>"
                + "<p>Beside it, \"Last change: Delete mode Combat\" names the mode it brings back. <b>Redo</b> stays greyed here.</p>"
                + "<p>The mode comes back with:</p>"
                + "<ul>"
                + "<li>its bindings,</li>"
                + "<li>its place in the list of parents,</li>"
                + "<li>the modes that moved up when it was deleted,</li>"
                + "<li>the <b>Startup Mode</b>, if it named the mode.</li>"
                + "</ul>"
                + _good([
                    "It works while the same profile is open. Pointing at <b>Undo</b> shows \"Undo Delete Mode\" and the mode it brings back.",
                    "If a mode can't come back, a notice says why."
                ]),
            related: ["modes-delete", "modes-manage"]
        },
        {
            id: "modes-mode-box",
            section: "Modes",
            title: "Choose the mode you edit and run",
            body: "<p>The <b>Mode</b> box <a href=\"show:modebar\">Show me ›</a>, on the mode bar under the toolbar, is the mode you edit and the mode that runs.</p>"
                + "<ul>"
                + "<li>While the profile is stopped, it picks the mode you edit and the mode <b>Run</b> starts in.</li>"
                + "<li>While the profile runs, it shows the mode that runs; picking another mode there switches the running profile to it.</li>"
                + "<li>Actions you add belong to the mode shown in the Mode box.</li>"
                + "</ul>"
                + _good([
                    "The mode a profile opens in when it is loaded is its <b>Startup Mode</b> (see <a href=\"topic:options-profile-profile-settings\">Profile Settings</a>).",
                    "An action editor with changes stays open when you pick another mode; its title says which mode it edits."
                ]),
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
            body: "<p>Yes, while the same profile is open: Undo Delete Mode, the <b>Undo</b> button in Manage Modes, brings it back with its bindings. See <a href=\"topic:modes-undo-delete\">Bring back a deleted mode</a>.</p>",
            related: ["modes-undo-delete"]
        },
        {
            id: "modes-q-cannot-delete",
            section: "Common questions",
            title: "Why can't I delete a mode?",
            body: "<p>It is the profile's only mode. A profile always has at least one; add another mode first. See <a href=\"topic:modes-delete\">Delete a mode</a>.</p>",
            related: ["modes-delete", "modes-manage"]
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
