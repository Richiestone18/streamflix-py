# PyInstaller spec file for building Streamflix Windows DEBUG executable
# This build has a console window for debugging output.
# Usage: pyinstaller Streamflix-Windows-Debug.spec

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

datas = [
    ('app/', 'app'),
]

hiddenimports = [
    'cloudscraper',
    'bs4',
    'lxml',
    'httpx',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'starlette',
    'fastapi',
    'pywebview',
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='Streamflix-Windows-DEBUG',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # DEBUG: show console window for error output
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
