"""
Dialog window for Twitch chat authentication. Handles secure storage of login credentials
using encrypted OAuth tokens. Features a dark theme UI and persistent login state.
"""

import json
import os
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QLabel,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from utils.encryption import TokenEncryption
from utils.paths import get_data_file
from utils.error_handler import (
    handle_encryption_error,
    handle_encryption_operation_error,
    handle_encryption_save_error,
    show_error,
)


class ChatLoginDialog(QDialog):
    """
    A dialog window for managing Twitch chat credentials. Provides fields for username
    and OAuth token input, with secure encryption for token storage. Features:
    - Dark theme UI with custom styling
    - Automatic loading of saved credentials
    - Secure token encryption/decryption
    - Link to token generation website
    - Input validation and error handling
    """

    def __init__(self, parent=None):
        """
        Creates the login dialog with username and OAuth token fields.
        Loads any previously saved credentials and applies dark theme styling.
        Handles encryption setup and credential decryption if saved data exists.
        """
        super().__init__(parent)
        self.setWindowTitle("Twitch Chat Login")
        self.setFixedWidth(300)

        # Dark theme configuration
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        layout = QVBoxLayout(self)

        # Apply dark theme stylesheet
        self.setStyleSheet(
            """
            QWidget {
                color: white;
            }
            QLineEdit {
                color: white;
                background-color: rgb(60, 60, 60);
            }
            QPushButton {
                color: white;
                background-color: rgb(60, 60, 60);
            }
            QLabel {
                color: white;
            }
            QCheckBox {
                color: white;
            }
            QCheckBox::indicator {
                width: 13px;
                height: 13px;
                background-color: rgb(45, 45, 45);
                border: 1px solid rgb(60, 60, 60);
            }
            QCheckBox::indicator:checked {
                background-color: rgb(60, 60, 60);
            }
            QDialogButtonBox {
                background-color: transparent;
            }
            QDialogButtonBox QPushButton {
                color: white;
                background-color: rgb(60, 60, 60);
            }
            """
        )
        form = QFormLayout()
        self.username_input = QLineEdit()
        self.oauth_input = QLineEdit()
        self.oauth_input.setEchoMode(QLineEdit.EchoMode.Password)
        try:
            settings_path = get_data_file("chat_login.json")
            if os.path.exists(settings_path):
                with open(settings_path, "r") as f:
                    settings = json.load(f)
                    token_encryption = TokenEncryption()
                    if not token_encryption.cipher_suite:
                        handle_encryption_error(self)
                        return
                    self.username_input.setText(settings.get("username", ""))
                    if "oauth" in settings:
                        try:
                            decrypted_oauth = token_encryption.decrypt_token(
                                settings["oauth"]
                            )
                            if decrypted_oauth == settings["oauth"]:
                                handle_encryption_error(self)
                                return
                            self.oauth_input.setText(decrypted_oauth)
                        except Exception:
                            handle_encryption_error(self)
                            return
        except Exception:
            pass
        form.addRow("Username:", self.username_input)
        form.addRow("OAuth Token:", self.oauth_input)
        help_text = QLabel(
            'Get token: <a href="https://twitchtokengenerator.com/">twitchtokengenerator.com</a>'
        )
        help_text.setOpenExternalLinks(True)
        form.addRow("", help_text)
        layout.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self):
        """
        Processes the login form submission. Handles:
        - Input validation and OAuth token formatting
        - Token encryption for secure storage
        - Saving credentials to local settings file
        - Error handling for encryption and file operations
        """
        try:
            username = self.username_input.text().strip()
            oauth = self.oauth_input.text().strip()
            if not oauth.startswith("oauth:"):
                oauth = f"oauth:{oauth}"

            token_encryption = TokenEncryption()
            if not token_encryption.cipher_suite:
                from utils.error_handler import handle_encryption_operation_error

                handle_encryption_operation_error(self, "initialize")
                return

            encrypted_oauth = token_encryption.encrypt_token(oauth)
            if not encrypted_oauth or encrypted_oauth == oauth:
                from utils.error_handler import handle_encryption_operation_error

                handle_encryption_operation_error(self, "encrypt")
                return

            settings = {"username": username, "oauth": encrypted_oauth}
            settings_path = get_data_file("chat_login.json")
            os.makedirs(os.path.dirname(settings_path), exist_ok=True)

            try:
                with open(settings_path, "w") as f:
                    json.dump(settings, f, indent=4)
            except Exception:
                from utils.error_handler import handle_encryption_save_error

                handle_encryption_save_error(self)
                return


            super().accept()

        except Exception:
            from utils.error_handler import show_error

            show_error(self, "Error", "Failed to save chat login information")
