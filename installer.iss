; Скрипт создания инсталлятора Inno Setup для настольного приложения «Рейс-Проверка»
; Поддерживаемая целевая платформа: Windows 10/11 (64-bit)
; Установка выполняется строго без прав администратора (Non-Admin / Per-User Install)

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
; Уникальный идентификатор приложения (GUID)
AppId={{C182A43B-91E5-46D9-8F8D-D500C5F9D8D2}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Установка строго без повышения прав (в профиль текущего пользователя)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
DefaultDirName={autopf}\{#MyAppEnglishName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes

; Целевая платформа — только 64-битные версии Windows
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Директории и имена выходных файлов
OutputDir=dist_installer
OutputBaseFilename=freight-check-setup-v{#MyAppVersion}-x64
SetupIconFile=assets\icons\app_icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

; Алгоритм сжатия инсталлятора
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Закрытие запущенных копий приложения перед установкой/обновлением
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
; Очистка временных и пользовательских кэшей при удалении программы
Type: filesandordirs; Name: "{localappdata}\{#MyAppEnglishName}"
Type: filesandordirs; Name: "{localappdata}\Temp\freight-check*"
