"""
Configuration dialog for setting up automated chat messages when a streamer goes live.
Features chat connection management, message timing controls, and dark theme styling.
Messages can be configured to send with delays between lines.
"""

import json
import os
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QLineEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator, QPalette, QColor
import asyncio
from utils.paths import get_data_file
from core.chat import TwitchChat
from utils.encryption import TokenEncryption
from ui.chat_login_dialog import ChatLoginDialog


class EmoteConfigDialog(QDialog):
    """
    Dialog for configuring automated Twitch chat messages. Features:
    - Chat connection testing
    - Multi-line message input
    - Message delay configuration
    - Initial delay before first message
    - Dark theme UI with custom styling
    - Persistent settings storage
    """

    def __init__(self, streamer_name, parent=None):
        super().__init__(parent)
        self.streamer_name = streamer_name
        self.setWindowTitle(f"Chat Message Setup - {streamer_name}")
        self.setFixedWidth(400)

        # Dark theme configuration for dialog
        palette = self.palette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        layout = QVBoxLayout(self)

        # Dark theme styles for UI components
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
            QTextEdit {
                color: white;
                background-color: rgb(45, 45, 45);
                border: 1px solid rgb(60, 60, 60);
                padding: 4px;
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
        chat_layout = QHBoxLayout()
        self.connect_btn = QPushButton("Connect to Chat")
        self.connect_btn.clicked.connect(self.toggle_chat_connection)
        self.status_label = QLabel("Not Connected")
        chat_layout.addWidget(self.connect_btn)
        chat_layout.addWidget(self.status_label)
        layout.addLayout(chat_layout)
        message_layout = QVBoxLayout()
        message_label = QLabel("Messages (one per line):")
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Enter messages...\nOne message per line")
        self.message_input.setMinimumHeight(120)
        message_layout.addWidget(message_label)
        message_layout.addWidget(self.message_input)
        timing_layout = QHBoxLayout()
        timing_layout.addWidget(QLabel("Message Delay (ms):"))
        self.msg_delay_input = QLineEdit()
        self.msg_delay_input.setPlaceholderText("1")
        self.msg_delay_input.setMaximumWidth(40)
        self.msg_delay_input.setValidator(QIntValidator(1, 60000))
        timing_layout.addWidget(self.msg_delay_input)
        timing_layout.addSpacing(20)
        timing_layout.addWidget(QLabel("Initial Delay (ms):"))
        self.initial_delay_input = QLineEdit()
        self.initial_delay_input.setPlaceholderText("0")
        self.initial_delay_input.setMaximumWidth(40)
        self.initial_delay_input.setValidator(QIntValidator(0, 60000))
        timing_layout.addWidget(self.initial_delay_input)
        timing_layout.addStretch()
        message_layout.addLayout(timing_layout)
        layout.addLayout(message_layout)
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        try:
            chat_settings_path = get_data_file("chat_login.json")
            if os.path.exists(chat_settings_path):
                self.connect_btn.setText("Disconnect")
                self.status_label.setText("Connected")
        except Exception:
            pass

    def toggle_chat_connection(self):
        """
        Manages Twitch chat connection state. When connecting:
        - Opens login dialog for credentials
        - Tests connection with provided details
        - Updates UI to reflect connection status
        When disconnecting, closes connection and resets UI state.
        """
        if self.connect_btn.text() == "Connect to Chat":
            dialog = ChatLoginDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                try:
                    settings_path = get_data_file("chat_login.json")
                    with open(settings_path, "r") as f:
                        settings = json.load(f)
                        token_encryption = TokenEncryption()
                        username = settings["username"]
                        oauth = token_encryption.decrypt_token(settings["oauth"])
                    chat = TwitchChat()

                    async def connect():
                        if await chat.ensure_connected(username, oauth):
                            self.connect_btn.setText("Disconnect")
                            self.status_label.setText("Connected")
                        else:
                            self.status_label.setText("Connection Failed")

                    asyncio.create_task(connect())
                except Exception as e:
                    self.status_label.setText("Connection Failed")
        else:
            try:
                chat = TwitchChat()
                chat.disconnect()
                self.connect_btn.setText("Connect to Chat")
                self.status_label.setText("Not Connected")
            except Exception:
                pass

    def accept(self):
        """
        Saves chat message configuration when dialog is accepted.
        Stores message content, delays, and enabled state to JSON file.
        Creates necessary directories if they don't exist.
        """
        try:
            emote_settings_path = get_data_file("emote_settings.json")
            if not os.path.exists(emote_settings_path):
                emote_settings = {}
            else:
                with open(emote_settings_path, "r") as f:
                    emote_settings = json.load(f)
            emote_settings[self.streamer_name] = {
                "enabled": True,
                "message": self.message_input.toPlainText(),
                "message_delay": int(self.msg_delay_input.text() or "1"),
                "initial_delay": int(self.initial_delay_input.text() or "0"),
            }
            os.makedirs(os.path.dirname(emote_settings_path), exist_ok=True)
            with open(emote_settings_path, "w") as f:
                json.dump(emote_settings, f, indent=4)
            super().accept()
        except Exception:
            pass
