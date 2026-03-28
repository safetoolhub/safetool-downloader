; SafeTool Downloader Inno Setup Script
; Copyright (C) 2026 safetoolhub.org
; License: GPL-3.0-or-later
;
; Build with:
;   iscc packaging\windows\safetool-downloader.iss
;
; Environment variables used (set by build.py / GitHub Actions):
;   APP_VERSION       - e.g. "0.1.0"
;   APP_FULL_VERSION  - e.g. "0.1.0-beta"

#ifndef APP_VERSION
  #define APP_VERSION GetEnv("APP_VERSION")
#endif
#ifndef APP_FULL_VERSION
  #define APP_FULL_VERSION GetEnv("APP_FULL_VERSION")
#endif
; Fallback to APP_VERSION when FULL_VERSION is not set
#if APP_FULL_VERSION == ""
  #define APP_FULL_VERSION APP_VERSION
#endif

#define AppName    "SafeTool Downloader"
#define AppPublisher "SafeToolHub"
#define AppURL     "https://safetoolhub.org"
#define AppExeName "safetool-downloader-desktop.exe"

; Paths relative to this script (which lives in packaging/windows/)
#define RootDir    "..\.."
#define SourceDir  "..\..\dist\safetool-downloader"
#define OutputDir  "..\..\dist"
#define OutputFile "SafeToolDownloader-" + APP_FULL_VERSION + "-windows-setup"

[Setup]
AppId={{B8F2G4C3-5E7D-4F9B-A10C-2D3E4F5G6H7I}
AppName={#AppName}
AppVersion={#APP_VERSION}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile={#RootDir}\LICENSE
OutputDir={#OutputDir}
OutputBaseFilename={#OutputFile}
SetupIconFile={#RootDir}\assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Bundle all PyInstaller output (exe + _internal/ with libs and data)
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(AppName,'&','&&')}}"; Flags: nowait postinstall skipifsilent
