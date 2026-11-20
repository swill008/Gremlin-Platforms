"""The release carries the installer under the R2 and the R1 name (OT-6).

Installed R1 1.0.39 copies download only Gremlin-Platforms-R1-<version>-Setup.exe.
"""

import pathlib

_V = "${{ steps.version.outputs.version }}"
_ROOT = pathlib.Path(__file__).parents[2]


def test_workflow_attaches_both_setup_names() -> None:
    text = (_ROOT / ".github" / "workflows" / "release-exe.yml").read_text("utf-8")
    r2 = f"dist/Gremlin-Platforms-R2-{_V}-Setup.exe"
    r1 = f"dist/Gremlin-Platforms-R1-{_V}-Setup.exe"
    assert text.count(r2) == 2 and text.count(r1) == 2  # artifact + release
    assert "ONE-TIME (tracker OT-6)" in text
    assert rf"Copy-Item dist\Gremlin-Platforms-R2-{_V}-Setup.exe" in text
    assert "tag_name: Gremlin-Platforms-R2-" in text
    assert rf"dist\Gremlin-Platforms-R2-{_V}.zip" in text
