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
from utils.paths import ensure_app_dirs, get_asset_file


def main():
    if os.name == "nt":
        try:
            from ctypes import windll

            windll.shcore.SetProcessDpiAwareness(1)
        except:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("WifeAlert")

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

    window = MainWindow(monitor)
    window.setWindowIcon(app_icon)
    monitor.notification_manager = window.tray_icon
    window.show()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    def force_quit():
        try:
            monitor.should_run = False

            tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
            if tasks:
                for task in tasks:
                    task.cancel()

                loop.run_until_complete(asyncio.sleep(0.1))

                loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))

            if monitor.ws:
                loop.run_until_complete(monitor.ws.close())
                monitor.ws = None

            loop.run_until_complete(window.shutdown())

            window.tray_icon.hide()
            window.close()

            loop.stop()
            try:
                loop.close()
            except:
                pass

            sys.exit(0)
        except:
            os._exit(1)

    app.aboutToQuit.connect(force_quit)

    with loop:
        try:
            loop.run_forever()
        except:
            force_quit()


if __name__ == "__main__":
    main()
