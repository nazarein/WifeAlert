from PyQt6.QtWidgets import QMessageBox
import os
from utils.paths import get_data_file


def show_error(parent, title, message):
    """Show an error message box"""
    QMessageBox.critical(parent, title, message)


def handle_encryption_error(parent):
    """Handle corrupted encryption files"""
    key_file = get_data_file(".encryption_key")
    salt_file = get_data_file(".salt")

    try:
        if os.path.exists(key_file):
            os.remove(key_file)
        if os.path.exists(salt_file):
            os.remove(salt_file)
    except:
        show_error(
            parent,
            "Critical Error",
            "Failed to remove corrupted encryption files. You may need to delete them manually.",
        )
        return

    show_error(
        parent,
        "Encryption Error",
        "Encryption files were corrupted and have been reset. You will need to re-enter your chat login information.",
    )


def handle_streamer_not_found(parent, username):
    """Handle invalid/not found streamer username"""
    show_error(
        parent,
        "Invalid Username",
        f"The streamer '{username}' could not be found. Please check the username and try again.",
    )


def handle_invalid_oauth(parent):
    """Handle invalid OAuth token"""
    show_error(
        parent,
        "Authentication Error",
        "Invalid OAuth token. Please make sure you've entered a valid token from twitchtokengenerator.com",
    )


def handle_encryption_save_error(parent):
    """Handle failures in saving encryption keys"""
    show_error(
        parent,
        "Security Error",
        "Failed to save encryption data. Please check if the application has write permissions in AppData.",
    )


def handle_encryption_operation_error(parent, operation="encrypt"):
    """Handle encryption/decryption operation failures"""
    show_error(
        parent,
        "Encryption Error",
        f"Failed to {operation} sensitive data. Your chat login information may need to be re-entered.",
    )


def handle_pubsub_connection_error(parent):
    """Handle PubSub connection failures"""
    show_error(
        parent,
        "Connection Error",
        "Failed to connect to Twitch. Please check your internet connection and try again.",
    )


def handle_chat_connection_error(parent):
    """Handle failures in connecting to Twitch chat"""
    show_error(
        parent,
        "Chat Connection Error",
        "Failed to connect to Twitch chat. Please check your login information and try again.",
    )
