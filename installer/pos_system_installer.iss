[Setup]
AppName=POS 360
AppVersion=1.0
DefaultDirName={autopf}\POS_360
DefaultGroupName=POS 360
OutputDir=dist
OutputBaseFilename=POS_360_Installer
Compression=lzma
SolidCompression=yes
; Uncomment the next line to use a custom icon
; SetupIconFile=..\mylogo.ico

[Files]
Source: "..\dist\pos_system.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\mylogo.png"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\mylogo.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\sales_history.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\settings.json"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\users.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\POS 360"; Filename: "{app}\pos_system.exe"
Name: "{group}\Uninstall POS 360"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\pos_system.exe"; Description: "Run POS 360"; Flags: nowait postinstall skipifsilent 