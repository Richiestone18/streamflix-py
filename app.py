#!/usr/bin/env python3
"""
Streamflix Desktop App
Cross-platform desktop app (Windows, Linux, macOS) using pywebview.
Launches the FastAPI server in a thread and wraps the UI in a native window.
"""
import sys
import os
import threading
import time
import socket
import argparse


def get_app_path():
    """Get the path to the app directory, works both in dev and PyInstaller."""
    if getattr(sys, '_MEIPASS', None):
        # PyInstaller: files are extracted to sys._MEIPASS
        return sys._MEIPASS
    # Dev mode: use the directory of this file
    return os.path.dirname(os.path.abspath(__file__))


def setup_paths():
    """Add the app path to sys.path so imports work."""
    app_path = get_app_path()
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    # Change working directory so relative paths work
    os.chdir(app_path)


def find_free_port():
    """Find a free port to run the server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_server(port: int):
    """Start the FastAPI server in a background thread."""
    try:
        # Import here so paths are set up first
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


def main():
    parser = argparse.ArgumentParser(description="Streamflix Desktop App")
    parser.add_argument("--port", type=int, default=0, help="Server port (0=auto)")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    args = parser.parse_args()

    # Set up paths for PyInstaller
    setup_paths()

    # Find free port
    port = args.port or find_free_port()

    # Start FastAPI server in background
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
    print(f"Opening desktop window...")

    # Open native window with pywebview
    try:
        import webview

        window = webview.create_window(
            title="Streamflix",
            url=f"http://127.0.0.1:{port}/browse",
            width=1280,
            height=800,
            min_size=(800, 600),
            resizable=True,
            fullscreen=args.fullscreen,
            easy_drag=False,
        )

        webview.start(
            debug=False,
            gui=None,  # Auto-detect: 'gtk' on Linux, 'edgechromium' on Windows, 'cocoa' on macOS
        )
    except Exception as e:
        print(f"Window error: {e}")
        import traceback
        traceback.print_exc()
        # Fallback: open in browser
        import webbrowser
        print("Falling back to web browser...")
        webbrowser.open(url)
        print(f"The app is running at {url}")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()