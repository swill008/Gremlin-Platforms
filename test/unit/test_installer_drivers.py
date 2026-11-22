"""01 S187-S192, 06 S186: setup's Drivers page and driver jobs.

ISCC is not run in tests, so these read installer/gremlin_platforms.iss: the
names and keys must match gremlin/drivers.py, the job file the script writes
must be one the helper reads, and the Pascal must at least be well formed.
"""

from __future__ import annotations

import json
import pathlib
import re

import pytest

from gremlin import drivers

_ROOT = pathlib.Path(__file__).parents[2]
_ISS = _ROOT / "installer" / "gremlin_platforms.iss"


def _iss() -> str:
    return _ISS.read_text(encoding="utf-8")


def _code() -> str:
    return _iss().split("[Code]", 1)[1]


def _section(name: str) -> str:
    return _iss().split(f"[{name}]", 1)[1].split("\n[", 1)[0]


def _routine(iss: str, header: str) -> str:
    body = iss[iss.index(header):]
    return body[: body.index("\nend;") + 5]


def _pascal_string(text: str) -> str:
    """Joins 'a' + 'b' Pascal string pieces into one Python string."""
    return "".join(re.findall(r"'((?:[^']|'')*)'", text)).replace("''", "'")


def _define(name: str) -> str:
    found = re.search(rf'^#define {name} "([^"]*)"$', _iss(), re.M)
    assert found, f"#define {name} missing"
    return found.group(1)


def _strip(code: str) -> str:
    """The Pascal code with strings, comments and // lines blanked out.

    Fails on a { comment that holds another '{': Pascal comments don't nest,
    so its first '}' would end it early (an easy slip with '{app}' or JSON).
    """
    out: list[str] = []
    i = 0
    while i < len(code):
        c = code[i]
        if c == "'":
            j = i + 1
            while True:
                j = code.index("'", j)
                if code[j + 1: j + 2] == "'":
                    j += 2
                    continue
                break
            out.append("''")
            i = j + 1
        elif c == "{":
            j = code.index("}", i)
            inner = code[i + 1: j]
            assert "{" not in inner, f"brace inside a {{ }} comment: {inner[:60]!r}"
            out.append(" ")
            i = j + 1
        elif code.startswith("(*", i):
            j = code.index("*)", i)
            out.append(" ")
            i = j + 2
        elif code.startswith("//", i):
            j = code.find("\n", i)
            i = len(code) if j < 0 else j
        else:
            out.append(c)
            i += 1
    return "".join(out)


# -- a small evaluator for the script's string expressions ---------------------


def _eval(expr: str, env: dict[str, str]) -> str:
    """Evaluates a Pascal '+' chain of string literals, #$xxxx characters and
    names looked up in env (JsonEscape(x) escapes env[x] like the script)."""
    result = []
    for part in _split_plus(expr):
        part = part.strip()
        if part.startswith("'"):
            result.append(part[1:-1].replace("''", "'"))
        elif part.startswith("#$"):
            result.append(chr(int(part[2:], 16)))
        elif part.startswith("JsonEscape(") and part.endswith(")"):
            value = env[part[len("JsonEscape("):-1].strip()]
            result.append(value.replace("\\", "\\\\").replace('"', '\\"'))
        else:
            result.append(env[part])
    return "".join(result)


def _split_plus(expr: str) -> list[str]:
    parts, depth, current, in_string = [], 0, "", False
    for c in expr:
        if c == "'":
            in_string = not in_string
        if not in_string:
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            elif c == "+" and depth == 0:
                parts.append(current)
                current = ""
                continue
        current += c
    parts.append(current)
    return parts


def _assignments(routine: str, target: str) -> list[str]:
    """The right-hand sides of `target := ...;` in a routine, in order."""
    found = re.findall(
        rf"{re.escape(target)} := ((?:'(?:[^']|'')*'|[^;'])*);", routine
    )
    return [" ".join(line.split()) for line in found]


# -- 01 S187: the Drivers page ---------------------------------------------------


def test_the_drivers_page_comes_after_the_folder_page() -> None:
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "CreateCustomPage(wpSelectDir, 'Drivers'," in create
    assert "TNewCheckListBox.Create(DriversPage)" in create
    assert "DisableDirPage=no" in _iss()


def test_missing_is_ticked_older_unticked_same_or_newer_has_no_box() -> None:
    fill = _routine(_code(), "procedure FillDriverList;")
    assert "(Drivers[I].State = 'missing') or (Drivers[I].State = 'older')" in fill
    # AddCheckBox(caption, sub item, level, checked, ...): ticked only when missing.
    assert re.search(
        r"AddCheckBox\(Drivers\[I\]\.Name, DriverLabel\(I\),\s*0, "
        r"Drivers\[I\]\.State = 'missing', True,",
        fill,
    )
    assert "AddGroup(Drivers[I].Name, DriverLabel(I)" in fill  # no box
    words = _routine(_code(), "function DriverLabel(")
    assert "'not installed'" in words
    assert "'update available: ' + Drivers[I].Installed + ' ' + #$2192 + ' ' +" in words


def test_states_follow_drivers_compare() -> None:
    detect = _routine(_code(), "procedure DetectDrivers;")
    for line in (
        "-1: Drivers[I].State := 'older';",
        "0: Drivers[I].State := 'same';",
        "Drivers[I].State := 'newer';",
        "Drivers[I].State := 'missing'",
    ):
        assert line in detect
    compare = _routine(_code(), "function CompareVersions(")
    assert "NextVersionPart(A)" in compare and "NextVersionPart(B)" in compare


def test_bundled_names_and_versions_match_drivers_py() -> None:
    defines = {
        "vjoy": ("VJoyBundled", "VJoyFile"),
        "vigembus": ("ViGEmBusBundled", "ViGEmBusFile"),
        "hidhide": ("HidHideBundled", "HidHideFile"),
    }
    assert list(drivers.DRIVERS) == list(defines)
    init = _routine(_code(), "procedure InitDrivers;")
    for index, (key, info) in enumerate(drivers.DRIVERS.items()):
        version_name, file_name = defines[key]
        assert _define(version_name) == info.bundled_version
        assert _define(file_name) == info.bundled_file
        call = re.search(
            rf"SetDriver\({index}, '{key}', '{re.escape(info.name)}', "
            rf"'\{{#{version_name}\}}', '\{{#{file_name}\}}',\s*"
            r"'([^']*)', '([^']*)', '([^']*)'\);",
            init,
        )
        assert call, f"SetDriver for {key}"
        repo, prefix, suffix = call.groups()
        assert repo == (info.repo or "")
        if info.asset_regex is None:
            assert (prefix, suffix) == ("", "")
        else:
            # Prefix + digits and dots + suffix is drivers.py's asset_regex.
            assert re.escape(prefix) + r"[\d.]+" + re.escape(suffix) == info.asset_regex


def test_detection_reads_the_same_keys_as_drivers_py() -> None:
    code = _code()
    assert f"UninstallRoot = '{drivers.UNINSTALL}';" in code
    assert f"VJoyUninstallKey = '{drivers.VJOY_UNINSTALL}';" in code
    assert f"HidHideKey = '{drivers.HIDHIDE_KEY}';" in code
    names = drivers.VIGEMBUS_DISPLAY_NAMES
    assert f"ViGEmBusDisplayName = '{names[0]}';" in code
    assert f"ViGEmBusDisplayName2 = '{names[1]}';" in code
    found = _routine(code, "function InstalledDriverVersion(")
    assert "MachineValue(VJoyUninstallKey, 'DisplayVersion')" in found
    assert "MachineValue(HidHideKey, 'Version')" in found
    assert r"ExpandConstant('{sys}\drivers\ViGEmBus.sys')" in found
    assert pathlib.Path(drivers.vigembus_sys_path()).parts[-3:] == (
        "System32", "drivers", "ViGEmBus.sys"
    )
    assert "UninstallVersion(ViGEmBusDisplayName)" in found
    assert "UninstallVersion(ViGEmBusDisplayName2)" in found
    # The Uninstall entry is read before the .sys file (whose version differs).
    assert found.index("UninstallVersion(ViGEmBusDisplayName)") < found.index(
        "ViGEmBus.sys"
    )
    # Both registry views, like drivers.WindowsRegistry.
    machine = _routine(code, "function MachineValue(")
    assert "HKLM64" in machine and "HKLM32" in machine


# -- 01 S188: bundled copies and licences ---------------------------------------


def test_bundled_installers_and_licences_are_in_files() -> None:
    files = _section("Files")
    for info in drivers.DRIVERS.values():
        name = {
            "vjoy": "VJoyFile", "vigembus": "ViGEmBusFile", "hidhide": "HidHideFile",
        }[info.key]
        line = next(
            (x for x in files.splitlines() if f"{{#{name}}}" in x), None
        )
        assert line, f"{info.key} is not in [Files]"
        assert line.startswith(
            rf'Source: "drivers\{{#{name}}}"; DestDir: "{{app}}\drivers"'
        )
        # A missing bundled file fails the build, never a silent gap.
        assert "skipifsourcedoesntexist" not in line
    assert 'Source: "..\\licenses\\*"; DestDir: "{app}\\licenses"' in files
    for licence in ("vjoy.txt", "vigembus.txt", "hidhide.txt"):
        assert (_ROOT / "licenses" / licence).is_file(), licence


# -- 01 S189: newer versions -----------------------------------------------------


def test_vjoy_and_hidhide_ask_github_and_download_with_progress() -> None:
    code = _code()
    check = _routine(code, "procedure CheckLatest(")
    assert "if Drivers[I].LatestChecked or (Drivers[I].Repo = '') then" in check
    assert "'https://api.github.com/repos/' + Drivers[I].Repo +" in check
    assert "'/releases/latest'" in check
    assert "CompareVersions(Tag, Drivers[I].Bundled) <= 0" in check
    assert "(Copy(Url, 1, 19) = 'https://github.com/')" in check
    fetch = _routine(code, "function FetchText(")
    assert "Http.SetTimeouts(5000, 5000, 5000, 5000);" in fetch
    assert "except" in fetch
    create = _routine(code, "procedure CreateDriverPages;")
    assert "CreateDownloadPage('Drivers'," in create
    download = _routine(code, "procedure DownloadNewerDrivers;")
    assert "DriverDownloadPage.Download;" in download
    # A failed or stopped download leaves the bundled copy, never stops setup.
    after = download[download.index("except"):]
    assert "Drivers[I].Download := '';" in after
    assert "Result := False" not in download
    click = _routine(code, "function NextButtonClick(")
    assert "else if CurPageID = wpReady then" in click
    assert "DownloadNewerDrivers;" in click


# -- 12 S25: the job file -----------------------------------------------------------


def _job_json(
    op: str, key: str, download: str, bundled: str, devices_json: str = ""
) -> str:
    routine = _routine(_code(), "function JobJson(")
    files_parts = _assignments(routine, "Files")
    assert len(files_parts) == 3, files_parts  # '', download, bundled
    env = {
        "Drivers[I].Download": download,
        "BundledPath(I)": bundled,
        "Drivers[I].Op": op,
        "Drivers[I].Key": key,
    }
    files = ""
    if op != "remove":
        if download:
            env["Files"] = files
            files = _eval(files_parts[1], env)
        env["Files"] = files
        files = _eval(files_parts[2], env)
    env["Files"] = files
    env["Devices"] = devices_json
    (result,) = _assignments(routine, "Result")
    return _eval(result, env)


def _job_file(jobs: list[str]) -> str:
    routine = _routine(_code(), "function WriteJobFile(")
    (line,) = _assignments(routine, "Lines[0]")
    assert "Jobs := Jobs + ', ';" in routine
    return _eval(line, {"Jobs": ", ".join(jobs)})


def test_the_job_file_is_one_the_helper_reads(tmp_path: pathlib.Path) -> None:
    # Paths with a quote-free space and backslashes, as {app} and {tmp} are.
    app = r"C:\Users\A B\AppData\Local\Programs\Gremlin-Platforms"
    tmp = r"C:\Users\A B\AppData\Local\Temp\is-ABC.tmp"
    text = _job_file([
        _job_json("install", "vjoy", tmp + r"\vJoySetup_v2.2.3.0_Win10_Win11.exe",
                  app + r"\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe"),
        _job_json("update", "vigembus", "",
                  app + r"\drivers\ViGEmBus_1.22.0_x64_x86_arm64.exe"),
        _job_json("remove", "hidhide", "", app + r"\drivers\HidHide_1.5.230_x64.exe"),
    ])
    data = json.loads(text)
    assert data["version"] == 1
    path = tmp_path / "jobs.json"
    path.write_text(text, encoding="utf-8")
    jobs = drivers.read_jobs(path)
    assert [(j.op, j.driver) for j in jobs] == [
        ("install", "vjoy"), ("update", "vigembus"), ("remove", "hidhide")
    ]
    # Download first, bundled second (01 S189, 12 S25); a remove lists no file.
    assert jobs[0].files == [
        {"path": tmp + r"\vJoySetup_v2.2.3.0_Win10_Win11.exe", "kind": "download"},
        {
            "path": app + r"\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe",
            "kind": "bundled",
        },
    ]
    assert [f["kind"] for f in jobs[1].files] == ["bundled"]
    assert jobs[2].files == []
    assert all(j.devices == [] for j in jobs)


def test_the_job_file_has_no_bom_and_lives_in_tmp() -> None:
    code = _code()
    write = _routine(code, "function WriteJobFile(")
    assert "SaveStringsToUTF8FileWithoutBOM(Path, Lines, False)" in write
    run = _routine(code, "procedure RunDriverJobs;")
    assert "JobFile := ExpandConstant('{tmp}\\' + JobFileName);" in run
    assert "ResultsFile := ExpandConstant('{tmp}\\' + ResultsFileName);" in run
    ops = _routine(code, "procedure DriversPageDone;")
    for op in re.findall(r"Drivers\[I\]\.Op := '(\w+)'", ops):
        assert op in drivers.JOB_OPS


# -- 01 S190: one admin prompt -----------------------------------------------------


def test_one_elevated_helper_start_with_jobs_and_results() -> None:
    iss = _iss()
    assert "PrivilegesRequired=lowest" in iss
    assert _define("HelperExeName") == "Gremlin Device Helper.exe"
    spec = (_ROOT / "joystick_gremlin.spec").read_text(encoding="utf-8")
    assert 'helper_name = "Gremlin Device Helper"' in spec
    run = _routine(_code(), "procedure RunHelperJobs(")
    assert "ShellExec(" not in _code()
    assert run.count("StartElevated(") == 1
    start = "StartElevated(ExpandConstant('{app}\\{#HelperExeName}'), Params,"
    assert start in run
    # RunDriverJobs and Repair Now both start the helper this one way.
    assert _code().count(start) == 1
    assert "RunHelperJobs(JobFile, ResultsFile);" in _routine(
        _code(), "procedure RunDriverJobs;"
    )
    assert "Params := '--jobs ' + AddQuotes(JobFile) + ' --results ' +" in run
    assert "AddQuotes(ResultsFile);" in run
    assert "WaitForHelper(ResultsFile)" in run
    assert "CloseHandle(Process);" in run
    # The drivers' one prompt, and the runtime's own (S193): both through the
    # one elevated start.
    assert _code().count("'runas'") == 1
    assert "Info.lpVerb := 'runas';" in _routine(_code(), "function StartElevated(")
    assert _runtime_install().count("StartElevated(") == 1


def test_the_prompt_opens_in_front_of_setup() -> None:
    # Answer 4a: ShellExecuteExW with setup's own window as the prompt's owner,
    # setup brought forward first; a silent install has no window to own it.
    code = _code()
    assert "external 'ShellExecuteExW@shell32.dll stdcall';" in code
    assert "external 'SetForegroundWindow@user32.dll stdcall';" in code
    record = code[code.index("TShellExecuteInfo = record"):]
    record = record[: record.index("end;")]
    fields = re.findall(r"^    (\w+): (\w+);$", record, re.M)
    assert [f for f, _ in fields] == [
        "cbSize", "fMask", "Wnd", "lpVerb", "lpFile", "lpParameters", "lpDirectory",
        "nShow", "hInstApp", "lpIDList", "lpClass", "hkeyClass", "dwHotKey",
        "hMonitor", "hProcess",
    ]
    start = _routine(code, "function StartElevated(")
    assert "Info.cbSize := SizeOf(Info);" in start
    assert "Info.Wnd := WizardForm.Handle;" in start
    front = start.index("SetForegroundWindow(WizardForm.Handle);")
    assert start.index("if not WizardSilent then") < front < start.index(
        "Result := ShellExecuteEx(Info);"
    )
    assert "SeeMaskNoCloseProcess" in start and "SeeMaskFlagNoUi" in start
    assert "Process := Info.hProcess" in start
    assert "ErrorCode := DLLGetLastError;" in start
    assert int(_const_int_hex("SeeMaskNoCloseProcess"), 16) == 0x40
    # The refused prompt (1223) still has its own result in both places.
    run = _routine(code, "procedure RunHelperJobs(")
    assert "else if ErrorCode = UacRefusedCode then" in run
    assert "else if ErrorCode = UacRefusedCode then" in _runtime_install()


def _const_int_hex(name: str) -> str:
    found = re.search(rf"^  {name} = \$([0-9A-Fa-f]+);$", _code(), re.M)
    assert found, name
    return found.group(1)


def test_progress_comes_from_the_results_file_until_finished() -> None:
    code = _code()
    read = _routine(code, "function ReadDriverResults(")
    for key in ("'jobs'", "'state'", "'message'", "'restart'", "'finished'"):
        assert key in read
    wait = _routine(code, "procedure WaitForHelper(")
    assert "if AllDone then" in wait
    assert "DriverProgressPage.SetProgress(DoneCount," in wait
    # Bounded: a helper that never starts or never finishes fails its jobs.
    assert "for Tick := 1 to Limit do" in wait
    assert "FailOpenJobs('Gremlin Device Helper did not start.');" in wait
    assert "FailOpenJobs('Gremlin Device Helper did not finish in time.');" in wait


def test_the_results_file_fields_match_drivers_py(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "results.json"
    drivers.write_results(
        path, [drivers.JobResult("done", "vJoy 2.2.2.0 installed", True, "bundled")],
        finished=True,
    )
    data = json.loads(path.read_text(encoding="utf-8"))
    assert set(data) == {"version", "finished", "jobs"}
    assert set(data["jobs"][0]) == {
        "state", "message", "restart", "used", "lost", "added"
    }
    # The script's reader keeps to ASCII \u escapes, which json writes by default.
    assert path.read_text(encoding="utf-8").isascii()


# -- 01 S191: Gremlin always installs ---------------------------------------------


def test_a_driver_failure_never_stops_the_install() -> None:
    code = _code()
    run = _routine(code, "procedure RunDriverJobs;")
    assert run.index("try") < run.index("RunHelperJobs(")
    assert "except" in run and "GetExceptionMessage" in run
    helper = _routine(code, "procedure RunHelperJobs(")
    assert "FailOpenJobs('Administrator permission was not given.')" in helper
    step = _routine(code, "procedure CurStepChanged(")
    assert step.index("Finished := True;") < step.index("RunDriverJobs;")
    click = _routine(code, "function NextButtonClick(")
    # Only the folder check, the in-use No (D-01-VJOY-IN-USE) and the alike
    # devices' No (D-01-VJOY-COUNTDOWN) keep setup on a page; never a result.
    assert click.count("Result := False;") == 3
    assert click.index("VJoyAlikeQuestion") < click.rindex("Result := False;")
    assert "Drivers" not in _routine(code, "function PrepareToInstall(")


def test_the_last_page_lists_results_and_offers_a_restart() -> None:
    code = _code()
    page = _routine(code, "procedure CurPageChanged(")
    assert "CurPageID <> wpFinished" in page
    assert "'Drivers:' + #13#10 + DriverSummary" in page
    assert "'Restart now'" in page and "'Restart later'" in page
    assert "Result := DriversNeedRestart or RuntimeNeedRestart;" in _routine(
        code, "function NeedRestart:"
    )
    summary = _routine(code, "procedure BuildDriverSummary;")
    assert "if Drivers[I].ResultRestart then" in summary


def test_the_ready_page_says_what_and_when() -> None:
    memo = _routine(_code(), "function UpdateReadyMemo(")
    assert "'Drivers, after the files are copied (Windows asks for '" in memo
    assert "MemoDirInfo" in memo and "MemoTasksInfo" in memo


def test_setup_closed_program_starts_after_the_drivers() -> None:
    code = _code()
    restart = _routine(code, "function RestartAfterClose:")
    assert "not DriverJobsPlanned" in restart
    run = _routine(code, "procedure RunDriverJobs;")
    tail = run[run.rindex("end;", 0, len(run) - 5):]
    assert "ClosedByInstaller and not LaunchAfterSilentUpdate" in tail
    assert "ExecAsOriginalUser(AppExe," in tail


# -- 06 S186: the HidHide update's first half ---------------------------------------


def test_hidhide_step_1_prompt_has_the_spec_words() -> None:
    ask = _routine(_code(), "function AskHidHideStep1(")
    assert "TaskDialogMsgBox('HidHide update, step 1 of 2'," in ask
    assert "['Continue', 'Skip HidHide update']" in ask
    body = ask[ask.index("'Setup will"): ask.index("mbConfirmation")]
    text = _pascal_string(body)
    assert text.startswith("Setup will remove HidHide ")
    assert "After a restart, Gremlin installs HidHide " in text
    assert "and asks for one more restart." in text
    assert text.endswith("Devices aren't hidden until then.")
    done = _routine(_code(), "procedure DriversPageDone;")
    # Nested, so the prompt shows only for a HidHide remove.
    nested = "if Drivers[I].Op = 'remove' then\n      if not AskHidHideStep1(I) then"
    assert nested in done
    assert "DriverList.Checked[Drivers[I].Row] := False;" in done


def test_removing_hidhide_shows_progress_and_asks_for_the_restart() -> None:
    code = _code()
    progress = _routine(code, "function JobProgressText(")
    assert "'Removing HidHide ' + Drivers[I].Installed + #$2026" in progress
    page = _routine(code, "procedure CurPageChanged(")
    assert "'Restart needed to continue the HidHide update'" in page
    summary = _routine(code, "procedure BuildDriverSummary;")
    assert "HidHideRemoved := True;" in summary


def test_pending_json_is_written_after_the_remove(tmp_path: pathlib.Path) -> None:
    code = _code()
    run = _routine(code, "procedure RunDriverJobs;")
    assert run.index("BuildDriverSummary;") < run.index(
        "if HidHideRemoved then\n        WriteHidHidePending(DriverIndex('hidhide'));"
    )
    pending = _routine(code, "procedure WriteHidHidePending(")
    assert "ExpandConstant('{app}\\drivers\\pending.json')" in pending
    parts = drivers.pending_path(pathlib.Path("A")).parts
    assert parts[-2:] == ("drivers", "pending.json")
    (line,) = _assignments(pending, "Lines[0]")
    text = _eval(line, {
        "Version": "1.5.230",
        "Path": r"C:\Users\A B\Gremlin-Platforms\drivers\HidHide_1.5.230_x64.exe",
        "Kind": "bundled",
    })
    app = tmp_path / "app"
    (app / "drivers").mkdir(parents=True)
    drivers.pending_path(app).write_text(text, encoding="utf-8")
    assert drivers.read_pending(app) == {
        "hidhide": {
            "version": "1.5.230",
            "file": r"C:\Users\A B\Gremlin-Platforms\drivers\HidHide_1.5.230_x64.exe",
            "kind": "bundled",
        }
    }
    assert "SaveStringsToUTF8FileWithoutBOM(" in pending


# -- 01 S192 and silent installs ---------------------------------------------------


def test_uninstall_leaves_the_drivers() -> None:
    iss = _iss()
    assert "[UninstallRun]" not in iss
    assert "msiexec" not in iss.lower()
    assert "UninstallString" not in iss
    deleted = _section("UninstallDelete")
    driver_lines = [x for x in deleted.splitlines() if "drivers" in x.lower()]
    assert driver_lines == ['Type: files; Name: "{app}\\drivers\\pending.json"']
    assert "UninstallNeedRestart" not in iss
    # 01 S194: the one uninstall step removes only the Start with Windows value.
    assert iss.count("CurUninstallStepChanged") == 1


def test_a_silent_install_skips_the_drivers() -> None:
    code = _code()
    planned = _routine(code, "function DriverJobsPlanned:")
    assert planned.index("if WizardSilent then") < planned.index("for I := 0")
    head = planned[planned.index("if WizardSilent then"): planned.index("for I")]
    assert "Exit;" in head
    run = _routine(code, "procedure RunDriverJobs;")
    assert run.split("begin", 1)[1].lstrip().startswith(
        "if not DriverJobsPlanned then\n    Exit;"
    )
    click = _routine(code, "function NextButtonClick(")
    silent = click.index("if WizardSilent then\n    Exit;")
    assert silent < click.index("DriversPageDone") < click.index("DownloadNewerDrivers")
    skip = _routine(code, "function ShouldSkipPage(")
    assert "(PageID = DriversPage.ID) and WizardSilent" in skip
    # The in-app update path is unchanged.
    assert "Check: LaunchAfterSilentUpdate" in _section("Run")


# -- the Pascal is well formed (no compiler in this batch) ---------------------------


def test_the_code_section_is_well_formed() -> None:
    code = _strip(_code())
    words = re.findall(r"[A-Za-z_]\w*", code.lower())
    opens = sum(words.count(w) for w in ("begin", "case", "try", "record"))
    assert opens == words.count("end"), (opens, words.count("end"))
    assert code.count("(") == code.count(")")
    assert code.count("[") == code.count("]")


@pytest.mark.parametrize(
    "name",
    [
        "DriverJobsPlanned", "CompareVersions", "InstalledDriverVersion",
        "DetectDrivers", "CheckLatest", "DownloadNewerDrivers", "DriversPageDone",
        "WriteJobFile", "ReadDriverResults", "WaitForHelper", "WriteHidHidePending",
        "BuildDriverSummary", "RunDriverJobs", "CharAt", "JsonValue",
        "VJoyDevicesJson", "VJoyNamesJoined", "VJoyUpdateInfoText", "VJoyLostText",
        "VJoyAddedText", "VJoyRestoreJobJson", "JsonIntArray", "AxesFromJson",
        "ReadVJoyUpdateCheck", "IsVJoyJob", "RunHelperJobs",
        "VJoyRestoreResultLine", "RunVJoyRestore", "AskVJoyRepair",
        "RuntimeInstalled", "RuntimeFileTrusted", "RuntimeCodeResult",
        "SetRuntimeText", "InstallRuntime", "CountText", "StartElevated",
        "RuntimeSignedByMicrosoft", "RuntimeInstalledVersion", "UrlSha256",
        "ResolveRuntimeUrl", "CheckNewestRuntime",
    ],
)
def test_every_routine_is_declared_before_it_is_used(name: str) -> None:
    # Pascal Script has no forward use: the declaration must come first.
    code = _strip(_code())
    declared = re.search(rf"\b(?:function|procedure) {name}\b", code)
    assert declared, name
    first_use = re.search(rf"\b{name}\b", code)
    assert first_use and first_use.start() >= declared.start(), name


# -- 01 S187 (answer 1a): the vJoy device choice on the Drivers page (06 S185) ------


def _const(name: str) -> str:
    found = re.search(rf"^  {name} = '((?:[^']|'')*)';$", _code(), re.M)
    assert found, f"const {name} missing"
    return found.group(1).replace("''", "'")


def _pascal_default_buttons(vjoy_id: int) -> int:
    """Runs the .iss DefaultButtons on one id (its three lines, read as written)."""
    body = _routine(_code(), "function DefaultButtons(")
    assert "Result := VJoyMaxButtons + 1 - Id;" in body
    assert "if Result > VJoyMaxButtons then\n    Result := VJoyMaxButtons;" in body
    assert "if Result < 0 then\n    Result := 0;" in body
    top = int(_const_int("VJoyMaxButtons"))
    return max(0, min(top, top + 1 - vjoy_id))


def test_new_devices_count_down_like_drivers_py() -> None:
    """D-01-VJOY-COUNTDOWN (1a, 3a): one rule, vJoy N gets 129 - N buttons."""
    for vjoy_id in range(0, 20):
        assert _pascal_default_buttons(vjoy_id) == drivers.default_buttons(vjoy_id)
    for vjoy_id in range(1, drivers.VJOY_MAX_DEVICES + 1):
        dev = drivers.new_device(vjoy_id)
        assert (dev.axes, dev.buttons, dev.hats) == (
            drivers.VJOY_AXES, _pascal_default_buttons(vjoy_id), 4
        )
    # Add device gives the new row that count, wherever it is slotted in.
    add = _routine(_code(), "procedure VJoyAddClick(")
    assert "AddVJoyDevice(VJoyChosen, Id, VJoyAllAxes, DefaultButtons(Id), " in add
    assert "VJoyChosen[K].Buttons := DefaultButtons(Id);" in add
    assert "VJoyMaxButtons, VJoyMaxHats" not in add


def _alike_sentence(groups: list[list[int]]) -> str:
    """What VJoyAlikeWarning builds for these groups, from its own pieces."""
    found = re.search(r"^  VJoyAlikeText = (.*?);$", _code(), re.M | re.S)
    assert found
    tail = _pascal_string(found.group(1))
    out = []
    for ids in groups:
        names = [f"vJoy {i}" for i in ids]
        who = names[0]
        for j, name in enumerate(names[1:], start=1):
            who += (" and " if j == len(names) - 1 else ", ") + name
        out.append(who + tail)
    return " ".join(out)


def test_the_alike_warning_matches_drivers_py() -> None:
    """D-01-VJOY-COUNTDOWN (4a, 5a): same wording and the same sameness rule."""
    for groups in ([[1, 3]], [[1, 2, 4]], [[1, 2], [3, 5, 6, 7]]):
        assert _alike_sentence(groups) == drivers.alike_warning(groups)
    assert _const("VJoyAlikeQuestion") == " Continue anyway?"
    alike = _routine(_code(), "function VJoyAlikeWarning(")
    # The key is drivers.layout_key: (axes count, buttons, hats).
    assert "(AxesCountOf(List[J].Axes) = AxesCountOf(List[K].Axes)) and" in alike
    same = "(List[J].Buttons = List[K].Buttons) and (List[J].Hats = List[K].Hats)"
    assert same in alike
    assert "if G < 2 then\n      Continue;" in alike
    assert "Who := Who + ' and vJoy ' + IntToStr(Ids[J])" in alike
    assert "Who := Who + ', vJoy ' + IntToStr(Ids[J]);" in alike
    assert "Result := Result + Who + VJoyAlikeText;" in alike
    # Next on the Drivers page asks Yes/No; No stays; after the silent exit.
    nxt = _routine(_code(), "function NextButtonClick(")
    assert nxt.index("if WizardSilent then\n    Exit;") < nxt.index("VJoyAlikeWarning")
    assert "if MsgBox(VJoyAlikeWarning(VJoyChosen) + VJoyAlikeQuestion,\n" in nxt
    assert "mbConfirmation, MB_YESNO) <> IDYES then" in nxt
    asked = nxt.index("VJoyAlikeQuestion")
    assert nxt.index("Result := False;\n          Exit;", asked) < nxt.index(
        "DriversPageDone;", asked
    )
    assert "if VJoyActive then" in nxt


def test_the_hint_sits_under_the_box_above_the_bottom_line() -> None:
    create = _routine(_code(), "procedure CreateDriverPages;")
    found = re.search(r"^  VJoyHintText = (.*?);$", _code(), re.M | re.S)
    assert found
    assert _pascal_string(found.group(1)) == (
        "Each device needs its own number of axes, buttons or hats, so "
        "Gremlin-Platforms can tell them apart."
    )
    assert "VJoyHint.Caption := VJoyHintText;" in create
    assert "VJoyHint.WordWrap := True;" in create
    assert "VJoyHint.Height := ScaleY(30);" in create  # two lines
    # Layout b: the hint under the box, then the bottom line (warning,
    # "Showing"); the hint's place follows from that line.
    above = "VJoyHint.Top := VJoyWarningText.Top - ScaleY(1) - VJoyHint.Height;"
    assert above in create
    assert "Bottom := VJoyHint.Top - ScaleY(2);" in create
    assert create.index("VJoyShowingText.Top :=") < create.index("VJoyHint.Top :=")
    assert create.index("VJoyHint.Top :=") < create.index("VJoyViewport := TPanel")


def test_the_vjoy_choice_has_the_presets_and_custom() -> None:
    from gremlin.ui import drivers_model

    assert [_const("VJoyPresetOne"), _const("VJoyPresetTwo")] == list(drivers.PRESETS)
    assert _const("VJoyCustom") == drivers_model.CUSTOM
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "VJoyPresetBox := TNewComboBox.Create(DriversPage);" in create
    assert "VJoyPresetBox.Style := csDropDownList;" in create
    items = re.findall(r"VJoyPresetBox\.Items\.Add\((\w+)\);", create)
    assert items == ["VJoyPresetOne", "VJoyPresetTwo", "VJoyCustom"]
    # Answer 2a: rows, not the old Custom text box.
    assert "TNewMemo" not in _code() and "CustomMemo" not in _code()
    # Presets are full devices: all eight axes, the countdown buttons, 4 hats
    # (D-01-VJOY-COUNTDOWN: "2 devices, full" is 128 and 127).
    preset = _routine(_code(), "procedure PresetDevices(")
    assert "AddVJoyDevice(List, K, VJoyAllAxes, DefaultButtons(K), VJoyMaxHats);" in (
        preset
    )
    assert "if Name = VJoyPresetTwo then\n    Count := 2;" in preset
    assert int(_const_int("VJoyAllAxes")) == 2 ** len(drivers.VJOY_AXES) - 1
    assert int(_const_int("VJoyMaxButtons")) == 128
    assert int(_const_int("VJoyMaxHats")) == 4
    for name, devices in drivers.PRESETS.items():
        count = 2 if name == _const("VJoyPresetTwo") else 1
        assert [(d.id, d.axes, d.buttons, d.hats) for d in devices] == [
            (k, drivers.VJOY_AXES, _pascal_default_buttons(k), 4)
            for k in range(1, count + 1)
        ]
    assert [d.buttons for d in drivers.PRESETS[_const("VJoyPresetTwo")]] == [128, 127]
    assert re.search(r"^  VJoyMaxDevices = 16;$", _code(), re.M)
    assert drivers.VJOY_MAX_DEVICES == 16


def test_the_vjoy_rows_have_named_axis_boxes_lists_and_add_remove() -> None:
    code = _code()
    rows = _routine(code, "procedure CreateVJoyRows(")
    # One set of controls per possible device (16), eight boxes each.
    assert "for R := 0 to VJoyMaxDevices - 1 do" in rows
    assert "SetArrayLength(VJoyRowAxes, VJoyMaxDevices * 8);" in rows
    assert "Box := TNewCheckBox.Create(DriversPage);" in rows
    assert "Box.Tag := R * 8 + K;" in rows and "Box.OnClick := @VJoyAxisClick;" in rows
    # Buttons 0-128 and hats 0-4 as drop-downs (item N is the number N).
    assert rows.count("List.Style := csDropDownList;") == 2
    assert "for N := 0 to VJoyMaxButtons do" in rows
    assert "for N := 0 to VJoyMaxHats do" in rows
    assert "Button.OnClick := @VJoyRemoveClick;" in rows
    # The headings name the axes X ... S2 (axis_names), then Buttons, Hats.
    create = _routine(code, "procedure CreateDriverPages;")
    assert "AddVJoyHeading(AxisHeading(K), X + K * BoxW, ScaleY(2));" in create
    assert "AddVJoyHeading('Buttons', X, ScaleY(2));" in create
    assert "AddVJoyHeading('Hats', X + ButtonsW + Gap, ScaleY(2));" in create
    assert "Result := AxisHeading(K);" in _routine(code, "function AxisLabel(")
    # "+ Add device" (the list's last row): the lowest free number, at most 16.
    add = _routine(code, "procedure VJoyAddClick(")
    assert "if (N >= VJoyMaxDevices) or not VJoyActive then\n    Exit;" in add
    assert "Id := VJoyNextFreeId(VJoyChosen);" in add
    free = _routine(code, "function VJoyNextFreeId(")
    assert "while VJoyIdUsed(List, Result) do\n    Result := Result + 1;" in free
    fill = _routine(code, "procedure FillVJoyRows;")
    assert "VJoyAddRow.Visible := N < VJoyMaxDevices;" in fill
    assert "VJoyRowRemove[R].Enabled := N > 1;" in fill
    assert "'vJoy ' + IntToStr(VJoyChosen[R].Id)" in fill
    # The list scrolls: whole rows in a clipping panel, moved by a scroll bar.
    assert "TScrollBox" not in _strip(code)
    assert "VJoyRowsPanel.Parent := VJoyRowsClip;" in create
    assert "VJoyRowsClip.Parent := VJoyViewport;" in create
    assert (
        "VJoyViewport.Height := BandH + VJoyVisibleRows * VJoyRowHeight + EdgeW;"
    ) in create
    assert "VJoyScroll.Visible := Lines > VJoyVisibleRows;" in fill
    top = _routine(code, "procedure ShowVJoyTopRow;")
    assert "VJoyRowsPanel.Top := -Top * VJoyRowHeight;" in top
    page = _routine(code, "procedure CurPageChanged(")
    assert "WatchVJoyScroll(CurPageID = DriversPage.ID);" in page
    assert "WatchVJoyScroll(False);" in _routine(code, "procedure DeinitializeSetup;")
    # Any edit shows the matching preset, else Custom; a preset fills the rows.
    edited = _routine(code, "procedure VJoyRowsEdited;")
    assert "VJoyUserEdited := True;" in edited
    assert "Items.IndexOf(MatchingPreset(VJoyChosen))" in edited
    for name in ("VJoyAxisClick", "VJoyButtonsChange", "VJoyHatsChange",
                 "VJoyRemoveClick", "VJoyAddClick"):
        assert "VJoyRowsEdited;" in _routine(code, f"procedure {name}(")
    assert "FillVJoyRows;" in _routine(code, "procedure VJoyPresetChange(")
    axis = _routine(code, "procedure VJoyAxisClick(")
    assert "VJoyChosen[R].Axes or (1 shl K)" in axis
    assert "VJoyChosen[R].Axes and (VJoyAllAxes - (1 shl K))" in axis


def test_the_mouse_wheel_scrolls_the_vjoy_rows() -> None:
    """01 S187 (answer 6a+b): the bar stays and the wheel over the rows scrolls.

    A thread mouse hook lives with the scroll timer (Drivers page only, gone in
    DeinitializeSetup), reads MOUSEHOOKSTRUCTEX at its 32-bit offsets and moves
    VJoyScroll a row per notch through the timer's own ShowVJoyTopRow.
    """
    code = _code()
    watch = _routine(code, "procedure WatchVJoyScroll(")
    assert "SetWindowsHookEx(WhMouse, CreateCallback(@VJoyWheelProc), 0,\n" in watch
    assert "GetCurrentThreadId);" in watch
    assert "UnhookWindowsHookEx(VJoyWheelHook);\n    VJoyWheelHook := 0;" in watch
    assert "SetWindowsHookExW@user32.dll stdcall" in code
    assert re.search(r"\bWhMouse = 7;", code)
    assert re.search(r"\bWmMouseWheel = \$020A;", code)
    # 32-bit Setup: pt at 0 and 4, mouseData (high word = delta) at 20.
    assert re.search(r"\bHookPointX = 0;", code)
    assert re.search(r"\bHookPointY = 4;", code)
    assert re.search(r"\bHookMouseData = 20;", code)
    hook = _routine(code, "function VJoyWheelProc(")
    assert "(Code = HcAction) and (WParam = WmMouseWheel)" in hook
    assert "ReadHookLong(Data, LParam + HookMouseData, 4);" in hook
    assert "if OverVJoyRows(X, Y) then" in hook
    assert "ScrollVJoyRows(-Rows);" in hook
    assert "Result := 1;" in hook
    assert "Result := CallNextHookEx(VJoyWheelHook, Code, WParam, LParam);" in hook
    # Over the rows and the bar: one owner, so the bar scrolls the same way.
    over = _routine(code, "function OverVJoyRows(")
    assert "GetWindowRect(VJoyViewport.Handle, Rows)" in over
    assert "GetWindowRect(VJoyScroll.Handle, Bar)" in over
    assert "(X < Bar.Right)" in over
    scroll = _routine(code, "procedure ScrollVJoyRows(")
    assert "MaxTop := VJoyScroll.Items.Count - VJoyVisibleRows;" in scroll
    assert "SendMessage(VJoyScroll.Handle, LbSetTopIndex, Top, 0);" in scroll
    assert "ShowVJoyTopRow;" in scroll
    assert re.search(r"\bLbSetTopIndex = \$0197;", code)


def test_vjoy_not_installed_gets_the_default_preset_and_no_current_layout() -> None:
    init = _routine(_code(), "procedure InitVJoyChoice;")
    read = init.index("ReadVJoyLayout;")
    assert init.index("if not WizardSilent then") < read
    assert init.index("State <> 'missing' then") < read
    assert "CopyVJoyDevices(VJoyCurrent, VJoyChosen)" in init
    assert "PresetDevices(VJoyPresetOne, VJoyChosen);" in init
    line = _routine(_code(), "function VJoyCurrentLine:")
    assert "State = 'missing' then\n    Result := ''" in line
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "Items.IndexOf(MatchingPreset(VJoyChosen))" in create
    order = _routine(_code(), "procedure InitializeWizard;")
    assert order.index("InitDrivers;") < order.index("InitVJoyChoice;") < order.index(
        "CreateDriverPages;"
    )


def test_the_current_layout_is_read_like_driver_jobs() -> None:
    code = _code()
    run = _routine(code, "function RunVJoyConfig(")
    # Never as administrator; output to a file in setup's temp folder.
    assert "ExecAsOriginalUser(ExpandConstant('{cmd}')" in run
    assert "ewWaitUntilTerminated" in run
    assert "ExpandConstant('{tmp}\\') + VJoyCaptureFile" in run
    assert "LoadStringsFromFile(OutFile, Lines)" in run
    assert "'runas'" not in run
    path = _routine(code, "function VJoyConfigPath:")
    assert r"ExpandConstant('{commonpf64}\vJoy\x64\vJoyConfig.exe')" in path
    layout = _routine(code, "procedure ReadVJoyLayout;")
    assert "RunVJoyConfig('-t', Lines)" in layout
    assert "RunVJoyConfig('-t ' + IntToStr(Ids[J]), Report)" in layout
    # The same rules as parse_status_list and parse_report.
    assert _const("VJoyAxisNames") == " ".join(drivers.VJOY_AXES)
    status = _routine(code, "procedure ParseVJoyStatus(")
    assert "(State = 'MISSING') or (State = 'UNKNOWN')" in status
    report = _routine(code, "procedure ParseVJoyReport(")
    for name in ("'device'", "'buttons'", "'continous povs'", "'continuous povs'",
                 "'axes'"):
        assert name in report
    assert "List[Current].Axes := AxesFromReport(Value);" in report
    # By position, '-' for a missing axis (verified with vJoy 2.2.2.0).
    axes = _routine(code, "function AxesFromReport(")
    assert "for K := 0 to 7 do" in axes
    assert "if Token <> '-' then\n      Result := Result or (1 shl K);" in axes
    assert _axes_from_report("X Y - - - - Sl0 - - - - - - - - -") == ("x", "y", "sl0")


def _axes_from_report(value: str) -> tuple[str, ...]:
    """AxesFromReport's rule, run on a line: bit K set when token K isn't '-'."""
    tokens = value.split()[:8]
    return tuple(drivers.VJOY_AXES[k] for k, t in enumerate(tokens) if t != "-")


def test_existing_devices_change_only_when_edited_with_the_warning() -> None:
    from gremlin.ui import drivers_model

    assert _const("VJoyWarning") == drivers_model.VJOY_WARNING
    assert _const("VJoyWarning") == (
        "Running games will lose the vJoy devices until they restart."
    )
    code = _code()
    edited = _routine(code, "function VJoyEdited:")
    assert "if not VJoyUserEdited then\n    Exit;" in edited
    assert "Result := not SameLayout(VJoyCurrent, VJoyChosen);" in edited
    update = _routine(code, "procedure UpdateVJoyControls;")
    assert "if Active and VJoyEdited then" in update
    assert "VJoyWarningText.Caption := VJoyWarning;" in update
    memo = _routine(code, "function UpdateReadyMemo(")
    assert "Steps := Steps + Space + VJoyWarning + NewLine;" in memo
    assert "' will be deleted.'" in memo
    # Only the user's own changes count as edits (filling the rows is not one).
    for name in ("VJoyAxisClick", "VJoyButtonsChange", "VJoyHatsChange"):
        change = _routine(code, f"procedure {name}(")
        assert "if VJoyFilling then\n    Exit;" in change


def test_vjoy_setup_comes_after_the_vjoy_install_job() -> None:
    code = _code()
    done = _routine(code, "procedure DriversPageDone;")
    tail = done[done.index("I := DriverIndex('vjoy');"):]
    assert "if Drivers[I].Op = 'install' then\n    VJoySetupPlanned := True" in tail
    assert (
        "else if Drivers[I].State <> 'missing' then\n"
        "    VJoySetupPlanned := VJoyEdited;"
    ) in tail
    write = _routine(code, "function WriteJobFile(")
    assert "for Pass := 0 to 1 do" in write
    assert write.index("Json := JobJson(I);") < write.index("Json := VJoySetupJobJson;")
    assert "Index := VJoySetupJob;" in write
    planned = _routine(code, "function DriverJobsPlanned:")
    assert "Result := VJoySetupPlanned;" in planned


def _devices_json(devices: list[drivers.VJoyDevice]) -> str:
    """What VJoyDevicesJson(List) builds, from its own pieces."""
    routine = _routine(_code(), "function VJoyDevicesJson(")
    parts = _assignments(routine, "Result")
    assert len(parts) == 3, parts  # '', ', ', one device
    text = ""
    for k, device in enumerate(devices):
        env = {
            "Result": text,
            "IntToStr(List[K].Id)": str(device.id),
            "AxesJson(List[K].Axes)": json.dumps(list(device.axes)),
            "IntToStr(List[K].Buttons)": str(device.buttons),
            "IntToStr(List[K].Hats)": str(device.hats),
        }
        if k > 0:
            text = _eval(parts[1], env)
            env["Result"] = text
        text = _eval(parts[2], env)
    return text


def _vjoy_job_json(header: str, call: str, devices: list[drivers.VJoyDevice]) -> str:
    routine = _routine(_code(), header)
    (result,) = _assignments(routine, "Result")
    return _eval(result, {call: _devices_json(devices)})


def _vjoy_setup_json(devices: list[drivers.VJoyDevice]) -> str:
    return _vjoy_job_json(
        "function VJoySetupJobJson:", "VJoyDevicesJson(VJoyChosen)", devices
    )


def test_the_vjoy_setup_job_is_one_the_helper_reads(tmp_path: pathlib.Path) -> None:
    app = r"C:\Users\A B\AppData\Local\Programs\Gremlin-Platforms"
    layout = [
        drivers.VJoyDevice(1),
        drivers.VJoyDevice(3, axes=(), buttons=0, hats=0),
        drivers.VJoyDevice(16, axes=("x", "y", "sl0"), buttons=12, hats=1),
    ]
    text = _job_file([
        _job_json("install", "vjoy", "",
                  app + r"\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe"),
        _vjoy_setup_json(layout),
    ])
    assert json.loads(text)["jobs"][1] == {
        "op": "vjoy_setup", "driver": "vjoy", "files": [],
        "devices": [
            {"id": 1, "axes": list(drivers.VJOY_AXES), "buttons": 128, "hats": 4},
            {"id": 3, "axes": [], "buttons": 0, "hats": 0},
            {"id": 16, "axes": ["x", "y", "sl0"], "buttons": 12, "hats": 1},
        ],
    }
    path = tmp_path / "jobs.json"
    path.write_text(text, encoding="utf-8")
    jobs = drivers.read_jobs(path)
    assert [(j.op, j.driver) for j in jobs] == [
        ("install", "vjoy"), ("vjoy_setup", "vjoy")
    ]
    assert jobs[1].files == []
    assert [(d.id, d.axes, d.buttons, d.hats) for d in jobs[1].devices] == [
        (1, drivers.VJOY_AXES, 128, 4), (3, (), 0, 0), (16, ("x", "y", "sl0"), 12, 1)
    ]


def test_the_job_file_names_the_axes_like_drivers_py() -> None:
    # AxesJson writes VJoyAxisNames' names for the set bits, in that order.
    body = _routine(_code(), "function AxesJson(")
    assert "Result := Result + '\"' + AxisName(K) + '\"';" in body
    assert "Result := '[' + Result + ']';" in body
    assert _const("VJoyAxisNames").split() == list(drivers.VJOY_AXES)


def test_the_vjoy_setup_job_has_its_progress_and_result_line() -> None:
    code = _code()
    progress = _routine(code, "function JobProgressText(")
    assert "if I = VJoySetupJob then" in progress
    assert "'Setting up the vJoy devices' + #$2026" in progress
    summary = _routine(code, "procedure BuildDriverSummary;")
    assert "DriverSummary := DriverSummary + VJoySetupResultLine;" in summary
    assert "if VJoySetupRestart then" in summary
    for name in ("ReadDriverResults", "FailOpenJobs"):
        body = _routine(code, ("function " if name == "ReadDriverResults" else
                               "procedure ") + name + "(")
        assert "SetJobResult(J," in body


def test_a_silent_install_never_reads_or_sets_up_vjoy() -> None:
    code = _code()
    planned = _routine(code, "function DriverJobsPlanned:")
    assert planned.index("if WizardSilent then") < planned.index(
        "Result := VJoySetupPlanned;"
    )
    init = _routine(code, "procedure InitVJoyChoice;")
    assert "VJoySetupPlanned := False;" in init
    assert init.index("if not WizardSilent then") < init.index("ReadVJoyLayout;")
    # Only DriversPageDone plans the job, and a silent install never calls it.
    assert re.findall(r"VJoySetupPlanned := True", code) == [
        "VJoySetupPlanned := True"
    ]
    assert "VJoySetupPlanned := True" in _routine(code, "procedure DriversPageDone;")


def test_no_code_line_starts_with_a_hash() -> None:
    # ISPP reads a line starting with '#' as a directive (#13#10 continuations).
    bad = [x for x in _code().splitlines() if x.lstrip().startswith("#")]
    assert bad == []


@pytest.mark.parametrize(
    "name",
    [
        "AddVJoyDevice", "CopyVJoyDevices", "PresetDevices", "SameLayout",
        "MatchingPreset", "VJoyEdited", "NextToken", "VJoyField", "AxesFromReport",
        "ParseVJoyReport", "ParseVJoyStatus", "RunVJoyConfig", "ReadVJoyLayout",
        "InitVJoyChoice", "VJoyLayoutText", "FillVJoyRows", "VJoyRowsEdited",
        "UpdateVJoyControls", "VJoySetupJobJson", "JobState", "SetJobResult",
        "VJoySetupResultLine", "VJoyIdUsed", "IsDigits", "AxisName", "AxisLabel",
        "AxisTicked", "AxesCountOf", "AxesJson", "AxesText", "ShowVJoyTopRow",
        "WatchVJoyScroll", "ScrollVJoyRows", "OverVJoyRows", "VJoyWheelProc",
        "SetWindowsHookEx", "UnhookWindowsHookEx", "CallNextHookEx",
        "GetWindowRect", "IsWindowVisible", "ReadHookLong", "CreateVJoyRows",
        "AddVJoyHeading", "VJoyAxisClick",
        "VJoyButtonsChange", "VJoyHatsChange", "VJoyRemoveClick", "VJoyAddClick",
        "DefaultButtons", "VJoyAlikeWarning", "VJoyActive", "AxisHeading",
        "VJoyIdBusy", "VJoyIndexOf", "VJoyChangedBusy", "VJoyInUseWarning",
        "VJoyNextFreeId", "VJoyAddPreviewText",
    ],
)
def test_vjoy_routines_are_declared_before_use(name: str) -> None:
    code = _strip(_code())
    declared = re.search(rf"\b(?:function|procedure) {name}\b", code)
    assert declared, name
    first_use = re.search(rf"\b{name}\b", code)
    assert first_use and first_use.start() >= declared.start(), name


# -- 01 S193: the Microsoft Visual C++ Runtime ---------------------------------------


def _runtime_install() -> str:
    return _routine(_code(), "procedure InstallRuntime;")


def test_the_runtime_matches_drivers_py() -> None:
    info = drivers.RUNTIME
    assert info.key not in drivers.DRIVERS
    assert _define("RuntimeBundled") == info.bundled_version
    assert _define("RuntimeFile") == info.bundled_file
    assert _define("RuntimeSha256") == info.sha256
    assert _define("RuntimeSigner") == info.signer_prefix
    assert _const("RuntimeName") == info.name
    assert _const("RuntimeArgs") == " ".join(info.install_args)


def test_the_runtime_file_goes_to_tmp_only() -> None:
    files = _section("Files")
    lines = [x for x in files.splitlines() if "Runtime" in x and not x.startswith(";")]
    # dontcopy: never copied to {app}; extracted to {tmp} when it is missing.
    assert lines == ['Source: "drivers\\{#RuntimeFile}"; Flags: dontcopy']
    assert "skipifsourcedoesntexist" not in lines[0]
    assert "ExtractTemporaryFile('{#RuntimeFile}');" in _runtime_install()
    assert r"ExpandConstant('{tmp}\{#RuntimeFile}')" in _runtime_install()
    # The old [Files]/[Run] copy from dist\ is gone.
    assert r"dist\vc_redist" not in _iss().lower()
    assert r"{tmp}\vc_redist" not in _iss().lower()


def test_runtime_detection_reads_drivers_py_key_in_both_views() -> None:
    assert _const("RuntimeKey") == drivers.RUNTIME_KEYS[0]
    # The 32-bit view of RuntimeKey is drivers.py's WOW6432Node key.
    assert drivers.RUNTIME_KEYS[1] == drivers.RUNTIME_KEYS[0].replace(
        "SOFTWARE\\", "SOFTWARE\\WOW6432Node\\", 1
    )
    found = _routine(_code(), "function RuntimeInstalled:")
    assert found.index("HKLM64, RuntimeKey, 'Installed'") < found.index(
        "HKLM32, RuntimeKey, 'Installed'"
    )
    assert found.count("Result := Value = 1;") == 2


def test_the_runtime_is_the_drivers_box_first_row_ticked_and_greyed() -> None:
    """01 S193 (2026-11-21, 8a): the required parent row, status on the right."""
    assert _const("RuntimeName") == "Microsoft Visual C++ Runtime"
    assert not re.search(r"^  RuntimeLine = ", _code(), re.M)
    fill = _routine(_code(), "procedure FillDriverList;")
    # Level 0, ticked, not enabled (greyed: can't be unticked).
    parent = ("RuntimeRow := DriverList.AddCheckBox(RuntimeName, Status, 0, True, "
              "False,\n    False, False, nil);")
    assert parent in fill
    assert fill.index("DriverList.Items.Clear;") < fill.index(parent)
    assert fill.index(parent) < fill.index("for I := 0 to GetArrayLength(Drivers)")
    # Status like the drivers': "not installed", else the installed version.
    assert "if RuntimeMissing then\n    Status := 'not installed'" in fill
    assert "Status := RuntimeInstalledVersion;" in fill
    assert "AddGroup(RuntimeName" not in _code()
    # Shown on every install, not only when the runtime is missing.
    assert "if RuntimeMissing then\n    DriverList.AddGroup" not in fill
    # RuntimeInstalledVersion comes before its first use (Pascal order).
    code = _code()
    assert code.index("function RuntimeInstalledVersion:") < code.index(
        "procedure FillDriverList;"
    )
    assert "RuntimeMissing := not RuntimeInstalled;" in _routine(
        _code(), "procedure InitDrivers;"
    )


def test_the_runtime_installs_first() -> None:
    code = _code()
    step = _routine(code, "procedure CurStepChanged(")
    # ssInstall comes before the files are copied, ssPostInstall's driver jobs
    # and every [Run] entry, so nothing can start the program before it.
    assert step.index("if CurStep = ssInstall then\n    InstallRuntime;") < step.index(
        "RunDriverJobs;"
    )
    run = [x for x in _section("Run").splitlines() if x and not x.startswith(";")]
    assert run
    assert all(x.startswith(r'Filename: "{app}\{#MyAppExeName}"') for x in run)
    assert code.index("procedure InstallRuntime;") < code.index(
        "procedure CurStepChanged("
    )


def test_the_runtime_runs_elevated_with_the_switches_and_bounded_wait() -> None:
    body = _runtime_install()
    # Started elevated straight from setup's window (answer 4a), so the prompt
    # names Microsoft's installer (answer 30a) and opens in front of setup.
    assert "{cmd}" not in body and "ShellExec(" not in body
    assert "powershell" not in body.lower()
    assert (
        "StartElevated(Path, RuntimeArgs, ExpandConstant('{tmp}'), SW_HIDE,\n"
        "        Process, ErrorCode)"
    ) in body
    assert _const("RuntimeArgs") == "/install /quiet /norestart"
    assert "for Tick := 1 to RuntimeWaitTicks do" in body
    assert "WaitForSingleObject(Process, 0) = WaitObject0" in body
    assert "Sleep(RuntimeWaitStep);" in body
    assert "GetExitCodeProcess(Process, Code)" in body
    assert "CloseHandle(Process);" in body
    ticks = int(_const_int("RuntimeWaitTicks"))
    assert ticks * int(_const_int("RuntimeWaitStep")) == 600_000
    assert "'not installed: it did not finish within 10 minutes'" in body
    # The bundled copy is checked before it runs (SHA-256 and signer).
    assert body.index("RuntimeFileTrusted(Path)") < body.index("StartElevated(")
    trusted = _routine(_code(), "function RuntimeFileTrusted(")
    assert "GetSHA256OfFile(Path)" in trusted and "'{#RuntimeSha256}'" in trusted
    assert "RuntimeSignedByMicrosoft(Path)" in trusted
    signed = _routine(_code(), "function RuntimeSignedByMicrosoft(")
    assert "Get-AuthenticodeSignature" in signed and "{#RuntimeSigner}" in signed
    assert "$s.Status -eq ''Valid''" in signed


def _const_int(name: str) -> str:
    found = re.search(rf"^  {name} = (\d+);$", _code(), re.M)
    assert found, name
    return found.group(1)


def test_runtime_exit_codes() -> None:
    assert int(_const_int("RuntimeDoneCode")) == drivers.RUNTIME_DONE_CODES[0]
    assert int(_const_int("RuntimeNewerCode")) == drivers.RUNTIME_DONE_CODES[1]
    assert int(_const_int("RuntimeRestartCode")) == drivers.RUNTIME_RESTART_CODE
    assert drivers.RUNTIME.restart_codes == (drivers.RUNTIME_RESTART_CODE,)
    codes = _routine(_code(), "function RuntimeCodeResult(")
    restart = codes[
        codes.index("Code = RuntimeRestartCode"):
        codes.index("  else\n    Result := 'not installed")
    ]
    assert "RuntimeNeedRestart := True;" in restart
    assert codes.count("RuntimeNeedRestart := True;") == 1
    assert "'not installed (error ' + IntToStr(Code)" in codes
    assert "Result := DriversNeedRestart or RuntimeNeedRestart;" in _routine(
        _code(), "function NeedRestart:"
    )
    page = _routine(_code(), "procedure CurPageChanged(")
    assert "RuntimeName + ': ' + RuntimeResult" in page
    assert "if DriversNeedRestart or RuntimeNeedRestart then" in page


def test_a_runtime_failure_never_stops_the_install() -> None:
    body = _runtime_install()
    assert body.index("try") < body.index("ExtractTemporaryFile(")
    assert "except" in body and "GetExceptionMessage" in body
    assert "'not installed: administrator permission was not given'" in body
    assert "Abort" not in body and "RaiseException" not in body
    assert "Runtime" not in _routine(_code(), "function PrepareToInstall(")


def test_a_silent_install_installs_the_runtime() -> None:
    body = _runtime_install()
    # Only "already installed" (and no newer download) skips it; a silent
    # install only skips the page.
    assert body.split("begin", 1)[1].lstrip().startswith(
        "if RuntimeInstalled and (RuntimeNewestPath = '') then"
    )
    assert "if WizardSilent then\n    Exit" not in body
    assert "InstallRuntime;" in _routine(_code(), "procedure CurStepChanged(")
    # Silent installs still run no driver jobs, and never restart on their own.
    planned = _routine(_code(), "function DriverJobsPlanned:")
    assert "if WizardSilent then\n    Exit;" in planned
    codes = _routine(_code(), "function RuntimeCodeResult(")
    assert "if not WizardSilent then\n      RuntimeNeedRestart := True;" in codes


def test_the_runtime_shows_its_progress_text() -> None:
    body = _runtime_install()
    assert "SetRuntimeText('Installing the ' + RuntimeName + #$2026);" in body
    assert _const("RuntimeName") + "…" == "Microsoft Visual C++ Runtime…"


def test_the_runtime_bar_moves_and_the_driver_bar_is_normal() -> None:
    body = _runtime_install()
    assert body.index("ProgressBar.Style := npbstMarquee;") < body.index(
        "RuntimeProgressPage.Show;"
    )
    # Back to normal before the page is hidden for good.
    assert body.index("RuntimeProgressPage.Hide;") < body.index(
        "RuntimeProgressPage.ProgressBar.Style := npbstNormal;"
    )
    # SetProgress each tick pumps the messages the marquee needs.
    assert "RuntimeProgressPage.SetProgress(Tick, RuntimeWaitTicks);" in body
    jobs = _routine(_code(), "procedure RunHelperJobs(")
    assert jobs.index("DriverProgressPage.ProgressBar.Style := npbstNormal;") < (
        jobs.index("DriverProgressPage.Show;")
    )
    assert "npbstMarquee" not in jobs


def test_uninstall_never_touches_the_runtime() -> None:
    iss = _iss()
    assert "[UninstallRun]" not in iss
    assert "VisualStudio" not in _section("UninstallDelete")
    assert "Runtime" not in _section("UninstallDelete")
    for x in ("RegDeleteKey", "/uninstall"):
        assert x not in iss
    assert iss.count("RegDeleteValue(") == 1  # 01 S194: the Run value only


def test_a_refused_runtime_prompt_is_reported_as_refused() -> None:
    body = _runtime_install()
    # ShellExecuteEx fails with Windows' error 1223 when the prompt is refused:
    # the wait never starts, so a refusal is never a hang.
    assert "UacRefusedCode = 1223;" in _code()
    refused = body.index("else if ErrorCode = UacRefusedCode then")
    assert body.index(
        "RuntimeResult := 'not installed: administrator permission was not given'"
    ) > refused
    assert body.index("StartElevated(") < refused
    assert "RuntimeResult := 'not installed: ' + SysErrorMessage(ErrorCode);" in body


# -- 01 S193 (answer 6a): Microsoft's newest runtime -------------------------------


def test_the_newest_runtime_is_an_unticked_child_row_on_every_install() -> None:
    """01 S193 (2026-11-21, 9b): indented under the runtime row, in the box."""
    assert _const("RuntimeNewestCaption") == (
        "Check and download an updated Visual C++ Runtime"
    )
    fill = _routine(_code(), "procedure FillDriverList;")
    # Level 1 (indented), unticked, enabled, not ticked by its parent.
    child = ("RuntimeNewestRow := DriverList.AddCheckBox(RuntimeNewestCaption, '', 1,"
             "\n    False, True, False, False, nil);")
    assert child in fill
    parent = fill.index("RuntimeRow := DriverList.AddCheckBox(")
    assert parent < fill.index(child) < fill.index("for I := 0 to GetArrayLength")
    at = fill.index(child)
    assert "if RuntimeMissing then" not in fill[at - 120: at]
    # The old separate tick box under the box is gone.
    assert "RuntimeNewestBox" not in _code()
    done = _routine(_code(), "procedure DriversPageDone;")
    assert "RuntimeNewestWanted := DriverList.Checked[RuntimeNewestRow];" in done
    click = _routine(_code(), "function NextButtonClick(")
    # Silent installs (no page) never check: the Exit comes first.
    assert click.index("if WizardSilent then\n    Exit;") < click.index(
        "CheckNewestRuntime;"
    )
    memo = _routine(_code(), "function UpdateReadyMemo(")
    assert "if RuntimeNewestWanted then" in memo
    # The Ready page follows the row's wording.
    assert "'Check and download an updated Visual C++ ' +" in memo
    assert "Check for an updated" not in _code()


def test_the_runtime_parent_row_stays_ticked() -> None:
    """Clicking the child never unticks the required parent (01 S193)."""
    keep = _routine(_code(), "procedure KeepRuntimeTicked;")
    assert "if DriverList.State[RuntimeRow] = cbChecked then\n    Exit;" in keep
    assert "Child := DriverList.Checked[RuntimeNewestRow];" in keep
    assert "DriverList.Checked[RuntimeRow] := True;" in keep
    # The child keeps its own tick if setting the parent changed it.
    assert "DriverList.Checked[RuntimeNewestRow] := Child;" in keep
    click = _routine(_code(), "procedure DriverListClickCheck(")
    assert click.index("KeepRuntimeTicked;") < click.index("UpdateVJoyControls;")
    fill = _routine(_code(), "procedure FillDriverList;")
    assert fill.rstrip().endswith("KeepRuntimeTicked;\nend;")
    # Five rows (runtime, its child, three drivers) fit in the box.
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "DriverList.Height := ScaleY(102);" in create
    assert "if RuntimeMissing then" not in create


def test_layout_b_line_then_bold_heading_with_preset_on_the_right() -> None:
    """06 S185 layout b (2026-11-21)."""
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "Line := TBevel.Create(DriversPage);" in create
    assert "Line.Shape := bsTopLine;" in create
    assert "Line.Top := DriverList.Top + DriverList.Height + ScaleY(6);" in create
    assert "VJoyLabel.Caption := 'vJoy devices';" in create
    assert "VJoyLabel.Font.Style := [fsBold];" in create
    assert "'vJoy devices:'" not in create
    assert "PresetLabel.Caption := 'Preset';" in create
    # Preset and its box right-aligned on the heading's line.
    assert (
        "VJoyPresetBox.Left := DriversPage.SurfaceWidth - VJoyPresetBox.Width;"
    ) in create
    assert (
        "PresetLabel.Left := VJoyPresetBox.Left - ScaleX(6) - PresetLabel.Width;"
    ) in create
    assert "PresetLabel.Top := VJoyLabel.Top;" in create
    assert "VJoyLabel.Top := VJoyPresetBox.Top + ScaleY(3);" in create
    assert "VJoyPresetBox.Top := Line.Top + ScaleY(6);" in create
    assert create.index("Line := TBevel") < create.index("VJoyViewport := TPanel")


def test_layout_b_headings_sit_in_a_grey_band_inside_the_box() -> None:
    code = _code()
    create = _routine(code, "procedure CreateDriverPages;")
    assert "VJoyHeadBand.Parent := VJoyViewport;" in create
    assert "VJoyHeadBand.Color := clBtnFace;" in create
    assert "VJoyHeadBand.Top := 0;" in create
    assert "VJoyHeadBand.Height := BandH;" in create
    assert "VJoyRowsClip.Top := BandH;" in create
    heading = _routine(code, "procedure AddVJoyHeading(")
    assert "Heading.Parent := VJoyHeadBand;" in heading
    # The band exists before the headings go in it.
    assert create.index("VJoyHeadBand := TPanel") < create.index(
        "AddVJoyHeading(AxisHeading(K)"
    )
    # Rows below the band; the band's height comes off the rows' room.
    assert (
        "VJoyVisibleRows := (VJoyViewport.ClientHeight - BandH) div VJoyRowHeight;"
    ) in create


def test_layout_b_rows_are_padded_from_the_left_border() -> None:
    create = _routine(_code(), "procedure CreateDriverPages;")
    assert "RowLeft := ScaleX(6);" in create
    rows = "CreateVJoyRows(RowLeft, NameW, BoxW, ButtonsW, HatsW, RemoveW, Gap);"
    assert rows in create
    assert "CreateVJoyRows(0," not in create
    # The headings use the same offset as the rows' columns.
    assert "X := RowLeft + NameW;" in create
    assert "RowLeft - NameW - ButtonsW" in create  # tick box width allows for it


def test_layout_b_bottom_line_warning_left_showing_right() -> None:
    create = _routine(_code(), "procedure CreateDriverPages;")
    # 01 S187 (3a): no Add device button on the bottom line any more.
    assert "LineTop := DriversPage.SurfaceHeight - ScaleY(21);" in create
    assert "VJoyWarningText.Left := 0;" in create
    assert "VJoyShowingText.Alignment := taRightJustify;" in create
    assert "VJoyShowingText.Left := DriversPage.SurfaceWidth - ShowingW;" in create
    assert "VJoyShowingText.Top := LineTop + ScaleY(4);" in create
    # The warning between them, never over the Showing line.
    assert (
        "VJoyWarningText.Width := VJoyShowingText.Left - ScaleX(8) - "
        "VJoyWarningText.Left;"
    ) in create
    assert "VJoyWarningText.WordWrap := True;" in create
    # Top to bottom: box, hint, bottom line.
    assert create.index("Bottom := VJoyHint.Top - ScaleY(2);") > create.index(
        "VJoyHint.Top :="
    )


def test_the_newest_runtime_link_and_head_request() -> None:
    assert _const("RuntimeNewestUrl") == "https://aka.ms/vs/17/release/vc_redist.x64.exe"
    resolve = _routine(_code(), "function ResolveRuntimeUrl(")
    assert "CreateOleObject('WinHttp.WinHttpRequest.5.1')" in resolve
    assert "Request.Open('HEAD', RuntimeNewestUrl, False);" in resolve
    assert "Final := Request.Option(1);" in resolve
    # Bounded: four timeouts of RuntimeHeadTimeout, at most 10 s in all.
    assert resolve.count("RuntimeHeadTimeout") == 4
    assert 4 * int(_const_int("RuntimeHeadTimeout")) <= 10_000
    assert "except" in resolve


def _url_sha256(url: str) -> str:
    """UrlSha256's rule: the last path part of 64 hex digits, lower case."""
    found = ""
    for part in url.split("/"):
        if len(part) == 64 and all(c in "0123456789abcdef" for c in part.lower()):
            found = part.lower()
    return found


def test_the_sha_in_microsofts_path_decides_the_download() -> None:
    sha = _define("RuntimeSha256")
    url = (
        "https://download.visualstudio.microsoft.com/download/pr/"
        "1754ea58-11a6-44ab-a262-696e194ce543/" + sha.upper() + "/VC_redist.x64.exe"
    )
    assert _url_sha256(url) == sha
    assert _url_sha256("https://example.invalid/a/VC_redist.x64.exe") == ""
    body = _routine(_code(), "function UrlSha256(")
    assert "if Length(Part) <> 64 then" in body
    assert "Part := Lowercase(Part);" in body
    assert "Pos(Copy(Part, K, 1), '0123456789abcdef') = 0" in body
    check = _routine(_code(), "procedure CheckNewestRuntime;")
    assert "if not RuntimeNewestWanted then\n    Exit;" in check
    same = check.index("if Sha = Lowercase('{#RuntimeSha256}') then")
    # The same copy: logged, nothing downloaded.
    assert check.index("RuntimeNewestNote := RuntimeSameNote;", same) < check.index(
        "DriverDownloadPage.Download;"
    )
    assert _const("RuntimeSameNote") == "Microsoft's newest is the copy setup carries"
    # A download is checked like the bundled copy, then kept only when newer
    # than both the bundled copy and the installed runtime.
    assert check.index("DriverDownloadPage.Download;") < check.index(
        "RuntimeSignedByMicrosoft(Path)"
    )
    assert "Lowercase(GetSHA256OfFile(Path)) <> Sha" in check
    assert "GetVersionNumbersString(Path, Version)" in check
    assert "CompareVersions(Version, '{#RuntimeBundled}') <= 0" in check
    assert "CompareVersions(Version, Installed) <= 0" in check
    assert check.index("CompareVersions(Version, Installed)") < check.index(
        "RuntimeNewestPath := Path;"
    )
    assert "except" in check
    installed = _routine(_code(), "function RuntimeInstalledVersion:")
    assert "MachineValue(RuntimeKey, 'Version')" in installed


def test_the_last_page_says_which_runtime_copy_was_used() -> None:
    body = _runtime_install()
    newest = body.index("if RuntimeNewestPath <> '' then")
    assert body.index("Path := RuntimeNewestPath;", newest) < body.index(
        "ExtractTemporaryFile("
    )
    assert "Used := 'Microsoft''s newest, ' + RuntimeNewestVersion;" in body
    assert "Used := 'the copy setup carries, {#RuntimeBundled}';" in body
    assert "RuntimeResult := RuntimeResult + ' (' + Used + ')';" in body
    # Installed and nothing newer to run: the box's finding still shows.
    assert "RuntimeResult := 'already installed; ' + RuntimeNewestNote;" in body


def test_the_launch_box_is_not_hidden_by_the_driver_results() -> None:
    # Answer 31a: after driver jobs the last page's taller text covered the
    # Launch box, which Setup had placed under its own shorter text. With no
    # restart it is moved under the new text; driver jobs never hide it.
    page = _routine(_code(), "procedure CurPageChanged(")
    adjust = page.index("WizardForm.FinishedLabel.AdjustHeight;")
    move = page.index("if not (DriversNeedRestart or RuntimeNeedRestart) then")
    assert adjust < move
    assert (
        "WizardForm.RunList.Top := WizardForm.FinishedLabel.Top +\n"
        "      WizardForm.FinishedLabel.Height + ScaleY(12);"
    ) in page[move:]
    # The box's height is fitted to its items before it is moved (Setup sizes
    # it to fill the page, so the clamp would put it back under the label).
    height = page.index("WizardForm.RunList.Height := ScaleY(20)", move)
    top = page.index("WizardForm.RunList.Top :=", move)
    assert height < top
    assert "WizardForm.RunList.Visible := True;" in page[move:]
    assert "WizardForm.RunList.BringToFront;" in page[move:]
    assert "Log('Finish page: RunList Top='" in page
    assert "FinishedPage.ClientHeight=" in page
    offer = _routine(_code(), "function OfferLaunch:")
    assert "DriverJobsPlanned" not in offer and "DriverSummary" not in offer
    run = _section("Run").splitlines()
    launch = next(x for x in run if 'Description: "Launch' in x)
    assert "unchecked" not in launch and "Check: OfferLaunch" in launch


def test_the_drivers_page_has_no_paragraph_under_the_runtime_box() -> None:
    """01 S193 (answer 1a, 2026-11-21): the paragraph under the box is gone."""
    page = _routine(_code(), "procedure CreateDriverPages;")
    assert "Note" not in page.replace("RuntimeNewestNote", "")
    assert "Ticked drivers are installed after" not in _code()
    assert "RuntimeNewestBox" not in page
    assert "Platforms''s" not in _code()


def test_the_vjoy_rows_sit_in_one_bordered_white_box() -> None:
    """01 S187 (answer 2b, 2026-11-21): as Git for Windows' Select Components."""
    code = _code()
    create = _routine(code, "procedure CreateDriverPages;")
    assert "VJoyViewport.BorderStyle := bsSingle;" in create
    assert "VJoyViewport.Color := clWindow;" in create
    assert "VJoyViewport.ParentBackground := False;" in create
    # The bar runs down the inside of the box's right edge, borderless and
    # wider than SM_CXVSCROLL so Windows always has room to draw it.
    assert "VJoyScroll.Parent := VJoyRowsClip;" in create
    assert "VJoyScroll.BorderStyle := bsNone;" in create
    assert "VJoyScroll.Left := VJoyRowsClip.ClientWidth - ScrollW;" in create
    assert "ScrollW := BarW + ScaleX(4);" in create
    assert "BarW := GetSystemMetrics(2);" in create
    # Rows follow from the box's real inside height; headings stay above it.
    assert (
        "VJoyVisibleRows := (VJoyViewport.ClientHeight - BandH) div VJoyRowHeight;"
    ) in create
    assert (
        "VJoyViewport.Height := BandH + VJoyVisibleRows * VJoyRowHeight + EdgeW;"
    ) in create
    # Layout b: the headings are inside the box (its grey band).
    heads = create.index("AddVJoyHeading('Hats'")
    assert heads > create.index("VJoyViewport := TPanel")
    # The bar shows only when the rows don't fit; without it, full width.
    fill = _routine(code, "procedure FillVJoyRows;")
    assert "VJoyScroll.Visible := Lines > VJoyVisibleRows;" in fill
    assert "VJoyRowsPanel.Width := VJoyScroll.Left\n    else" in fill
    assert "VJoyRowsPanel.Width := VJoyRowsClip.ClientWidth;" in fill
    # The item height comes back if the list box's window is made again.
    top = _routine(code, "procedure ShowVJoyTopRow;")
    assert "LbGetItemHeight, 0, 0) <> VJoyRowHeight then" in top
    assert re.search(r"\bLbGetItemHeight = \$01A1;", code)
    assert "VJoyScroll.ItemIndex := -1;" in _routine(code, "procedure VJoyScrollClick(")
    # At least 4 rows at 100%: a taller wizard (user 2026-11-21); 137 keeps
    # 5 with layout b (five driver-box rows, the line and heading, the grey
    # band, the hint and the bottom line).
    assert "WizardSizePercent=120,137" in _section("Setup")


def test_the_showing_line_under_the_box() -> None:
    code = _code()
    line = _routine(code, "function VJoyShowingLine(")
    assert "Result := 'No vJoy devices'" in line
    assert "Result := 'Showing 1 device'" in line
    assert "Result := 'Showing all ' + IntToStr(N) + ' devices'" in line
    assert "Result := 'Showing ' + IntToStr(Top + 1) + '-' +" in line
    assert "IntToStr(Last) + ' of ' + IntToStr(N) + ' devices';" in line
    # The add row is a list line but not a device: Last stops at N.
    assert "Last := Top + VJoyVisibleRows;\n  if Last > N then\n    Last := N;" in line
    assert "else if (Top = 0) and (Last = N) then" in line
    # Updated by the one scroll sync (wheel, timer, bar, add/remove refill);
    # it counts devices, never the list's lines.
    top = _routine(code, "procedure ShowVJoyTopRow;")
    caption = (
        "VJoyShowingText.Caption := VJoyShowingLine(Top, GetArrayLength(VJoyChosen));"
    )
    assert caption in top
    fill = _routine(code, "procedure FillVJoyRows;")
    assert "VJoyTopRow := -1;\n    ShowVJoyTopRow;" in fill
    create = _routine(code, "procedure CreateDriverPages;")
    showing = create.index("VJoyShowingText := TNewStaticText")
    assert showing < create.index("FillVJoyRows;")
    assert "Bottom := VJoyHint.Top - ScaleY(2);" in create


def test_vjoy_layout_text_uses_singular_for_one() -> None:
    count = _routine(_code(), "function CountText(")
    assert "if Count = 1 then\n    Result := '1 ' + One" in count
    assert "else\n    Result := IntToStr(Count) + ' ' + Many;" in count
    device = _routine(_code(), "function VJoyDeviceText(")
    assert "AxesText(D.Axes)" in device
    axes = _routine(_code(), "function AxesText(")
    # driver_jobs.describe_device: "3 axes (X, Y, S1)", "8 axes (X-S2)".
    assert "CountText(AxesCountOf(Mask), 'axis', 'axes')" in axes
    assert "' (' + AxisLabel(0) + '-' + AxisLabel(7) + ')'" in axes
    assert "Names := Names + ', ';" in axes
    from gremlin import driver_jobs
    assert driver_jobs.describe_device(
        drivers.VJoyDevice(1, axes=("x", "y", "sl0"), buttons=8, hats=0)
    ) == "3 axes (X, Y, S1), 8 buttons, 0 hats"
    full = driver_jobs.describe_device(drivers.VJoyDevice(1))
    assert full.startswith("8 axes (X-S2)")
    assert "CountText(D.Buttons, 'button', 'buttons')" in device
    assert "CountText(D.Hats, 'hat', 'hats')" in device
    assert "' hats'" not in device and "' axes, '" not in device
    memo = _routine(_code(), "function UpdateReadyMemo(")
    assert "device(s)" not in memo
    assert (
        "CountText(GetArrayLength(VJoyChosen),\n        'vJoy device', 'vJoy devices')"
    ) in memo


# -- 01 S187 (2026-11-22): S1/S2 headings, one axis stays, devices in use ------------


def test_the_headings_are_axis_names_short_names() -> None:
    """D-AXIS-NAMES: one table; vJoyConfig still gets sl0/sl1."""
    from gremlin import axis_names

    assert _const("VJoyAxisLabels").split() == [a.short for a in axis_names.AXES]
    assert _const("VJoyAxisLabels").split() == list(drivers.VJOY_AXIS_LABELS)
    assert _const("VJoyAxisNames").split() == [a.vjoy_config for a in axis_names.AXES]
    heading = _routine(_code(), "function AxisHeading(")
    assert "Names := VJoyAxisLabels;" in heading
    rows = _routine(_code(), "procedure CreateVJoyRows(")
    assert "Box.Hint := AxisHeading(K);" in rows
    # The bit mask and the job file's names are unchanged.
    assert "VJoyAllAxes = 255;" in _code()
    assert "AxisName(K)" in _routine(_code(), "function AxesJson(")


def test_the_last_ticked_axis_cant_be_unticked() -> None:
    """D-01-VJOY-ONE-AXIS (drivers.can_untick_axis)."""
    axis = _routine(_code(), "procedure VJoyAxisClick(")
    guard = (
        "if (not TNewCheckBox(Sender).Checked) and\n"
        "    ((VJoyChosen[R].Axes and (VJoyAllAxes - (1 shl K))) = 0) then"
    )
    assert guard in axis
    # Re-ticked without counting as an edit, before the mask changes.
    retick = axis.index("TNewCheckBox(Sender).Checked := True;")
    assert axis.index("VJoyFilling := True;") < retick
    assert axis.index("Exit;", retick) < axis.index("VJoyChosen[R].Axes or (1 shl K)")
    # The same rule as drivers.can_untick_axis.
    only = drivers.VJoyDevice(1, ("x",), 8, 0)
    assert not drivers.can_untick_axis(only, "x")
    assert drivers.can_untick_axis(drivers.VJoyDevice(1, ("x", "y"), 8, 0), "x")


def _in_use_sentence(ids: list[int]) -> str:
    """What VJoyInUseWarning builds for these ids, from its own pieces."""
    one = re.search(r"^  VJoyInUseOne = (.*?);$", _code(), re.M | re.S)
    many = re.search(r"^  VJoyInUseMany = (.*?);$", _code(), re.M | re.S)
    assert one and many
    names = [f"vJoy {i}" for i in ids]
    who = names[0]
    for j, name in enumerate(names[1:], start=1):
        who += (" and " if j == len(names) - 1 else ", ") + name
    return who + _pascal_string((one if len(ids) == 1 else many).group(1))


def test_the_in_use_warning_matches_drivers_py() -> None:
    """D-01-VJOY-IN-USE: same wording as Tools › Drivers, 1, 2 and 3 ids."""
    for ids in ([4], [1, 4], [1, 2, 4]):
        assert _in_use_sentence(ids) == drivers.in_use_warning(ids)
    warn = _routine(_code(), "function VJoyInUseWarning(")
    assert "Result := Result + ' and vJoy ' + IntToStr(Ids[J])" in warn
    assert "Result := Result + ', vJoy ' + IntToStr(Ids[J]);" in warn
    assert "if G = 1 then\n    Result := Result + VJoyInUseOne" in warn
    assert _const("VJoyInUseText") == "in use by another program"


def test_busy_or_owned_devices_are_read_from_the_status_lines() -> None:
    code = _code()
    status = _routine(code, "procedure ParseVJoyStatus(")
    assert "var Ids, Busy: TArrayOfInteger" in status
    assert "if (State = 'BUSY') or (State = 'OWNED') then" in status
    layout = _routine(code, "procedure ReadVJoyLayout;")
    assert "ParseVJoyStatus(Lines, Ids, VJoyBusy);" in layout
    # D-01-VJOY-IN-USE (1a): the row's name turns red and bold and says so on
    # hover; no extra column, the tick columns keep their widths.
    fill = _routine(code, "procedure FillVJoyRows;")
    busy = fill[fill.index("if VJoyIdBusy(VJoyChosen[R].Id) then"):]
    for line in (
        "VJoyRowNames[R].Font.Color := clRed;",
        "VJoyRowNames[R].Font.Style := [fsBold];",
        "VJoyRowNames[R].Hint := VJoyInUseText;",
        "VJoyRowNames[R].ShowHint := True;",
    ):
        assert line in busy
    # Rows are reused, so a free device's name goes back to normal.
    for line in (
        "VJoyRowNames[R].Font.Color := clWindowText;",
        "VJoyRowNames[R].Font.Style := [];",
        "VJoyRowNames[R].ShowHint := False;",
    ):
        assert line in busy
    stripped = _strip(code)
    for gone in ("VJoyRowBusy", "VJoyInUseW", "InUseRoom"):
        assert not re.search(rf"\b{gone}\b", stripped), gone
    create = _routine(code, "procedure CreateDriverPages;")
    assert "HatsW - RemoveW - 4 * Gap) div 8;" in create


def test_next_asks_before_changing_a_device_in_use() -> None:
    code = _code()
    changed = _routine(code, "procedure VJoyChangedBusy(")
    assert "if not VJoyEdited then\n    Exit;" in changed
    assert "if N < 0 then\n      Changed := True" in changed
    assert "(VJoyChosen[N].Axes <> VJoyCurrent[C].Axes)" in changed
    nxt = _routine(code, "function NextButtonClick(")
    asked = nxt.index("MsgBox(VJoyInUseWarning(Busy), mbConfirmation, MB_YESNO)")
    # After the silent exit, before the alike question; No stays on the page.
    assert nxt.index("if WizardSilent then\n    Exit;") < asked
    assert asked < nxt.index("VJoyAlikeWarning")
    assert nxt.index("Result := False;", asked) < nxt.index("VJoyAlikeWarning")


# -- 01 S187 (2026-11-22, 3a/4a): "+ Add device" row, short axis names in Now: ------


def _pascal_axes_text(mask: int) -> str:
    """The .iss AxesText on one mask, from its own lines and constants."""
    body = _routine(_code(), "function AxesText(")
    assert "' (' + AxisLabel(0) + '-' + AxisLabel(7) + ')'" in body
    assert "Names := Names + AxisLabel(K);" in body
    assert "Result := AxisHeading(K);" in _routine(_code(), "function AxisLabel(")
    labels = _const("VJoyAxisLabels").split()
    ticked = [labels[k] for k in range(8) if mask & (1 << k)]
    n = len(ticked)
    text = f"{n} {'axis' if n == 1 else 'axes'}"
    if mask == int(_const_int("VJoyAllAxes")):
        return f"{text} ({labels[0]}-{labels[7]})"
    return f"{text} ({', '.join(ticked)})" if ticked else text


def test_setup_now_line_names_axes_like_drivers_axis_label() -> None:
    """4a: setup's "Now:" axes use drivers.axis_label's short names."""
    from gremlin import driver_jobs

    assert [drivers.axis_label(a) for a in drivers.VJOY_AXES] == (
        _const("VJoyAxisLabels").split()
    )
    names = drivers.VJOY_AXES
    for picked in (("x",), ("x", "y", "sl0"), ("rx", "ry", "rz", "sl1"), (), names):
        mask = sum(1 << names.index(a) for a in picked)
        dev = drivers.VJoyDevice(1, axes=tuple(picked), buttons=8, hats=0)
        want = driver_jobs.describe_device(dev).split(", 8 buttons")[0]
        assert _pascal_axes_text(mask) == want
    assert "AxesText(D.Axes)" in _routine(_code(), "function VJoyDeviceText(")
    assert "UpperCase(AxisName" not in _code()


def test_the_add_row_is_the_lists_last_row() -> None:
    """3a: "+ Add device" scrolls with the rows, the whole row clicks, gone at 16."""
    code = _code()
    assert _const("VJoyAddText") == "+ Add device"
    create = _routine(code, "procedure CreateDriverPages;")
    assert "VJoyAddRow := TPanel.Create(DriversPage);" in create
    assert "VJoyAddRow.Parent := VJoyRowsPanel;" in create  # scrolls with the rows
    assert "VJoyAddRow.Height := VJoyRowHeight;" in create
    assert "VJoyAddLabel.Caption := VJoyAddText;" in create
    assert "VJoyAddPreview.Font.Color := clGrayText;" in create
    for part in ("VJoyAddRow", "VJoyAddLabel", "VJoyAddPreview"):
        assert f"{part}.Cursor := crHandPoint;" in create
        assert f"{part}.OnClick := @VJoyAddClick;" in create
    for part in ("VJoyAddLabel", "VJoyAddPreview"):
        assert f"{part}.Parent := VJoyAddRow;" in create
    fill = _routine(code, "procedure FillVJoyRows;")
    assert "VJoyAddRow.Visible := N < VJoyMaxDevices;" in fill
    assert "Lines := N + 1;\n      VJoyAddRow.Top := N * VJoyRowHeight;" in fill
    preview = (
        "VJoyAddPreview.Caption := "
        "VJoyAddPreviewText(VJoyNextFreeId(VJoyChosen));"
    )
    assert preview in fill
    assert "VJoyRowsPanel.Height := Lines * VJoyRowHeight;" in fill
    assert "for R := 1 to Lines do\n      VJoyScroll.Items.Add('');" in fill
    assert "VJoyAddRow.Width := VJoyRowsPanel.Width;" in fill
    update = _routine(code, "procedure UpdateVJoyControls;")
    assert "VJoyAddRow.Enabled := Active;" in update
    # The click adds the countdown device in number order.
    add = _routine(code, "procedure VJoyAddClick(")
    assert "AddVJoyDevice(VJoyChosen, Id, VJoyAllAxes, DefaultButtons(Id), " in add
    assert "FillVJoyRows;\n  VJoyRowsEdited;" in add


def test_no_add_device_button_is_left() -> None:
    code = _strip(_code())
    assert "VJoyAddButton" not in code
    assert not re.search(r"Caption := 'Add device'", code)
    buttons = re.findall(r"(\w+) := TNewButton\.Create", code)
    assert buttons == ["Button"]  # only the rows' remove buttons


def test_the_add_rows_preview_names_the_next_device() -> None:
    """3a: "vJoy 3 · 126 buttons": the lowest free id, 129 - id buttons."""
    body = _routine(_code(), "function VJoyAddPreviewText(")
    assert "Result := 'vJoy ' + IntToStr(Id) + ' ' + #$00B7 + ' ' +" in body
    assert "CountText(DefaultButtons(Id), 'button', 'buttons');" in body

    def preview(ids: list[int]) -> str:
        nxt = 1
        while nxt in ids:
            nxt += 1
        return f"vJoy {nxt} \u00b7 {_pascal_default_buttons(nxt)} buttons"

    assert preview([1, 2]) == "vJoy 3 \u00b7 126 buttons"
    assert preview([1, 3]) == "vJoy 2 \u00b7 127 buttons"
    assert preview([]) == "vJoy 1 \u00b7 128 buttons"
    assert _pascal_default_buttons(3) == drivers.default_buttons(3) == 126


# -- 01 S187, D-01-VJOY-UPDATE-KEEPS: a vJoy update keeps the devices ---------------


def _const_text(name: str) -> str:
    """A string const, one line or a '+' chain over several."""
    found = re.search(rf"^  {name} = ('.*?');$", _code(), re.M | re.S)
    assert found, f"const {name} missing"
    return _pascal_string(found.group(1))


def _joined(names: list[str]) -> str:
    """VJoyNamesJoined, as written (checked below)."""
    out = ""
    for k, name in enumerate(names):
        if k == 0:
            out = name
        elif k == len(names) - 1:
            out += " and " + name
        else:
            out += ", " + name
    return out


def _count(n: int, one: str, many: str) -> str:
    return f"1 {one}" if n == 1 else f"{n} {many}"


def _devices(*ids: int) -> list[drivers.VJoyDevice]:
    return [
        drivers.VJoyDevice(i, axes=drivers.VJOY_AXES[: 9 - i], buttons=32, hats=i % 2)
        for i in ids
    ]


def test_the_names_join_like_drivers_py() -> None:
    body = _routine(_code(), "function VJoyNamesJoined(")
    assert "if K = 0 then\n      Result := Names[K]" in body
    assert "else if K = N - 1 then\n      Result := Result + ' and ' + Names[K]" in body
    assert "Result := Result + ', ' + Names[K];" in body
    for n in range(1, 5):
        names = [f"vJoy {i}" for i in range(1, n + 1)]
        assert _joined(names) == drivers._join(names)


def _info_text(devices: list[drivers.VJoyDevice]) -> str:
    if not devices:
        return (
            _const_text("VJoyUpdateUnreadHead") + "\u203a"
            + _const_text("VJoyUpdateUnreadTail")
        )
    names = ", ".join(f"vJoy {d.id}" for d in devices)
    return (
        _const_text("VJoyUpdateInfoHead")
        + _count(len(devices), "vJoy device", "vJoy devices")
        + f" ({names})" + _const_text("VJoyUpdateInfoTail")
    )


def test_the_update_info_box_says_what_drivers_py_says() -> None:
    body = _routine(_code(), "function VJoyUpdateInfoText(")
    results = _assignments(body, "Result")
    assert results == [
        "VJoyUpdateUnreadHead + #$203A + VJoyUpdateUnreadTail",
        "VJoyUpdateInfoHead + CountText(GetArrayLength(List), 'vJoy device', "
        "'vJoy devices') + ' (' + Names + ')' + VJoyUpdateInfoTail",
    ]
    assert "if GetArrayLength(List) = 0 then" in body
    assert "Names := Names + ', ';" in body
    assert "Names := Names + 'vJoy ' + IntToStr(List[K].Id);" in body
    for devices in (_devices(1), _devices(1, 2), _devices(1, 3, 4, 16), []):
        assert _info_text(devices) == drivers.update_info_text(devices)
    assert _const_text("VJoyUpdateInfoTitle") == "vJoy update and your devices"


def test_the_info_box_shows_before_a_vjoy_update_only() -> None:
    nxt = _routine(_code(), "function NextButtonClick(")
    done = nxt.index("DriversPageDone;")
    ask = nxt.index("if Drivers[DriverIndex('vjoy')].Op = 'update' then")
    box = nxt.index(
        "TaskDialogMsgBox(VJoyUpdateInfoTitle, VJoyUpdateInfoText(VJoyCurrent),\n"
        "        mbInformation, MB_OK, [], 0);"
    )
    assert nxt.index("if WizardSilent then\n    Exit;") < done < ask < box
    # Logged before the update (the helper logs them again itself).
    logged = "Log('vJoy devices before the update: ' + VJoyLayoutText(VJoyCurrent));"
    assert logged in nxt


def test_the_vjoy_update_job_carries_the_devices(tmp_path: pathlib.Path) -> None:
    body = _routine(_code(), "function JobJson(")
    assert "if (Drivers[I].Key = 'vjoy') and (Drivers[I].Op = 'update') then" in body
    assert "Devices := VJoyDevicesJson(VJoyCurrent);" in body
    bundled = r"C:\A B\drivers\vJoySetup_v2.2.2.0_Win10_Win11.exe"
    before = _devices(1, 2, 4)
    for devices in (before, []):
        text = _job_file([
            _job_json("update", "vjoy", "", bundled, _devices_json(devices)),
        ])
        path = tmp_path / "jobs.json"
        path.write_text(text, encoding="utf-8")
        (job,) = drivers.read_jobs(path)
        assert (job.op, job.driver) == ("update", "vjoy")
        assert job.devices == devices


def _lost_text(devices: list[drivers.VJoyDevice]) -> str:
    names = [
        f"vJoy {d.id} ({_count(len(d.axes), 'axis', 'axes')}, "
        f"{_count(d.buttons, 'button', 'buttons')}, {_count(d.hats, 'hat', 'hats')})"
        for d in devices
    ]
    tail = _const_text("VJoyLostOne" if len(devices) == 1 else "VJoyLostMany")
    return _const_text("VJoyLostHead") + _joined(names) + tail


def test_the_lost_box_says_what_drivers_py_says() -> None:
    body = _routine(_code(), "function VJoyLostText(")
    assert "CountText(AxesCountOf(List[K].Axes), 'axis', 'axes') + ', ' +" in body
    assert "CountText(List[K].Buttons, 'button', 'buttons') + ', ' +" in body
    assert "CountText(List[K].Hats, 'hat', 'hats') + ')';" in body
    assert "Result := VJoyLostHead + VJoyNamesJoined(Names);" in body
    one = "if GetArrayLength(List) = 1 then\n    Result := Result + VJoyLostOne"
    assert one in body
    assert "Result := Result + VJoyLostMany;" in body
    four = drivers.VJoyDevice(4, axes=drivers.VJOY_AXES, buttons=32, hats=0)
    for devices in ([four], _devices(2, 4), _devices(1, 2, 7)):
        assert _lost_text(devices) == drivers.lost_text(devices)
    assert "vJoy 4 (8 axes, 32 buttons, 0 hats) is missing." in _lost_text([four])


def test_the_results_line_names_the_added_devices() -> None:
    body = _routine(_code(), "function VJoyAddedText(")
    assert "Names[K] := 'vJoy ' + IntToStr(Ids[K]);" in body
    assert "Result := VJoyNamesJoined(Names);" in body
    for ids in ([1], [1, 3], [1, 2, 5]):
        tail = _const_text("VJoyAddedOne" if len(ids) == 1 else "VJoyAddedMany")
        assert _joined([f"vJoy {i}" for i in ids]) + tail == drivers.added_text(ids)
    line = _routine(_code(), "function DriverResultLine(")
    assert "(GetArrayLength(VJoyUpdateAdded) > 0) then" in line
    assert "Result := Result + '; ' + VJoyAddedText(VJoyUpdateAdded);" in line


def test_the_vjoy_update_result_lost_and_added_are_read(
    tmp_path: pathlib.Path,
) -> None:
    code = _code()
    read = _routine(code, "function ReadDriverResults(")
    assert "if IsVJoyJob(J) then" in read
    # The last vJoy job's result wins: reset once, then each vJoy job reads.
    assert read.index("SetArrayLength(VJoyUpdateLost, 0);") < read.index(
        "if IsVJoyJob(J) then"
    )
    vjob = _routine(code, "function IsVJoyJob(")
    assert "JobDrivers[J] = VJoySetupJob" in vjob
    assert "Op = 'update'" in vjob
    job = "ReadVJoyUpdateCheck(Copy(Text, Starts[J], Ends[J] - Starts[J] + 1));"
    assert job in read
    check = _routine(code, "procedure ReadVJoyUpdateCheck(")
    for key in ("'lost'", "'id'", "'buttons'", "'hats'", "'added'"):
        assert key in check
    assert "AxesFromJson(Job, Starts[K], Ends[K])" in check
    assert "Pos('\"' + AxisName(K) + '\"', Names) > 0" in _routine(
        code, "function AxesFromJson("
    )
    # What the helper writes there: plain device dicts and a list of ids.
    path = tmp_path / "results.json"
    lost = _devices(2)
    drivers.write_results(
        path, [drivers.JobResult("done", "", False, "bundled", lost, [1])], True
    )
    job = json.loads(path.read_text(encoding="utf-8"))["jobs"][0]
    assert [set(d) for d in job["lost"]] == [{"id", "axes", "buttons", "hats"}]
    assert job["added"] == [1]


def test_the_lost_box_has_repair_now_and_repair_later() -> None:
    assert _const_text("VJoyLostTitle") == "The vJoy update lost a device"
    assert _const_text("VJoyRepairNow") == "Repair Now"
    assert _const_text("VJoyRepairLater") == "Repair Later"
    ask = _routine(_code(), "procedure AskVJoyRepair;")
    assert "if WizardSilent or (GetArrayLength(VJoyUpdateLost) = 0) then" in ask
    assert (
        "if TaskDialogMsgBox(VJoyLostTitle, VJoyLostText(VJoyUpdateLost),\n"
        "    mbError, MB_YESNO, [VJoyRepairNow, VJoyRepairLater], 0) = IDYES then"
    ) in ask
    # Repair Now runs the restore; Repair Later only logs.
    assert ask.index("RunVJoyRestore;") < ask.index("else\n    Log(")
    run = _routine(_code(), "procedure RunDriverJobs;")
    assert run.index("BuildDriverSummary;") < run.index("AskVJoyRepair;")


def test_repair_now_runs_the_helper_with_one_vjoy_restore_job(
    tmp_path: pathlib.Path,
) -> None:
    body = _routine(_code(), "procedure RunVJoyRestore;")
    assert "JobFile := ExpandConstant('{tmp}\\' + RestoreJobFileName);" in body
    assert "ResultsFile := ExpandConstant('{tmp}\\' + RestoreResultsFileName);" in body
    assert "SetArrayLength(JobDrivers, 1);\n  JobDrivers[0] := VJoyRestoreJob;" in body
    assert "SaveStringsToUTF8FileWithoutBOM(JobFile, Lines, False)" in body
    assert "RunHelperJobs(JobFile, ResultsFile)" in body
    assert "MsgBox(VJoyRestoreResultLine, mbInformation, MB_OK)" in body
    assert "DriverSummary := DriverSummary + VJoyRestoreResultLine;" in body
    (line,) = _assignments(body, "Lines[0]")
    lost = _devices(2, 4)
    restore = _vjoy_job_json(
        "function VJoyRestoreJobJson:", "VJoyDevicesJson(VJoyUpdateLost)", lost
    )
    text = _eval(line, {"VJoyRestoreJobJson": restore})
    path = tmp_path / "restore.json"
    path.write_text(text, encoding="utf-8")
    (job,) = drivers.read_jobs(path)
    assert (job.op, job.driver, job.files) == ("vjoy_restore", "vjoy", [])
    assert job.devices == lost
    # The restore job has its own progress text and result slot.
    code = _code()
    progress = _routine(code, "function JobProgressText(")
    assert "else if I = VJoyRestoreJob then" in progress
    assert "Result := VJoyRestoreState" in _routine(code, "function JobState(")
    assert "VJoyRestoreState := State;" in _routine(code, "procedure SetJobResult(")


def test_lost_is_taken_from_the_last_vjoy_result(tmp_path: pathlib.Path) -> None:
    """Update + vjoy_setup: the vjoy_setup result's lost/added decide the box."""

    def last(results: list[tuple[str, list, list]]) -> tuple[list, list]:
        lost, added = [], []
        for op, lo, ad in results:
            if op in ("update", "vjoy_setup"):
                lost, added = lo, ad  # ReadVJoyUpdateCheck resets, then fills
        return lost, added

    path = tmp_path / "results.json"
    dev = _devices(2)
    drivers.write_results(
        path,
        [
            drivers.JobResult("done", "", False, "bundled", [], []),
            drivers.JobResult("done", "", False, "bundled", dev, [1]),
        ],
        True,
    )
    jobs = json.loads(path.read_text(encoding="utf-8"))["jobs"]
    assert last([("update", j["lost"], j["added"]) for j in jobs[:1]]) == ([], [])
    lost, added = last(
        [("update", jobs[0]["lost"], jobs[0]["added"]),
         ("vjoy_setup", jobs[1]["lost"], jobs[1]["added"])]
    )
    assert lost == jobs[1]["lost"] and lost and added == [1]
    # An empty vjoy_setup result after a lost update clears it: no box.
    assert last([("update", jobs[1]["lost"], [1]), ("vjoy_setup", [], [])]) == ([], [])
