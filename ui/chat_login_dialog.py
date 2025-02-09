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
from utils.encryption import TokenEncryption
from utils.paths import get_data_file
from utils.error_handler import (
    handle_encryption_error,
    handle_encryption_operation_error,
    handle_encryption_save_error,
    show_error,
)


class ChatLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Twitch Chat Login")
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
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
