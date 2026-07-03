#!/bin/bash
# Build Streamflix desktop app for Linux using PyInstaller
# Output: dist/Streamflix (single executable)
#
# Requirements:
#   pip install pyinstaller
#
# Usage: ./build_linux.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Building Streamflix for Linux ==="

# Ensure venv is active
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d ".venv" ]; then
        source .venv/bin/activate
    else
        echo "Creating virtual environment..."
        python3 -m venv .venv
        source .venv/bin/activate
    fi
fi

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements-app.txt pyinstaller

# Clean previous build
rm -rf build dist *.spec

# Build single-file executable
echo "Building executable..."
pyinstaller \
    --onefile \
    --windowed \
    --name Streamflix \
    --add-data "app:app" \
    --hidden-import cloudscraper \
    --hidden-import bs4 \
    --hidden-import lxml \
    --hidden-import httpx \
    --hidden-import uvicorn.logging \
    --hidden-import uvicorn.loops \
    --hidden-import uvicorn.loops.auto \
    --hidden-import uvicorn.protocols \
    --hidden-import uvicorn.protocols.http \
    --hidden-import uvicorn.protocols.http.auto \
    --hidden-import starlette \
    --hidden-import fastapi \
    app.py

echo ""
echo "=== Build complete ==="
echo "Executable: $(readlink -f dist/Streamflix)"
echo "Run with: ./dist/Streamflix"
echo "Run fullscreen: ./dist/Streamflix --fullscreen"