# Release notes

Each version's notes live here as `<version>.md` (decision D-REL-NOTES-FILES),
e.g. `1.0.27.md`. The file starts with `## What's new in <version>`, then
`### New`, `### Changed` and `### Fixed` sections as needed.

A release needs its file. The release workflow
(`.github/workflows/release-exe.yml`) runs `tools/release_body.py <version>`
before building; it stops when the file for the version in `version.json` is
missing or doesn't start with that heading. The release text on GitHub is the
file followed by a "How to install" section. `test/unit/test_release_notes.py`
also fails when `version.json` names a version without a file here.
