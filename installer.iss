; Inno Setup Script: Рейс-Проверка

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

#ifndef MyAppPublisher
  #define MyAppPublisher "Alexander Lebedev, Egor Hotenov"
#endif

#define MyAppName "Рейс-Проверка"
#define MyAppEnglishName "FreightCheck"
#define MyAppURL "https://github.com/lebalexevg/freight-check"
#define MyAppExeName "freight-check.exe"
#define SourceDistDir "dist\freight-check"

[Setup]
AppId={{C182A43B-91E5-46D9-8F8D-D500C5F9D8D2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#MyAppEnglishName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

OutputDir=dist_installer
OutputBaseFilename=freight-check-setup-v{#MyAppVersion}-x64
SetupIconFile=assets\icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

CloseApplications=yes
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceDistDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\{#MyAppEnglishName}"
Type: filesandordirs; Name: "{localappdata}\Temp\freight-check*"
