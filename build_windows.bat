@echo off
REM Build Streamflix desktop app for Windows (DEBUG build with console)
REM Output: dist\Streamflix-Windows-DEBUG.exe
REM
REM Usage: build_windows.bat

echo === Building Streamflix for Windows (DEBUG) ===

REM Create venv if needed
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

REM Install dependencies
echo Installing dependencies...
pip install -q -r requirements-app.txt pyinstaller

REM Clean previous build
rmdir /s /q build dist 2>nul

REM Build DEBUG executable (with console for error output)
echo Building DEBUG executable...
pyinstaller Streamflix-Windows-Debug.spec --noconfirm

echo.
echo === Build complete ===
echo Executable: dist\Streamflix-Windows-DEBUG.exe
echo Run with: dist\Streamflix-Windows-DEBUG.exe
echo Run fullscreen: dist\Streamflix-Windows-DEBUG.exe --fullscreen
echo.
echo NOTE: This is a DEBUG build - a console window will appear
echo showing server logs and errors for troubleshooting.
pause
