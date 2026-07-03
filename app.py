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


def find_free_port():
    """Find a free port to run the server on."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def run_server(port: int):
    """Start the FastAPI server in a background thread."""
    import uvicorn
    # Change dir to the app directory so imports work
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    uvicorn.run(
        "app.server:app",
        host="127.0.0.1",
        port=port,
        log_level="warning",
        access_log=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Streamflix Desktop App")
    parser.add_argument("--port", type=int, default=0, help="Server port (0=auto)")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen mode")
    args = parser.parse_args()

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
        sys.exit(1)

    print(f"Server ready at {url}")
    print(f"Opening desktop window...")

    # Open native window with pywebview
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
        gui=None,  # Auto-detect: 'gtk' on Linux, 'edgechromium'/'cef' on Windows, 'cocoa' on macOS
    )


if __name__ == "__main__":
    main()