"""01 S194: setup's uninstall removes the Start with Windows Run value."""

from __future__ import annotations

import pathlib
import re

_ISS = pathlib.Path(__file__).parents[2] / "installer" / "gremlin_platforms.iss"


def _iss() -> str:
    return _ISS.read_text(encoding="utf-8")


def test_uninstall_deletes_run_value() -> None:
    code = _iss().split("[Code]", 1)[1]
    m = re.search(
        r"procedure CurUninstallStepChanged\(.*?\)\s*;\s*begin(.*?)\nend;",
        code, re.S)
    assert m, "no CurUninstallStepChanged"
    body = m.group(1)
    assert "usUninstall" in body
    assert re.search(
        r"RegDeleteValue\(\s*HKCU\s*,\s*'Software\\Microsoft\\Windows\\"
        r"CurrentVersion\\Run'\s*,\s*'Gremlin-Platforms'\s*\)", body)


def test_install_writes_no_run_value() -> None:
    iss = _iss()
    assert "RegWriteStringValue" not in iss
    reg = re.search(r"\[Registry\](.*?)(?=\n\[)", iss, re.S)
    assert not reg or "CurrentVersion\Run" not in reg.group(1)


def test_per_user_install_so_hkcu_is_the_user() -> None:
    iss = _iss()
    assert "PrivilegesRequired=lowest" in iss
    assert "PrivilegesRequiredOverridesAllowed" not in iss
