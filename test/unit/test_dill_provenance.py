# -*- coding: utf-8; -*-

# SPDX-License-Identifier: GPL-3.0-only

"""The shipped DirectInput reader is upstream R16's dill2 (02 S139,
D-02-DILL2): its checksum matches dill/PROVENANCE.md."""

from __future__ import annotations

import hashlib
import pathlib

_ROOT = pathlib.Path(__file__).parents[2]
_SHA256 = "afa5373d3c57fa722ee60fc94faa9b3cff9404f60f3d5c09968f3577b6664948"


def test_shipped_reader_is_r16_dill2() -> None:
    data = (_ROOT / "dill" / "dill.dll").read_bytes()
    assert hashlib.sha256(data).hexdigest() == _SHA256
    assert b"DILL v2.0" in data or "DILL v2.0".encode("utf-16-le") in data


def test_provenance_note_names_the_same_checksum() -> None:
    note = (_ROOT / "dill" / "PROVENANCE.md").read_text(encoding="utf-8")
    assert _SHA256 in note
    assert "Release_16" in note
