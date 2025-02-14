import os
import sys
import winreg


def get_app_data_dir():
    """Get user-specific data directory in AppData"""
    return os.path.join(os.getenv("APPDATA"), "WifeAlert")


def get_program_dir():
    """Get program installation directory"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(__file__))


def ensure_app_dirs():
    """Create necessary application directories"""
    try:
        app_data = get_app_data_dir()
        
        # Create main directory first
        if not os.path.exists(app_data):
            os.makedirs(app_data)

        # Then create all subdirectories
        subdirs = [
            "data",
            "assets",
            os.path.join("assets", "profile_cache")
        ]

        for subdir in subdirs:
            full_path = os.path.join(app_data, subdir)
            if not os.path.exists(full_path):
                os.makedirs(full_path)

        # Create empty settings files if they don't exist
        files_to_create = [
            ("settings.json", "{}"),
            ("streamers.json", "{}"),
            ("chat_login.json", "{}")
        ]

        for filename, default_content in files_to_create:
            file_path = os.path.join(app_data, "data", filename)
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    f.write(default_content)

    except Exception as e:
        # If we can't create directories, something is seriously wrong
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.critical(None, "Error", 
            f"Failed to create required directories in AppData.\n\n"
            f"Please try running as administrator for first launch.")
        sys.exit(1)


def get_data_file(filename):
    """Get path for a data file"""
    return os.path.join(get_app_data_dir(), "data", filename)


def get_asset_file(filename):
    """Get path for an asset file, checking AppData first, then program directory"""
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
    """Set or remove autostart registry entry"""
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
    """Check if autostart is enabled"""
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
