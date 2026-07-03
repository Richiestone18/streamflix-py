@echo off
REM Build Streamflix desktop app for Windows using PyInstaller
REM Output: dist\Streamflix.exe (single executable)
REM
REM Requirements: Python 3.10+, pip install pyinstaller
REM
REM Usage: build_windows.bat

echo === Building Streamflix for Windows ===

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

REM Build single-file executable (no console window)
echo Building executable...
pyinstaller ^
    --onefile ^
    --windowed ^
    --name Streamflix ^
    --add-data "app;app" ^
    --hidden-import cloudscraper ^
    --hidden-import bs4 ^
    --hidden-import lxml ^
    --hidden-import httpx ^
    --hidden-import uvicorn.logging ^
    --hidden-import uvicorn.loops ^
    --hidden-import uvicorn.loops.auto ^
    --hidden-import uvicorn.protocols ^
    --hidden-import uvicorn.protocols.http ^
    --hidden-import uvicorn.protocols.http.auto ^
    --hidden-import starlette ^
    --hidden-import fastapi ^
    app.py

echo.
echo === Build complete ===
echo Executable: dist\Streamflix.exe
echo Run with: dist\Streamflix.exe
echo Run fullscreen: dist\Streamflix.exe --fullscreen
pause