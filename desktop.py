"""
GALACTOS - Desktop Mode
Opens the app in a Chrome/Edge app window (no browser UI).
"""

import threading
import time
import subprocess
import webbrowser
from app import app


def start_flask():
    """Run Flask server in a background thread."""
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)


if __name__ == '__main__':
    # Start Flask in background
    flask_thread = threading.Thread(target=start_flask, daemon=True)
    flask_thread.start()

    # Wait for Flask to start
    time.sleep(2)

    # Try Chrome/Edge app mode (looks like a desktop app)
    app_url = 'http://localhost:5000'
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]

    opened = False
    for path in chrome_paths:
        try:
            subprocess.Popen([path, '--app=' + app_url, '--window-size=1280,800', '--new-window'])
            opened = True
            break
        except FileNotFoundError:
            continue

    if not opened:
        # Fallback: open in default browser
        webbrowser.open(app_url)

    # Keep running until window is closed
    try:
        flask_thread.join()
    except KeyboardInterrupt:
        pass
