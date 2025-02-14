#define MyAppName "WifeAlert"
#define MyAppVersion "1.0"
#define MyAppPublisher "Nazarein"
#define MyAppURL "https://github.com/nazarein/wifealert"
#define MyAppExeName "WifeAlert.exe"

[Setup]
AppId={{E5A7B27E-4A42-44F2-B1C8-89F2D766B6F3}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={userpf}\{#MyAppName}
DisableProgramGroupPage=yes
OutputDir=installer
OutputBaseFilename=WifeAlert_Setup
SetupIconFile=assets\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
VersionInfoVersion={#MyAppVersion}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Twitch Stream Notification Tool
VersionInfoCopyright=© 2024 {#MyAppPublisher}
VersionInfoProductName={#MyAppName}
VersionInfoProductVersion={#MyAppVersion}
AppMutex={#MyAppName}
UsePreviousAppDir=yes
AppReadmeFile={#MyAppURL}
ShowLanguageDialog=no
CloseApplications=yes
RestartApplications=no
AlwaysShowDirOnReadyPage=yes
DisableWelcomePage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupicon"; Description: "Start with Windows"; GroupDescription: "Windows Integration:"; Flags: unchecked
Name: "clearuserdata"; Description: "Clear user data on uninstall"; GroupDescription: "Cleanup:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "assets\*"; DestDir: "{app}\assets\"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Registry]
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"
Root: HKA; Subkey: "Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#MyAppURL}"

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent runascurrentuser

[Components]
Name: "main"; Description: "Main Files"; Types: full compact custom; Flags: fixed

[InstallDelete]
Type: files; Name: "{app}\{#MyAppExeName}"
Type: files; Name: "{app}\assets\*"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\assets"
Type: dirifempty; Name: "{app}"
Type: filesandordirs; Name: "{localappdata}\{#MyAppName}"; Tasks: clearuserdata

[Code]
function InitializeSetup(): Boolean;
var
  ResultCode: Integer;
  Uninstaller: String;
begin
  Result := True;

  // Check for previous version
  if RegQueryStringValue(HKCU,
    'Software\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1',
    'UninstallString', Uninstaller) then
  begin
    if MsgBox('A previous version of {#MyAppName} was found. Do you want to uninstall it first?',
      mbConfirmation, MB_YESNO) = IDYES then
    begin
      Uninstaller := RemoveQuotes(Uninstaller);
      if not Exec(Uninstaller, '/SILENT', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
      begin
        MsgBox('Error uninstalling previous version. Please uninstall it manually.',
          mbError, MB_OK);
        Result := False;
      end;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
var
  ResultCode: Integer;
begin
  Result := True;
  
  // Try to close the application if it's running
  try
    if FindWindowByClassName('{#MyAppName}') <> 0 then
    begin
      if MsgBox('The application is currently running. Close it?',
        mbConfirmation, MB_YESNO) = IDYES then
      begin
        if not Exec(ExpandConstant('{app}\{#MyAppExeName}'), '--quit', '', SW_SHOW, ewWaitUntilTerminated, ResultCode) then
        begin
          MsgBox('Failed to close the application. Please close it manually and try again.',
            mbError, MB_OK);
          Result := False;
        end;
      end
      else
        Result := False;
    end;
  except
    // Ignore errors and proceed with uninstall
  end;
end;
