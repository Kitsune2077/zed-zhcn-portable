; Inno Setup script for the Zed zh-CN portable build.
;
; The app itself keeps all user data in `<install dir>\data` (see
; scripts/apply_portable_patch.py), so the installer defaults to a
; per-user directory that is always writable:
;   %LOCALAPPDATA%\Programs\Zed-zhCN
; Installing under Program Files would make `data\` unwritable and the app
; would silently fall back to %LOCALAPPDATA%\Zed, so this script requires
; the lowest privilege level and never elevates.
;
; All #define values below are supplied by installer/build-installer.ps1.

#ifndef ZedVersion
  #define ZedVersion "0.0.0"
#endif
#ifndef NumericVersion
  #define NumericVersion "0.0.0"
#endif
#ifndef SafeVersion
  #define SafeVersion ZedVersion
#endif
#ifndef SourceExe
  #define SourceExe "..\dist\zed.exe"
#endif
#ifndef SeedSettings
  #define SeedSettings "..\seed\settings-official.json"
#endif
#ifndef UsageFile
  #define UsageFile "..\seed\USAGE.txt"
#endif
#ifndef RepoRoot
  #define RepoRoot ".."
#endif
#ifndef OutputDir
  #define OutputDir "..\dist"
#endif
#ifndef SetupIcon
  #define SetupIcon ""
#endif

[Setup]
AppId={{7C4E9A2B-3F1D-4B8E-9C5A-2D6F8E1A4B73}
AppName=Zed 汉化便携版
AppVersion={#ZedVersion}
AppVerName=Zed 汉化便携版 {#ZedVersion}
AppPublisher=zed-zhcn-portable
AppPublisherURL=https://github.com/Kitsune2077/zed-zhcn-portable
AppSupportURL=https://github.com/Kitsune2077/zed-zhcn-portable/issues
AppUpdatesURL=https://github.com/Kitsune2077/zed-zhcn-portable/releases
DefaultDirName={autopf}\Zed-zhCN
DefaultGroupName=Zed 汉化便携版
DisableProgramGroupPage=yes
AllowNoIcons=yes
PrivilegesRequired=lowest
OutputDir={#OutputDir}
OutputBaseFilename=Zed-zhCN-{#SafeVersion}-setup-x64
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.16299
VersionInfoVersion={#NumericVersion}
VersionInfoDescription=Zed 汉化便携版 安装程序
VersionInfoProductName=Zed 汉化便携版
VersionInfoProductVersion={#NumericVersion}
UninstallDisplayIcon={app}\zed.exe
CloseApplications=yes
SetupLogging=yes

#if FileExists(SetupIcon)
SetupIconFile={#SetupIcon}
#endif

[Languages]
Name: "chinesesimplified"; MessagesFile: "{#RepoRoot}\installer\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "{#SourceExe}"; DestDir: "{app}"; DestName: "zed.exe"; Flags: ignoreversion
; First-run settings (zh-CN default). Never overwrite an existing config and
; never remove it on uninstall: that file belongs to the user once created.
Source: "{#SeedSettings}"; DestDir: "{app}\data\config"; DestName: "settings.json"; Flags: onlyifdoesntexist uninsneveruninstall
Source: "{#UsageFile}"; DestDir: "{app}"; DestName: "USAGE.txt"; Flags: ignoreversion
Source: "{#RepoRoot}\LICENSE"; DestDir: "{app}"; DestName: "LICENSE.txt"; Flags: ignoreversion

[Icons]
Name: "{group}\Zed 汉化便携版"; Filename: "{app}\zed.exe"
Name: "{autodesktop}\Zed 汉化便携版"; Filename: "{app}\zed.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\zed.exe"; Description: "{cm:LaunchProgram,Zed 汉化便携版}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{app}\data');
    if DirExists(DataDir) and not UninstallSilent then
    begin
      if MsgBox('是否删除 data 文件夹? / Delete the data folder?' + #13#10 + #13#10 +
                '其中包含全部配置、扩展、数据库和日志。' + #13#10 +
                'It contains all settings, extensions, databases and logs.' + #13#10 + #13#10 +
                '选择"否"将保留数据。 / Choose No to keep your data.',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
        DelTree(DataDir, True, True, True);
    end;
  end;
end;
