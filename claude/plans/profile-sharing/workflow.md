# Profile sharing: workflow (draft, planning only, 2026-10-13)

User decisions so far (2026-10-13):
- Cloudflare Worker + R2 as the upload inbox (pending), GitHub as the permanent store ("all profiles are stored on github, the webservice is storage that we move to git hub"; "thats a good plan for now").
- Approved packages as GitHub Release files; the repo holds per-package description files + the catalogue (index.json); Cloudflare keeps a backup copy; the app reads the catalogue from GitHub Pages with Cloudflare as backup (recommended; confirm).
- One package format with a "what's inside" file at the top, owned by one piece of code and used by both Export/Import and Share/Install (recommended; confirm).
- Package = the profile + each device's setup (.gmap pieces) + the shared parts it uses, with a "match your devices" step on install ("yes, lets use this for the plan and workflow").

## A. Share (uploader, in the app)
1. Profile › Share Profile… on the open profile.
2. The app builds the package: the profile, each device it uses (input module, pictures, bindings via the existing .gmap pieces), the vJoy/Xbox output modules the bindings send to, Logical Device controls and OSC inputs/targets it uses.
3. Review screen ("What will be shared"): devices, modes, binding/action counts; flags: Run Command, scripts, sound files, Load Profile, personal paths (user folders) — each with keep / remove; optional files (sounds, scripts) with a tick to include.
4. Details: name, author (typed, no account), description, game/sim tags, licence note.
5. Upload -> Cloudflare function. Result: "Sent for review" + a reference number; the app remembers it so the user can see Pending / Approved / Declined (with reason).

## B. Review (owner)
1. Function checks: size, zip, layout, file types (no programs), contents file vs real files and checksums; per-IP and daily limits. Stores in pending.
2. Optional Discord notice to the owner's private channel (webhook kept in the function).
3. Owner's admin page (only the owner): contents, flags, the uploader's text; Approve / Decline (reason).
4. Approve: function publishes a GitHub Release file + the description file in the profiles repo, rebuilds index.json, keeps a backup copy in R2. Decline: kept for N days then deleted.
5. Take-down: remove the Release file + description; catalogue rebuilds; history keeps the record.

## C. Install (any user, in the app)
1. Profile › Browse Shared Profiles…: catalogue (from GitHub Pages, Cloudflare as backup), search by typing, filter by device/game/tags; detail shows contents and flags.
2. Download -> checksum check -> the same "what's inside" review as Import.
3. Match devices: each package device -> one of the user's devices (suggested by name/model), or Skip, or keep as not plugged in.
4. Checks on this PC: enough vJoy devices with the controls used, ViGEm if Xbox outputs are used, missing plugins; says what's missing (cannot fix drivers).
5. Run Command / scripts arrive switched off until the user turns them on (pending decision).
6. Import: as a new profile (name, "(2)" if taken), device setups through the existing Import Device path (re-keyed, vJoy renumbering, Logical Device controls created). Nothing overwrites the user's existing device setups without asking (pending decision).

## D. Export / Import (local file, same format)
- Export Profile Package… = steps A2-A4 saved to a file (no upload).
- Import Profile Package… = steps C2-C6 from a file.

## Open questions (to settle before the spec)
- Where existing device setups conflict on install: replace / keep mine / ask per device.
- Run Command and scripts on install: off until turned on (recommended) / refuse / as is.
- File type and words (glossary): e.g. ".gprofile", "profile package", "Share Profile…", "Browse Shared Profiles…".
- Uploader status lookup: by reference number only (no account).
- Licence wording for shared packages.

## Big picture update (user, 2026-10-13)
User: "I want a user to see profiles based on their own devices, if they have an evo R or L, then I want them to see all EVO R or L's ... pick or choose any of the profile, wire, color, images, maps macro settings etc ... a top list of the device, the picture and all the wires etc, with a select all, or individually select each piece to copy over to their profile, or use the entire profile."
- Proposed (not yet answered): the shared unit is the device profile (one device's setup); whole profiles are bundles of device profiles; the catalogue shows inside the Device Library as a "Shared" source; picking per piece and per mode, single inputs on opening a mode.

## Device matching (decided, user 2026-10-13)
User: "This can be a warning, so if you match by name, you can say it may not be compatible. the program can pass this information along with the profile so the data is present, but the user may choose to download a matched name, vs product id."
- Every device profile carries both the model codes (USB vendor + product id) and the device name.
- Browse shows exact matches (same vendor + product id) as matches; same-name-only matches are shown too, marked "may not be compatible"; the user may still pick either.
- Still to verify (scout): does the app record vendor/product ids today; do EVO R and EVO L report different ids.
- User 2026-10-13: "if the app does not at this time, we can make it a feature if we decide to execute this feature" — recording the model codes is part of the sharing feature if the app lacks it today (no separate build now).

## Browse All (decided, user 2026-10-13: "I agree to these recommendations")
User: "I also want a just browse all function, so people can see and compare what others are doing ... see any device, see all data, and even download the entire profile [the whole profile wont work, but pieces can]".
1. Two ways into one catalogue: Device Library › Shared (my devices, for installing) and Browse All Shared Profiles (any device, for ideas).
2. Browse All: everything read-only; download the whole package to disk; copy single pieces labelled "works on any device" (macros, curves, look, mode trees, OSC setups, Logical Device layouts) / "needs a matching input" (bindings, modes; re-pointed like Import Device) / "only for that model" (pictures, device maps; may-not-be-compatible warning).
3. Shared catalogue as a Search source ("Look in: Shared profiles"): later add-on.
4. Compare side by side: later add-on.
- Needs: each package's contents file carries a readable summary (bindings list, macro steps, modes, small picture) so Browse All shows everything without downloading the zip.
