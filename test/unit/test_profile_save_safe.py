# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""Saving a profile is safe (G-PROFATOMIC).

The profile was written over in place, so a crash or power cut mid-save
could leave it broken. It now goes through the module files' writer (a
temporary file, then a swap) and the file is the same as before: UTF-8 with
a BOM and its line ends kept.
"""

from __future__ import annotations

import pathlib

import pytest

from gremlin import shared_state
from gremlin.profile import Profile


@pytest.fixture
def profile() -> Profile:
    made = Profile()
    shared_state.current_profile = made
    yield made
    shared_state.current_profile = None


def test_the_file_is_as_before(profile: Profile, tmp_path: pathlib.Path) -> None:
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    data = path.read_bytes()
    assert data.startswith(b"\xef\xbb\xbf<?xml")
    assert b"\r\n" not in data
    assert data.decode("utf-8-sig") == profile._xml_text()
    assert not (tmp_path / "p.xml.tmp").exists()


def test_a_failed_save_leaves_the_old_profile_whole(
    profile: Profile, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "p.xml"
    profile.to_xml(path)
    before = path.read_bytes()
    profile.modes.add_mode("Combat")
    real = pathlib.Path.write_text

    def crash(self: pathlib.Path, *args: object, **kwargs: object) -> int:
        if self.name.endswith(".tmp"):
            real(self, "<profile half-writ", encoding="utf-8")
            raise RuntimeError("power cut")
        return real(self, *args, **kwargs)

    monkeypatch.setattr(pathlib.Path, "write_text", crash)
    with pytest.raises(RuntimeError):
        profile.to_xml(path)
    assert path.read_bytes() == before
