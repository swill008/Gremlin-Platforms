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
  { One vJoy device (gremlin/drivers.py VJoyDevice): axes 0-8 (the first N
    of X Y Z RX RY RZ SL0 SL1), buttons 0-128, hats 0-4. }
  TVJoyDevice = record
    Id, Axes, Buttons, Hats: Integer;
  end;
  TVJoyDevices = array of TVJoyDevice;

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
    layout to set. VJoyUserEdited: the preset or the Custom lines were
    changed on the page. }
  VJoyCurrent, VJoyChosen: TVJoyDevices;
  VJoyLayoutRead, VJoyUserEdited, VJoyFilling: Boolean;
  { A vjoy_setup job runs after the vJoy install job (12 S25b). }
  VJoySetupPlanned: Boolean;
  VJoySetupState, VJoySetupMessage: String;
  VJoySetupRestart: Boolean;
  VJoyPresetBox: TNewComboBox;
  VJoyCurrentText, VJoyWarningText: TNewStaticText;
  VJoyCustomMemo: TNewMemo;

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
  RuntimeLine = 'Microsoft Visual C++ Runtime: will be installed (Gremlin-Platforms needs it to run)';
  RuntimeArgs = '/install /quiet /norestart';
  RuntimeDoneCode = 0;
  RuntimeNewerCode = 1638;
  RuntimeRestartCode = 3010;
  { The installer's exit code, written by the hidden PowerShell that starts
    it (InstallRuntime). }
  RuntimeExitFile = 'runtime_exit_code.txt';
  { Half-second ticks: ten minutes before setup stops waiting. }
  RuntimeWaitStep = 500;
  RuntimeWaitTicks = 1200;
  { 06 S185: the vJoy choice's words and limits, as in
    gremlin/ui/drivers_model.py and gremlin/drivers.py. }
  VJoyPresetOne = '1 device, full';
  VJoyPresetTwo = '2 devices, full';
  VJoyCustom = 'Custom';
  VJoyWarning = 'Running games will lose the vJoy devices until they restart.';
  VJoyMaxDevices = 16;
  VJoyAxisNames = 'x y z rx ry rz sl0 sl1';
  { JobDrivers' entry for the vjoy_setup job (it has no row of its own). }
  VJoySetupJob = -1;
  VJoyCaptureFile = 'vjoyconfig_output.txt';

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

{ A preset's devices (gremlin/drivers.py PRESETS): "full" is 8 axes, 128
  buttons and 4 hats. }
procedure PresetDevices(const Name: String; var List: TVJoyDevices);
var
  K, Count: Integer;
begin
  SetArrayLength(List, 0);
  Count := 1;
  if Name = VJoyPresetTwo then
    Count := 2;
  for K := 1 to Count do
    AddVJoyDevice(List, K, 8, 128, 4);
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

function ClampInt(Value, Low, High: Integer): Integer;
begin
  Result := Value;
  if Result < Low then
    Result := Low;
  if Result > High then
    Result := High;
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

{ How many of X Y Z RX RY RZ SL0 SL1 the "Axes:" value has, in order. }
function AxesCount(Value: String): Integer;
var
  Names, Axis, Token: String;
begin
  Result := 0;
  Names := VJoyAxisNames;
  while Result < 8 do
  begin
    Axis := NextToken(Names);
    Token := LowerCase(NextToken(Value));
    if (Token = '') or (Token <> Axis) then
      Exit;
    Result := Result + 1;
  end;
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
      List[Current].Axes := AxesCount(Value);
  end;
end;

{ `vJoyConfig -t`: the numbers of the devices that exist ("Device N:
  Status: S", S not MISSING or UNKNOWN). }
procedure ParseVJoyStatus(const Lines: TArrayOfString; var Ids: TArrayOfInteger);
var
  K, P, N: Integer;
  Left, Right, Number, State: String;
begin
  SetArrayLength(Ids, 0);
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
  VJoyLayoutRead := RunVJoyConfig('-t', Lines);
  if not VJoyLayoutRead then
    Exit;
  ParseVJoyStatus(Lines, Ids);
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

function VJoyDeviceText(const D: TVJoyDevice): String;
begin
  Result := IntToStr(D.Id) + ': ' + CountText(D.Axes, 'axis', 'axes') + ', ' +
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

{ The Custom lines: one per device, "axes, buttons, hats". }
procedure FillCustomMemo;
var
  K: Integer;
begin
  VJoyFilling := True;
  try
    VJoyCustomMemo.Lines.Clear;
    for K := 0 to GetArrayLength(VJoyChosen) - 1 do
      VJoyCustomMemo.Lines.Add(IntToStr(VJoyChosen[K].Axes) + ', ' +
        IntToStr(VJoyChosen[K].Buttons) + ', ' + IntToStr(VJoyChosen[K].Hats));
  finally
    VJoyFilling := False;
  end;
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

{ Reads the Custom lines into VJoyChosen: 1-16 devices, each number held to
  its range (like DriversModel.setDevice); a row keeps the device number it
  had, a new row takes the lowest free one. }
procedure ReadCustomMemo;
var
  Old: TVJoyDevices;
  K, Id, Axes, Buttons, Hats: Integer;
  Line: String;
begin
  CopyVJoyDevices(VJoyChosen, Old);
  SetArrayLength(VJoyChosen, 0);
  for K := 0 to VJoyCustomMemo.Lines.Count - 1 do
  begin
    Line := Trim(VJoyCustomMemo.Lines[K]);
    if Line = '' then
      Continue;
    if GetArrayLength(VJoyChosen) >= VJoyMaxDevices then
      Break;
    StringChangeEx(Line, ',', ' ', True);
    Axes := ClampInt(StrToIntDef(NextToken(Line), 8), 0, 8);
    Buttons := ClampInt(StrToIntDef(NextToken(Line), 128), 0, 128);
    Hats := ClampInt(StrToIntDef(NextToken(Line), 4), 0, 4);
    Id := 0;
    if GetArrayLength(VJoyChosen) < GetArrayLength(Old) then
      Id := Old[GetArrayLength(VJoyChosen)].Id;
    if (Id = 0) or VJoyIdUsed(VJoyChosen, Id) then
    begin
      Id := 1;
      while VJoyIdUsed(VJoyChosen, Id) do
        Id := Id + 1;
    end;
    AddVJoyDevice(VJoyChosen, Id, Axes, Buttons, Hats);
  end;
  if GetArrayLength(VJoyChosen) = 0 then
    AddVJoyDevice(VJoyChosen, 1, 8, 128, 4);
end;

{ The vJoy part is live when vJoy is installed or ticked to install; the
  warning shows once an edit would change devices that exist (06 S185). }
procedure UpdateVJoyControls;
var
  V: Integer;
  Active: Boolean;
begin
  V := DriverIndex('vjoy');
  Active := Drivers[V].State <> 'missing';
  if not Active then
    if Drivers[V].Row >= 0 then
      Active := DriverList.Checked[Drivers[V].Row];
  VJoyPresetBox.Enabled := Active;
  VJoyCustomMemo.Enabled := Active;
  VJoyCustomMemo.ReadOnly := VJoyPresetBox.Text <> VJoyCustom;
  VJoyWarningText.Caption := '';
  if Active and VJoyEdited then
    if GetArrayLength(VJoyCurrent) > 0 then
      VJoyWarningText.Caption := VJoyWarning;
end;

procedure VJoyPresetChange(Sender: TObject);
begin
  if VJoyPresetBox.Text <> VJoyCustom then
  begin
    PresetDevices(VJoyPresetBox.Text, VJoyChosen);
    VJoyUserEdited := True;
    FillCustomMemo;
  end;
  UpdateVJoyControls;
end;

procedure VJoyMemoChange(Sender: TObject);
begin
  if VJoyFilling or VJoyCustomMemo.ReadOnly then
    Exit;
  ReadCustomMemo;
  VJoyUserEdited := True;
  UpdateVJoyControls;
end;

procedure DriverListClickCheck(Sender: TObject);
begin
  UpdateVJoyControls;
end;

{ -- the Drivers page (01 S187) }

procedure FillDriverList;
var
  I: Integer;
begin
  DriverList.Items.Clear;
  { 01 S193: required, so a line with no box. }
  if RuntimeMissing then
    DriverList.AddGroup(RuntimeLine, '', 0, nil);
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
end;

procedure CreateDriverPages;
var
  Note, VJoyLabel, CustomHint: TNewStaticText;
begin
  DriversPage := CreateCustomPage(wpSelectDir, 'Drivers',
    'vJoy, ViGEmBus and HidHide on this PC.');
  DriverList := TNewCheckListBox.Create(DriversPage);
  DriverList.Parent := DriversPage.Surface;
  DriverList.Left := 0;
  DriverList.Top := 0;
  DriverList.Width := DriversPage.SurfaceWidth;
  DriverList.Height := ScaleY(62);
  if RuntimeMissing then
    DriverList.Height := ScaleY(82);
  DriverList.Flat := True;
  DriverList.OnClickCheck := @DriverListClickCheck;
  FillDriverList;
  Note := TNewStaticText.Create(DriversPage);
  Note.Parent := DriversPage.Surface;
  Note.Left := 0;
  Note.Top := DriverList.Top + DriverList.Height + ScaleY(6);
  Note.Width := DriversPage.SurfaceWidth;
  Note.AutoSize := False;
  Note.WordWrap := True;
  Note.Caption := 'Ticked drivers are installed after Gremlin-Platforms'' ' +
    'files are copied; Windows asks for administrator permission once. ' +
    'Gremlin-Platforms installs even when a driver doesn''t.';
  if RuntimeMissing then
    Note.Caption := Note.Caption + ' The ' + RuntimeName + ' is installed ' +
      'first, before the files are copied, with its own administrator prompt.';
  Note.AdjustHeight;
  { 06 S185: the vJoy device choice. }
  VJoyLabel := TNewStaticText.Create(DriversPage);
  VJoyLabel.Parent := DriversPage.Surface;
  VJoyLabel.Left := 0;
  VJoyLabel.Top := Note.Top + Note.Height + ScaleY(10);
  VJoyLabel.Caption := 'vJoy devices:';
  VJoyPresetBox := TNewComboBox.Create(DriversPage);
  VJoyPresetBox.Parent := DriversPage.Surface;
  VJoyPresetBox.Style := csDropDownList;
  VJoyPresetBox.Left := ScaleX(90);
  VJoyPresetBox.Top := VJoyLabel.Top - ScaleY(3);
  VJoyPresetBox.Width := ScaleX(160);
  VJoyPresetBox.Items.Add(VJoyPresetOne);
  VJoyPresetBox.Items.Add(VJoyPresetTwo);
  VJoyPresetBox.Items.Add(VJoyCustom);
  VJoyPresetBox.ItemIndex := VJoyPresetBox.Items.IndexOf(MatchingPreset(VJoyChosen));
  VJoyPresetBox.OnChange := @VJoyPresetChange;
  VJoyCurrentText := TNewStaticText.Create(DriversPage);
  VJoyCurrentText.Parent := DriversPage.Surface;
  VJoyCurrentText.Left := 0;
  VJoyCurrentText.Top := VJoyPresetBox.Top + VJoyPresetBox.Height + ScaleY(4);
  VJoyCurrentText.Width := DriversPage.SurfaceWidth;
  VJoyCurrentText.AutoSize := False;
  VJoyCurrentText.WordWrap := True;
  VJoyCurrentText.Height := ScaleY(26);
  VJoyCurrentText.Caption := VJoyCurrentLine;
  CustomHint := TNewStaticText.Create(DriversPage);
  CustomHint.Parent := DriversPage.Surface;
  CustomHint.Left := 0;
  CustomHint.Top := VJoyCurrentText.Top + VJoyCurrentText.Height + ScaleY(2);
  CustomHint.Caption := 'Custom: one line per device (1-16): axes (0-8), buttons ' +
    '(0-128), hats (0-4).';
  VJoyWarningText := TNewStaticText.Create(DriversPage);
  VJoyWarningText.Parent := DriversPage.Surface;
  VJoyWarningText.Left := 0;
  VJoyWarningText.Width := DriversPage.SurfaceWidth;
  VJoyWarningText.AutoSize := False;
  VJoyWarningText.Height := ScaleY(16);
  VJoyWarningText.Top := DriversPage.SurfaceHeight - VJoyWarningText.Height;
  VJoyWarningText.Font.Style := [fsBold];
  VJoyCustomMemo := TNewMemo.Create(DriversPage);
  VJoyCustomMemo.Parent := DriversPage.Surface;
  VJoyCustomMemo.Left := 0;
  VJoyCustomMemo.Top := CustomHint.Top + CustomHint.Height + ScaleY(4);
  VJoyCustomMemo.Width := ScaleX(160);
  VJoyCustomMemo.Height := VJoyWarningText.Top - ScaleY(4) - VJoyCustomMemo.Top;
  if VJoyCustomMemo.Height < ScaleY(36) then
    VJoyCustomMemo.Height := ScaleY(36);
  VJoyCustomMemo.ScrollBars := ssVertical;
  VJoyCustomMemo.WantReturns := True;
  FillCustomMemo;
  VJoyCustomMemo.OnChange := @VJoyMemoChange;
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

(* One job: {"op", "driver", "files": [download first, bundled second],
   "devices": []}. A remove lists no file. *)
function JobJson(I: Integer): String;
var
  Files: String;
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
  Result := '{"op": "' + Drivers[I].Op + '", "driver": "' + Drivers[I].Key +
    '", "files": [' + Files + '], "devices": []}';
end;

(* The vJoy device job (06 S185, 12 S25b): {"op": "vjoy_setup", "driver":
   "vjoy", "files": [], "devices": [{"id", "axes", "buttons", "hats"}]}. *)
function VJoySetupJobJson: String;
var
  K: Integer;
  Devices: String;
begin
  Devices := '';
  for K := 0 to GetArrayLength(VJoyChosen) - 1 do
  begin
    if K > 0 then
      Devices := Devices + ', ';
    Devices := Devices + '{"id": ' + IntToStr(VJoyChosen[K].Id) +
      ', "axes": ' + IntToStr(VJoyChosen[K].Axes) +
      ', "buttons": ' + IntToStr(VJoyChosen[K].Buttons) +
      ', "hats": ' + IntToStr(VJoyChosen[K].Hats) + '}';
  end;
  Result := '{"op": "vjoy_setup", "driver": "vjoy", "files": [], "devices": [' +
    Devices + ']}';
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
  else
    Result := Drivers[JobDrivers[J]].ResultState;
end;

function JobRestart(J: Integer): Boolean;
begin
  if JobDrivers[J] = VJoySetupJob then
    Result := VJoySetupRestart
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
  else
  begin
    Drivers[I].ResultState := State;
    Drivers[I].ResultMessage := Message;
    Drivers[I].ResultRestart := Restart;
  end;
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
  AllDone := JsonValue(Text, 'finished', 1, Length(Text)) = 'true';
  Result := True;
end;

{ What the progress page says while a job runs. }
function JobProgressText(I: Integer): String;
begin
  if I = VJoySetupJob then
    Result := 'Setting up the vJoy devices' + #$2026
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

{ 01 S190, S191: after the files are copied, one elevated start of Gremlin
  Device Helper for every ticked driver; a failure never stops Gremlin's own
  install. }
procedure RunDriverJobs;
var
  JobFile, ResultsFile, Params: String;
  ErrorCode, J, ResultCode: Integer;
begin
  if not DriverJobsPlanned then
    Exit;
  try
    JobFile := ExpandConstant('{tmp}\' + JobFileName);
    ResultsFile := ExpandConstant('{tmp}\' + ResultsFileName);
    DeleteFile(ResultsFile);
    if WriteJobFile(JobFile) then
    begin
      for J := 0 to GetArrayLength(JobDrivers) - 1 do
        SetJobResult(J, 'waiting', '', False);
      Params := '--jobs ' + AddQuotes(JobFile) + ' --results ' +
        AddQuotes(ResultsFile);
      DriverProgressPage.SetText(
        'Windows asks for administrator permission' + #$2026, '');
      DriverProgressPage.SetProgress(0, GetArrayLength(JobDrivers));
      DriverProgressPage.Show;
      try
        Log('Starting Gremlin Device Helper ' + Params);
        if ShellExec('runas', ExpandConstant('{app}\{#HelperExeName}'), Params,
          ExpandConstant('{app}'), SW_HIDE, ewNoWait, ErrorCode) then
          WaitForHelper(ResultsFile)
        else if ErrorCode = UacRefusedCode then
          FailOpenJobs('Administrator permission was not given.')
        else
          FailOpenJobs('Gremlin Device Helper could not start: ' +
            SysErrorMessage(ErrorCode));
      finally
        DriverProgressPage.Hide;
      end;
      BuildDriverSummary;
      if HidHideRemoved then
        WriteHidHidePending(DriverIndex('hidhide'));
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

{ The extracted copy is the one Microsoft signed: drivers.RUNTIME's SHA-256
  and a valid Authenticode signature by Microsoft Corporation. }
function RuntimeFileTrusted(const Path: String): Boolean;
var
  Literal, Params: String;
  Code: Integer;
begin
  Result := False;
  if Lowercase(GetSHA256OfFile(Path)) <> '{#RuntimeSha256}' then
  begin
    Log(RuntimeName + ': the bundled copy''s SHA-256 does not match.');
    Exit;
  end;
  Literal := Path;
  StringChangeEx(Literal, '''', '''''', True);
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "' +
    '$s = Get-AuthenticodeSignature -LiteralPath ''' + Literal + '''; ' +
    'if (($s.Status -eq ''Valid'') -and ($s.SignerCertificate.Subject -like ' +
    '''CN={#RuntimeSigner}*'')) { exit 0 } else { exit 1 }"';
  if Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params,
    '', SW_HIDE, ewWaitUntilTerminated, Code) and (Code = 0) then
    Result := True
  else
    Log(RuntimeName + ': the bundled copy''s signature is not Microsoft''s.');
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
  too. A failure is listed on the last page and never stops the install. }
procedure InstallRuntime;
var
  Path, ExitFile, Literal, ExitLiteral, Params, Line: String;
  ErrorCode, Tick, Code: Integer;
  Lines: TArrayOfString;
  Ended, Started: Boolean;
begin
  if RuntimeInstalled then
    Exit;
  RuntimeMissing := True;
  try
    ExtractTemporaryFile('{#RuntimeFile}');
    Path := ExpandConstant('{tmp}\{#RuntimeFile}');
    if not RuntimeFileTrusted(Path) then
    begin
      RuntimeResult := 'not installed: the bundled copy failed its check';
      Exit;
    end;
    ExitFile := ExpandConstant('{tmp}\' + RuntimeExitFile);
    DeleteFile(ExitFile);
    Literal := Path;
    StringChangeEx(Literal, '''', '''''', True);
    ExitLiteral := ExitFile;
    StringChangeEx(ExitLiteral, '''', '''''', True);
    { A hidden, non-elevated PowerShell asks Windows to start Microsoft's
      installer elevated, so the administrator prompt names that installer
      (not a command prompt). It writes 'started' once the prompt is
      accepted, then the exit code, 'timeout', or 'error N' (1223: the
      prompt was refused). Process.Start keeps that Windows error code;
      Start-Process -Verb RunAs loses it in its own error message. }
    Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -Command "' +
      '$f = ''' + ExitLiteral + '''; $r = ''error''; try { ' +
      '$i = New-Object System.Diagnostics.ProcessStartInfo; ' +
      '$i.FileName = ''' + Literal + '''; $i.Arguments = ''' + RuntimeArgs + '''; ' +
      '$i.Verb = ''runas''; $i.UseShellExecute = $true; ' +
      '$p = [System.Diagnostics.Process]::Start($i); ' +
      'Set-Content -LiteralPath $f -Value ''started'' -Encoding Ascii; ' +
      'if ($p.WaitForExit(' + IntToStr(RuntimeWaitTicks * RuntimeWaitStep) + ')) ' +
      '{ $r = $p.ExitCode } else { $r = ''timeout'' } } catch { ' +
      '$e = $_.Exception; while ($e -and -not ($e -is ' +
      '[System.ComponentModel.Win32Exception])) { $e = $e.InnerException }; ' +
      'if ($e) { $r = ''error '' + $e.NativeErrorCode } }; ' +
      'Set-Content -LiteralPath $f -Value $r -Encoding Ascii"';
    if not WizardSilent then
    begin
      RuntimeProgressPage.SetProgress(0, RuntimeWaitTicks);
      RuntimeProgressPage.Show;
    end;
    try
      SetRuntimeText('Windows asks for administrator permission' + #$2026);
      Log('Installing ' + RuntimeName + ' {#RuntimeBundled}: ' + Path + ' ' +
        RuntimeArgs);
      if Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'), Params,
        ExpandConstant('{tmp}'), SW_HIDE, ewNoWait, ErrorCode) then
      begin
        Ended := False;
        Started := False;
        Line := '';
        for Tick := 1 to RuntimeWaitTicks do
        begin
          if LoadStringsFromFile(ExitFile, Lines) and (GetArrayLength(Lines) > 0) then
          begin
            Line := Trim(Lines[0]);
            if (Line = 'started') and not Started then
            begin
              Started := True;
              SetRuntimeText('Installing the ' + RuntimeName + #$2026);
            end
            else if (Line <> '') and (Line <> 'started') then
            begin
              Ended := True;
              Break;
            end;
          end;
          if not WizardSilent then
            RuntimeProgressPage.SetProgress(Tick, RuntimeWaitTicks);
          Sleep(RuntimeWaitStep);
        end;
        if not Ended or (Line = 'timeout') then
          RuntimeResult := 'not installed: it did not finish within 10 minutes'
        else if Line = 'error ' + IntToStr(UacRefusedCode) then
          RuntimeResult := 'not installed: administrator permission was not given'
        else if Copy(Line, 1, 6) = 'error ' then
          RuntimeResult := 'not installed: ' +
            SysErrorMessage(StrToIntDef(Copy(Line, 7, Length(Line)), 0))
        else if Line = 'error' then
          RuntimeResult := 'not installed: Windows could not start its installer'
        else
        begin
          Code := StrToIntDef(Line, -1);
          Log(RuntimeName + ' installer exit code ' + IntToStr(Code));
          RuntimeResult := RuntimeCodeResult(Code);
        end;
      end
      else
        RuntimeResult := 'not installed: ' + SysErrorMessage(ErrorCode);
    finally
      if not WizardSilent then
        RuntimeProgressPage.Hide;
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
    DriversPageDone
  else if CurPageID = wpReady then
    { 01 S189: newer versions download before the install; a failure only
      means the bundled copy is used. }
    DownloadNewerDrivers;
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
      NewLine + NewLine;
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
    WizardForm.RunList.Top := WizardForm.FinishedLabel.Top +
      WizardForm.FinishedLabel.Height + ScaleY(12);
    if WizardForm.RunList.Top + WizardForm.RunList.Height >
      WizardForm.FinishedPage.ClientHeight then
      WizardForm.RunList.Top := WizardForm.FinishedPage.ClientHeight -
        WizardForm.RunList.Height;
  end;
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
