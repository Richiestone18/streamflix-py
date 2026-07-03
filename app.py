#!/usr/bin/env python3
"""
Streamflix Desktop App
Launches FastAPI server and opens the UI.
- Tries pywebview native window first
- Falls back to web browser in app mode (no address bar, looks like desktop app)
- Use --browser to force browser mode
- Use --fullscreen for fullscreen/kiosk mode
"""
import sys
import os
import threading
import time
import socket
import argparse
import subprocess
import shutil


def get_app_path():
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def setup_paths():
    app_path = get_app_path()
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    os.chdir(app_path)


def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_server(port: int):
    try:
        from app.server import app
        import uvicorn
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def open_browser_app(url: str, fullscreen: bool = False):
    """Open URL in browser app mode (looks like a desktop app, no address bar).
    Priority: Brave > Chrome > Edge > Firefox > default browser.
    App mode = no address bar, no tabs, looks like a native window.
    """
    args = ['--app=' + url, '--new-window']
    if fullscreen:
        args.append('--start-fullscreen')

    # Try browsers in order of preference (app mode support)
    browsers = []
    
    # Windows
    if sys.platform == 'win32':
        # Brave (first priority - has built-in adblock)
        for p in [
            os.path.expandvars(r'%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe'),
            r'C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe',
            r'C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe',
        ]:
            if os.path.exists(p):
                browsers.append((p, args))
                break
        # Chrome
        for p in [
            os.path.expandvars(r'%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe'),
            r'C:\Program Files\Google\Chrome\Application\chrome.exe',
            r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
        ]:
            if os.path.exists(p):
                browsers.append((p, args))
                break
        # Edge (comes with Windows 10/11)
        for p in [
            os.path.expandvars(r'%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe'),
            r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
            r'C:\Program Files\Microsoft\Edge\Application\msedge.exe',
        ]:
            if os.path.exists(p):
                browsers.append((p, args))
                break
    else:
        # Linux/Mac
        for name in ['brave-browser', 'google-chrome', 'chromium-browser', 'firefox', 'microsoft-edge']:
            path = shutil.which(name)
            if path:
                browsers.append((path, args))

    # Try each browser
    for exe, browser_args in browsers:
        try:
            subprocess.Popen([exe] + browser_args)
            print(f"Opened in: {exe}")
            return True
        except Exception:
            continue

    # Last resort: default browser (no app mode)
    import webbrowser
    webbrowser.open(url)
    print("Opened in default browser")
    return True


def try_pywebview(url: str, fullscreen: bool = False) -> bool:
    """Try to open pywebview native window. Returns True if successful."""
    try:
        import webview
        window = webview.create_window(
            title="Streamflix",
            url=url,
            width=1280,
            height=800,
            min_size=(800, 600),
            resizable=True,
            fullscreen=fullscreen,
            easy_drag=False,
        )
        webview.start(debug=False, gui=None)
        return True
    except Exception as e:
        print(f"pywebview failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Streamflix Desktop App")
    parser.add_argument("--port", type=int, default=0, help="Server port (0=auto)")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    parser.add_argument("--browser", action="store_true", help="Force web browser mode")
    parser.add_argument("--pywebview", action="store_true", help="Force pywebview mode")
    args = parser.parse_args()

    setup_paths()
    port = args.port or find_free_port()

    print(f"Starting server on port {port}...")
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server
    import urllib.request
    url_base = f"http://127.0.0.1:{port}/"
    browse_url = f"http://127.0.0.1:{port}/browse"
    for i in range(30):
        try:
            urllib.request.urlopen(url_base, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        print("ERROR: Server failed to start")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"Server ready at {url_base}")

    # Mode selection
    if args.pywebview:
        # Force pywebview
        try_pywebview(browse_url, args.fullscreen)
    elif args.browser:
        # Force browser
        open_browser_app(browse_url, args.fullscreen)
    else:
        # Auto: try pywebview first, fallback to browser
        # On Windows, go straight to browser app mode (more reliable)
        if sys.platform == 'win32':
            open_browser_app(browse_url, args.fullscreen)
        else:
            if not try_pywebview(browse_url, args.fullscreen):
                open_browser_app(browse_url, args.fullscreen)

    # Keep the server running
    print("Streamflix is running. Close this window to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()