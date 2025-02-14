"""
Application path and directory management system. Handles data storage locations,
asset resolution, and Windows autostart configuration. Ensures proper directory
structure and file initialization for the application.
"""

import os
import sys
import winreg


def get_app_data_dir():
    """
    Gets the application's data directory in Windows AppData.
    Creates a WifeAlert subdirectory in the user's AppData/Roaming folder.

    Returns:
        str: Full path to application data directory
    """
    return os.path.join(os.getenv("APPDATA"), "WifeAlert")


def get_program_dir():
    """
    Gets the main program installation directory.
    Handles both development and frozen (packaged) environments.

    Returns:
        str: Path to program directory or executable location
    """
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(__file__))


def ensure_app_dirs():
    """
    Creates and initializes required application directories and files.
    Sets up directory structure in AppData:
    - data/: Configuration and settings files
    - assets/: Application resources
    - assets/profile_cache/: Cached Twitch profile images

    Creates empty JSON files if they don't exist:
    - settings.json: Application settings
    - streamers.json: Monitored streamers list
    - chat_login.json: Chat credentials

    Raises:
        SystemExit: If directory creation fails
    """
    try:
        app_data = get_app_data_dir()

        # Base application directory initialization
        if not os.path.exists(app_data):
            os.makedirs(app_data)

        # Resource and configuration subdirectories
        subdirs = ["data", "assets", os.path.join("assets", "profile_cache")]

        for subdir in subdirs:
            full_path = os.path.join(app_data, subdir)
            if not os.path.exists(full_path):
                os.makedirs(full_path)

        # Default configuration file initialization
        files_to_create = [
            ("settings.json", "{}"),
            ("streamers.json", "{}"),
            ("chat_login.json", "{}"),
        ]

        for filename, default_content in files_to_create:
            file_path = os.path.join(app_data, "data", filename)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    f.write(default_content)

    except Exception as e:
        # Critical error handling for directory creation failure
        from PyQt6.QtWidgets import QMessageBox

        QMessageBox.critical(
            None,
            "Error",
            f"Failed to create required directories in AppData.\n\n"
            f"Please try running as administrator for first launch.",
        )
        sys.exit(1)


def get_data_file(filename):
    """
    Resolves path for a data file in the application's data directory.

    Args:
        filename: Name of data file to locate

    Returns:
        str: Full path to requested data file
    """
    return os.path.join(get_app_data_dir(), "data", filename)


def get_asset_file(filename):
    """
    Resolves path for an asset file with fallback locations.
    Checks in order:
    1. AppData/assets/
    2. PyInstaller bundle
    3. Program directory

    Args:
        filename: Name of asset file to locate

    Returns:
        str: Full path to asset file or None if not found
    """
    appdata_path = os.path.join(get_app_data_dir(), "assets", filename)
    if os.path.exists(appdata_path):
        return appdata_path

    if getattr(sys, "_MEIPASS", None):
        bundle_path = os.path.join(sys._MEIPASS, "assets", filename)
        if os.path.exists(bundle_path):
            return bundle_path

    program_path = os.path.join(get_program_dir(), "assets", filename)
    if os.path.exists(program_path):
        return program_path

    return None


def set_autostart(enable: bool):
    """
    Configures Windows autostart registry entry.
    Adds or removes application from Windows startup.
    Only works in packaged (frozen) environment.

    Args:
        enable: True to enable autostart, False to disable
    """
    app_path = ""
    if getattr(sys, "frozen", False):
        app_path = f'"{sys.executable}"'
    else:
        return

    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS
        ) as key:
            if enable:
                winreg.SetValueEx(key, "WifeAlert", 0, winreg.REG_SZ, app_path)
            else:
                try:
                    winreg.DeleteValue(key, "WifeAlert")
                except WindowsError:
                    pass
    except Exception:
        pass


def check_autostart() -> bool:
    """
    Checks if application is configured to start with Windows.
    Verifies registry entry existence.

    Returns:
        bool: True if autostart is enabled
    """
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ
        ) as key:
            try:
                winreg.QueryValueEx(key, "WifeAlert")
                return True
            except WindowsError:
                return False
    except Exception:
        return False
