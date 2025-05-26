@echo off
REM === Full Automated Build Script for POS-360 ===
REM 1. Remove old virtual environment if it exists
if exist ..\.venv rmdir /s /q ..\.venv

REM 2. Create new virtual environment
python -m venv ..\.venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

REM 3. Activate the virtual environment
call ..\.venv\Scripts\activate.bat
if errorlevel 1 (
    echo Failed to activate virtual environment.
    pause
    exit /b 1
)

REM 4. Install dependencies
pip install --upgrade pip
pip install -r ..\requirements.txt
pip install pyinstaller
if errorlevel 1 (
    echo Failed to install dependencies.
    pause
    exit /b 1
)

REM 5. Build the executable with PyInstaller
pyinstaller --noconfirm --onefile --windowed --add-data "..\mylogo.png;." --add-data "..\mylogo.ico;." --add-data "..\sales_history.json;." --add-data "..\settings.json;." --add-data "..\users.json;." ..\pos_system.py
if errorlevel 1 (
    echo PyInstaller build failed.
    pause
    exit /b 1
)

REM 6. Build the installer with Inno Setup
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

@echo === Build Complete! ===
pause 