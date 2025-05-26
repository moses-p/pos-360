@echo off
REM Build the POS system executable and installer

REM Step 1: Build the executable with PyInstaller
pyinstaller --noconfirm --onefile --windowed --add-data "..\mylogo.png;." --add-data "..\mylogo.ico;." --add-data "..\sales_history.json;." --add-data "..\settings.json;." --add-data "..\users.json;." ..\pos_system.py

REM Step 2: Compile the Inno Setup installer
where iscc >nul 2>nul
if %ERRORLEVEL%==0 (
    iscc pos_system_installer.iss
) else (
    if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" pos_system_installer.iss
    ) else (
        echo Inno Setup not found. Please install it from https://jrsoftware.org/isinfo.php and add to PATH.
        pause
        exit /b 1
    )
)

pause 