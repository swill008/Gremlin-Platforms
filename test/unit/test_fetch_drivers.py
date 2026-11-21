# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""tools/fetch_drivers.py with a fake opener: nothing is downloaded (01 S188)."""

from __future__ import annotations

import hashlib
import importlib.util
import io
import pathlib
import sys
from collections.abc import Callable
from typing import IO

import pytest

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "fetch_drivers", _ROOT / "tools" / "fetch_drivers.py"
)
assert _spec is not None
assert _spec.loader is not None
fd = importlib.util.module_from_spec(_spec)
sys.modules["fetch_drivers"] = fd
_spec.loader.exec_module(fd)

DATA = b"driver installer bytes"


def _pin(data: bytes = DATA, sha: str | None = None, key: str = "vjoy") -> "fd.Pin":
    return fd.Pin(
        key, f"{key}.exe", f"https://example.invalid/{key}.exe", len(data),
        hashlib.sha256(data).hexdigest() if sha is None else sha,
    )


def _opener(
    data: bytes, calls: list[str] | None = None
) -> Callable[[str, float], IO[bytes]]:
    def opener(url: str, timeout: float) -> IO[bytes]:
        assert timeout > 0
        if calls is not None:
            calls.append(url)
        return io.BytesIO(data)
    return opener


def test_good_download_is_kept(tmp_path: pathlib.Path) -> None:
    pin = _pin()
    problems = fd.fetch_all(tmp_path, None, _opener(DATA), (pin,))
    assert problems == []
    assert (tmp_path / pin.file).read_bytes() == DATA
    assert not list(tmp_path.glob("*.part"))


def test_existing_good_file_is_not_downloaded_again(tmp_path: pathlib.Path) -> None:
    pin = _pin()
    (tmp_path / pin.file).write_bytes(DATA)
    calls: list[str] = []
    assert fd.fetch_all(tmp_path, None, _opener(b"other", calls), (pin,)) == []
    assert calls == []
    assert (tmp_path / pin.file).read_bytes() == DATA


def test_bad_hash_is_refused_and_part_removed(tmp_path: pathlib.Path) -> None:
    pin = _pin()
    problems = fd.fetch_all(tmp_path, None, _opener(b"X" * len(DATA)), (pin,))
    assert len(problems) == 1 and "SHA-256" in problems[0]
    assert list(tmp_path.iterdir()) == []


def test_wrong_size_is_refused(tmp_path: pathlib.Path) -> None:
    pin = _pin()
    problems = fd.fetch_all(tmp_path, None, _opener(DATA + b"!"), (pin,))
    assert len(problems) == 1 and "size" in problems[0]
    assert list(tmp_path.iterdir()) == []


def test_no_sha256_is_refused_without_downloading(tmp_path: pathlib.Path) -> None:
    pin = _pin(sha="", key="vigembus")
    calls: list[str] = []
    problems = fd.fetch_all(tmp_path, None, _opener(DATA, calls), (pin,))
    assert len(problems) == 1 and "no SHA-256" in problems[0]
    assert calls == [] and list(tmp_path.iterdir()) == []


def test_network_error_leaves_no_part_file(tmp_path: pathlib.Path) -> None:
    def broken(url: str, timeout: float) -> IO[bytes]:
        raise OSError("no network")
    problems = fd.fetch_all(tmp_path, None, broken, (_pin(),))
    assert len(problems) == 1 and "no network" in problems[0]
    assert list(tmp_path.iterdir()) == []


def test_from_folder_copies_and_checks(tmp_path: pathlib.Path) -> None:
    src, dest = tmp_path / "src", tmp_path / "dest"
    src.mkdir()
    good, bad = _pin(), _pin(b"second", key="hidhide")
    (src / good.file).write_bytes(DATA)
    (src / bad.file).write_bytes(b"tampered")  # right size is 6, this is 8
    calls: list[str] = []
    problems = fd.fetch_all(dest, src, _opener(b"", calls), (good, bad))
    assert calls == []
    assert len(problems) == 1 and bad.file in problems[0]
    assert (dest / good.file).read_bytes() == DATA
    assert not (dest / bad.file).exists() and not list(dest.glob("*.part"))


def test_from_folder_missing_file_is_reported(tmp_path: pathlib.Path) -> None:
    problems = fd.fetch_all(tmp_path / "d", tmp_path, None, (_pin(),))
    assert len(problems) == 1 and "not found" in problems[0]


def test_real_pins_all_have_a_hash_and_size() -> None:
    assert [p.key for p in fd.PINS] == ["vjoy", "vigembus", "hidhide"]
    assert all(len(p.sha256) == 64 and p.size > 0 for p in fd.PINS)
    assert all(p.url.startswith("https://github.com/") for p in fd.PINS)


def test_main_fails_when_a_driver_has_no_hash(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(fd, "PINS", (_pin(sha="", key="vigembus"),))
    assert fd.main(["--dest", str(tmp_path)], _opener(b"x")) == 1
    assert "vigembus" in capsys.readouterr().out
    assert list(tmp_path.iterdir()) == []


def test_main_succeeds_when_every_file_is_good(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(fd, "PINS", (_pin(),))
    assert fd.main(["--dest", str(tmp_path)], _opener(DATA)) == 0


def test_pins_agree_with_gremlin_drivers() -> None:
    drivers = pytest.importorskip("gremlin.drivers")
    for pin in fd.PINS:
        info = drivers.DRIVERS[pin.key]
        assert info.bundled_file == pin.file
        assert info.sha256 == pin.sha256
