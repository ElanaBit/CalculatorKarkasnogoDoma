; Установщик «Калькулятор стоимости каркасного дома»
; Для сборки нужен Inno Setup 6 (https://jrsoftware.org/isdl.php)
; Запуск: build.bat или ISCC installer.iss

#define MyAppName "Калькулятор стоимости каркасного дома"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "КаркасДом"
#define MyAppExeName "КалькуляторКаркасногоДома.exe"

[Setup]
AppId={{0E74DE06-CB1A-4B2A-92EE-4B32E467D267}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\КалькуляторКаркасногоДома
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=Калькулятор_КаркасногоДома_Установка
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=app\app.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
MinVersion=10.0
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription=Приложение для расчёта стоимости каркасного дома
VersionInfoProductName={#MyAppName}

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Key = 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function IsWebView2Installed(): Boolean;
begin
  Result := RegKeyExists(HKLM, WebView2Key);
  if not Result then
    Result := RegKeyExists(HKCU, WebView2Key);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWebView2Installed() then
    if MsgBox('Для работы приложения требуется Microsoft Edge WebView2 Runtime.' + #13#10 +
              'Он обычно уже установлен на Windows 10/11.' + #13#10#13#10 +
              'Продолжить установку?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
end;
