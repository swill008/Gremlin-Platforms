; Gremlin-Platforms R2 installer (Inno Setup 6).
;
; Per-user install, no admin rights, so the in-app updater can run it silently.
; Build with installer\build_installer.ps1, or pass the version yourself:
;   ISCC /DMyAppVersion=1.0.3 installer\gremlin_platforms.iss

#ifndef MyAppVersion
  #error Pass the version: ISCC /DMyAppVersion=X.Y.Z
#endif
#ifndef DistDir
  #define DistDir "..\dist\gremlin_platforms"
#endif

#define MyAppName "Gremlin-Platforms R2"
#define MyAppPublisher "swill008"
#define MyAppURL "https://github.com/swill008/Gremlin-Platforms"
#define MyAppExeName "gremlin_platforms.exe"
; 12 S25: the only part that runs with administrator rights (driver jobs).
#define HelperExeName "Gremlin Device Helper.exe"
; 01 S188: the bundled driver installers, as in gremlin/drivers.py's DRIVERS.
; tools\fetch_drivers.py puts them in installer\drivers\ (not in git).
#define VJoyBundled "2.2.2.0"
#define VJoyFile "vJoySetup_v2.2.2.0_Win10_Win11.exe"
#define ViGEmBusBundled "1.22.0"
#define ViGEmBusFile "ViGEmBus_1.22.0_x64_x86_arm64.exe"
#define HidHideBundled "1.5.230"
#define HidHideFile "HidHide_1.5.230_x64.exe"
; 01 S193: Microsoft's Visual C++ Runtime, as in gremlin/drivers.py's RUNTIME.
#define RuntimeBundled "14.44.35211"
#define RuntimeFile "VC_redist.x64.exe"
#define RuntimeSha256 "cc0ff0eb1dc3f5188ae6300faef32bf5beeba4bdd6e8e445a9184072096b713b"
#define RuntimeSigner "Microsoft Corporation"

[Setup]
; Never change the AppId: updates and uninstall find the install by it.
AppId={{D0744CCA-1462-4ADB-A90F-48B62DDC092C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
VersionInfoVersion={#MyAppVersion}
PrivilegesRequired=lowest
DefaultDirName={autopf}\Gremlin-Platforms
DisableDirPage=no
UsePreviousAppDir=yes
; One setup at a time: a second run (a double-click, or the program's own update) stops while the
; first one is still running. Per-user mutex (no ,Global): the install is per user and both runs
; are in the same Windows session, so Global would only block other users for no reason.
SetupMutex=GremlinPlatformsSetup
DefaultGroupName={#MyAppName}
; Always this name: the AppId is R1's, so the previous group would be
; "Gremlin-Platforms R1", which OT-7 deletes after the shortcut is made there.
UsePreviousGroup=no
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=Gremlin-Platforms-R2-{#MyAppVersion}-Setup
SetupIconFile=..\gfx\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; 120,120 is Inno's default; the extra height lets the Drivers page show at
; least 4 vJoy device rows without scrolling (user 2026-11-21); 134 (was 128)
; keeps 5 rows with the two-line hint above the "Showing" line.
WizardSizePercent=120,137
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; The Restart Manager is not used: PrepareToInstall runs before its in-use
; check and moves the program aside, so it never saw Gremlin running. The
; script asks the program to quit itself instead (01 S173).
CloseApplications=no
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

; The old version's program files are not deleted up front: PrepareToInstall
; moves them aside (_internal.old, gremlin_platforms.exe.old) and they are
; removed only once the new ones are in, or put back if the install fails.
; User data lives in %USERPROFILE%\Gremlin Platforms and is never touched.

[Files]
; The whole PyInstaller folder: gremlin_platforms.exe, Gremlin Input Tester.exe,
; Gremlin Device Helper.exe and the gremlin-ctl.exe command line, with _internal.
Source: "{#DistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Third-party licence notices (dill, spdlog, Qt, ...) next to the program,
; with vjoy.txt, vigembus.txt and hidhide.txt for the bundled drivers (01 S188).
Source: "..\licenses\*"; DestDir: "{app}\licenses"; Flags: ignoreversion
; 01 S188: the bundled driver installers. The helper runs each only when its
; SHA-256 matches gremlin/drivers.py's; a missing file fails the build.
Source: "drivers\{#VJoyFile}"; DestDir: "{app}\drivers"; Flags: ignoreversion
Source: "drivers\{#ViGEmBusFile}"; DestDir: "{app}\drivers"; Flags: ignoreversion
Source: "drivers\{#HidHideFile}"; DestDir: "{app}\drivers"; Flags: ignoreversion
; 01 S193: the Visual C++ Runtime is never copied to {app}: setup extracts it
; to {tmp} (ExtractTemporaryFile) only when it is missing, and {tmp} goes when
; setup ends. A missing file fails the build.
Source: "drivers\{#RuntimeFile}"; Flags: dontcopy

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; 01 S193: the Visual C++ Runtime is installed at ssInstall (InstallRuntime),
; before the files are copied and before any entry here can start the program.
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent; Check: OfferLaunch
; The in-app updater runs setup silently with /LAUNCH=1 to start the new version.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: LaunchAfterSilentUpdate
; Setup closed the running program (01 S173): start it again.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: RestartAfterClose

[UninstallDelete]
Type: files; Name: "{app}\dill_debug.log"
Type: filesandordirs; Name: "{app}\_internal.old"
Type: files; Name: "{app}\{#MyAppExeName}.old"
Type: files; Name: "{app}\.update-in-progress"
; 01 S192: uninstall leaves vJoy, ViGEmBus and HidHide installed; only the
; unfinished HidHide update's note goes with the program.
Type: files; Name: "{app}\drivers\pending.json"

[Code]
var
  { The old program was moved aside and is put back unless the install
    finishes. }
  MovedAside: Boolean;
  Finished: Boolean;
  { The program to start again if an in-app update doesn't finish; set
    once setup reaches the install step. }
  AppExe: String;
  { Setup asked the running program to quit and it did (01 S173). }
  ClosedByInstaller: Boolean;

{ 01 S187-S192: the Drivers page and the driver jobs. }
type
  TDriver = record
    Key, Name, Bundled, BundledFile: String;
    { GitHub "owner/repo" and the asset name around the version; '' for
      ViGEmBus, which is retired and has no check (01 S189). }
    Repo, AssetPrefix, AssetSuffix: String;
    { What is on the PC: version ('' = not installed) and
      'missing' | 'older' | 'same' | 'newer' against the bundled copy. }
    Installed, State: String;
    { Its row on the Drivers page; -1 when it shows no box. }
    Row: Integer;
    Chosen, LatestChecked: Boolean;
    { The newer GitHub release, when there is one. }
    LatestVersion, LatestUrl, LatestName: String;
    { The downloaded copy in setup's temp folder; '' when there is none. }
    Download: String;
    { 'install' | 'update' | 'remove'; '' = no job. }
    Op: String;
    ResultState, ResultMessage: String;
    ResultRestart: Boolean;
  end;
  { One vJoy device (gremlin/drivers.py VJoyDevice): Axes is a bit mask of
    the ticked axes (bit K = VJoyAxisNames' K-th name, X Y Z RX RY RZ SL0
    SL1), buttons 0-128, hats 0-4. }
  TVJoyDevice = record
    Id, Axes, Buttons, Hats: Integer;
  end;
  TVJoyDevices = array of TVJoyDevice;
  { GetWindowRect's RECT, in screen pixels. }
  TWheelRect = record
    Left, Top, Right, Bottom: Longint;
  end;
  { ShellExecuteExW's SHELLEXECUTEINFOW (32-bit Setup: 60 bytes). }
  TShellExecuteInfo = record
    cbSize: DWORD;
    fMask: Cardinal;
    Wnd: HWND;
    lpVerb: String;
    lpFile: String;
    lpParameters: String;
    lpDirectory: String;
    nShow: Integer;
    hInstApp: Longint;
    lpIDList: Longint;
    lpClass: String;
    hkeyClass: Longint;
    dwHotKey: DWORD;
    hMonitor: Longint;
    hProcess: Longint;
  end;

var
  Drivers: array of TDriver;
  DriversPage: TWizardPage;
  DriverList: TNewCheckListBox;
  DriverDownloadPage: TDownloadWizardPage;
  DriverProgressPage: TOutputProgressWizardPage;
  { Driver index of each job in the job file, in order. }
  JobDrivers: TArrayOfInteger;
  { A driver asked for a restart, or the HidHide update's first half ran. }
  DriversNeedRestart: Boolean;
  HidHideRemoved: Boolean;
  { The results for setup's last page; '' when no driver job ran. }
  DriverSummary: String;
  { 01 S193: the Visual C++ Runtime was missing when setup started; its
    line for the last page ('' when setup didn't install it) and whether
    it asked for a restart. }
  RuntimeMissing, RuntimeNeedRestart: Boolean;
  RuntimeResult: String;
  RuntimeProgressPage: TOutputProgressWizardPage;
  { The vJoy device choice (06 S185, on this page by 01 S187): what vJoy
    has now (vJoyConfig -t; empty when not installed or unread) and the
    layout to set. VJoyUserEdited: the preset or a device row was changed
    on the page. }
  VJoyCurrent, VJoyChosen: TVJoyDevices;
  VJoyLayoutRead, VJoyUserEdited, VJoyFilling: Boolean;
  { D-01-VJOY-IN-USE: the devices vJoyConfig -t lists as BUSY or OWNED
    (another program holds them; vJoyConfig is its own process). }
  VJoyBusy: TArrayOfInteger;
  { A vjoy_setup job runs after the vJoy install job (12 S25b). }
  VJoySetupPlanned: Boolean;
  VJoySetupState, VJoySetupMessage: String;
  VJoySetupRestart: Boolean;
  { D-01-VJOY-UPDATE-KEEPS: the vJoy update's result "lost" (devices to
    put back) and "added" (ids), and Repair Now's vjoy_restore result. }
  VJoyUpdateLost: TVJoyDevices;
  VJoyUpdateAdded: TArrayOfInteger;
  VJoyRestoreState, VJoyRestoreMessage: String;
  VJoyRestoreRestart: Boolean;
  VJoyPresetBox: TNewComboBox;
  VJoyCurrentText, VJoyWarningText, VJoyShowingText, VJoyHint: TNewStaticText;
  { The device rows (answer 2a): one set of controls per possible device,
    shown for VJoyChosen's devices in order. The rows sit on VJoyRowsPanel
    inside VJoyViewport; VJoyScroll is a list box with one item per row
    whose scroll bar moves the rows (Pascal Script has no TScrollBox or
    TScrollBar). }
  VJoyViewport, VJoyRowsPanel: TPanel;
  { Layout b: the column headings' grey band at the box's top and the
    rows' window under it. }
  VJoyHeadBand, VJoyRowsClip: TPanel;
  VJoyScroll: TNewListBox;
  VJoyRowNames: array of TNewStaticText;
  VJoyRowAxes: array of TNewCheckBox;
  VJoyRowButtons, VJoyRowHats: array of TNewComboBox;
  VJoyRowRemove: array of TNewButton;
  { 01 S187 (3a): the list's last row, "+ Add device" with the next
    device in grey on its right; the whole row is clickable. }
  VJoyAddRow: TPanel;
  VJoyAddLabel, VJoyAddPreview: TNewStaticText;
  VJoyRowHeight, VJoyVisibleRows, VJoyTopRow: Integer;
  VJoyScrollTimer: LongWord;
  { The thread mouse hook behind the wheel over the rows (answer 6a+b), and
    the part of a notch not scrolled yet (fine-grained wheels). }
  VJoyWheelHook: LongWord;
  VJoyWheelRest: Integer;
  { 01 S193: the runtime's rows in the drivers box: the required parent
    (ticked, greyed) and its child, the "newest runtime" row (answer 6a,
    9b); what the child found (a note for the last page) and the checked
    download to run instead of the bundled copy ('' = the bundled copy). }
  RuntimeRow, RuntimeNewestRow: Integer;
  RuntimeNewestWanted: Boolean;
  RuntimeNewestPath, RuntimeNewestVersion, RuntimeNewestNote: String;

const
  WM_CLOSE = $0010;
  GW_OWNER = 4;
  GW_HWNDNEXT = 2;
  SMTO_ABORTIFHUNG = $0002;
  { How long the program gets to quit before setup gives up (10 s). }
  CloseWaitTries = 20;
  CloseWaitStep = 500;
  { The program's own quit request, handled by its tray window
    (gremlin/ui/system_tray.py), which answers QuitRequestHandled. }
  QuitRequestName = 'GremlinPlatformsQuitRequest';
  QuitRequestHandled = 1;
  TrayWindowClass = 'JoystickGremlinSystemTray';

function GetTopWindow(Wnd: HWND): HWND;
  external 'GetTopWindow@user32.dll stdcall';
function GetWindow(Wnd: HWND; Cmd: Cardinal): HWND;
  external 'GetWindow@user32.dll stdcall';
function GetWindowThreadProcessId(Wnd: HWND; var ProcessId: Cardinal): Cardinal;
  external 'GetWindowThreadProcessId@user32.dll stdcall';
function GetClassName(Wnd: HWND; ClassName: String; MaxCount: Integer): Integer;
  external 'GetClassNameW@user32.dll stdcall';
function RegisterWindowMessage(const Name: String): Cardinal;
  external 'RegisterWindowMessageW@user32.dll stdcall';
function SendMessageTimeout(Wnd: HWND; Msg: Cardinal; WParam, LParam: Longint;
  Flags, Timeout: Cardinal; var MsgResult: Cardinal): Cardinal;
  external 'SendMessageTimeoutW@user32.dll stdcall';
{ Answer 4a: elevated starts from setup's own window, so Windows' prompt
  opens in front of it. }
function ShellExecuteEx(var Info: TShellExecuteInfo): BOOL;
  external 'ShellExecuteExW@shell32.dll stdcall';
function WaitForSingleObject(Handle: Longint; Milliseconds: Cardinal): Cardinal;
  external 'WaitForSingleObject@kernel32.dll stdcall';
function GetExitCodeProcess(Process: Longint; var ExitCode: Cardinal): BOOL;
  external 'GetExitCodeProcess@kernel32.dll stdcall';
function CloseHandle(Handle: Longint): BOOL;
  external 'CloseHandle@kernel32.dll stdcall';
function SetForegroundWindow(Wnd: HWND): BOOL;
  external 'SetForegroundWindow@user32.dll stdcall';
function SetTimer(Wnd: HWND; IDEvent, Elapse, TimerFunc: LongWord): LongWord;
  external 'SetTimer@user32.dll stdcall';
function KillTimer(Wnd: HWND; IDEvent: LongWord): BOOL;
  external 'KillTimer@user32.dll stdcall';
function GetSystemMetrics(Index: Integer): Integer;
  external 'GetSystemMetrics@user32.dll stdcall';
function SetWindowsHookEx(IdHook: Integer; Fn, Module, ThreadId: LongWord): LongWord;
  external 'SetWindowsHookExW@user32.dll stdcall';
function UnhookWindowsHookEx(Hook: LongWord): BOOL;
  external 'UnhookWindowsHookEx@user32.dll stdcall';
function CallNextHookEx(Hook: LongWord; Code: Integer; WParam, LParam: Longint): Longint;
  external 'CallNextHookEx@user32.dll stdcall';
function GetCurrentThreadId: LongWord;
  external 'GetCurrentThreadId@kernel32.dll stdcall';
function GetWindowRect(Wnd: HWND; var Rect: TWheelRect): Longint;
  external 'GetWindowRect@user32.dll stdcall';
function IsWindowVisible(Wnd: HWND): Longint;
  external 'IsWindowVisible@user32.dll stdcall';
procedure ReadHookLong(var Dest: Longint; Src: Longint; Len: Integer);
  external 'RtlMoveMemory@kernel32.dll stdcall';

function LaunchAfterSilentUpdate: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:LAUNCH|0}') = '1');
end;

{ True when a driver job will run after the files are copied. A silent
  install (/SILENT, /VERYSILENT, the in-app update) never runs driver jobs. }
function DriverJobsPlanned: Boolean;
var
  I: Integer;
begin
  Result := False;
  if WizardSilent then
    Exit;
  for I := 0 to GetArrayLength(Drivers) - 1 do
    if Drivers[I].Chosen then
    begin
      Result := True;
      Exit;
    end;
  Result := VJoySetupPlanned;
end;

{ [Run]: start the program again once, after setup closed it; the in-app
  update's /LAUNCH=1 entry starts it otherwise. With driver jobs it is
  started after them instead (RunDriverJobs), so it never starts while a
  driver is being installed. }
function RestartAfterClose: Boolean;
begin
  Result := ClosedByInstaller and not LaunchAfterSilentUpdate and
    not DriverJobsPlanned;
end;

{ [Run]: the "Launch" box, unless setup starts the program anyway. }
function OfferLaunch: Boolean;
begin
  Result := not ClosedByInstaller;
end;

function AppFile(const Name: String): String;
begin
  Result := AddBackslash(WizardDirValue) + Name;
end;

{ Written once the old program is moved aside, removed when the install
  finishes: found at the start of a later install, it means this one stopped
  half-way, so the .old copies are the good ones. }
function MarkerFile: String;
begin
  Result := AppFile('.update-in-progress');
end;

function ExistsAt(const Path: String): Boolean;
begin
  Result := DirExists(Path) or FileExists(Path);
end;

procedure RemovePath(const Path: String);
begin
  if DirExists(Path) then
    DelTree(Path, True, True, True)
  else if FileExists(Path) then
    DeleteFile(Path);
end;

{ Moves Name to Name.old. The old program may still be closing after it
  started the update, and its files stay locked until it has: keep trying for
  up to 30 seconds. }
function MoveAside(const Name: String): Boolean;
var
  Tries: Integer;
begin
  Result := True;
  if not ExistsAt(AppFile(Name)) then
    Exit;
  for Tries := 1 to 60 do
  begin
    if RenameFile(AppFile(Name), AppFile(Name + '.old')) then
      Exit;
    Sleep(500);
  end;
  Result := False;
end;

procedure PutBack(const Name: String);
begin
  if ExistsAt(AppFile(Name + '.old')) then
  begin
    RemovePath(AppFile(Name));
    RenameFile(AppFile(Name + '.old'), AppFile(Name));
  end;
end;

{ True when the chosen folder holds Gremlin-Platforms (its program, the copy
  an update set aside, or an update that did not finish). }
function OursIsHere: Boolean;
begin
  Result := ExistsAt(AppFile('{#MyAppExeName}')) or
    ExistsAt(AppFile('{#MyAppExeName}.old')) or FileExists(MarkerFile);
end;

{ Process ids of the program running from the chosen folder (this user's
  copies; WMI hides other users' paths without admin rights). }
function RunningIds(const Exe: String): TArrayOfString;
var
  Locator, Service, Found, Item: Variant;
  I, N: Integer;
begin
  SetArrayLength(Result, 0);
  try
    Locator := CreateOleObject('WbemScripting.SWbemLocator');
    Service := Locator.ConnectServer('.', 'root\CIMV2');
    Found := Service.ExecQuery('SELECT ProcessId, ExecutablePath FROM ' +
      'Win32_Process WHERE Name = ''{#MyAppExeName}''');
    N := 0;
    for I := 0 to Found.Count - 1 do
    begin
      Item := Found.ItemIndex(I);
      if not VarIsNull(Item.ExecutablePath) and
        (CompareText(Item.ExecutablePath, Exe) = 0) then
      begin
        SetArrayLength(Result, N + 1);
        Result[N] := IntToStr(Item.ProcessId);
        N := N + 1;
      end;
    end;
  except
    Log('Could not list running programs: ' + GetExceptionMessage);
  end;
end;

function IsOneOf(const Id: Cardinal; const Ids: TArrayOfString): Boolean;
var
  I: Integer;
begin
  Result := False;
  for I := 0 to GetArrayLength(Ids) - 1 do
    if Ids[I] = IntToStr(Id) then
    begin
      Result := True;
      Exit;
    end;
end;

function ClassOf(Wnd: HWND): String;
var
  Len: Integer;
begin
  Result := StringOfChar(' ', 256);
  Len := GetClassName(Wnd, Result, 256);
  Result := Copy(Result, 1, Len);
end;

{ Qt's main window class, e.g. Qt6112QWindowIcon. }
function IsQtMainClass(const Name: String): Boolean;
begin
  Result := (Copy(Name, 1, 2) = 'Qt') and (Length(Name) > 13) and
    (Copy(Name, Length(Name) - 10, 11) = 'QWindowIcon');
end;

{ Asks the program to quit the way File > Exit does, hidden in the tray or
  not: its tray window gets the quit request, and the program shows its
  window and runs File > Exit (which asks about unsaved changes). A program
  too old to answer the request gets WM_CLOSE on its main window, hidden
  too, so Main.qml's onClosing quits it or asks. Never TerminateProcess:
  unsaved work must not be lost. }
procedure AskToClose(const Ids: TArrayOfString);
var
  Wnd: HWND;
  Id, QuitRequest, Answer: Cardinal;
  Handled: Boolean;
begin
  QuitRequest := RegisterWindowMessage(QuitRequestName);
  Handled := False;
  Wnd := GetTopWindow(0);
  while Wnd <> 0 do
  begin
    Id := 0;
    GetWindowThreadProcessId(Wnd, Id);
    if IsOneOf(Id, Ids) and (ClassOf(Wnd) = TrayWindowClass) then
    begin
      Answer := 0;
      if (SendMessageTimeout(Wnd, QuitRequest, 0, 0, SMTO_ABORTIFHUNG,
        2000, Answer) <> 0) and (Answer = QuitRequestHandled) then
        Handled := True;
    end;
    Wnd := GetWindow(Wnd, GW_HWNDNEXT);
  end;
  if Handled then
  begin
    Log('Gremlin-Platforms took the quit request.');
    Exit;
  end;
  Log('No quit request answer; closing the main window instead.');
  Wnd := GetTopWindow(0);
  while Wnd <> 0 do
  begin
    Id := 0;
    GetWindowThreadProcessId(Wnd, Id);
    if IsOneOf(Id, Ids) and (GetWindow(Wnd, GW_OWNER) = 0) and
      IsQtMainClass(ClassOf(Wnd)) then
      PostMessage(Wnd, WM_CLOSE, 0, 0);
    Wnd := GetWindow(Wnd, GW_HWNDNEXT);
  end;
end;

{ 01 S173: closes a running Gremlin-Platforms before its files are touched.
  False when it is still running after the wait (it is asking about unsaved
  changes, or would not quit). }
function CloseRunningProgram: Boolean;
var
  Tries: Integer;
begin
  Result := True;
  if GetArrayLength(RunningIds(AppExe)) = 0 then
    Exit;
  Log('Gremlin-Platforms is running; asking it to quit.');
  AskToClose(RunningIds(AppExe));
  for Tries := 1 to CloseWaitTries do
  begin
    Sleep(CloseWaitStep);
    if GetArrayLength(RunningIds(AppExe)) = 0 then
    begin
      Log('Gremlin-Platforms quit.');
      ClosedByInstaller := True;
      Exit;
    end;
  end;
  Log('Gremlin-Platforms is still running; not updating.');
  Result := False;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  AppExe := AppFile('{#MyAppExeName}');
  if not CloseRunningProgram then
  begin
    Result := 'Gremlin-Platforms has unsaved changes. Save or close them, ' +
      'then run the update again. Nothing was changed.';
    Exit;
  end;
  if not OursIsHere then
  begin
    { A new install. Another program's _internal folder must not be moved
      aside and deleted (it used to be), nor have ours copied into it. }
    if ExistsAt(AppFile('_internal')) then
      Result := 'The folder you chose already holds another program''s ' +
        '_internal folder. Choose an empty folder for Gremlin-Platforms. ' +
        'Nothing was changed.';
    Exit;
  end;
  if FileExists(MarkerFile) then
  begin
    { An earlier install stopped half-way: keep its .old copies (the last
      working version) and drop the half-copied files. }
    Log('Earlier install did not finish; keeping its backup.');
    if ExistsAt(AppFile('_internal.old')) then
      RemovePath(AppFile('_internal'));
    if ExistsAt(AppFile('{#MyAppExeName}.old')) then
      RemovePath(AppFile('{#MyAppExeName}'));
    MovedAside := True;
    Exit;
  end;
  { Leftovers of a finished install that could not delete them. }
  RemovePath(AppFile('_internal.old'));
  RemovePath(AppFile('{#MyAppExeName}.old'));
  if not MoveAside('_internal') then
  begin
    Result := 'Gremlin-Platforms is still running, so it could not be updated. ' +
      'Close it and run the update again. Nothing was changed.';
    Exit;
  end;
  if not MoveAside('{#MyAppExeName}') then
  begin
    PutBack('_internal');
    Result := 'Gremlin-Platforms is still running, so it could not be updated. ' +
      'Close it and run the update again. Nothing was changed.';
    Exit;
  end;
  MovedAside := True;
  if ExistsAt(AppFile('_internal.old')) or ExistsAt(AppFile('{#MyAppExeName}.old')) then
    SaveStringToFile(MarkerFile, 'update in progress', False);
end;

{ ---- Drivers (01 S187-S192) --------------------------------------------- }

const
  { Detection: the same keys as gremlin/drivers.py (read-only). }
  UninstallRoot = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall';
  VJoyUninstallKey = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{8E31F76F-74C3-47F1-9550-E041EEDC5FBB}_is1';
  HidHideKey = 'SOFTWARE\Nefarius Software Solutions e.U.\HidHide';
  ViGEmBusDisplayName = 'ViGEm Bus Driver';
  ViGEmBusDisplayName2 = 'Nefarius Virtual Gamepad Emulation Bus Driver';
  { The helper's job and result files (12 S25), in setup's temp folder. }
  JobFileName = 'driver_jobs.json';
  ResultsFileName = 'driver_results.json';
  { Half-second ticks: the helper writes its results file at once; each job
    gets ten minutes before setup stops waiting. }
  HelperWaitStep = 500;
  HelperStartTicks = 120;
  HelperJobTicks = 1200;
  UacRefusedCode = 1223;
  { 01 S193: the Visual C++ Runtime, as gremlin/drivers.py's RUNTIME_KEYS
    (read in the 64-bit view, then the 32-bit one) and RUNTIME_DONE_CODES. }
  RuntimeKey = 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64';
  RuntimeName = 'Microsoft Visual C++ Runtime';
  RuntimeArgs = '/install /quiet /norestart';
  RuntimeDoneCode = 0;
  RuntimeNewerCode = 1638;
  RuntimeRestartCode = 3010;
  { Half-second ticks: ten minutes before setup stops waiting. }
  RuntimeWaitStep = 500;
  RuntimeWaitTicks = 1200;
  { 01 S193 (answer 6a): Microsoft's link to its newest x64 runtime. It
    redirects to a path that holds the file's SHA-256 (observed, not
    documented), so a HEAD request tells whether it is the bundled copy. }
  RuntimeNewestCaption = 'Check and download an updated Visual C++ Runtime';
  RuntimeNewestUrl = 'https://aka.ms/vs/17/release/vc_redist.x64.exe';
  RuntimeNewestFile = 'VC_redist.newest.x64.exe';
  RuntimeSameNote = 'Microsoft''s newest is the copy setup carries';
  { Each of WinHttp's four timeouts (resolve, connect, send, receive): at
    most 10 s for the HEAD request. }
  RuntimeHeadTimeout = 2500;
  { ShellExecuteEx (answer 4a). }
  SeeMaskNoCloseProcess = $40;
  SeeMaskNoAsync = $100;
  SeeMaskFlagNoUi = $400;
  WaitObject0 = 0;
  { 06 S185: the vJoy choice's words and limits, as in
    gremlin/ui/drivers_model.py and gremlin/drivers.py. }
  VJoyPresetOne = '1 device, full';
  VJoyPresetTwo = '2 devices, full';
  VJoyCustom = 'Custom';
  VJoyWarning = 'Running games will lose the vJoy devices until they restart.';
  VJoyMaxDevices = 16;
  VJoyAxisNames = 'x y z rx ry rz sl0 sl1';
  { D-AXIS-NAMES: the column headings, gremlin/axis_names.py AXES' short
    names in the same order (vJoyConfig still gets VJoyAxisNames). }
  VJoyAxisLabels = 'X Y Z Rx Ry Rz S1 S2';
  { D-01-VJOY-IN-USE: an in-use row's name hover text, and
    drivers.in_use_warning's words after the names ("vJoy 4", "vJoy 1 and
    vJoy 4"). }
  VJoyInUseText = 'in use by another program';
  VJoyInUseOne = ' is in use by another program. Changing it can stop ' +
    'that program''s controls working until it restarts. Change it anyway?';
  VJoyInUseMany = ' are in use by another program. Changing them can stop ' +
    'that program''s controls working until it restarts. Change them anyway?';
  { All eight axes ticked (drivers.PRESETS' "full"). }
  VJoyAllAxes = 255;
  VJoyMaxButtons = 128;
  VJoyMaxHats = 4;
  { D-01-VJOY-COUNTDOWN: drivers.alike_warning's sentence after the names
    ("vJoy 1 and vJoy 3"), the question setup adds, and the hint above the
    "Showing" line (the lead swaps the hint's words here). }
  VJoyAlikeText = ' have the same number of axes, buttons and hats, so ' +
    'Gremlin-Platforms can''t tell them apart and won''t use them.';
  VJoyAlikeQuestion = ' Continue anyway?';
  VJoyHintText = 'Each device needs its own number of axes, buttons or hats, ' +
    'so Gremlin-Platforms can tell them apart.';
  { 01 S187 (3a): the list's last row. }
  VJoyAddText = '+ Add device';
  { The list box messages behind the rows' scroll bar. }
  LbGetTopIndex = $018E;
  LbSetItemHeight = $01A0;
  LbGetItemHeight = $01A1;
  LbSetTopIndex = $0197;
  { The wheel over the rows: a thread mouse hook (WH_MOUSE) sees
    WM_MOUSEWHEEL before the focused control does. MOUSEHOOKSTRUCTEX in
    32-bit Setup: pt.x 0, pt.y 4, hwnd 8, wHitTestCode 12, dwExtraInfo 16,
    mouseData 20 (high word = the signed wheel delta). }
  WhMouse = 7;
  HcAction = 0;
  WmMouseWheel = $020A;
  WheelDelta = 120;
  HookPointX = 0;
  HookPointY = 4;
  HookMouseData = 20;
  { JobDrivers' entry for the vjoy_setup job (it has no row of its own). }
  VJoySetupJob = -1;
  { JobDrivers' entry for Repair Now's vjoy_restore job (D-01-VJOY-UPDATE-KEEPS). }
  VJoyRestoreJob = -2;
  VJoyCaptureFile = 'vjoyconfig_output.txt';
  RestoreJobFileName = 'vjoy_restore_jobs.json';
  RestoreResultsFileName = 'vjoy_restore_results.json';
  { 01 S187, D-01-VJOY-UPDATE-KEEPS: drivers.update_info_text, lost_text and
    added_text, in pieces around the device names. }
  VJoyUpdateInfoTitle = 'vJoy update and your devices';
  VJoyUpdateInfoHead = 'Updating vJoy can lose vJoy devices that were set up ' +
    'with older vJoy tools. Gremlin-Platforms has noted your ';
  VJoyUpdateInfoTail = ' and checks them after the update. If one is missing ' +
    'or different, you''ll be asked whether to repair it.';
  VJoyUpdateUnreadHead = 'vJoy''s devices couldn''t be read before the update, ' +
    'so they can''t be checked afterwards. Check them in Tools ';
  VJoyUpdateUnreadTail = ' Drivers after the update.';
  VJoyLostTitle = 'The vJoy update lost a device';
  VJoyLostHead = 'After updating vJoy, ';
  VJoyLostOne = ' is missing. It was probably set up with an older vJoy tool ' +
    'that the new vJoy doesn''t read. Gremlin-Platforms can put it back ' +
    'exactly as it was.';
  VJoyLostMany = ' are missing. They were probably set up with an older vJoy ' +
    'tool that the new vJoy doesn''t read. Gremlin-Platforms can put them ' +
    'back exactly as they were.';
  VJoyRepairNow = 'Repair Now';
  VJoyRepairLater = 'Repair Later';
  VJoyAddedOne = ' was added by the vJoy update';
  VJoyAddedMany = ' were added by the vJoy update';

procedure SetDriver(I: Integer; const Key, Name, Bundled, BundledFile, Repo,
  AssetPrefix, AssetSuffix: String);
begin
  Drivers[I].Key := Key;
  Drivers[I].Name := Name;
  Drivers[I].Bundled := Bundled;
  Drivers[I].BundledFile := BundledFile;
  Drivers[I].Repo := Repo;
  Drivers[I].AssetPrefix := AssetPrefix;
  Drivers[I].AssetSuffix := AssetSuffix;
  Drivers[I].Installed := '';
  Drivers[I].State := 'missing';
  Drivers[I].Row := -1;
  Drivers[I].Chosen := False;
  Drivers[I].LatestChecked := False;
  Drivers[I].LatestVersion := '';
  Drivers[I].LatestUrl := '';
  Drivers[I].LatestName := '';
  Drivers[I].Download := '';
  Drivers[I].Op := '';
  Drivers[I].ResultState := '';
  Drivers[I].ResultMessage := '';
  Drivers[I].ResultRestart := False;
end;

{ Pos from a start index (1-based); 0 when not found. }
function FindFrom(const Sub, S: String; From: Integer): Integer;
var
  P: Integer;
begin
  if From < 1 then
    From := 1;
  P := Pos(Sub, Copy(S, From, Length(S)));
  if P = 0 then
    Result := 0
  else
    Result := P + From - 1;
end;

{ Takes the next dot-separated number off the front of S. }
function NextVersionPart(var S: String): Integer;
var
  P: Integer;
  Part: String;
begin
  P := Pos('.', S);
  if P = 0 then
  begin
    Part := S;
    S := '';
  end
  else
  begin
    Part := Copy(S, 1, P - 1);
    S := Copy(S, P + 1, Length(S));
  end;
  Result := StrToIntDef(Trim(Part), 0);
end;

{ -1, 0 or 1; missing parts count as 0 (drivers.compare). }
function CompareVersions(A, B: String): Integer;
var
  PA, PB: Integer;
begin
  Result := 0;
  while (Result = 0) and ((A <> '') or (B <> '')) do
  begin
    PA := NextVersionPart(A);
    PB := NextVersionPart(B);
    if PA < PB then
      Result := -1
    else if PA > PB then
      Result := 1;
  end;
end;

{ A value under HKLM, 64-bit view first, like drivers.WindowsRegistry. }
function MachineValue(const SubKey, Name: String): String;
begin
  Result := '';
  if not RegQueryStringValue(HKLM64, SubKey, Name, Result) then
    if not RegQueryStringValue(HKLM32, SubKey, Name, Result) then
      Result := '';
end;

{ DisplayVersion of the first Uninstall entry whose DisplayName starts with
  Prefix (drivers.uninstall_entry); '' when there is none. }
function UninstallVersion(const Prefix: String): String;
var
  Names: TArrayOfString;
  I, View, Root: Integer;
  Display: String;
begin
  Result := '';
  for View := 0 to 1 do
  begin
    if View = 0 then
      Root := HKLM64
    else
      Root := HKLM32;
    if not RegGetSubkeyNames(Root, UninstallRoot, Names) then
      Continue;
    for I := 0 to GetArrayLength(Names) - 1 do
    begin
      if not RegQueryStringValue(Root, UninstallRoot + '\' + Names[I],
        'DisplayName', Display) then
        Continue;
      if Copy(Display, 1, Length(Prefix)) = Prefix then
      begin
        if not RegQueryStringValue(Root, UninstallRoot + '\' + Names[I],
          'DisplayVersion', Result) then
          Result := '';
        Exit;
      end;
    end;
  end;
end;

{ The installed version of a driver; '' = not installed. }
function InstalledDriverVersion(const Key: String): String;
begin
  Result := '';
  if Key = 'vjoy' then
    Result := MachineValue(VJoyUninstallKey, 'DisplayVersion')
  else if Key = 'vigembus' then
  begin
    { The Uninstall entry first: the .sys file's version can lag the
      installer's (1.22.0 leaves a file that says 1.21.442.0). }
    Result := UninstallVersion(ViGEmBusDisplayName);
    if Result = '' then
      Result := UninstallVersion(ViGEmBusDisplayName2);
    if Result = '' then
      if not GetVersionNumbersString(
        ExpandConstant('{sys}\drivers\ViGEmBus.sys'), Result) then
        Result := '';
  end
  else if Key = 'hidhide' then
    Result := MachineValue(HidHideKey, 'Version');
end;

procedure DetectDrivers;
var
  I: Integer;
begin
  for I := 0 to GetArrayLength(Drivers) - 1 do
  begin
    try
      Drivers[I].Installed := Trim(InstalledDriverVersion(Drivers[I].Key));
    except
      Log('Could not read the ' + Drivers[I].Name + ' version: ' +
        GetExceptionMessage);
      Drivers[I].Installed := '';
    end;
    if Drivers[I].Installed = '' then
      Drivers[I].State := 'missing'
    else
      case CompareVersions(Drivers[I].Installed, Drivers[I].Bundled) of
        -1: Drivers[I].State := 'older';
        0: Drivers[I].State := 'same';
      else
        Drivers[I].State := 'newer';
      end;
    Log(Drivers[I].Name + ': installed "' + Drivers[I].Installed + '", bundled ' +
      Drivers[I].Bundled + ', ' + Drivers[I].State);
  end;
end;

{ 01 S193: Installed is 1 under the runtime's key, 64-bit view first, like
  drivers.runtime_installed. }
function RuntimeInstalled: Boolean;
var
  Value: Cardinal;
begin
  Result := False;
  if RegQueryDWordValue(HKLM64, RuntimeKey, 'Installed', Value) then
    Result := Value = 1;
  if not Result and RegQueryDWordValue(HKLM32, RuntimeKey, 'Installed', Value) then
    Result := Value = 1;
end;

{ The installed runtime's version (drivers.runtime_version: the key's
  "Version" value, "v14.51.36247.00" -> "14.51.36247.00"); '' when none. }
function RuntimeInstalledVersion: String;
begin
  Result := Trim(MachineValue(RuntimeKey, 'Version'));
  if (Copy(Result, 1, 1) = 'v') or (Copy(Result, 1, 1) = 'V') then
    Result := Copy(Result, 2, Length(Result));
end;

procedure InitDrivers;
begin
  RuntimeMissing := not RuntimeInstalled;
  if RuntimeMissing then
    Log(RuntimeName + ': missing; setup installs it first.')
  else
    Log(RuntimeName + ': installed.');
  SetArrayLength(Drivers, 3);
  SetDriver(0, 'vjoy', 'vJoy', '{#VJoyBundled}', '{#VJoyFile}',
    'BrunnerInnovation/vJoy', 'vJoySetup_v', '_Win10_Win11.exe');
  SetDriver(1, 'vigembus', 'ViGEmBus', '{#ViGEmBusBundled}', '{#ViGEmBusFile}',
    '', '', '');
  SetDriver(2, 'hidhide', 'HidHide', '{#HidHideBundled}', '{#HidHideFile}',
    'nefarius/HidHide', 'HidHide_', '_x64.exe');
  DetectDrivers;
end;

function DriverIndex(const Key: String): Integer;
var
  I: Integer;
begin
  Result := -1;
  for I := 0 to GetArrayLength(Drivers) - 1 do
    if Drivers[I].Key = Key then
    begin
      Result := I;
      Exit;
    end;
end;

{ The row's words on the Drivers page (01 S187). }
function DriverLabel(I: Integer): String;
begin
  if Drivers[I].State = 'missing' then
    Result := 'not installed'
  else if Drivers[I].State = 'older' then
    Result := 'update available: ' + Drivers[I].Installed + ' ' + #$2192 + ' ' +
      Drivers[I].Bundled
  else
    Result := Drivers[I].Installed;
end;

{ The version a job installs: the newer download when there is one. }
function TargetVersion(I: Integer): String;
begin
  if Drivers[I].LatestVersion <> '' then
    Result := Drivers[I].LatestVersion
  else
    Result := Drivers[I].Bundled;
end;

{ -- a small JSON reader: enough for GitHub's release and the helper's
  results file (12 S25); never raises. }

{ S[P] as a string; '' past either end. Used wherever an index may be out
  of range: the script never relies on short-circuit evaluation. }
function CharAt(const S: String; P: Integer): String;
begin
  if (P < 1) or (P > Length(S)) then
    Result := ''
  else
    Result := Copy(S, P, 1);
end;

function SkipSpaces(const S: String; P: Integer): Integer;
var
  C: String;
begin
  while True do
  begin
    C := CharAt(S, P);
    if (C <> ' ') and (C <> #9) and (C <> #10) and (C <> #13) then
      Break;
    P := P + 1;
  end;
  Result := P;
end;

{ A \u escape's character. Python's json writes ASCII only, so the program's
  own non-ASCII characters arrive this way. }
function CodeToChar(Code: Integer): String;
begin
  if (Code >= 32) and (Code < 256) then
    Result := Chr(Code)
  else if Code = $2026 then
    Result := #$2026
  else if Code = $2192 then
    Result := #$2192
  else if Code = $203A then
    Result := #$203A
  else if (Code = $2018) or (Code = $2019) then
    Result := ''''
  else if (Code = $201C) or (Code = $201D) then
    Result := '"'
  else
    Result := '?';
end;

{ The JSON string starting at S[P] (its opening quote); P ends after the
  closing quote. }
function ReadJsonString(const S: String; var P: Integer): String;
var
  C: Char;
begin
  Result := '';
  P := P + 1;
  while P <= Length(S) do
  begin
    C := S[P];
    if C = '"' then
    begin
      P := P + 1;
      Exit;
    end;
    if (C = '\') and (P < Length(S)) then
    begin
      P := P + 1;
      C := S[P];
      case C of
        'n': Result := Result + #13#10;
        'r': Result := Result + '';
        't': Result := Result + ' ';
        'b', 'f': Result := Result + '';
        'u':
          begin
            Result := Result + CodeToChar(StrToIntDef('$' + Copy(S, P + 1, 4), 63));
            P := P + 4;
          end;
      else
        Result := Result + C;
      end;
    end
    else
      Result := Result + C;
    P := P + 1;
  end;
end;

{ The value of "Key" found in S[From..UpTo]: a string decoded, a bare word
  (true, false, a number) as it is; '' when not there. }
function JsonValue(const S, Key: String; From, UpTo: Integer): String;
var
  P, Start: Integer;
begin
  Result := '';
  P := FindFrom('"' + Key + '"', S, From);
  if (P = 0) or (P > UpTo) then
    Exit;
  P := SkipSpaces(S, P + Length(Key) + 2);
  if CharAt(S, P) <> ':' then
    Exit;
  P := SkipSpaces(S, P + 1);
  if CharAt(S, P) = '' then
    Exit;
  if CharAt(S, P) = '"' then
    Result := ReadJsonString(S, P)
  else
  begin
    Start := P;
    while (CharAt(S, P) <> '') and (Pos(CharAt(S, P), ',}] ' + #9#13#10) = 0) do
      P := P + 1;
    Result := Copy(S, Start, P - Start);
  end;
end;

{ Where each object of the array "Key" starts and ends in S; the count. }
function JsonArrayObjects(const S, Key: String; var Starts, Ends: TArrayOfInteger): Integer;
var
  P, Depth: Integer;
  InString: Boolean;
  C: Char;
begin
  Result := 0;
  SetArrayLength(Starts, 0);
  SetArrayLength(Ends, 0);
  P := FindFrom('"' + Key + '"', S, 1);
  if P = 0 then
    Exit;
  P := FindFrom('[', S, P);
  if P = 0 then
    Exit;
  Depth := 0;
  InString := False;
  P := P + 1;
  while P <= Length(S) do
  begin
    C := S[P];
    if InString then
    begin
      if C = '\' then
        P := P + 1
      else if C = '"' then
        InString := False;
    end
    else if C = '"' then
      InString := True
    else if C = '{' then
    begin
      if Depth = 0 then
      begin
        SetArrayLength(Starts, Result + 1);
        Starts[Result] := P;
      end;
      Depth := Depth + 1;
    end
    else if C = '}' then
    begin
      Depth := Depth - 1;
      if Depth = 0 then
      begin
        SetArrayLength(Ends, Result + 1);
        Ends[Result] := P;
        Result := Result + 1;
      end;
    end
    else if (C = ']') and (Depth = 0) then
      Exit;
    P := P + 1;
  end;
end;

function JsonEscape(const S: String): String;
begin
  Result := S;
  StringChangeEx(Result, '\', '\\', True);
  StringChangeEx(Result, '"', '\"', True);
end;

function JoinLines(const Lines: TArrayOfString): String;
var
  I: Integer;
begin
  Result := '';
  for I := 0 to GetArrayLength(Lines) - 1 do
    Result := Result + Lines[I] + #10;
end;

{ -- newer versions (01 S189) }

{ GET Url with a 5-second limit at each stage; False for no internet or
  any error. }
function FetchText(const Url: String; var Text: String): Boolean;
var
  Http: Variant;
begin
  Result := False;
  Text := '';
  try
    Http := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Http.SetTimeouts(5000, 5000, 5000, 5000);
    Http.Open('GET', Url, False);
    Http.SetRequestHeader('User-Agent', 'Gremlin-Platforms');
    Http.SetRequestHeader('Accept', 'application/vnd.github+json');
    Http.Send('');
    if Http.Status = 200 then
    begin
      Text := Http.ResponseText;
      Result := True;
    end
    else
      Log('GitHub answered ' + IntToStr(Http.Status) + ' for ' + Url);
  except
    Log('No answer from ' + Url + ': ' + GetExceptionMessage);
  end;
end;

function UrlFileName(const Url: String): String;
var
  I: Integer;
begin
  Result := Url;
  for I := Length(Url) downto 1 do
    if Url[I] = '/' then
    begin
      Result := Copy(Url, I + 1, Length(Url));
      Exit;
    end;
end;

{ Prefix + digits and dots + Suffix: drivers.py's asset_regex. }
function AssetMatches(I: Integer; const Name: String): Boolean;
var
  Middle: String;
  J: Integer;
begin
  Result := False;
  if Length(Name) <= Length(Drivers[I].AssetPrefix) + Length(Drivers[I].AssetSuffix) then
    Exit;
  if Copy(Name, 1, Length(Drivers[I].AssetPrefix)) <> Drivers[I].AssetPrefix then
    Exit;
  if Copy(Name, Length(Name) - Length(Drivers[I].AssetSuffix) + 1,
    Length(Drivers[I].AssetSuffix)) <> Drivers[I].AssetSuffix then
    Exit;
  Middle := Copy(Name, Length(Drivers[I].AssetPrefix) + 1,
    Length(Name) - Length(Drivers[I].AssetPrefix) - Length(Drivers[I].AssetSuffix));
  for J := 1 to Length(Middle) do
    if Pos(Copy(Middle, J, 1), '0123456789.') = 0 then
      Exit;
  Result := True;
end;

{ Asks GitHub for the driver's latest release once; keeps it only when it is
  newer than the bundled copy. No internet or a bad answer: bundled only. }
procedure CheckLatest(I: Integer);
var
  Text, Tag, Url, Name: String;
  P: Integer;
begin
  if Drivers[I].LatestChecked or (Drivers[I].Repo = '') then
    Exit;
  Drivers[I].LatestChecked := True;
  if not FetchText('https://api.github.com/repos/' + Drivers[I].Repo +
    '/releases/latest', Text) then
    Exit;
  Tag := JsonValue(Text, 'tag_name', 1, Length(Text));
  while (CharAt(Tag, 1) = 'v') or (CharAt(Tag, 1) = 'V') do
    Tag := Copy(Tag, 2, Length(Tag));
  if (Tag = '') or (CompareVersions(Tag, Drivers[I].Bundled) <= 0) then
  begin
    Log(Drivers[I].Name + ': latest release "' + Tag + '" is not newer than ' +
      Drivers[I].Bundled);
    Exit;
  end;
  P := 1;
  while True do
  begin
    P := FindFrom('"browser_download_url"', Text, P);
    if P = 0 then
      Break;
    Url := JsonValue(Text, 'browser_download_url', P, Length(Text));
    Name := UrlFileName(Url);
    if (Copy(Url, 1, 19) = 'https://github.com/') and AssetMatches(I, Name) then
    begin
      Drivers[I].LatestVersion := Tag;
      Drivers[I].LatestUrl := Url;
      Drivers[I].LatestName := Name;
      Log(Drivers[I].Name + ': newer release ' + Tag + ' at ' + Url);
      Exit;
    end;
    P := P + 1;
  end;
  Log(Drivers[I].Name + ': release ' + Tag + ' has no matching file');
end;

{ Downloads each newer release with the download page (progress, Abort);
  a failure or Abort leaves that driver on its bundled copy. The helper
  checks the signature before it runs one (12 S25). }
procedure DownloadNewerDrivers;
var
  I: Integer;
begin
  for I := 0 to GetArrayLength(Drivers) - 1 do
  begin
    Drivers[I].Download := '';
    if not Drivers[I].Chosen or (Drivers[I].LatestUrl = '') then
      Continue;
    DriverDownloadPage.Clear;
    DriverDownloadPage.Add(Drivers[I].LatestUrl, Drivers[I].LatestName, '');
    DriverDownloadPage.SetText('Downloading ' + Drivers[I].Name + ' ' +
      Drivers[I].LatestVersion + #$2026, '');
    DriverDownloadPage.Show;
    try
      try
        DriverDownloadPage.Download;
        Drivers[I].Download := ExpandConstant('{tmp}\') + Drivers[I].LatestName;
        Log(Drivers[I].Name + ': downloaded ' + Drivers[I].Download);
      except
        if DriverDownloadPage.AbortedByUser then
          Log(Drivers[I].Name + ': download stopped; using the bundled copy.')
        else
          Log(Drivers[I].Name + ': download failed (' + GetExceptionMessage +
            '); using the bundled copy.');
        Drivers[I].Download := '';
        Drivers[I].LatestVersion := '';
        Drivers[I].LatestUrl := '';
        Drivers[I].LatestName := '';
      end;
    finally
      DriverDownloadPage.Hide;
    end;
  end;
end;

{ -- the vJoy device choice (06 S185, on the Drivers page by 01 S187) }

procedure AddVJoyDevice(var List: TVJoyDevices; Id, Axes, Buttons, Hats: Integer);
var
  N: Integer;
begin
  N := GetArrayLength(List);
  SetArrayLength(List, N + 1);
  List[N].Id := Id;
  List[N].Axes := Axes;
  List[N].Buttons := Buttons;
  List[N].Hats := Hats;
end;

procedure CopyVJoyDevices(const Source: TVJoyDevices; var Target: TVJoyDevices);
var
  K: Integer;
begin
  SetArrayLength(Target, 0);
  for K := 0 to GetArrayLength(Source) - 1 do
    AddVJoyDevice(Target, Source[K].Id, Source[K].Axes, Source[K].Buttons,
      Source[K].Hats);
end;

{ drivers.default_buttons: a new device's buttons count down from its
  number, vJoy N = 129 - N, so no two new devices are alike. }
function DefaultButtons(Id: Integer): Integer;
begin
  Result := VJoyMaxButtons + 1 - Id;
  if Result > VJoyMaxButtons then
    Result := VJoyMaxButtons;
  if Result < 0 then
    Result := 0;
end;

{ A preset's devices (gremlin/drivers.py PRESETS): "full" is all eight
  axes, DefaultButtons(id) buttons (128, 127) and 4 hats. }
procedure PresetDevices(const Name: String; var List: TVJoyDevices);
var
  K, Count: Integer;
begin
  SetArrayLength(List, 0);
  Count := 1;
  if Name = VJoyPresetTwo then
    Count := 2;
  for K := 1 to Count do
    AddVJoyDevice(List, K, VJoyAllAxes, DefaultButtons(K), VJoyMaxHats);
end;

{ The same axes, buttons and hats, device by device (ids aside). }
function SameLayout(const A, B: TVJoyDevices): Boolean;
var
  K: Integer;
begin
  Result := GetArrayLength(A) = GetArrayLength(B);
  if not Result then
    Exit;
  for K := 0 to GetArrayLength(A) - 1 do
    if (A[K].Axes <> B[K].Axes) or (A[K].Buttons <> B[K].Buttons) or
      (A[K].Hats <> B[K].Hats) then
    begin
      Result := False;
      Exit;
    end;
end;

function MatchingPreset(const List: TVJoyDevices): String;
var
  Preset: TVJoyDevices;
begin
  Result := VJoyCustom;
  PresetDevices(VJoyPresetOne, Preset);
  if SameLayout(List, Preset) then
    Result := VJoyPresetOne;
  PresetDevices(VJoyPresetTwo, Preset);
  if SameLayout(List, Preset) then
    Result := VJoyPresetTwo;
end;

{ Existing devices change only when edited (06 S185): an edit that ends
  where vJoy already is is no edit. }
function VJoyEdited: Boolean;
begin
  Result := False;
  if not VJoyUserEdited then
    Exit;
  if GetArrayLength(VJoyCurrent) = 0 then
    Result := True
  else
    Result := not SameLayout(VJoyCurrent, VJoyChosen);
end;

function IsDigits(const S: String): Boolean;
var
  K: Integer;
begin
  Result := S <> '';
  for K := 1 to Length(S) do
    if (Copy(S, K, 1) < '0') or (Copy(S, K, 1) > '9') then
    begin
      Result := False;
      Exit;
    end;
end;

{ The first word of S (split on spaces and tabs); S keeps the rest. }
function NextToken(var S: String): String;
var
  P: Integer;
begin
  S := Trim(S);
  P := 1;
  while (CharAt(S, P) <> '') and (CharAt(S, P) > ' ') do
    P := P + 1;
  Result := Copy(S, 1, P - 1);
  S := Copy(S, P, Length(S));
end;

{ -- reading vJoyConfig -t: the same rules as gremlin/driver_jobs.py
  parse_status_list and parse_report }

{ "Name: value" with a name of letters and spaces only (driver_jobs _FIELD);
  Name comes back in lower case. }
function VJoyField(const Line: String; var Name, Value: String): Boolean;
var
  P, K: Integer;
  C: String;
begin
  Result := False;
  P := Pos(':', Line);
  if P = 0 then
    Exit;
  Name := LowerCase(Trim(Copy(Line, 1, P - 1)));
  Value := Trim(Copy(Line, P + 1, Length(Line)));
  if Name = '' then
    Exit;
  for K := 1 to Length(Name) do
  begin
    C := Copy(Name, K, 1);
    if ((C < 'a') or (C > 'z')) and (C <> ' ') then
      Exit;
  end;
  Result := True;
end;

{ VJoyAxisNames' K-th name (0-7), e.g. 'sl0'. }
function AxisName(K: Integer): String;
var
  Names: String;
  J: Integer;
begin
  Names := VJoyAxisNames;
  for J := 0 to K do
    Result := NextToken(Names);
end;

{ D-AXIS-NAMES: the K-th column heading (0-7), e.g. 'S1'. }
function AxisHeading(K: Integer): String;
var
  Names: String;
  J: Integer;
begin
  Names := VJoyAxisLabels;
  for J := 0 to K do
    Result := NextToken(Names);
end;

{ drivers.axis_label: the axis table's short name, 'sl0' -> 'S1'. }
function AxisLabel(K: Integer): String;
begin
  Result := AxisHeading(K);
end;

function AxisTicked(Mask, K: Integer): Boolean;
begin
  Result := (Mask and (1 shl K)) <> 0;
end;

function AxesCountOf(Mask: Integer): Integer;
var
  K: Integer;
begin
  Result := 0;
  for K := 0 to 7 do
    if AxisTicked(Mask, K) then
      Result := Result + 1;
end;

{ The "Axes:" value of vJoyConfig -t <id> has one token per position, '-'
  for a missing axis ("X Y - - - - Sl0 - ..."); positions 1-8 are X Y Z
  RX RY RZ SL0 SL1 (driver_jobs.parse_report), the rest are ignored. }
function AxesFromReport(Value: String): Integer;
var
  K: Integer;
  Token: String;
begin
  Result := 0;
  for K := 0 to 7 do
  begin
    Token := NextToken(Value);
    if Token = '' then
      Exit;
    if Token <> '-' then
      Result := Result or (1 shl K);
  end;
end;

{ The job file's names list (12 S25a): ["x", "y", "sl0"]. }
function AxesJson(Mask: Integer): String;
var
  K: Integer;
begin
  Result := '';
  for K := 0 to 7 do
    if AxisTicked(Mask, K) then
    begin
      if Result <> '' then
        Result := Result + ', ';
      Result := Result + '"' + AxisName(K) + '"';
    end;
  Result := '[' + Result + ']';
end;

{ `vJoyConfig -t <id>`: adds device Wanted to List when the report has it. }
procedure ParseVJoyReport(const Lines: TArrayOfString; Wanted: Integer;
  var List: TVJoyDevices);
var
  K, Current: Integer;
  Name, Value: String;
begin
  Current := -1;
  for K := 0 to GetArrayLength(Lines) - 1 do
  begin
    if not VJoyField(Lines[K], Name, Value) then
      Continue;
    if Name = 'device' then
    begin
      Current := -1;
      if IsDigits(Value) then
        if StrToIntDef(Value, 0) = Wanted then
        begin
          AddVJoyDevice(List, Wanted, 0, 0, 0);
          Current := GetArrayLength(List) - 1;
        end;
    end
    else if Current < 0 then
      Continue
    else if (Name = 'buttons') and IsDigits(Value) then
      List[Current].Buttons := StrToIntDef(Value, 0)
    else if ((Name = 'continous povs') or (Name = 'continuous povs')) and
      IsDigits(Value) then
      List[Current].Hats := StrToIntDef(Value, 0)
    else if Name = 'axes' then
      List[Current].Axes := AxesFromReport(Value);
  end;
end;

{ `vJoyConfig -t`: the numbers of the devices that exist ("Device N:
  Status: S", S not MISSING or UNKNOWN), and in Busy those whose S is BUSY
  or OWNED (driver_jobs.busy_vjoy_devices). }
procedure ParseVJoyStatus(const Lines: TArrayOfString; var Ids, Busy: TArrayOfInteger);
var
  K, P, N: Integer;
  Left, Right, Number, State: String;
begin
  SetArrayLength(Ids, 0);
  SetArrayLength(Busy, 0);
  for K := 0 to GetArrayLength(Lines) - 1 do
  begin
    P := Pos(':', Lines[K]);
    if P = 0 then
      Continue;
    Left := Trim(Copy(Lines[K], 1, P - 1));
    Right := Trim(Copy(Lines[K], P + 1, Length(Lines[K])));
    if LowerCase(Copy(Left, 1, 6)) <> 'device' then
      Continue;
    if (CharAt(Left, 7) = '') or (CharAt(Left, 7) > ' ') then
      Continue;
    Number := Trim(Copy(Left, 7, Length(Left)));
    if not IsDigits(Number) then
      Continue;
    if LowerCase(Copy(Right, 1, 6)) <> 'status' then
      Continue;
    Right := Trim(Copy(Right, 7, Length(Right)));
    if CharAt(Right, 1) <> ':' then
      Continue;
    Right := Copy(Right, 2, Length(Right));
    State := UpperCase(NextToken(Right));
    if (State = '') or (State = 'MISSING') or (State = 'UNKNOWN') then
      Continue;
    N := GetArrayLength(Ids);
    SetArrayLength(Ids, N + 1);
    Ids[N] := StrToIntDef(Number, 0);
    if (State = 'BUSY') or (State = 'OWNED') then
    begin
      N := GetArrayLength(Busy);
      SetArrayLength(Busy, N + 1);
      Busy[N] := StrToIntDef(Number, 0);
    end;
  end;
end;

function VJoyConfigPath: String;
begin
  Result := ExpandConstant('{commonpf64}\vJoy\x64\vJoyConfig.exe');
end;

{ Runs vJoyConfig read-only, as setup's own user (never as administrator),
  with its output in a file in setup's temp folder. False when it could not
  run or print. }
function RunVJoyConfig(const Params: String; var Lines: TArrayOfString): Boolean;
var
  Exe, OutFile: String;
  Code: Integer;
begin
  Result := False;
  SetArrayLength(Lines, 0);
  Exe := VJoyConfigPath;
  if not FileExists(Exe) then
    Exit;
  OutFile := ExpandConstant('{tmp}\') + VJoyCaptureFile;
  DeleteFile(OutFile);
  if not ExecAsOriginalUser(ExpandConstant('{cmd}'), '/C ""' + Exe + '" ' +
    Params + ' > "' + OutFile + '" 2>&1"', '', SW_HIDE, ewWaitUntilTerminated,
    Code) then
  begin
    Log('vJoyConfig ' + Params + ' could not run: ' + SysErrorMessage(Code));
    Exit;
  end;
  Result := LoadStringsFromFile(OutFile, Lines);
  DeleteFile(OutFile);
end;

{ What vJoy has now, device by device (driver_jobs.current_vjoy_devices). }
procedure ReadVJoyLayout;
var
  Lines, Report: TArrayOfString;
  Ids: TArrayOfInteger;
  J: Integer;
begin
  SetArrayLength(VJoyCurrent, 0);
  SetArrayLength(VJoyBusy, 0);
  VJoyLayoutRead := RunVJoyConfig('-t', Lines);
  if not VJoyLayoutRead then
    Exit;
  ParseVJoyStatus(Lines, Ids, VJoyBusy);
  if GetArrayLength(VJoyBusy) > 0 then
    Log('vJoy devices in use by another program: ' +
      IntToStr(GetArrayLength(VJoyBusy)));
  for J := 0 to GetArrayLength(Ids) - 1 do
    if RunVJoyConfig('-t ' + IntToStr(Ids[J]), Report) then
      ParseVJoyReport(Report, Ids[J], VJoyCurrent);
  Log('vJoy has ' + IntToStr(GetArrayLength(VJoyCurrent)) + ' device(s) now.');
end;

{ vJoy installed: its devices are read and shown as they are; not
  installed: the default preset, no current layout (01 S187). }
procedure InitVJoyChoice;
begin
  VJoyLayoutRead := False;
  VJoyUserEdited := False;
  VJoySetupPlanned := False;
  SetArrayLength(VJoyCurrent, 0);
  SetArrayLength(VJoyBusy, 0);
  if not WizardSilent then
    if Drivers[DriverIndex('vjoy')].State <> 'missing' then
      ReadVJoyLayout;
  if GetArrayLength(VJoyCurrent) > 0 then
    CopyVJoyDevices(VJoyCurrent, VJoyChosen)
  else
    PresetDevices(VJoyPresetOne, VJoyChosen);
end;

{ "1 hat", "2 hats": a count with its word, singular for 1. }
function CountText(Count: Integer; const One, Many: String): String;
begin
  if Count = 1 then
    Result := '1 ' + One
  else
    Result := IntToStr(Count) + ' ' + Many;
end;

{ driver_jobs.describe_device's axes: "3 axes (X, Y, S1)", "1 axis (X)",
  "0 axes", all eight "8 axes (X-S2)". }
function AxesText(Mask: Integer): String;
var
  K: Integer;
  Names: String;
begin
  Result := CountText(AxesCountOf(Mask), 'axis', 'axes');
  if Mask = VJoyAllAxes then
    Result := Result + ' (' + AxisLabel(0) + '-' + AxisLabel(7) + ')'
  else if Mask <> 0 then
  begin
    Names := '';
    for K := 0 to 7 do
      if AxisTicked(Mask, K) then
      begin
        if Names <> '' then
          Names := Names + ', ';
        Names := Names + AxisLabel(K);
      end;
    Result := Result + ' (' + Names + ')';
  end;
end;

function VJoyDeviceText(const D: TVJoyDevice): String;
begin
  Result := IntToStr(D.Id) + ': ' + AxesText(D.Axes) + ', ' +
    CountText(D.Buttons, 'button', 'buttons') + ', ' +
    CountText(D.Hats, 'hat', 'hats');
end;

function VJoyLayoutText(const List: TVJoyDevices): String;
var
  K: Integer;
begin
  Result := '';
  for K := 0 to GetArrayLength(List) - 1 do
  begin
    if K > 0 then
      Result := Result + '; ';
    Result := Result + VJoyDeviceText(List[K]);
  end;
end;

{ "vJoy 1", "vJoy 1 and vJoy 3", "vJoy 1, vJoy 2 and vJoy 4". }
function VJoyNamesJoined(const Names: TArrayOfString): String;
var
  K, N: Integer;
begin
  Result := '';
  N := GetArrayLength(Names);
  for K := 0 to N - 1 do
  begin
    if K = 0 then
      Result := Names[K]
    else if K = N - 1 then
      Result := Result + ' and ' + Names[K]
    else
      Result := Result + ', ' + Names[K];
  end;
end;

{ drivers.update_info_text: the information box before a vJoy update. }
function VJoyUpdateInfoText(const List: TVJoyDevices): String;
var
  K: Integer;
  Names: String;
begin
  if GetArrayLength(List) = 0 then
  begin
    Result := VJoyUpdateUnreadHead + #$203A + VJoyUpdateUnreadTail;
    Exit;
  end;
  Names := '';
  for K := 0 to GetArrayLength(List) - 1 do
  begin
    if K > 0 then
      Names := Names + ', ';
    Names := Names + 'vJoy ' + IntToStr(List[K].Id);
  end;
  Result := VJoyUpdateInfoHead + CountText(GetArrayLength(List), 'vJoy device',
    'vJoy devices') + ' (' + Names + ')' + VJoyUpdateInfoTail;
end;

{ drivers.lost_text: "After updating vJoy, vJoy 4 (8 axes, 32 buttons,
  0 hats) is missing. ..." }
function VJoyLostText(const List: TVJoyDevices): String;
var
  K: Integer;
  Names: TArrayOfString;
begin
  SetArrayLength(Names, GetArrayLength(List));
  for K := 0 to GetArrayLength(List) - 1 do
    Names[K] := 'vJoy ' + IntToStr(List[K].Id) + ' (' +
      CountText(AxesCountOf(List[K].Axes), 'axis', 'axes') + ', ' +
      CountText(List[K].Buttons, 'button', 'buttons') + ', ' +
      CountText(List[K].Hats, 'hat', 'hats') + ')';
  Result := VJoyLostHead + VJoyNamesJoined(Names);
  if GetArrayLength(List) = 1 then
    Result := Result + VJoyLostOne
  else
    Result := Result + VJoyLostMany;
end;

{ drivers.added_text: "vJoy 1 was added by the vJoy update"; '' for none. }
function VJoyAddedText(const Ids: TArrayOfInteger): String;
var
  K: Integer;
  Names: TArrayOfString;
begin
  Result := '';
  if GetArrayLength(Ids) = 0 then
    Exit;
  SetArrayLength(Names, GetArrayLength(Ids));
  for K := 0 to GetArrayLength(Ids) - 1 do
    Names[K] := 'vJoy ' + IntToStr(Ids[K]);
  Result := VJoyNamesJoined(Names);
  if GetArrayLength(Ids) = 1 then
    Result := Result + VJoyAddedOne
  else
    Result := Result + VJoyAddedMany;
end;

function VJoyCurrentLine: String;
begin
  if Drivers[DriverIndex('vjoy')].State = 'missing' then
    Result := ''
  else if not VJoyLayoutRead then
    Result := 'The vJoy devices could not be read.'
  else if GetArrayLength(VJoyCurrent) = 0 then
    Result := 'Now: no vJoy devices.'
  else
    Result := 'Now: ' + VJoyLayoutText(VJoyCurrent);
end;

function VJoyIdUsed(const List: TVJoyDevices; Id: Integer): Boolean;
var
  K: Integer;
begin
  Result := False;
  for K := 0 to GetArrayLength(List) - 1 do
    if List[K].Id = Id then
      Result := True;
end;

{ drivers.alike_warning(drivers.alike_devices(List)): one sentence per
  group of devices with the same number of axes, buttons and hats (the
  program's own rule, gremlin/device_initialization.py); '' when none.
  The rows are in id order, so each group's ids and the groups are too. }
function VJoyAlikeWarning(const List: TVJoyDevices): String;
var
  K, J, N, G: Integer;
  Done: array of Boolean;
  Ids: TArrayOfInteger;
  Who: String;
begin
  Result := '';
  N := GetArrayLength(List);
  SetArrayLength(Done, N);
  for K := 0 to N - 1 do
    Done[K] := False;
  for K := 0 to N - 1 do
  begin
    if Done[K] then
      Continue;
    SetArrayLength(Ids, 0);
    for J := K to N - 1 do
      if (AxesCountOf(List[J].Axes) = AxesCountOf(List[K].Axes)) and
        (List[J].Buttons = List[K].Buttons) and (List[J].Hats = List[K].Hats) then
      begin
        Done[J] := True;
        G := GetArrayLength(Ids);
        SetArrayLength(Ids, G + 1);
        Ids[G] := List[J].Id;
      end;
    G := GetArrayLength(Ids);
    if G < 2 then
      Continue;
    Who := 'vJoy ' + IntToStr(Ids[0]);
    for J := 1 to G - 1 do
      if J = G - 1 then
        Who := Who + ' and vJoy ' + IntToStr(Ids[J])
      else
        Who := Who + ', vJoy ' + IntToStr(Ids[J]);
    if Result <> '' then
      Result := Result + ' ';
    Result := Result + Who + VJoyAlikeText;
  end;
end;

function VJoyIdBusy(Id: Integer): Boolean;
var
  K: Integer;
begin
  Result := False;
  for K := 0 to GetArrayLength(VJoyBusy) - 1 do
    if VJoyBusy[K] = Id then
      Result := True;
end;

{ The row holding device Id, -1 when List has none. }
function VJoyIndexOf(const List: TVJoyDevices; Id: Integer): Integer;
var
  K: Integer;
begin
  Result := -1;
  for K := 0 to GetArrayLength(List) - 1 do
    if List[K].Id = Id then
      Result := K;
end;

{ D-01-VJOY-IN-USE: the in-use devices that exist now and that the chosen
  layout changes or removes (preset included), in id order; none unless the
  user edited the devices (06 S185: they change only then). }
procedure VJoyChangedBusy(var Ids: TArrayOfInteger);
var
  Id, C, N, G: Integer;
  Changed: Boolean;
begin
  SetArrayLength(Ids, 0);
  if not VJoyEdited then
    Exit;
  for Id := 1 to VJoyMaxDevices do
  begin
    if not VJoyIdBusy(Id) then
      Continue;
    C := VJoyIndexOf(VJoyCurrent, Id);
    if C < 0 then
      Continue;
    N := VJoyIndexOf(VJoyChosen, Id);
    if N < 0 then
      Changed := True
    else
      Changed := (VJoyChosen[N].Axes <> VJoyCurrent[C].Axes) or
        (VJoyChosen[N].Buttons <> VJoyCurrent[C].Buttons) or
        (VJoyChosen[N].Hats <> VJoyCurrent[C].Hats);
    if Changed then
    begin
      G := GetArrayLength(Ids);
      SetArrayLength(Ids, G + 1);
      Ids[G] := Id;
    end;
  end;
end;

{ drivers.in_use_warning(Ids): "vJoy 4 is in use ... Change it anyway?",
  "vJoy 1 and vJoy 4 are ...", "vJoy 1, vJoy 2 and vJoy 4 are ..."; ''
  for none. Ids in id order. }
function VJoyInUseWarning(const Ids: TArrayOfInteger): String;
var
  J, G: Integer;
begin
  Result := '';
  G := GetArrayLength(Ids);
  if G = 0 then
    Exit;
  Result := 'vJoy ' + IntToStr(Ids[0]);
  for J := 1 to G - 1 do
    if J = G - 1 then
      Result := Result + ' and vJoy ' + IntToStr(Ids[J])
    else
      Result := Result + ', vJoy ' + IntToStr(Ids[J]);
  if G = 1 then
    Result := Result + VJoyInUseOne
  else
    Result := Result + VJoyInUseMany;
end;

{ -- the device rows (answer 2a) }

{ The line under the box: which device rows show, of how many (N =
  devices; the "+ Add device" row under them is not counted). }
function VJoyShowingLine(Top, N: Integer): String;
var
  Last: Integer;
begin
  Last := Top + VJoyVisibleRows;
  if Last > N then
    Last := N;
  if N = 0 then
    Result := 'No vJoy devices'
  else if (Top = 0) and (N = 1) then
    Result := 'Showing 1 device'
  else if (Top = 0) and (Last = N) then
    Result := 'Showing all ' + IntToStr(N) + ' devices'
  else
    Result := 'Showing ' + IntToStr(Top + 1) + '-' +
      IntToStr(Last) + ' of ' + IntToStr(N) + ' devices';
end;

{ Moves the rows to the list box's scroll position and updates the
  "Showing" line. }
procedure ShowVJoyTopRow;
var
  Top: Integer;
begin
  Top := 0;
  if VJoyScroll.Visible then
  begin
    { The list box keeps its own item height only while its window lives:
      put the row height back if the window was made again. }
    if SendMessage(VJoyScroll.Handle, LbGetItemHeight, 0, 0) <> VJoyRowHeight then
      SendMessage(VJoyScroll.Handle, LbSetItemHeight, 0, VJoyRowHeight);
    Top := SendMessage(VJoyScroll.Handle, LbGetTopIndex, 0, 0);
  end;
  if Top < 0 then
    Top := 0;
  if Top <> VJoyTopRow then
  begin
    VJoyTopRow := Top;
    VJoyRowsPanel.Top := -Top * VJoyRowHeight;
    VJoyShowingText.Caption := VJoyShowingLine(Top, GetArrayLength(VJoyChosen));
  end;
end;

{ A click in the list box's thin strip beside the bar selects nothing. }
procedure VJoyScrollClick(Sender: TObject);
begin
  VJoyScroll.ItemIndex := -1;
end;

{ The list box has no scroll event in Pascal Script: a timer follows its
  position while the Drivers page shows. }
procedure VJoyScrollTick(Wnd: HWND; Msg, TimerId, Time: LongWord);
begin
  ShowVJoyTopRow;
end;

{ Scrolls the list box by whole rows (clamped) and moves the rows with it
  at once, through the same ShowVJoyTopRow the timer uses. }
procedure ScrollVJoyRows(Rows: Integer);
var
  Top, MaxTop: Integer;
begin
  MaxTop := VJoyScroll.Items.Count - VJoyVisibleRows;
  if MaxTop < 0 then
    MaxTop := 0;
  Top := SendMessage(VJoyScroll.Handle, LbGetTopIndex, 0, 0) + Rows;
  if Top > MaxTop then
    Top := MaxTop;
  if Top < 0 then
    Top := 0;
  SendMessage(VJoyScroll.Handle, LbSetTopIndex, Top, 0);
  ShowVJoyTopRow;
end;

{ True when the screen point is over the rows or their scroll bar. }
function OverVJoyRows(X, Y: Longint): Boolean;
var
  Rows, Bar: TWheelRect;
begin
  Result := False;
  if not VJoyScroll.Visible or (IsWindowVisible(VJoyViewport.Handle) = 0) then
    Exit;
  if (GetWindowRect(VJoyViewport.Handle, Rows) = 0) or
     (GetWindowRect(VJoyScroll.Handle, Bar) = 0) then
    Exit;
  Result := (X >= Rows.Left) and (X < Bar.Right) and (Y >= Rows.Top) and
    (Y < Rows.Bottom);
end;

{ 01 S187 (answer 6a+b): the wheel over the rows or the bar scrolls one row
  per notch. Other mouse messages pass on untouched. }
function VJoyWheelProc(Code: Integer; WParam, LParam: Longint): Longint;
var
  X, Y, Data, Delta, Rows: Longint;
begin
  if (Code = HcAction) and (WParam = WmMouseWheel) then
  begin
    ReadHookLong(X, LParam + HookPointX, 4);
    ReadHookLong(Y, LParam + HookPointY, 4);
    if OverVJoyRows(X, Y) then
    begin
      ReadHookLong(Data, LParam + HookMouseData, 4);
      Delta := (Data shr 16) and $FFFF;
      if Delta >= $8000 then
        Delta := Delta - $10000;
      VJoyWheelRest := VJoyWheelRest + Delta;
      Rows := VJoyWheelRest div WheelDelta;
      VJoyWheelRest := VJoyWheelRest - Rows * WheelDelta;
      { Wheel up (positive) shows earlier rows. }
      if Rows <> 0 then
        ScrollVJoyRows(-Rows);
      Result := 1;
      Exit;
    end;
  end;
  Result := CallNextHookEx(VJoyWheelHook, Code, WParam, LParam);
end;

{ The timer and the wheel hook live while the Drivers page shows. }
procedure WatchVJoyScroll(Watch: Boolean);
begin
  if Watch and (VJoyScrollTimer = 0) then
    VJoyScrollTimer := SetTimer(0, 0, 100, CreateCallback(@VJoyScrollTick))
  else if not Watch and (VJoyScrollTimer <> 0) then
  begin
    KillTimer(0, VJoyScrollTimer);
    VJoyScrollTimer := 0;
  end;
  if Watch and (VJoyWheelHook = 0) then
  begin
    VJoyWheelRest := 0;
    VJoyWheelHook := SetWindowsHookEx(WhMouse, CreateCallback(@VJoyWheelProc), 0,
      GetCurrentThreadId);
  end
  else if not Watch and (VJoyWheelHook <> 0) then
  begin
    UnhookWindowsHookEx(VJoyWheelHook);
    VJoyWheelHook := 0;
  end;
end;

{ The number "+ Add device" gives: the lowest one not in the list. }
function VJoyNextFreeId(const List: TVJoyDevices): Integer;
begin
  Result := 1;
  while VJoyIdUsed(List, Result) do
    Result := Result + 1;
end;

{ The add row's grey preview (01 S187 3a): "vJoy 3 · 126 buttons". }
function VJoyAddPreviewText(Id: Integer): String;
begin
  Result := 'vJoy ' + IntToStr(Id) + ' ' + #$00B7 + ' ' +
    CountText(DefaultButtons(Id), 'button', 'buttons');
end;

{ Shows VJoyChosen in the rows: one row per device, the rest hidden. }
procedure FillVJoyRows;
var
  R, K, N, Lines: Integer;
  Shown: Boolean;
begin
  VJoyFilling := True;
  try
    N := GetArrayLength(VJoyChosen);
    for R := 0 to VJoyMaxDevices - 1 do
    begin
      Shown := R < N;
      VJoyRowNames[R].Visible := Shown;
      VJoyRowButtons[R].Visible := Shown;
      VJoyRowHats[R].Visible := Shown;
      VJoyRowRemove[R].Visible := Shown;
      for K := 0 to 7 do
        VJoyRowAxes[R * 8 + K].Visible := Shown;
      if not Shown then
        Continue;
      VJoyRowNames[R].Caption := 'vJoy ' + IntToStr(VJoyChosen[R].Id);
      { D-01-VJOY-IN-USE (1a): a device another program holds has a red,
        bold name that says so on hover. }
      if VJoyIdBusy(VJoyChosen[R].Id) then
      begin
        VJoyRowNames[R].Font.Color := clRed;
        VJoyRowNames[R].Font.Style := [fsBold];
        VJoyRowNames[R].Hint := VJoyInUseText;
        VJoyRowNames[R].ShowHint := True;
      end
      else
      begin
        VJoyRowNames[R].Font.Color := clWindowText;
        VJoyRowNames[R].Font.Style := [];
        VJoyRowNames[R].Hint := '';
        VJoyRowNames[R].ShowHint := False;
      end;
      for K := 0 to 7 do
        VJoyRowAxes[R * 8 + K].Checked := AxisTicked(VJoyChosen[R].Axes, K);
      VJoyRowButtons[R].ItemIndex := VJoyChosen[R].Buttons;
      VJoyRowHats[R].ItemIndex := VJoyChosen[R].Hats;
      VJoyRowRemove[R].Enabled := N > 1;
    end;
    { 01 S187 (3a): the list's last row "+ Add device", under the last
      device, gone at 16; it is one more line in the scrolling list. }
    Lines := N;
    VJoyAddRow.Visible := N < VJoyMaxDevices;
    if VJoyAddRow.Visible then
    begin
      Lines := N + 1;
      VJoyAddRow.Top := N * VJoyRowHeight;
      VJoyAddPreview.Caption := VJoyAddPreviewText(VJoyNextFreeId(VJoyChosen));
    end;
    VJoyRowsPanel.Height := Lines * VJoyRowHeight;
    { One list item per line, each a row high: its scroll bar moves by rows. }
    VJoyScroll.Items.Clear;
    for R := 1 to Lines do
      VJoyScroll.Items.Add('');
    SendMessage(VJoyScroll.Handle, LbSetItemHeight, 0, VJoyRowHeight);
    VJoyScroll.Visible := Lines > VJoyVisibleRows;
    { Without the bar the rows use the box's full width. }
    if VJoyScroll.Visible then
      VJoyRowsPanel.Width := VJoyScroll.Left
    else
      VJoyRowsPanel.Width := VJoyRowsClip.ClientWidth;
    VJoyAddRow.Width := VJoyRowsPanel.Width;
    VJoyAddPreview.Left := VJoyAddRow.Width - VJoyAddPreview.Width - ScaleX(8);
    VJoyTopRow := -1;
    ShowVJoyTopRow;
  finally
    VJoyFilling := False;
  end;
end;

{ The vJoy part is live when vJoy is installed or ticked to install; the
  warning shows once an edit would change devices that exist (06 S185). }
function VJoyActive: Boolean;
var
  V: Integer;
begin
  V := DriverIndex('vjoy');
  Result := Drivers[V].State <> 'missing';
  if not Result then
    if Drivers[V].Row >= 0 then
      Result := DriverList.Checked[Drivers[V].Row];
end;

procedure UpdateVJoyControls;
var
  R, K: Integer;
  Active: Boolean;
begin
  Active := VJoyActive;
  VJoyPresetBox.Enabled := Active;
  for R := 0 to VJoyMaxDevices - 1 do
  begin
    VJoyRowNames[R].Enabled := Active;
    VJoyRowButtons[R].Enabled := Active;
    VJoyRowHats[R].Enabled := Active;
    VJoyRowRemove[R].Enabled := Active and (GetArrayLength(VJoyChosen) > 1);
    for K := 0 to 7 do
      VJoyRowAxes[R * 8 + K].Enabled := Active;
  end;
  VJoyAddRow.Enabled := Active;
  VJoyAddLabel.Enabled := Active;
  VJoyAddPreview.Enabled := Active;
  VJoyWarningText.Caption := '';
  if Active and VJoyEdited then
    if GetArrayLength(VJoyCurrent) > 0 then
      VJoyWarningText.Caption := VJoyWarning;
end;

{ A row edit: the preset box shows the preset the rows now match, else
  Custom. }
procedure VJoyRowsEdited;
begin
  VJoyUserEdited := True;
  VJoyPresetBox.ItemIndex := VJoyPresetBox.Items.IndexOf(MatchingPreset(VJoyChosen));
  UpdateVJoyControls;
end;

procedure VJoyPresetChange(Sender: TObject);
begin
  if VJoyPresetBox.Text <> VJoyCustom then
  begin
    PresetDevices(VJoyPresetBox.Text, VJoyChosen);
    VJoyUserEdited := True;
    FillVJoyRows;
  end;
  UpdateVJoyControls;
end;

{ Tag = row * 8 + axis. }
procedure VJoyAxisClick(Sender: TObject);
var
  R, K: Integer;
begin
  if VJoyFilling then
    Exit;
  R := TNewCheckBox(Sender).Tag div 8;
  K := TNewCheckBox(Sender).Tag mod 8;
  { D-01-VJOY-ONE-AXIS (drivers.can_untick_axis): the last ticked axis
    stays ticked (vJoyConfig without -a would give the device every axis). }
  if (not TNewCheckBox(Sender).Checked) and
    ((VJoyChosen[R].Axes and (VJoyAllAxes - (1 shl K))) = 0) then
  begin
    VJoyFilling := True;
    try
      TNewCheckBox(Sender).Checked := True;
    finally
      VJoyFilling := False;
    end;
    Exit;
  end;
  if TNewCheckBox(Sender).Checked then
    VJoyChosen[R].Axes := VJoyChosen[R].Axes or (1 shl K)
  else
    VJoyChosen[R].Axes := VJoyChosen[R].Axes and (VJoyAllAxes - (1 shl K));
  VJoyRowsEdited;
end;

{ Tag = row; item N is the number N. }
procedure VJoyButtonsChange(Sender: TObject);
begin
  if VJoyFilling then
    Exit;
  VJoyChosen[TNewComboBox(Sender).Tag].Buttons := TNewComboBox(Sender).ItemIndex;
  VJoyRowsEdited;
end;

procedure VJoyHatsChange(Sender: TObject);
begin
  if VJoyFilling then
    Exit;
  VJoyChosen[TNewComboBox(Sender).Tag].Hats := TNewComboBox(Sender).ItemIndex;
  VJoyRowsEdited;
end;

{ At least one device stays (the remove button is off on the last one). }
procedure VJoyRemoveClick(Sender: TObject);
var
  R, K, N: Integer;
begin
  R := TNewButton(Sender).Tag;
  N := GetArrayLength(VJoyChosen);
  if (N <= 1) or (R >= N) then
    Exit;
  for K := R to N - 2 do
  begin
    VJoyChosen[K].Id := VJoyChosen[K + 1].Id;
    VJoyChosen[K].Axes := VJoyChosen[K + 1].Axes;
    VJoyChosen[K].Buttons := VJoyChosen[K + 1].Buttons;
    VJoyChosen[K].Hats := VJoyChosen[K + 1].Hats;
  end;
  SetArrayLength(VJoyChosen, N - 1);
  FillVJoyRows;
  VJoyRowsEdited;
end;

{ A full device with the lowest free number, kept in number order (the
  "+ Add device" row, 01 S187 3a). }
procedure VJoyAddClick(Sender: TObject);
var
  Id, K, N: Integer;
begin
  N := GetArrayLength(VJoyChosen);
  if (N >= VJoyMaxDevices) or not VJoyActive then
    Exit;
  Id := VJoyNextFreeId(VJoyChosen);
  AddVJoyDevice(VJoyChosen, Id, VJoyAllAxes, DefaultButtons(Id), VJoyMaxHats);
  K := N;
  while (K > 0) and (VJoyChosen[K - 1].Id > Id) do
  begin
    VJoyChosen[K].Id := VJoyChosen[K - 1].Id;
    VJoyChosen[K].Axes := VJoyChosen[K - 1].Axes;
    VJoyChosen[K].Buttons := VJoyChosen[K - 1].Buttons;
    VJoyChosen[K].Hats := VJoyChosen[K - 1].Hats;
    K := K - 1;
  end;
  VJoyChosen[K].Id := Id;
  VJoyChosen[K].Axes := VJoyAllAxes;
  VJoyChosen[K].Buttons := DefaultButtons(Id);
  VJoyChosen[K].Hats := VJoyMaxHats;
  FillVJoyRows;
  VJoyRowsEdited;
end;

{ 01 S193: the runtime's parent row stays ticked whatever its child does
  (the child doesn't follow the parent's tick and keeps its own). }
procedure KeepRuntimeTicked;
var
  Child: Boolean;
begin
  if DriverList.State[RuntimeRow] = cbChecked then
    Exit;
  Child := DriverList.Checked[RuntimeNewestRow];
  DriverList.Checked[RuntimeRow] := True;
  if DriverList.Checked[RuntimeNewestRow] <> Child then
  begin
    DriverList.Checked[RuntimeNewestRow] := Child;
    DriverList.Checked[RuntimeRow] := True;
  end;
end;

procedure DriverListClickCheck(Sender: TObject);
begin
  KeepRuntimeTicked;
  UpdateVJoyControls;
end;

{ -- the Drivers page (01 S187) }

procedure FillDriverList;
var
  I: Integer;
  Status: String;
begin
  DriverList.Items.Clear;
  { 01 S193: the runtime first, required: ticked and greyed, its status on
    the right like the drivers'. A missing runtime is installed from the
    copy setup carries. }
  if RuntimeMissing then
    Status := 'not installed'
  else
  begin
    Status := RuntimeInstalledVersion;
    if Status = '' then
      Status := 'installed';
  end;
  RuntimeRow := DriverList.AddCheckBox(RuntimeName, Status, 0, True, False,
    False, False, nil);
  { Its child (answer 9b): unticked, on every install; it doesn't follow
    the parent's tick. }
  RuntimeNewestRow := DriverList.AddCheckBox(RuntimeNewestCaption, '', 1,
    False, True, False, False, nil);
  for I := 0 to GetArrayLength(Drivers) - 1 do
  begin
    if (Drivers[I].State = 'missing') or (Drivers[I].State = 'older') then
      { A missing driver is ticked, an older one is not. }
      Drivers[I].Row := DriverList.AddCheckBox(Drivers[I].Name, DriverLabel(I),
        0, Drivers[I].State = 'missing', True, False, False, nil)
    else
    begin
      { The same or a newer version: no box, never touched. }
      Drivers[I].Row := -1;
      DriverList.AddGroup(Drivers[I].Name, DriverLabel(I), 0, nil);
    end;
  end;
  KeepRuntimeTicked;
end;

{ The rows' controls, once for all 16 devices (FillVJoyRows shows them). }
procedure CreateVJoyRows(Left, NameW, BoxW, ButtonsW, HatsW, RemoveW, Gap: Integer);
var
  R, K, N, X: Integer;
  Box: TNewCheckBox;
  List: TNewComboBox;
  Button: TNewButton;
begin
  SetArrayLength(VJoyRowNames, VJoyMaxDevices);
  SetArrayLength(VJoyRowAxes, VJoyMaxDevices * 8);
  SetArrayLength(VJoyRowButtons, VJoyMaxDevices);
  SetArrayLength(VJoyRowHats, VJoyMaxDevices);
  SetArrayLength(VJoyRowRemove, VJoyMaxDevices);
  for R := 0 to VJoyMaxDevices - 1 do
  begin
    VJoyRowNames[R] := TNewStaticText.Create(DriversPage);
    VJoyRowNames[R].Parent := VJoyRowsPanel;
    VJoyRowNames[R].Left := Left;
    VJoyRowNames[R].Top := R * VJoyRowHeight + ScaleY(4);
    X := Left + NameW;
    for K := 0 to 7 do
    begin
      Box := TNewCheckBox.Create(DriversPage);
      Box.Parent := VJoyRowsPanel;
      Box.Left := X + K * BoxW;
      Box.Top := R * VJoyRowHeight + ScaleY(3);
      Box.Width := BoxW;
      Box.Height := ScaleY(17);
      Box.Caption := '';
      Box.Hint := AxisHeading(K);
      Box.ShowHint := True;
      Box.Tag := R * 8 + K;
      Box.OnClick := @VJoyAxisClick;
      VJoyRowAxes[R * 8 + K] := Box;
    end;
    X := X + 8 * BoxW + Gap;
    List := TNewComboBox.Create(DriversPage);
    List.Parent := VJoyRowsPanel;
    List.Style := csDropDownList;
    List.Left := X;
    List.Top := R * VJoyRowHeight + ScaleY(1);
    List.Width := ButtonsW;
    for N := 0 to VJoyMaxButtons do
      List.Items.Add(IntToStr(N));
    List.Tag := R;
    List.OnChange := @VJoyButtonsChange;
    VJoyRowButtons[R] := List;
    X := X + ButtonsW + Gap;
    List := TNewComboBox.Create(DriversPage);
    List.Parent := VJoyRowsPanel;
    List.Style := csDropDownList;
    List.Left := X;
    List.Top := R * VJoyRowHeight + ScaleY(1);
    List.Width := HatsW;
    for N := 0 to VJoyMaxHats do
      List.Items.Add(IntToStr(N));
    List.Tag := R;
    List.OnChange := @VJoyHatsChange;
    VJoyRowHats[R] := List;
    X := X + HatsW + Gap;
    Button := TNewButton.Create(DriversPage);
    Button.Parent := VJoyRowsPanel;
    Button.Left := X;
    Button.Top := R * VJoyRowHeight + ScaleY(1);
    Button.Width := RemoveW;
    Button.Height := ScaleY(21);
    Button.Caption := #$00D7;
    Button.Hint := 'Remove this device';
    Button.ShowHint := True;
    Button.Tag := R;
    Button.OnClick := @VJoyRemoveClick;
    VJoyRowRemove[R] := Button;
  end;
end;

{ A column heading over the rows, in the box's grey band (layout b). }
procedure AddVJoyHeading(const Caption: String; Left, Top: Integer);
var
  Heading: TNewStaticText;
begin
  Heading := TNewStaticText.Create(DriversPage);
  Heading.Parent := VJoyHeadBand;
  Heading.Left := Left;
  Heading.Top := Top;
  Heading.Caption := Caption;
end;

procedure CreateDriverPages;
var
  VJoyLabel, PresetLabel: TNewStaticText;
  Line: TBevel;
  NameW, BoxW, ButtonsW, HatsW, RemoveW, BarW, ScrollW, EdgeW, Gap, RowLeft,
    BandH, ShowingW, LineTop, Bottom, K, X: Integer;
begin
  DriversPage := CreateCustomPage(wpSelectDir, 'Drivers',
    'vJoy, ViGEmBus and HidHide on this PC.');
  { 01 S187, S193: the runtime's parent and child rows, then the drivers. }
  DriverList := TNewCheckListBox.Create(DriversPage);
  DriverList.Parent := DriversPage.Surface;
  DriverList.Left := 0;
  DriverList.Top := 0;
  DriverList.Width := DriversPage.SurfaceWidth;
  DriverList.Height := ScaleY(102);
  DriverList.Flat := True;
  DriverList.OnClickCheck := @DriverListClickCheck;
  FillDriverList;
  { 06 S185: the vJoy device choice (layout b): a thin line, then the bold
    heading with Preset and its box on the right of the same line. }
  Line := TBevel.Create(DriversPage);
  Line.Parent := DriversPage.Surface;
  Line.Shape := bsTopLine;
  Line.Left := 0;
  Line.Top := DriverList.Top + DriverList.Height + ScaleY(6);
  Line.Width := DriversPage.SurfaceWidth;
  Line.Height := ScaleY(2);
  VJoyPresetBox := TNewComboBox.Create(DriversPage);
  VJoyPresetBox.Parent := DriversPage.Surface;
  VJoyPresetBox.Style := csDropDownList;
  VJoyPresetBox.Width := ScaleX(160);
  VJoyPresetBox.Left := DriversPage.SurfaceWidth - VJoyPresetBox.Width;
  VJoyPresetBox.Top := Line.Top + ScaleY(6);
  VJoyPresetBox.Items.Add(VJoyPresetOne);
  VJoyPresetBox.Items.Add(VJoyPresetTwo);
  VJoyPresetBox.Items.Add(VJoyCustom);
  VJoyPresetBox.ItemIndex := VJoyPresetBox.Items.IndexOf(MatchingPreset(VJoyChosen));
  VJoyPresetBox.OnChange := @VJoyPresetChange;
  VJoyLabel := TNewStaticText.Create(DriversPage);
  VJoyLabel.Parent := DriversPage.Surface;
  VJoyLabel.Left := 0;
  VJoyLabel.Top := VJoyPresetBox.Top + ScaleY(3);
  VJoyLabel.Font.Style := [fsBold];
  VJoyLabel.Caption := 'vJoy devices';
  PresetLabel := TNewStaticText.Create(DriversPage);
  PresetLabel.Parent := DriversPage.Surface;
  PresetLabel.Top := VJoyLabel.Top;
  PresetLabel.Caption := 'Preset';
  PresetLabel.Left := VJoyPresetBox.Left - ScaleX(6) - PresetLabel.Width;
  PresetLabel.FocusControl := VJoyPresetBox;
  VJoyCurrentText := TNewStaticText.Create(DriversPage);
  VJoyCurrentText.Parent := DriversPage.Surface;
  VJoyCurrentText.Left := 0;
  VJoyCurrentText.Top := VJoyPresetBox.Top + VJoyPresetBox.Height + ScaleY(3);
  VJoyCurrentText.Width := DriversPage.SurfaceWidth;
  VJoyCurrentText.AutoSize := False;
  VJoyCurrentText.WordWrap := True;
  VJoyCurrentText.Caption := VJoyCurrentLine;
  VJoyCurrentText.AdjustHeight;
  if VJoyCurrentText.Caption = '' then
    VJoyCurrentText.Height := 0;
  { Bottom line (01 S187 3a: adding is the list's last row now): the
    "Showing" line on the right, the warning on its left (two lines when it
    needs them). LineTop: the line's top, one control high. }
  LineTop := DriversPage.SurfaceHeight - ScaleY(21);
  ShowingW := ScaleX(150);
  VJoyShowingText := TNewStaticText.Create(DriversPage);
  VJoyShowingText.Parent := DriversPage.Surface;
  VJoyShowingText.AutoSize := False;
  VJoyShowingText.Alignment := taRightJustify;
  VJoyShowingText.Width := ShowingW;
  VJoyShowingText.Left := DriversPage.SurfaceWidth - ShowingW;
  VJoyShowingText.Height := ScaleY(15);
  VJoyShowingText.Top := LineTop + ScaleY(4);
  VJoyWarningText := TNewStaticText.Create(DriversPage);
  VJoyWarningText.Parent := DriversPage.Surface;
  VJoyWarningText.Left := 0;
  VJoyWarningText.Width := VJoyShowingText.Left - ScaleX(8) - VJoyWarningText.Left;
  VJoyWarningText.AutoSize := False;
  VJoyWarningText.WordWrap := True;
  VJoyWarningText.Height := ScaleY(26);
  VJoyWarningText.Top := LineTop - ScaleY(5);
  VJoyWarningText.Font.Style := [fsBold];
  { D-01-VJOY-COUNTDOWN: the hint, room for two lines, right under the
    box and above the bottom line. }
  VJoyHint := TNewStaticText.Create(DriversPage);
  VJoyHint.Parent := DriversPage.Surface;
  VJoyHint.Left := 0;
  VJoyHint.AutoSize := False;
  VJoyHint.WordWrap := True;
  VJoyHint.Width := DriversPage.SurfaceWidth;
  VJoyHint.Height := ScaleY(30);
  VJoyHint.Top := VJoyWarningText.Top - ScaleY(1) - VJoyHint.Height;
  VJoyHint.Caption := VJoyHintText;
  { The rows' columns: vJoy N, X ... S2, Buttons, Hats, remove; the tick
    boxes share what is left of the width. RowLeft: the rows' padding from
    the box's left border. }
  Gap := ScaleX(4);
  RowLeft := ScaleX(6);
  NameW := ScaleX(46);
  ButtonsW := ScaleX(50);
  HatsW := ScaleX(38);
  RemoveW := ScaleX(22);
  { The list box has no border and is a little wider than its scroll bar
    (SM_CXVSCROLL), so Windows always has room to draw the bar; the white
    strip left of the bar matches the white box. EdgeW: the box's sunken
    border, both sides. }
  BarW := GetSystemMetrics(2);
  if BarW < ScaleX(17) then
    BarW := ScaleX(17);
  ScrollW := BarW + ScaleX(4);
  EdgeW := ScaleX(4);
  BoxW := (DriversPage.SurfaceWidth - EdgeW - ScrollW - RowLeft - NameW - ButtonsW -
    HatsW - RemoveW - 4 * Gap) div 8;
  if BoxW > ScaleX(40) then
    BoxW := ScaleX(40);
  VJoyRowHeight := ScaleY(24);
  BandH := ScaleY(18);
  { The scrolling list: one white box with a border (as Git for Windows'
    Select Components page): the column headings in a light grey band at
    its top, then as many whole rows as fit above the hint, the scroll bar
    down the inside of its right edge. }
  VJoyViewport := TPanel.Create(DriversPage);
  VJoyViewport.Parent := DriversPage.Surface;
  VJoyViewport.BevelOuter := bvNone;
  VJoyViewport.BorderStyle := bsSingle;
  VJoyViewport.ParentBackground := False;
  VJoyViewport.Color := clWindow;
  VJoyViewport.Left := 0;
  VJoyViewport.Top := VJoyCurrentText.Top + VJoyCurrentText.Height + ScaleY(3);
  VJoyViewport.Width := DriversPage.SurfaceWidth;
  Bottom := VJoyHint.Top - ScaleY(2);
  VJoyViewport.Height := Bottom - VJoyViewport.Top;
  { The real border, from the box's own window. }
  if VJoyViewport.Handle <> 0 then
    EdgeW := VJoyViewport.Height - VJoyViewport.ClientHeight;
  VJoyVisibleRows := (VJoyViewport.ClientHeight - BandH) div VJoyRowHeight;
  if VJoyVisibleRows < 1 then
    VJoyVisibleRows := 1;
  VJoyViewport.Height := BandH + VJoyVisibleRows * VJoyRowHeight + EdgeW;
  VJoyHeadBand := TPanel.Create(DriversPage);
  VJoyHeadBand.Parent := VJoyViewport;
  VJoyHeadBand.BevelOuter := bvNone;
  VJoyHeadBand.ParentBackground := False;
  VJoyHeadBand.Color := clBtnFace;
  VJoyHeadBand.Left := 0;
  VJoyHeadBand.Top := 0;
  VJoyHeadBand.Width := VJoyViewport.ClientWidth;
  VJoyHeadBand.Height := BandH;
  { The headings line up with the rows' columns. }
  X := RowLeft + NameW;
  for K := 0 to 7 do
    AddVJoyHeading(AxisHeading(K), X + K * BoxW, ScaleY(2));
  X := X + 8 * BoxW + Gap;
  AddVJoyHeading('Buttons', X, ScaleY(2));
  AddVJoyHeading('Hats', X + ButtonsW + Gap, ScaleY(2));
  { The rows' window under the band: the rows panel moves inside it. }
  VJoyRowsClip := TPanel.Create(DriversPage);
  VJoyRowsClip.Parent := VJoyViewport;
  VJoyRowsClip.BevelOuter := bvNone;
  VJoyRowsClip.ParentBackground := False;
  VJoyRowsClip.Color := clWindow;
  VJoyRowsClip.Left := 0;
  VJoyRowsClip.Top := BandH;
  VJoyRowsClip.Width := VJoyViewport.ClientWidth;
  VJoyRowsClip.Height := VJoyVisibleRows * VJoyRowHeight;
  VJoyRowsPanel := TPanel.Create(DriversPage);
  VJoyRowsPanel.Parent := VJoyRowsClip;
  VJoyRowsPanel.BevelOuter := bvNone;
  VJoyRowsPanel.ParentBackground := False;
  VJoyRowsPanel.Color := clWindow;
  VJoyRowsPanel.Left := 0;
  VJoyRowsPanel.Top := 0;
  VJoyRowsPanel.Width := VJoyRowsClip.ClientWidth;
  VJoyRowsPanel.Height := VJoyMaxDevices * VJoyRowHeight;
  VJoyScroll := TNewListBox.Create(DriversPage);
  VJoyScroll.Parent := VJoyRowsClip;
  VJoyScroll.BorderStyle := bsNone;
  VJoyScroll.Color := clWindow;
  VJoyScroll.Left := VJoyRowsClip.ClientWidth - ScrollW;
  VJoyScroll.Top := 0;
  VJoyScroll.Width := ScrollW;
  VJoyScroll.Height := VJoyVisibleRows * VJoyRowHeight;
  VJoyScroll.TabStop := False;
  VJoyScroll.OnClick := @VJoyScrollClick;
  CreateVJoyRows(RowLeft, NameW, BoxW, ButtonsW, HatsW, RemoveW, Gap);
  { 01 S187 (3a): "+ Add device", a full-width row in the rows panel (it
    scrolls with them); FillVJoyRows puts it under the last device. }
  VJoyAddRow := TPanel.Create(DriversPage);
  VJoyAddRow.Parent := VJoyRowsPanel;
  VJoyAddRow.BevelOuter := bvNone;
  VJoyAddRow.ParentBackground := False;
  VJoyAddRow.Color := clWindow;
  VJoyAddRow.Left := 0;
  VJoyAddRow.Top := 0;
  VJoyAddRow.Width := VJoyRowsPanel.Width;
  VJoyAddRow.Height := VJoyRowHeight;
  VJoyAddRow.Cursor := crHandPoint;
  VJoyAddRow.OnClick := @VJoyAddClick;
  VJoyAddLabel := TNewStaticText.Create(DriversPage);
  VJoyAddLabel.Parent := VJoyAddRow;
  VJoyAddLabel.Left := RowLeft;
  VJoyAddLabel.Top := ScaleY(4);
  VJoyAddLabel.Caption := VJoyAddText;
  VJoyAddLabel.Cursor := crHandPoint;
  VJoyAddLabel.OnClick := @VJoyAddClick;
  VJoyAddPreview := TNewStaticText.Create(DriversPage);
  VJoyAddPreview.Parent := VJoyAddRow;
  VJoyAddPreview.Top := ScaleY(4);
  VJoyAddPreview.Font.Color := clGrayText;
  VJoyAddPreview.Cursor := crHandPoint;
  VJoyAddPreview.OnClick := @VJoyAddClick;
  Log('Drivers page: surface ' + IntToStr(DriversPage.SurfaceWidth) + 'x' +
    IntToStr(DriversPage.SurfaceHeight) + ', vJoy rows shown ' +
    IntToStr(VJoyVisibleRows) + ', box border ' + IntToStr(EdgeW) +
    ', scroll bar ' + IntToStr(BarW) + ' in ' + IntToStr(ScrollW) +
    ', tick box column ' + IntToStr(BoxW));
  FillVJoyRows;
  UpdateVJoyControls;
  DriverDownloadPage := CreateDownloadPage('Drivers',
    'Downloading the newer driver versions.', nil);
  DriverDownloadPage.ShowBaseNameInsteadOfUrl := True;
  DriverProgressPage := CreateOutputProgressPage('Drivers',
    'Installing the drivers you ticked.');
  RuntimeProgressPage := CreateOutputProgressPage(RuntimeName,
    'Gremlin-Platforms needs it to run.');
end;

{ 06 S186: the HidHide update's first half. True = Continue. }
function AskHidHideStep1(I: Integer): Boolean;
begin
  Result := TaskDialogMsgBox('HidHide update, step 1 of 2',
    'Setup will remove HidHide ' + Drivers[I].Installed + '. After a restart, ' +
    'Gremlin installs HidHide ' + TargetVersion(I) + ' and asks for one more ' +
    'restart. Devices aren''t hidden until then.',
    mbConfirmation, MB_YESNO, ['Continue', 'Skip HidHide update'], 0) = IDYES;
end;

{ Leaving the Drivers page: keeps the ticks, asks GitHub about newer
  versions and, for a HidHide update, asks step 1 (06 S186). }
procedure DriversPageDone;
var
  I: Integer;
begin
  RuntimeNewestWanted := DriverList.Checked[RuntimeNewestRow];
  for I := 0 to GetArrayLength(Drivers) - 1 do
  begin
    Drivers[I].Chosen := False;
    if Drivers[I].Row >= 0 then
      Drivers[I].Chosen := DriverList.Checked[Drivers[I].Row];
    Drivers[I].Op := '';
    if not Drivers[I].Chosen then
      Continue;
    CheckLatest(I);
    if Drivers[I].State = 'missing' then
      Drivers[I].Op := 'install'
    else if Drivers[I].Key = 'hidhide' then
      Drivers[I].Op := 'remove'
    else
      Drivers[I].Op := 'update';
    { Nested, so the step 1 prompt shows only for a HidHide remove, whether
      or not Pascal Script stops at the first false part of an "and". }
    if Drivers[I].Op = 'remove' then
      if not AskHidHideStep1(I) then
      begin
        Log('HidHide update skipped.');
        Drivers[I].Chosen := False;
        Drivers[I].Op := '';
        DriverList.Checked[Drivers[I].Row] := False;
      end;
  end;
  { 06 S185: a newly installed vJoy gets the chosen layout; an installed one
    changes only when edited. }
  I := DriverIndex('vjoy');
  VJoySetupPlanned := False;
  if Drivers[I].Op = 'install' then
    VJoySetupPlanned := True
  else if Drivers[I].State <> 'missing' then
    VJoySetupPlanned := VJoyEdited;
  if VJoySetupPlanned then
    Log('vJoy devices to set up: ' + VJoyLayoutText(VJoyChosen));
end;

{ -- the job (12 S25) }

function BundledPath(I: Integer): String;
begin
  Result := ExpandConstant('{app}\drivers\') + Drivers[I].BundledFile;
end;

(* The job file's devices: {"id", "axes", "buttons", "hats"}, comma-joined. *)
function VJoyDevicesJson(const List: TVJoyDevices): String;
var
  K: Integer;
begin
  Result := '';
  for K := 0 to GetArrayLength(List) - 1 do
  begin
    if K > 0 then
      Result := Result + ', ';
    Result := Result + '{"id": ' + IntToStr(List[K].Id) +
      ', "axes": ' + AxesJson(List[K].Axes) +
      ', "buttons": ' + IntToStr(List[K].Buttons) +
      ', "hats": ' + IntToStr(List[K].Hats) + '}';
  end;
end;

(* One job: {"op", "driver", "files": [download first, bundled second],
   "devices": []}. A remove lists no file. *)
function JobJson(I: Integer): String;
var
  Files, Devices: String;
begin
  Files := '';
  if Drivers[I].Op <> 'remove' then
  begin
    if Drivers[I].Download <> '' then
      Files := '{"path": "' + JsonEscape(Drivers[I].Download) +
        '", "kind": "download"}, ';
    Files := Files + '{"path": "' + JsonEscape(BundledPath(I)) +
      '", "kind": "bundled"}';
  end;
  { D-01-VJOY-UPDATE-KEEPS: a vJoy update carries the devices read before
    it (none = they couldn't be read: no check afterwards). }
  Devices := '';
  if (Drivers[I].Key = 'vjoy') and (Drivers[I].Op = 'update') then
    Devices := VJoyDevicesJson(VJoyCurrent);
  Result := '{"op": "' + Drivers[I].Op + '", "driver": "' + Drivers[I].Key +
    '", "files": [' + Files + '], "devices": [' + Devices + ']}';
end;

(* The vJoy device job (06 S185, 12 S25b): {"op": "vjoy_setup", "driver":
   "vjoy", "files": [], "devices": [{"id", "axes", "buttons", "hats"}]}. *)
function VJoySetupJobJson: String;
begin
  Result := '{"op": "vjoy_setup", "driver": "vjoy", "files": [], "devices": [' +
    VJoyDevicesJson(VJoyChosen) + ']}';
end;

(* Repair Now (D-01-VJOY-UPDATE-KEEPS): {"op": "vjoy_restore", "driver":
   "vjoy", "files": [], "devices": [the lost ones]}; the helper sets up
   exactly those and deletes no other device. *)
function VJoyRestoreJobJson: String;
begin
  Result := '{"op": "vjoy_restore", "driver": "vjoy", "files": [], "devices": [' +
    VJoyDevicesJson(VJoyUpdateLost) + ']}';
end;

{ Writes the job file (UTF-8, no BOM: Python's json reads it) and lists the
  jobs' drivers in JobDrivers (VJoySetupJob for the vJoy device job, which
  comes right after vJoy's own). False when there is no job or no file. }
function WriteJobFile(const Path: String): Boolean;
var
  I, N, Pass, Index: Integer;
  Jobs, Json: String;
  Lines: TArrayOfString;
begin
  Result := False;
  N := 0;
  Jobs := '';
  SetArrayLength(JobDrivers, 0);
  for I := 0 to GetArrayLength(Drivers) - 1 do
    for Pass := 0 to 1 do
    begin
      Json := '';
      Index := I;
      if Pass = 0 then
      begin
        if Drivers[I].Chosen and (Drivers[I].Op <> '') then
          Json := JobJson(I);
      end
      else if (Drivers[I].Key = 'vjoy') and VJoySetupPlanned then
      begin
        Json := VJoySetupJobJson;
        Index := VJoySetupJob;
      end;
      if Json = '' then
        Continue;
      if N > 0 then
        Jobs := Jobs + ', ';
      Jobs := Jobs + Json;
      SetArrayLength(JobDrivers, N + 1);
      JobDrivers[N] := Index;
      N := N + 1;
    end;
  if N = 0 then
    Exit;
  SetArrayLength(Lines, 1);
  Lines[0] := '{"version": 1, "jobs": [' + Jobs + ']}';
  Result := SaveStringsToUTF8FileWithoutBOM(Path, Lines, False);
  if not Result then
    Log('Could not write the driver job file ' + Path);
end;

{ A job's result, whether it belongs to a driver or is the vJoy device job. }
function JobState(J: Integer): String;
begin
  if JobDrivers[J] = VJoySetupJob then
    Result := VJoySetupState
  else if JobDrivers[J] = VJoyRestoreJob then
    Result := VJoyRestoreState
  else
    Result := Drivers[JobDrivers[J]].ResultState;
end;

function JobRestart(J: Integer): Boolean;
begin
  if JobDrivers[J] = VJoySetupJob then
    Result := VJoySetupRestart
  else if JobDrivers[J] = VJoyRestoreJob then
    Result := VJoyRestoreRestart
  else
    Result := Drivers[JobDrivers[J]].ResultRestart;
end;

procedure SetJobResult(J: Integer; const State, Message: String; Restart: Boolean);
var
  I: Integer;
begin
  I := JobDrivers[J];
  if I = VJoySetupJob then
  begin
    VJoySetupState := State;
    VJoySetupMessage := Message;
    VJoySetupRestart := Restart;
  end
  else if I = VJoyRestoreJob then
  begin
    VJoyRestoreState := State;
    VJoyRestoreMessage := Message;
    VJoyRestoreRestart := Restart;
  end
  else
  begin
    Drivers[I].ResultState := State;
    Drivers[I].ResultMessage := Message;
    Drivers[I].ResultRestart := Restart;
  end;
end;

(* The numbers of the array "Key" in S: "added": [1, 3]. *)
procedure JsonIntArray(const S, Key: String; var Ids: TArrayOfInteger);
var
  P, Q, N: Integer;
  Items, Item: String;
begin
  SetArrayLength(Ids, 0);
  P := FindFrom('"' + Key + '"', S, 1);
  if P = 0 then
    Exit;
  P := FindFrom('[', S, P);
  Q := FindFrom(']', S, P);
  if (P = 0) or (Q = 0) then
    Exit;
  Items := Copy(S, P + 1, Q - P - 1) + ',';
  N := 0;
  while Pos(',', Items) > 0 do
  begin
    Item := Trim(Copy(Items, 1, Pos(',', Items) - 1));
    Delete(Items, 1, Pos(',', Items));
    if StrToIntDef(Item, -1) < 0 then
      Continue;
    SetArrayLength(Ids, N + 1);
    Ids[N] := StrToInt(Item);
    N := N + 1;
  end;
end;

(* A device's "axes": ["x", "sl0"] in S[From..UpTo] as the bit mask. *)
function AxesFromJson(const S: String; From, UpTo: Integer): Integer;
var
  P, Q, K: Integer;
  Names: String;
begin
  Result := 0;
  P := FindFrom('"axes"', S, From);
  if (P = 0) or (P > UpTo) then
    Exit;
  P := FindFrom('[', S, P);
  Q := FindFrom(']', S, P);
  if (P = 0) or (Q = 0) or (Q > UpTo) then
    Exit;
  Names := Copy(S, P, Q - P + 1);
  for K := 0 to 7 do
    if Pos('"' + AxisName(K) + '"', Names) > 0 then
      Result := Result or (1 shl K);
end;

(* D-01-VJOY-UPDATE-KEEPS: the last vJoy job's (update or vjoy_setup) result object Job:
   "lost": [{"id", "axes", "buttons", "hats"}] and "added": [ids]. *)
procedure ReadVJoyUpdateCheck(const Job: String);
var
  Starts, Ends: TArrayOfInteger;
  N, K: Integer;
begin
  SetArrayLength(VJoyUpdateLost, 0);
  N := JsonArrayObjects(Job, 'lost', Starts, Ends);
  for K := 0 to N - 1 do
    AddVJoyDevice(VJoyUpdateLost,
      StrToIntDef(JsonValue(Job, 'id', Starts[K], Ends[K]), 0),
      AxesFromJson(Job, Starts[K], Ends[K]),
      StrToIntDef(JsonValue(Job, 'buttons', Starts[K], Ends[K]), 0),
      StrToIntDef(JsonValue(Job, 'hats', Starts[K], Ends[K]), 0));
  JsonIntArray(Job, 'added', VJoyUpdateAdded);
end;

{ The job J is a vJoy job whose result can carry lost/added: the vJoy
  driver's update, or the vjoy_setup job. The helper reports them on the last
  vJoy job of the run, so the last such result read wins. }
function IsVJoyJob(J: Integer): Boolean;
begin
  Result := JobDrivers[J] = VJoySetupJob;
  if Result or (JobDrivers[J] < 0) then
    Exit;
  Result := (Drivers[JobDrivers[J]].Key = 'vjoy') and
    (Drivers[JobDrivers[J]].Op = 'update');
end;

{ Reads the helper's results file into the jobs; False while it is
  missing or half-written. AllDone is its "finished". }
function ReadDriverResults(const Path: String; var AllDone: Boolean): Boolean;
var
  Lines: TArrayOfString;
  Text: String;
  Starts, Ends: TArrayOfInteger;
  N, J: Integer;
begin
  Result := False;
  AllDone := False;
  if not FileExists(Path) or not LoadStringsFromFile(Path, Lines) then
    Exit;
  Text := JoinLines(Lines);
  N := JsonArrayObjects(Text, 'jobs', Starts, Ends);
  if N <> GetArrayLength(JobDrivers) then
    Exit;
  for J := 0 to N - 1 do
    SetJobResult(J, JsonValue(Text, 'state', Starts[J], Ends[J]),
      JsonValue(Text, 'message', Starts[J], Ends[J]),
      JsonValue(Text, 'restart', Starts[J], Ends[J]) = 'true');
  SetArrayLength(VJoyUpdateLost, 0);
  SetArrayLength(VJoyUpdateAdded, 0);
  for J := 0 to N - 1 do
    if IsVJoyJob(J) then
      ReadVJoyUpdateCheck(Copy(Text, Starts[J], Ends[J] - Starts[J] + 1));
  AllDone := JsonValue(Text, 'finished', 1, Length(Text)) = 'true';
  Result := True;
end;

{ What the progress page says while a job runs. }
function JobProgressText(I: Integer): String;
begin
  if I = VJoySetupJob then
    Result := 'Setting up the vJoy devices' + #$2026
  else if I = VJoyRestoreJob then
    Result := 'Putting back the vJoy devices' + #$2026
  else if Drivers[I].Op = 'remove' then
    Result := 'Removing HidHide ' + Drivers[I].Installed + #$2026
  else
    Result := 'Installing ' + Drivers[I].Name + ' ' + TargetVersion(I) + #$2026;
end;

procedure FailOpenJobs(const Why: String);
var
  J: Integer;
begin
  for J := 0 to GetArrayLength(JobDrivers) - 1 do
    if (JobState(J) <> 'done') and (JobState(J) <> 'failed') then
      SetJobResult(J, 'failed', Why, JobRestart(J));
end;

{ Shows the progress from the results file until "finished" (01 S190). }
procedure WaitForHelper(const ResultsFile: String);
var
  Tick, Limit, J, DoneCount: Integer;
  Seen, AllDone: Boolean;
  Text: String;
begin
  Seen := False;
  AllDone := False;
  Limit := HelperStartTicks + HelperJobTicks * GetArrayLength(JobDrivers);
  for Tick := 1 to Limit do
  begin
    if ReadDriverResults(ResultsFile, AllDone) then
      Seen := True;
    DoneCount := 0;
    Text := 'Waiting for Gremlin Device Helper' + #$2026;
    for J := 0 to GetArrayLength(JobDrivers) - 1 do
    begin
      if (JobState(J) = 'done') or (JobState(J) = 'failed') then
        DoneCount := DoneCount + 1
      else if JobState(J) = 'running' then
        Text := JobProgressText(JobDrivers[J]);
    end;
    DriverProgressPage.SetText(Text, '');
    DriverProgressPage.SetProgress(DoneCount, GetArrayLength(JobDrivers));
    if AllDone then
      Exit;
    if not Seen and (Tick >= HelperStartTicks) then
    begin
      FailOpenJobs('Gremlin Device Helper did not start.');
      Exit;
    end;
    Sleep(HelperWaitStep);
  end;
  FailOpenJobs('Gremlin Device Helper did not finish in time.');
end;

(* 06 S186: after the old HidHide is removed, Gremlin installs the new one
   at its next start from {app}\drivers\pending.json. A download is kept
   next to the bundled copy (setup's temp folder goes when setup ends). *)
procedure WriteHidHidePending(I: Integer);
var
  Path, Kind, Version: String;
  Lines: TArrayOfString;
begin
  Path := BundledPath(I);
  Kind := 'bundled';
  Version := Drivers[I].Bundled;
  if Drivers[I].Download <> '' then
  begin
    if CopyFile(Drivers[I].Download, ExpandConstant('{app}\drivers\') +
      Drivers[I].LatestName, False) then
    begin
      Path := ExpandConstant('{app}\drivers\') + Drivers[I].LatestName;
      Kind := 'download';
      Version := Drivers[I].LatestVersion;
    end
    else
      Log('Could not keep the HidHide download; step 2 uses the bundled copy.');
  end;
  SetArrayLength(Lines, 1);
  Lines[0] := '{"hidhide": {"version": "' + JsonEscape(Version) +
    '", "file": "' + JsonEscape(Path) + '", "kind": "' + Kind + '"}}';
  ForceDirectories(ExpandConstant('{app}\drivers'));
  if not SaveStringsToUTF8FileWithoutBOM(
    ExpandConstant('{app}\drivers\pending.json'), Lines, False) then
    Log('Could not write drivers\pending.json.');
end;

{ One line per driver for setup's last page (01 S191). }
function DriverResultLine(I: Integer): String;
begin
  Result := Drivers[I].Name + ': ';
  if Drivers[I].ResultMessage <> '' then
    Result := Result + Drivers[I].ResultMessage
  else if Drivers[I].ResultState = 'done' then
  begin
    if Drivers[I].Op = 'remove' then
      Result := Result + 'HidHide ' + Drivers[I].Installed + ' removed'
    else
      Result := Result + 'installed'
  end
  else
    Result := Result + 'not installed';
  { D-01-VJOY-UPDATE-KEEPS: devices that came only with the update. }
  if (Drivers[I].Key = 'vjoy') and (Drivers[I].Op = 'update') and
    (GetArrayLength(VJoyUpdateAdded) > 0) then
    Result := Result + '; ' + VJoyAddedText(VJoyUpdateAdded);
end;

{ The vJoy device job's line for setup's last page. }
function VJoySetupResultLine: String;
begin
  Result := 'vJoy devices: ';
  if VJoySetupMessage <> '' then
    Result := Result + VJoySetupMessage
  else if VJoySetupState = 'done' then
    Result := Result + 'set up'
  else
    Result := Result + 'not set up';
end;

procedure BuildDriverSummary;
var
  J, I: Integer;
begin
  DriverSummary := '';
  for J := 0 to GetArrayLength(JobDrivers) - 1 do
  begin
    I := JobDrivers[J];
    if DriverSummary <> '' then
      DriverSummary := DriverSummary + #13#10;
    if I = VJoySetupJob then
    begin
      if VJoySetupRestart then
        DriversNeedRestart := True;
      DriverSummary := DriverSummary + VJoySetupResultLine;
      Continue;
    end;
    if Drivers[I].ResultRestart then
      DriversNeedRestart := True;
    if (Drivers[I].Op = 'remove') and (Drivers[I].ResultState = 'done') then
    begin
      HidHideRemoved := True;
      DriversNeedRestart := True;
    end;
    DriverSummary := DriverSummary + DriverResultLine(I);
  end;
end;

{ Answer 4a: starts Exe elevated ("runas") from setup's own window, brought
  to the front first, so Windows' administrator prompt opens in front of
  setup rather than behind it. Process is the started program (the caller
  closes it); on False, ErrorCode is Windows' error (UacRefusedCode when the
  prompt was refused). A silent install has no window to own the prompt. }
function StartElevated(const Exe, Params, Dir: String; ShowCmd: Integer;
  var Process: Longint; var ErrorCode: Integer): Boolean;
var
  Info: TShellExecuteInfo;
begin
  Process := 0;
  ErrorCode := 0;
  Info.cbSize := SizeOf(Info);
  Info.fMask := SeeMaskNoCloseProcess or SeeMaskNoAsync or SeeMaskFlagNoUi;
  Info.Wnd := 0;
  if not WizardSilent then
  begin
    WizardForm.BringToFront;
    SetForegroundWindow(WizardForm.Handle);
    Info.Wnd := WizardForm.Handle;
  end;
  Info.lpVerb := 'runas';
  Info.lpFile := Exe;
  Info.lpParameters := Params;
  Info.lpDirectory := Dir;
  Info.nShow := ShowCmd;
  Result := ShellExecuteEx(Info);
  if Result then
    Process := Info.hProcess
  else
    ErrorCode := DLLGetLastError;
end;

{ 01 S190: one elevated start of Gremlin Device Helper for the jobs in
  JobFile (JobDrivers lists them), with the progress page until its results
  file says "finished". }
procedure RunHelperJobs(const JobFile, ResultsFile: String);
var
  Params: String;
  ErrorCode, J: Integer;
  Process: Longint;
begin
  for J := 0 to GetArrayLength(JobDrivers) - 1 do
    SetJobResult(J, 'waiting', '', False);
  Params := '--jobs ' + AddQuotes(JobFile) + ' --results ' +
    AddQuotes(ResultsFile);
  DriverProgressPage.SetText(
    'Windows asks for administrator permission' + #$2026, '');
  { The driver jobs show real per-job progress: the normal bar. }
  DriverProgressPage.ProgressBar.Style := npbstNormal;
  DriverProgressPage.SetProgress(0, GetArrayLength(JobDrivers));
  DriverProgressPage.Show;
  try
    Log('Starting Gremlin Device Helper ' + Params);
    if StartElevated(ExpandConstant('{app}\{#HelperExeName}'), Params,
      ExpandConstant('{app}'), SW_HIDE, Process, ErrorCode) then
    begin
      if Process <> 0 then
        CloseHandle(Process);
      WaitForHelper(ResultsFile);
    end
    else if ErrorCode = UacRefusedCode then
      FailOpenJobs('Administrator permission was not given.')
    else
      FailOpenJobs('Gremlin Device Helper could not start: ' +
        SysErrorMessage(ErrorCode));
  finally
    DriverProgressPage.Hide;
  end;
end;

{ Repair Now's result, for its box and setup's last page. }
function VJoyRestoreResultLine: String;
begin
  Result := 'vJoy repair: ';
  if VJoyRestoreMessage <> '' then
    Result := Result + VJoyRestoreMessage
  else if VJoyRestoreState = 'done' then
    Result := Result + 'the lost vJoy devices were put back'
  else
    Result := Result + 'the lost vJoy devices were not put back';
end;

(* D-01-VJOY-UPDATE-KEEPS, Repair Now: the helper again (the same elevated
   way) with one vjoy_restore job for the lost devices; its result shows in
   a box and on the last page. Repair Later does nothing more: the helper
   already remembered them (vjoy_lost.json) for Tools > Drivers. *)
procedure RunVJoyRestore;
var
  JobFile, ResultsFile: String;
  Lines: TArrayOfString;
begin
  JobFile := ExpandConstant('{tmp}\' + RestoreJobFileName);
  ResultsFile := ExpandConstant('{tmp}\' + RestoreResultsFileName);
  DeleteFile(ResultsFile);
  SetArrayLength(JobDrivers, 1);
  JobDrivers[0] := VJoyRestoreJob;
  SetArrayLength(Lines, 1);
  Lines[0] := '{"version": 1, "jobs": [' + VJoyRestoreJobJson + ']}';
  Log('vJoy devices to put back: ' + VJoyLayoutText(VJoyUpdateLost));
  if SaveStringsToUTF8FileWithoutBOM(JobFile, Lines, False) then
    RunHelperJobs(JobFile, ResultsFile)
  else
  begin
    Log('Could not write the vJoy repair job file ' + JobFile);
    SetJobResult(0, 'failed', 'Setup could not write the repair job.', False);
  end;
  if VJoyRestoreRestart then
    DriversNeedRestart := True;
  if DriverSummary <> '' then
    DriverSummary := DriverSummary + #13#10;
  DriverSummary := DriverSummary + VJoyRestoreResultLine;
  if VJoyRestoreState = 'done' then
    MsgBox(VJoyRestoreResultLine, mbInformation, MB_OK)
  else
    MsgBox(VJoyRestoreResultLine, mbError, MB_OK);
end;

{ After the vJoy update: "The vJoy update lost a device" with Repair Now /
  Repair Later (TaskDialogMsgBox's own button captions). }
procedure AskVJoyRepair;
begin
  if WizardSilent or (GetArrayLength(VJoyUpdateLost) = 0) then
    Exit;
  Log('The vJoy update lost: ' + VJoyLayoutText(VJoyUpdateLost));
  if TaskDialogMsgBox(VJoyLostTitle, VJoyLostText(VJoyUpdateLost),
    mbError, MB_YESNO, [VJoyRepairNow, VJoyRepairLater], 0) = IDYES then
  begin
    try
      RunVJoyRestore;
    except
      Log('vJoy repair failed: ' + GetExceptionMessage);
    end;
  end
  else
    Log('vJoy repair left for later (Tools > Drivers).');
end;

{ 01 S190, S191: after the files are copied, one elevated start of Gremlin
  Device Helper for every ticked driver; a failure never stops Gremlin's own
  install. }
procedure RunDriverJobs;
var
  JobFile, ResultsFile: String;
  ResultCode: Integer;
begin
  if not DriverJobsPlanned then
    Exit;
  SetArrayLength(VJoyUpdateLost, 0);
  SetArrayLength(VJoyUpdateAdded, 0);
  try
    JobFile := ExpandConstant('{tmp}\' + JobFileName);
    ResultsFile := ExpandConstant('{tmp}\' + ResultsFileName);
    DeleteFile(ResultsFile);
    if WriteJobFile(JobFile) then
    begin
      RunHelperJobs(JobFile, ResultsFile);
      BuildDriverSummary;
      if HidHideRemoved then
        WriteHidHidePending(DriverIndex('hidhide'));
      AskVJoyRepair;
    end;
  except
    Log('Driver step failed: ' + GetExceptionMessage);
    FailOpenJobs('Setup could not run the driver step.');
    BuildDriverSummary;
  end;
  { Setup closed the program (01 S173): start it again now the drivers are
    done ([Run]'s RestartAfterClose leaves it to here). }
  if ClosedByInstaller and not LaunchAfterSilentUpdate and FileExists(AppExe) then
    ExecAsOriginalUser(AppExe, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
end;

{ -- the Visual C++ Runtime (01 S193) }

{ A valid Authenticode signature by Microsoft Corporation. }
function RuntimeSignedByMicrosoft(const Path: String): Boolean;
var
  Literal, Params: String;
  Code: Integer;
begin
  Literal := Path;
  StringChangeEx(Literal, '''', '''''', True);
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "' +
    '$s = Get-AuthenticodeSignature -LiteralPath ''' + Literal + '''; ' +
    'if (($s.Status -eq ''Valid'') -and ($s.SignerCertificate.Subject -like ' +
    '''CN={#RuntimeSigner}*'')) { exit 0 } else { exit 1 }"';
  Result := Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    Params, '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0);
end;

{ The extracted copy is the one Microsoft signed: drivers.RUNTIME's SHA-256
  and a valid Authenticode signature by Microsoft Corporation. }
function RuntimeFileTrusted(const Path: String): Boolean;
begin
  Result := False;
  if Lowercase(GetSHA256OfFile(Path)) <> '{#RuntimeSha256}' then
  begin
    Log(RuntimeName + ': the bundled copy''s SHA-256 does not match.');
    Exit;
  end;
  Result := RuntimeSignedByMicrosoft(Path);
  if not Result then
    Log(RuntimeName + ': the bundled copy''s signature is not Microsoft''s.');
end;

{ The last 64-hex-digit part of Url's path, in lower case; '' when none. }
function UrlSha256(const Url: String): String;
var
  Rest, Part: String;
  P, K: Integer;
  Hex: Boolean;
begin
  Result := '';
  Rest := Url;
  while Rest <> '' do
  begin
    P := Pos('/', Rest);
    if P = 0 then
    begin
      Part := Rest;
      Rest := '';
    end
    else
    begin
      Part := Copy(Rest, 1, P - 1);
      Rest := Copy(Rest, P + 1, Length(Rest));
    end;
    if Length(Part) <> 64 then
      Continue;
    Part := Lowercase(Part);
    Hex := True;
    for K := 1 to 64 do
      if Pos(Copy(Part, K, 1), '0123456789abcdef') = 0 then
        Hex := False;
    if Hex then
      Result := Part;
  end;
end;

{ Microsoft's link after its redirects (a HEAD request: nothing is
  downloaded), within RuntimeHeadTimeout x 4. }
function ResolveRuntimeUrl(var Final: String): Boolean;
var
  Request: Variant;
begin
  Result := False;
  Final := '';
  try
    Request := CreateOleObject('WinHttp.WinHttpRequest.5.1');
    Request.SetTimeouts(RuntimeHeadTimeout, RuntimeHeadTimeout, RuntimeHeadTimeout,
      RuntimeHeadTimeout);
    Request.Open('HEAD', RuntimeNewestUrl, False);
    Request.Send;
    if Request.Status = 200 then
    begin
      { WinHttpRequestOption_URL (1): the URL after the redirects. }
      Final := Request.Option(1);
      Result := Final <> '';
    end
    else
      Log(RuntimeName + ': Microsoft''s link answered ' + IntToStr(Request.Status));
  except
    Log(RuntimeName + ': Microsoft''s link could not be checked: ' +
      GetExceptionMessage);
  end;
end;

{ 01 S193 (answer 6a), when the box is ticked, before the install: finds
  Microsoft's newest; when its SHA-256 (in the link's path) is the bundled
  copy's, nothing is downloaded; otherwise it is downloaded, checked like
  the bundled copy (signed by Microsoft, and the SHA-256 the link names) and
  kept to run when it is newer than both the bundled copy and the installed
  runtime. Any failure leaves the bundled copy (used when the runtime is
  missing). }
procedure CheckNewestRuntime;
var
  Final, Sha, Path, Version, Installed: String;
begin
  RuntimeNewestPath := '';
  RuntimeNewestVersion := '';
  RuntimeNewestNote := '';
  if not RuntimeNewestWanted then
    Exit;
  try
    if not ResolveRuntimeUrl(Final) then
    begin
      RuntimeNewestNote := 'Microsoft''s newest could not be checked';
      Exit;
    end;
    Log(RuntimeName + ': Microsoft''s newest is at ' + Final);
    Sha := UrlSha256(Final);
    if Sha = Lowercase('{#RuntimeSha256}') then
    begin
      RuntimeNewestNote := RuntimeSameNote;
      Log(RuntimeName + ': ' + RuntimeSameNote + '; nothing downloaded.');
      Exit;
    end;
    Path := ExpandConstant('{tmp}\') + RuntimeNewestFile;
    DriverDownloadPage.Clear;
    DriverDownloadPage.Add(Final, RuntimeNewestFile, '');
    DriverDownloadPage.SetText('Downloading Microsoft''s newest ' +
      RuntimeName + #$2026, '');
    DriverDownloadPage.Show;
    try
      try
        DriverDownloadPage.Download;
      except
        if DriverDownloadPage.AbortedByUser then
          RuntimeNewestNote := 'the download of Microsoft''s newest was stopped'
        else
          RuntimeNewestNote := 'Microsoft''s newest could not be downloaded';
        Log(RuntimeName + ': ' + RuntimeNewestNote + ' (' + GetExceptionMessage + ')');
        Exit;
      end;
    finally
      DriverDownloadPage.Hide;
    end;
    if (Sha <> '') and (Lowercase(GetSHA256OfFile(Path)) <> Sha) then
    begin
      RuntimeNewestNote := 'Microsoft''s newest failed its check';
      Log(RuntimeName + ': the download''s SHA-256 is not the one its link names.');
      Exit;
    end;
    if not RuntimeSignedByMicrosoft(Path) then
    begin
      RuntimeNewestNote := 'Microsoft''s newest failed its check';
      Log(RuntimeName + ': the download''s signature is not Microsoft''s.');
      Exit;
    end;
    if not GetVersionNumbersString(Path, Version) then
    begin
      RuntimeNewestNote := 'Microsoft''s newest has no version';
      Log(RuntimeName + ': the download has no file version.');
      Exit;
    end;
    Installed := RuntimeInstalledVersion;
    Log(RuntimeName + ': Microsoft''s newest is ' + Version + '; bundled ' +
      '{#RuntimeBundled}; installed ' + Installed);
    if CompareVersions(Version, '{#RuntimeBundled}') <= 0 then
      RuntimeNewestNote := 'Microsoft''s newest (' + Version + ') is not newer ' +
        'than the copy setup carries'
    else if (Installed <> '') and (CompareVersions(Version, Installed) <= 0) then
      RuntimeNewestNote := 'Microsoft''s newest (' + Version + ') is not newer ' +
        'than the installed one'
    else
    begin
      RuntimeNewestPath := Path;
      RuntimeNewestVersion := Version;
    end;
  except
    RuntimeNewestNote := 'Microsoft''s newest could not be checked';
    Log(RuntimeName + ': the newest check failed: ' + GetExceptionMessage);
  end;
end;

{ The last page's line for an exit code (drivers.RUNTIME_DONE_CODES). }
function RuntimeCodeResult(Code: Integer): String;
begin
  if Code = RuntimeDoneCode then
    Result := 'installed'
  else if Code = RuntimeNewerCode then
    Result := 'a newer version is already installed'
  else if Code = RuntimeRestartCode then
  begin
    Result := 'installed; a restart finishes it';
    { A silent install never restarts the PC on its own. }
    if not WizardSilent then
      RuntimeNeedRestart := True;
  end
  else
    Result := 'not installed (error ' + IntToStr(Code) + '). Gremlin-Platforms ' +
      'can''t start until it is installed';
end;

procedure SetRuntimeText(const Text: String);
begin
  WizardForm.StatusLabel.Caption := Text;
  if not WizardSilent then
    RuntimeProgressPage.SetText(Text, '');
end;

{ 01 S193: setup installs the runtime itself, first (at ssInstall, before
  the files are copied, the driver jobs and any [Run] entry), with its own
  administrator prompt: the helper can't start without it. Silent installs
  too. A failure is listed on the last page and never stops the install.
  Answer 6a: Microsoft's newest (CheckNewestRuntime) runs instead of the
  bundled copy when it is newer, even over an installed runtime; the last
  page says which copy was used. }
procedure InstallRuntime;
var
  Path, Used: String;
  ErrorCode, Tick: Integer;
  Process: Longint;
  Code: Cardinal;
  Ended: Boolean;
begin
  if RuntimeInstalled and (RuntimeNewestPath = '') then
  begin
    if RuntimeNewestNote <> '' then
    begin
      RuntimeResult := 'already installed; ' + RuntimeNewestNote;
      Log(RuntimeName + ': ' + RuntimeResult);
    end;
    Exit;
  end;
  if not RuntimeInstalled then
    RuntimeMissing := True;
  try
    if RuntimeNewestPath <> '' then
    begin
      Path := RuntimeNewestPath;
      Used := 'Microsoft''s newest, ' + RuntimeNewestVersion;
    end
    else
    begin
      ExtractTemporaryFile('{#RuntimeFile}');
      Path := ExpandConstant('{tmp}\{#RuntimeFile}');
      if not RuntimeFileTrusted(Path) then
      begin
        RuntimeResult := 'not installed: the bundled copy failed its check';
        Exit;
      end;
      Used := 'the copy setup carries, {#RuntimeBundled}';
      if RuntimeNewestNote <> '' then
        Used := Used + '; ' + RuntimeNewestNote;
    end;
    if not WizardSilent then
    begin
      { Microsoft's installer gives no percentage: a moving bar for the whole
        wait. SetProgress below pumps the window's messages each tick, which
        keeps the marquee moving. }
      RuntimeProgressPage.ProgressBar.Style := npbstMarquee;
      RuntimeProgressPage.SetProgress(0, RuntimeWaitTicks);
      RuntimeProgressPage.Show;
    end;
    try
      SetRuntimeText('Windows asks for administrator permission' + #$2026);
      Log('Installing ' + RuntimeName + ' (' + Used + '): ' + Path + ' ' +
        RuntimeArgs);
      { Started elevated from setup's window (answer 4a), so the prompt
        names Microsoft's installer and opens in front of setup; it returns
        once the prompt is answered. }
      if StartElevated(Path, RuntimeArgs, ExpandConstant('{tmp}'), SW_HIDE,
        Process, ErrorCode) then
      begin
        SetRuntimeText('Installing the ' + RuntimeName + #$2026);
        Ended := False;
        Code := 0;
        try
          for Tick := 1 to RuntimeWaitTicks do
          begin
            if (Process = 0) or (WaitForSingleObject(Process, 0) = WaitObject0) then
            begin
              Ended := True;
              Break;
            end;
            if not WizardSilent then
              RuntimeProgressPage.SetProgress(Tick, RuntimeWaitTicks);
            Sleep(RuntimeWaitStep);
          end;
          if Ended and (Process <> 0) then
            if not GetExitCodeProcess(Process, Code) then
              Ended := False;
        finally
          if Process <> 0 then
            CloseHandle(Process);
        end;
        if not Ended then
          RuntimeResult := 'not installed: it did not finish within 10 minutes'
        else
        begin
          Log(RuntimeName + ' installer exit code ' + IntToStr(Code));
          RuntimeResult := RuntimeCodeResult(Code);
        end;
      end
      else if ErrorCode = UacRefusedCode then
        RuntimeResult := 'not installed: administrator permission was not given'
      else
        RuntimeResult := 'not installed: ' + SysErrorMessage(ErrorCode);
      RuntimeResult := RuntimeResult + ' (' + Used + ')';
    finally
      if not WizardSilent then
      begin
        RuntimeProgressPage.Hide;
        RuntimeProgressPage.ProgressBar.Style := npbstNormal;
      end;
    end;
  except
    Log(RuntimeName + ' step failed: ' + GetExceptionMessage);
    RuntimeResult := 'not installed: setup could not run its installer';
  end;
  Log(RuntimeName + ': ' + RuntimeResult);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  { 01 S193: the runtime first, before anything else. }
  if CurStep = ssInstall then
    InstallRuntime;
  if CurStep = ssPostInstall then
  begin
    { The new version is in: the old one can go. }
    Finished := True;
    DeleteFile(MarkerFile);
    RemovePath(AppFile('_internal.old'));
    RemovePath(AppFile('{#MyAppExeName}.old'));
    { ONE-TIME (tracker OT-7): remove the R1 Start menu entry left by older installs }
    DelTree(ExpandConstant('{userprograms}\Gremlin-Platforms R1'), True, True, True);
    DeleteFile(ExpandConstant('{userdesktop}\Gremlin-Platforms R1.lnk'));
    { 01 S190: the driver jobs, once Gremlin's own files are in. }
    RunDriverJobs;
  end;
end;

procedure DeinitializeSetup;
var
  ResultCode: Integer;
begin
  WatchVJoyScroll(False);
  { Failed or cancelled after the old program was moved aside: put it back,
    so the version that worked before still starts. }
  if MovedAside and not Finished then
  begin
    Log('Install did not finish; putting the previous version back.');
    PutBack('_internal');
    PutBack('{#MyAppExeName}');
    DeleteFile(MarkerFile);
  end;
  { An in-app update that didn't finish, or one setup closed the program
    for: start the version that is there again (after an in-app update it
    says the update didn't finish and offers Try Again). }
  if (AppExe <> '') and not Finished and
    (LaunchAfterSilentUpdate or ClosedByInstaller) and FileExists(AppExe) then
  begin
    Log('Update did not finish; starting the previous version again.');
    ExecAsOriginalUser(AppExe, '', '', SW_SHOWNORMAL, ewNoWait, ResultCode);
  end;
end;

{ True when the folder can be written without admin rights. Removes anything
  it had to create for the test. }
function CanWriteTo(const Dir: String): Boolean;
var
  Existed: Boolean;
  Probe: String;
begin
  Existed := DirExists(Dir);
  Result := ForceDirectories(Dir);
  if Result then
  begin
    Probe := AddBackslash(Dir) + '.gremlin_write_test';
    Result := SaveStringToFile(Probe, 'test', False);
    DeleteFile(Probe);
  end;
  if not Existed then
    RemoveDir(Dir);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Busy: TArrayOfInteger;
begin
  Result := True;
  if (CurPageID = wpSelectDir) and not CanWriteTo(WizardDirValue) then
  begin
    MsgBox('This folder needs administrator rights to change, so updates could ' +
      'not be installed into it.' + #13#10#13#10 +
      'Choose a folder you can write to, for example the one suggested.',
      mbError, MB_OK);
    Result := False;
  end;
  { A silent install never runs driver jobs (Setup "clicks" Next there too). }
  if WizardSilent then
    Exit;
  if CurPageID = DriversPage.ID then
  begin
    { D-01-VJOY-IN-USE: changing or removing a device another program holds
      asks first; No stays on the page. Before the alike question. }
    if VJoyActive then
    begin
      VJoyChangedBusy(Busy);
      if GetArrayLength(Busy) > 0 then
        if MsgBox(VJoyInUseWarning(Busy), mbConfirmation, MB_YESNO) <> IDYES then
        begin
          Result := False;
          Exit;
        end;
    end;
    { D-01-VJOY-COUNTDOWN: alike devices are allowed, after a Yes; No stays
      on the page. }
    if VJoyActive then
      if VJoyAlikeWarning(VJoyChosen) <> '' then
        if MsgBox(VJoyAlikeWarning(VJoyChosen) + VJoyAlikeQuestion,
          mbConfirmation, MB_YESNO) <> IDYES then
        begin
          Result := False;
          Exit;
        end;
    DriversPageDone;
    { D-01-VJOY-UPDATE-KEEPS: a vJoy update (not a fresh install) says first
      that the devices are noted and checked afterwards (OK only). }
    if Drivers[DriverIndex('vjoy')].Op = 'update' then
    begin
      Log('vJoy devices before the update: ' + VJoyLayoutText(VJoyCurrent));
      TaskDialogMsgBox(VJoyUpdateInfoTitle, VJoyUpdateInfoText(VJoyCurrent),
        mbInformation, MB_OK, [], 0);
    end;
  end
  else if CurPageID = wpReady then
  begin
    { 01 S189: newer versions download before the install; a failure only
      means the bundled copy is used. 01 S193 (answer 6a): the same for
      Microsoft's newest runtime, when ticked. }
    DownloadNewerDrivers;
    CheckNewestRuntime;
  end;
end;

procedure InitializeWizard;
begin
  InitDrivers;
  InitVJoyChoice;
  CreateDriverPages;
end;

{ 01 S187: no Drivers page on a silent install (the in-app update). }
function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = DriversPage.ID) and WizardSilent;
end;

{ 06 S187: the Ready page says what each driver step will do and when. }
function UpdateReadyMemo(Space, NewLine, MemoUserInfoInfo, MemoDirInfo,
  MemoTypeInfo, MemoComponentsInfo, MemoGroupInfo, MemoTasksInfo: String): String;
var
  I: Integer;
  K: Integer;
  Steps, VJoyStep: String;
begin
  Result := '';
  if MemoUserInfoInfo <> '' then
    Result := Result + MemoUserInfoInfo + NewLine + NewLine;
  if MemoDirInfo <> '' then
    Result := Result + MemoDirInfo + NewLine + NewLine;
  if MemoTypeInfo <> '' then
    Result := Result + MemoTypeInfo + NewLine + NewLine;
  if MemoComponentsInfo <> '' then
    Result := Result + MemoComponentsInfo + NewLine + NewLine;
  if MemoGroupInfo <> '' then
    Result := Result + MemoGroupInfo + NewLine + NewLine;
  if MemoTasksInfo <> '' then
    Result := Result + MemoTasksInfo + NewLine + NewLine;
  { 01 S193: the runtime first, with its own administrator prompt. }
  if RuntimeMissing then
    Result := Result + 'First, before the files are copied (Windows asks for ' +
      'administrator permission):' + NewLine + Space + 'Install the ' +
      RuntimeName + ' {#RuntimeBundled} (Gremlin-Platforms needs it to run)' +
      NewLine;
  { 01 S193 (answer 6a). }
  if RuntimeNewestWanted then
  begin
    if not RuntimeMissing then
      Result := Result + 'First, before the files are copied:' + NewLine;
    Result := Result + Space + 'Check and download an updated Visual C++ ' +
      'Runtime, and install it when it is newer (Windows asks for administrator ' +
      'permission then)' + NewLine;
  end;
  if RuntimeMissing or RuntimeNewestWanted then
    Result := Result + NewLine;
  Steps := '';
  for I := 0 to GetArrayLength(Drivers) - 1 do
  begin
    if (Drivers[I].Key = 'vjoy') and VJoySetupPlanned then
      VJoyStep := Space + 'Set up ' + CountText(GetArrayLength(VJoyChosen),
        'vJoy device', 'vJoy devices') + ': ' + VJoyLayoutText(VJoyChosen) +
        NewLine
    else
      VJoyStep := '';
    if not Drivers[I].Chosen then
    begin
      Steps := Steps + VJoyStep;
      Continue;
    end;
    if Drivers[I].Op = 'install' then
      Steps := Steps + Space + 'Install ' + Drivers[I].Name + ' ' +
        TargetVersion(I) + NewLine
    else if Drivers[I].Op = 'update' then
      Steps := Steps + Space + 'Update ' + Drivers[I].Name + ' ' +
        Drivers[I].Installed + ' ' + #$2192 + ' ' + TargetVersion(I) + NewLine
    else if Drivers[I].Op = 'remove' then
      Steps := Steps + Space + 'Remove HidHide ' + Drivers[I].Installed +
        ' (HidHide update, step 1 of 2; restart needed)' + NewLine;
    Steps := Steps + VJoyStep;
  end;
  { 06 S185: devices left out of the layout are deleted; edits warn. }
  if VJoySetupPlanned then
  begin
    for K := 0 to GetArrayLength(VJoyCurrent) - 1 do
      if not VJoyIdUsed(VJoyChosen, VJoyCurrent[K].Id) then
        Steps := Steps + Space + 'vJoy device ' + IntToStr(VJoyCurrent[K].Id) +
          ' will be deleted.' + NewLine;
    if GetArrayLength(VJoyCurrent) > 0 then
      Steps := Steps + Space + VJoyWarning + NewLine;
  end;
  if Steps <> '' then
    Result := Result + 'Drivers, after the files are copied (Windows asks for ' +
      'administrator permission once):' + NewLine + Steps;
end;

{ 01 S191, S193: the last page lists the runtime's and each driver's result. }
procedure CurPageChanged(CurPageID: Integer);
var
  Text: String;
begin
  { The device rows follow their scroll bar only while they show. }
  WatchVJoyScroll(CurPageID = DriversPage.ID);
  if (CurPageID <> wpFinished) or ((DriverSummary = '') and (RuntimeResult = '')) then
    Exit;
  Text := 'Setup has finished installing {#MyAppName}.';
  if RuntimeResult <> '' then
    Text := Text + #13#10#13#10 + RuntimeName + ': ' + RuntimeResult;
  if DriverSummary <> '' then
    Text := Text + #13#10#13#10 + 'Drivers:' + #13#10 + DriverSummary;
  if HidHideRemoved then
    Text := Text + #13#10#13#10 + 'Restart needed to continue the HidHide update'
  else if DriversNeedRestart then
    Text := Text + #13#10#13#10 + 'A driver needs a restart to finish.'
  else if RuntimeNeedRestart then
    Text := Text + #13#10#13#10 + 'The ' + RuntimeName + ' needs a restart to finish.';
  WizardForm.FinishedLabel.Caption := Text;
  WizardForm.FinishedLabel.AdjustHeight;
  { Setup placed the Launch box (RunList) and the restart choice under its
    own, shorter text before this runs: move them under this one, or the
    taller text covers them. With a restart Setup shows no Launch box. }
  if not (DriversNeedRestart or RuntimeNeedRestart) then
  begin
    { Setup sizes RunList to fill the page, so the clamp below would put it
      back under the label: fit its height to its items first. }
    if WizardForm.RunList.Items.Count > 0 then
      WizardForm.RunList.Height := ScaleY(20) * WizardForm.RunList.Items.Count
    else
      WizardForm.RunList.Height := ScaleY(20);
    WizardForm.RunList.Top := WizardForm.FinishedLabel.Top +
      WizardForm.FinishedLabel.Height + ScaleY(12);
    if WizardForm.RunList.Top + WizardForm.RunList.Height >
      WizardForm.FinishedPage.ClientHeight then
      WizardForm.RunList.Top := WizardForm.FinishedPage.ClientHeight -
        WizardForm.RunList.Height;
    WizardForm.RunList.Visible := True;
    WizardForm.RunList.BringToFront;
  end;
  Log('Finish page: RunList Top=' + IntToStr(WizardForm.RunList.Top) +
    ' Height=' + IntToStr(WizardForm.RunList.Height) +
    ' Visible=' + IntToStr(Ord(WizardForm.RunList.Visible)) +
    ' Items=' + IntToStr(WizardForm.RunList.Items.Count) +
    '; FinishedLabel Top=' + IntToStr(WizardForm.FinishedLabel.Top) +
    ' Height=' + IntToStr(WizardForm.FinishedLabel.Height) +
    '; FinishedPage.ClientHeight=' + IntToStr(WizardForm.FinishedPage.ClientHeight));
  if DriversNeedRestart or RuntimeNeedRestart then
  begin
    WizardForm.YesRadio.Caption := 'Restart now';
    WizardForm.NoRadio.Caption := 'Restart later';
    WizardForm.YesRadio.Top := WizardForm.FinishedLabel.Top +
      WizardForm.FinishedLabel.Height + ScaleY(12);
    WizardForm.NoRadio.Top := WizardForm.YesRadio.Top +
      WizardForm.YesRadio.Height + ScaleY(4);
  end;
end;

{ 01 S191, S193: offers a restart when a driver or the runtime asked for one. }
function NeedRestart: Boolean;
begin
  Result := DriversNeedRestart or RuntimeNeedRestart;
end;

{ 01 S194: uninstall removes the program's Start with Windows entry. Install
  writes nothing there; the program adds it when the user turns the option on.
  PrivilegesRequired=lowest (no override), so HKCU is the signed-in user's. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
    RegDeleteValue(HKCU, 'Software\Microsoft\Windows\CurrentVersion\Run',
      'Gremlin-Platforms');
end;
