"""
WifeAlert's main application file that brings everything together. Handles the core setup like
Windows DPI scaling, dark mode theming, and system tray integration. Also manages the event loop
for Twitch monitoring and makes sure everything runs smoothly.
"""

import sys
import asyncio
import qasync
import os
import ctypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from config import Config
from core.wife_alert_monitor import WifeAlertMonitor
from ui.main_window import MainWindow
from utils.paths import ensure_app_dirs, get_asset_file, get_data_file
import json


def main():
    """
    Main application entry point that initializes all core components. Sets up SSL certificates
    for Twitch API communication, configures Windows-specific display settings for proper scaling
    and dark mode, and creates the main monitoring interface. Also handles the async event loop
    that powers the real-time Twitch monitoring system.
    """
    # Set up SSL certificate path for packaged app
    import certifi
    import os

    if getattr(sys, "frozen", False):
        os.environ["SSL_CERT_FILE"] = os.path.join(sys._MEIPASS, "cacert.pem")
        os.environ["REQUESTS_CA_BUNDLE"] = os.path.join(sys._MEIPASS, "cacert.pem")
    else:
        os.environ["SSL_CERT_FILE"] = certifi.where()
        os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

    import time

    start_time = time.time()

    if os.name == "nt":
        try:
            from ctypes import windll

            # Try SetProcessDpiAwareness first (Windows 8.1+)
            try:
                windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
            except AttributeError:
                # Fall back to older SetProcessDPIAware (Windows Vista through 8)
                windll.user32.SetProcessDPIAware()
        except:
            # If both DPI awareness attempts fail, continue without DPI awareness
            pass

    print(f"DPI setup took: {time.time() - start_time:.2f}s")
    qt_start = time.time()

    app = QApplication(sys.argv)

    
    if os.name == "nt":
        try:
            from ctypes import windll, byref, sizeof, c_int

            DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            windll.dwmapi.DwmSetWindowAttribute(
                int(app.winId()),
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                byref(c_int(2)),
                sizeof(c_int),
            )
        except:
            pass

    app.setApplicationName("WifeAlert")

    print(f"QT init took: {time.time() - qt_start:.2f}s")
    setup_start = time.time()

    ensure_app_dirs()

    icon_path = get_asset_file("icon.png")
    app_icon = QIcon(icon_path)
    app.setWindowIcon(app_icon)
    QApplication.setWindowIcon(app_icon)

    if os.name == "nt":
        myappid = "nazarein.wifealert.1.0"
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

    monitor = WifeAlertMonitor(Config.CLIENT_ID, [])

    # Check suppress status before creating window
    settings_path = get_data_file("settings.json")
    try:
        if os.path.exists(settings_path):
            with open(settings_path, "r") as f:
                settings = json.load(f)
                monitor.suppress_actions = settings.get("suppress_notifications", False)
    except Exception:
        pass

    window = MainWindow(monitor)
    window.setWindowIcon(app_icon)
    monitor.notification_manager = window.tray_icon
    window.show()

    print(f"App setup took: {time.time() - setup_start:.2f}s")

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    def force_quit():
        """
        Handles graceful application shutdown by cleaning up all running processes.
        Stops active monitoring, cancels pending tasks, closes open websocket
        connections, and properly disposes of UI elements before exiting.
        Prevents any orphaned processes or connections from persisting.
        """
        try:
            # First stop the monitor to prevent new tasks
            monitor.should_run = False

            # Cancel all running tasks
            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if tasks:
                # Cancel all tasks simultaneously
                for task in tasks:
                    if not task.done():
                        task.cancel()

                # Wait briefly for tasks to acknowledge cancellation
                loop.call_soon(asyncio.gather, *tasks, return_exceptions=True)
                loop.run_until_complete(asyncio.sleep(0.1))

            # Close websocket if it exists
            if monitor.ws:
                loop.call_soon(monitor.ws.close)
                monitor.ws = None

            # Shutdown window
            loop.call_soon(window.shutdown)
            window.tray_icon.hide()
            window.close()

            # Stop event loop
            loop.stop()

            # Exit cleanly
            sys.exit(0)
        except:
            sys.exit(1)  # Use sys.exit instead of os._exit for proper cleanup

    app.aboutToQuit.connect(force_quit)

    with loop:
        try:
            loop.run_forever()
        except:
            force_quit()


if __name__ == "__main__":
    main()
