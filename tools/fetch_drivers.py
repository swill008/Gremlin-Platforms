# -*- coding: utf-8; -*-
# SPDX-License-Identifier: GPL-3.0-only

"""Fetches the driver installers the setup carries into installer/drivers/.

Usage: python tools/fetch_drivers.py [--from FOLDER] [--dest FOLDER]

Each file comes from its pinned release URL (or is copied from FOLDER with
--from) and is kept only when its size and SHA-256 match; a download goes to
a .part file that is renamed on success and deleted on failure. A driver whose
SHA-256 isn't known yet (ViGEmBus until it is downloaded once and pinned) is
refused. The pins are a second copy of gremlin.drivers.DRIVERS' hashes;
test_fetch_drivers.py fails when the two differ. Exits 0 when every file is in
place, 1 otherwise (01 S188).
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

DEST = Path(__file__).resolve().parent.parent / "installer" / "drivers"
TIMEOUT = 30.0  # seconds, per connection and per read
CHUNK = 1 << 16


@dataclass(frozen=True)
class Pin:
    key: str
    file: str
    url: str
    size: int
    sha256: str  # "" = not known yet


PINS: tuple[Pin, ...] = (
    Pin(
        "vjoy",
        "vJoySetup_v2.2.2.0_Win10_Win11.exe",
        "https://github.com/BrunnerInnovation/vJoy/releases/download/v2.2.2.0/"
        "vJoySetup_v2.2.2.0_Win10_Win11.exe",
        5_302_312,
        "ef569a3105cd301b89580f18f60c66b339e95296acf2c0dfcaf4b4bbf8ab68fe",
    ),
    Pin(
        "vigembus",
        "ViGEmBus_1.22.0_x64_x86_arm64.exe",
        "https://github.com/nefarius/ViGEmBus/releases/download/v1.22.0/"
        "ViGEmBus_1.22.0_x64_x86_arm64.exe",
        6_278_576,
        "89220a7865076b342892f98865f3499fb7c4cfd673159e89d352c360fd014c6a",
    ),
    Pin(
        "hidhide",
        "HidHide_1.5.230_x64.exe",
        "https://github.com/nefarius/HidHide/releases/download/v1.5.230.0/"
        "HidHide_1.5.230_x64.exe",
        8_078_016,
        "f4bbbcb82e6258641b887c74bc81c4c5f66e4aa811808dfc304347687b7605f6",
    ),
)

Opener = Callable[[str, float], IO[bytes]]


def _default_opener(url: str, timeout: float) -> IO[bytes]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "gremlin-fetch-drivers"}
    )
    # Pinned https URLs only.
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(CHUNK), b""):
            digest.update(block)
    return digest.hexdigest()


def check_file(path: Path, pin: Pin) -> str:
    """"" when the file has the pinned size and SHA-256, else why not."""
    if not pin.sha256:
        return f"{pin.file}: no SHA-256 is pinned for {pin.key} yet; refusing it"
    size = path.stat().st_size
    if size != pin.size:
        return f"{pin.file}: size {size} bytes, expected {pin.size}"
    if sha256_of(path) != pin.sha256:
        return f"{pin.file}: SHA-256 does not match the pinned value"
    return ""


def _discard(path: Path) -> None:
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _place(part: Path, final: Path, pin: Pin) -> str:
    """Rename the checked .part file over the final name, or delete it."""
    problem = check_file(part, pin)
    if problem:
        _discard(part)
        return problem
    part.replace(final)
    return ""


def fetch_one(
    pin: Pin, dest: Path, source: Path | None, opener: Opener
) -> tuple[str, str]:
    """Returns (status, problem).

    status is "kept", "copied" or "downloaded"; problem "" means ok.
    """
    if not pin.sha256:
        return "", f"{pin.file}: no SHA-256 is pinned for {pin.key} yet; refusing it"
    final = dest / pin.file
    if final.is_file() and not check_file(final, pin):
        return "kept", ""
    part = dest / (pin.file + ".part")
    try:
        if source is not None:
            origin = source / pin.file
            if not origin.is_file():
                return "", f"{pin.file}: not found in {source}"
            shutil.copyfile(origin, part)
            status = "copied"
        else:
            with opener(pin.url, TIMEOUT) as response, open(part, "wb") as out:
                while block := response.read(CHUNK):
                    out.write(block)
            status = "downloaded"
    except (OSError, ValueError) as error:
        _discard(part)
        return "", f"{pin.file}: {error}"
    problem = _place(part, final, pin)
    return ("", problem) if problem else (status, "")


def fetch_all(
    dest: Path = DEST,
    source: Path | None = None,
    opener: Opener | None = None,
    pins: tuple[Pin, ...] = PINS,
) -> list[str]:
    """Fetch every pinned file; returns the list of problems (empty = all in place)."""
    dest.mkdir(parents=True, exist_ok=True)
    problems = []
    for pin in pins:
        status, problem = fetch_one(pin, dest, source, opener or _default_opener)
        if problem:
            problems.append(problem)
            print(f"FAILED  {problem}")
        else:
            print(f"{status:10s}{pin.file}")
    return problems


def main(argv: list[str] | None = None, opener: Opener | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--from", dest="source", type=Path, help="copy the files from this folder"
    )
    parser.add_argument(
        "--dest", type=Path, default=DEST, help="target folder (installer/drivers)"
    )
    args = parser.parse_args(argv)
    problems = fetch_all(args.dest, args.source, opener, PINS)
    if problems:
        print(f"{len(problems)} driver file(s) not in place; the build fails.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
