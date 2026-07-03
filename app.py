#!/usr/bin/env python3
"""
Streamflix Desktop App
Cross-platform desktop app using pywebview with browser fallback.
Tries native window first; if pywebview fails, opens in web browser.
"""
import sys
import os
import threading
import time
import socket
import argparse
import webbrowser


def get_app_path():
    """Get the path to the app directory, works both in dev and PyInstaller."""
    if getattr(sys, '_MEIPASS', None):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def setup_paths():
    """Add the app path to sys.path so imports work."""
    app_path = get_app_path()
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    os.chdir(app_path)


def find_free_port():
    """Find a free port to run the server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_server(port: int):
    """Start the FastAPI server in a background thread."""
    try:
        from app.server import app
        import uvicorn
        uvicorn.run(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            access_log=False,
        )
    except Exception as e:
        print(f"Server error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def try_pywebview(url: str, fullscreen: bool = False) -> bool:
    """Try to open pywebview window. Returns True if successful."""
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
    args = parser.parse_args()

    setup_paths()
    port = args.port or find_free_port()

    print(f"Starting server on port {port}...")
    server_thread = threading.Thread(target=run_server, args=(port,), daemon=True)
    server_thread.start()

    # Wait for server to be ready
    import urllib.request
    url = f"http://127.0.0.1:{port}/"
    for i in range(30):
        try:
            urllib.request.urlopen(url, timeout=1)
            break
        except Exception:
            time.sleep(0.5)
    else:
        print("ERROR: Server failed to start")
        input("Press Enter to exit...")
        sys.exit(1)

    print(f"Server ready at {url}")

    # Try pywebview first (unless --browser flag)
    if not args.browser:
        if try_pywebview(f"http://127.0.0.1:{port}/browse", args.fullscreen):
            return

    # Fallback: open in web browser
    print("Opening in web browser...")
    webbrowser.open(f"http://127.0.0.1:{port}/browse")
    print(f"Streamflix is running at {url}")
    print("Close this window to stop the server.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()