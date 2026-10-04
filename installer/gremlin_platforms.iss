; Gremlin-Platforms R1 installer (Inno Setup 6).
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

#define MyAppName "Gremlin-Platforms R1"
#define MyAppPublisher "swill008"
#define MyAppURL "https://github.com/swill008/Gremlin-Platforms"
#define MyAppExeName "gremlin_platforms.exe"

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
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=Gremlin-Platforms-R1-{#MyAppVersion}-Setup
SetupIconFile=..\gfx\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
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
Source: "..\dist\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ runtime..."; Flags: waituntilterminated skipifdoesntexist
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
; The in-app updater runs setup silently with /LAUNCH=1 to start the new version.
Filename: "{app}\{#MyAppExeName}"; Flags: nowait; Check: LaunchAfterSilentUpdate

[UninstallDelete]
Type: files; Name: "{app}\dill_debug.log"
Type: filesandordirs; Name: "{app}\_internal.old"
Type: files; Name: "{app}\{#MyAppExeName}.old"
Type: files; Name: "{app}\.update-in-progress"

[Code]
var
  { The old program was moved aside and is put back unless the install
    finishes. }
  MovedAside: Boolean;
  Finished: Boolean;
  { The program to start again if an in-app update doesn't finish; set
    once setup reaches the install step. }
  AppExe: String;

function LaunchAfterSilentUpdate: Boolean;
begin
  Result := WizardSilent and (ExpandConstant('{param:LAUNCH|0}') = '1');
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

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  Result := '';
  AppExe := AppFile('{#MyAppExeName}');
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

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { The new version is in: the old one can go. }
    Finished := True;
    DeleteFile(MarkerFile);
    RemovePath(AppFile('_internal.old'));
    RemovePath(AppFile('{#MyAppExeName}.old'));
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
  { An in-app update that didn't finish: start the version that is there
    again (it says the update didn't finish and offers Try Again). }
  if (AppExe <> '') and not Finished and LaunchAfterSilentUpdate
    and FileExists(AppExe) then
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
end;
