; student_setup.iss — Inno Setup конфигурация для сборки EXE-инсталлятора клиента студента

[Setup]
AppName=EduTest Pro - Студент
AppVersion=1.0
AppPublisher=EduTest
DefaultDirName={autopf}\EduTestStudent
DefaultGroupName=EduTest Pro
OutputDir=..\dist
OutputBaseFilename=EduTestStudent_Setup
;SetupIconFile=..\Gemini_Generated_Image_xjemh4xjemh4xjem.png
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
WizardStyle=modern
DisableProgramGroupPage=yes

[Files]
; Скомпилированный Nuitka-бинарник (onefile)
Source: "..\dist\student\edutest-student.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Ярлык на Рабочем столе
Name: "{userdesktop}\EduTest Pro - Студент"; Filename: "{app}\edutest-student.exe"; WorkingDir: "{app}"
; Ярлык в меню Пуск
Name: "{group}\EduTest Pro - Студент"; Filename: "{app}\edutest-student.exe"; WorkingDir: "{app}"
Name: "{group}\Удалить EduTest Pro"; Filename: "{uninstallexe}"

[Run]
; Запустить приложение после установки
Filename: "{app}\edutest-student.exe"; Description: "Запустить EduTest Pro"; Flags: nowait postinstall skipifsilent
