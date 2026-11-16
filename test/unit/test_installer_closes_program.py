"""01 S173: the installer closes a running Gremlin-Platforms the way File > Exit
does, stops when it won't quit (unsaved changes) and starts it again after."""

from __future__ import annotations

import pathlib
import re

_ISS = pathlib.Path(__file__).parents[2] / "installer" / "gremlin_platforms.iss"

_UNSAVED = (
    "Gremlin-Platforms has unsaved changes. Save or close them, "
    "then run the update again. Nothing was changed."
)


def _iss() -> str:
    return _ISS.read_text(encoding="utf-8")


def _routine(iss: str, header: str) -> str:
    body = iss[iss.index(header):]
    return body[: body.index("\nend;") + 5]


def _pascal_string(text: str) -> str:
    """Joins 'a' + 'b' Pascal string pieces into one Python string."""
    return "".join(re.findall(r"'((?:[^']|'')*)'", text)).replace("''", "'")


def test_closing_happens_before_the_files_are_moved_aside() -> None:
    # The Restart Manager runs after PrepareToInstall, which had already
    # moved the files aside (or failed to): the script must close it itself.
    prepare = _routine(_iss(), "function PrepareToInstall(")
    assert "CloseRunningProgram" in prepare
    assert prepare.index("CloseRunningProgram") < prepare.index("MoveAside(")
    assert prepare.index("CloseRunningProgram") < prepare.index("if not OursIsHere")


def test_it_asks_the_program_to_quit_and_never_kills_it() -> None:
    iss = _iss()
    ask = _routine(iss, "procedure AskToClose(")
    assert "PostMessage(Wnd, WM_CLOSE, 0, 0)" in ask
    assert "WM_CLOSE = $0010;" in iss
    assert "TerminateProcess" not in iss.replace("Never TerminateProcess", "")
    assert "taskkill" not in iss.lower()
    assert "CloseApplications=force" not in iss


def test_it_waits_about_fifteen_seconds() -> None:
    iss = _iss()
    tries = int(re.search(r"CloseWaitTries = (\d+);", iss).group(1))
    step = int(re.search(r"CloseWaitStep = (\d+);", iss).group(1))
    assert tries * step == 15000
    close = _routine(iss, "function CloseRunningProgram:")
    assert "for Tries := 1 to CloseWaitTries do" in close
    assert "Sleep(CloseWaitStep)" in close


def test_it_only_looks_at_the_program_in_the_chosen_folder() -> None:
    running = _routine(_iss(), "function RunningIds(")
    assert "Win32_Process" in running
    assert "CompareText(Item.ExecutablePath, Exe) = 0" in running


def test_still_running_stops_setup_with_the_spec_message() -> None:
    prepare = _routine(_iss(), "function PrepareToInstall(")
    block = prepare[prepare.index("if not CloseRunningProgram then"):]
    block = block[: block.index("Exit;")]
    assert _pascal_string(block) == _UNSAVED


def test_it_starts_the_program_again_once() -> None:
    iss = _iss()
    run = iss[iss.index("[Run]"): iss.index("[UninstallDelete]")]
    assert r'"{app}\{#MyAppExeName}"; Flags: nowait; Check: RestartAfterClose' in (
        run
    )
    restart = _routine(iss, "function RestartAfterClose:")
    # The in-app update's /LAUNCH=1 entry starts it already.
    assert "ClosedByInstaller and not LaunchAfterSilentUpdate" in restart
    assert "Check: LaunchAfterSilentUpdate" in run
    # The Launch box is kept, but hidden when setup starts it anyway.
    launch = next(line for line in run.splitlines() if "Description: \"Launch" in line)
    assert "postinstall" in launch and "Check: OfferLaunch" in launch
    assert "Result := not ClosedByInstaller;" in _routine(iss, "function OfferLaunch:")
    close = _routine(iss, "function CloseRunningProgram:")
    assert "ClosedByInstaller := True;" in close


def test_a_failed_install_starts_the_closed_program_again() -> None:
    deinit = _routine(_iss(), "procedure DeinitializeSetup;")
    assert "(LaunchAfterSilentUpdate or ClosedByInstaller)" in deinit


def test_still_a_per_user_install() -> None:
    iss = _iss()
    assert "PrivilegesRequired=lowest" in iss
    assert "CloseApplications=no" in iss
