"""
Error handling and user feedback system. Provides consistent error reporting
through message boxes and handles specific error cases for encryption,
authentication, and connection issues. Manages cleanup for corrupted states.
"""

from PyQt6.QtWidgets import QMessageBox
import os
from utils.paths import get_data_file


def show_error(parent, title, message):
    """
    Displays error message in a modal dialog box.

    Args:
        parent: Parent window for modal display
        title: Error dialog title
        message: Detailed error message
    """
    QMessageBox.critical(parent, title, message)


def handle_encryption_error(parent):
    """
    Handles corrupted encryption key files.
    Attempts to remove corrupted files and notifies user.
    Guides user through recovery process.

    Args:
        parent: Parent window for error dialog
    """
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
    """
    Handles invalid or nonexistent Twitch usernames.
    Provides user feedback for typos or deleted accounts.

    Args:
        parent: Parent window for error dialog
        username: Invalid username that caused error
    """
    show_error(
        parent,
        "Invalid Username",
        f"The streamer '{username}' could not be found. Please check the username and try again.",
    )


def handle_invalid_oauth(parent):
    """
    Handles invalid Twitch OAuth token errors.
    Guides user to token generation service.

    Args:
        parent: Parent window for error dialog
    """
    show_error(
        parent,
        "Authentication Error",
        "Invalid OAuth token. Please make sure you've entered a valid token from twitchtokengenerator.com",
    )


def handle_encryption_save_error(parent):
    """
    Handles failures in encryption key storage.
    Usually indicates permission issues in AppData.

    Args:
        parent: Parent window for error dialog
    """
    show_error(
        parent,
        "Security Error",
        "Failed to save encryption data. Please check if the application has write permissions in AppData.",
    )


def handle_encryption_operation_error(parent, operation="encrypt"):
    """
    Handles failures in encryption/decryption operations.
    Provides guidance for credential recovery.

    Args:
        parent: Parent window for error dialog
        operation: Type of operation that failed ('encrypt'/'decrypt'/'initialize')
    """
    show_error(
        parent,
        "Encryption Error",
        f"Failed to {operation} sensitive data. Your chat login information may need to be re-entered.",
    )


def handle_pubsub_connection_error(parent):
    """
    Handles Twitch PubSub connection failures.
    Usually indicates network or API issues.

    Args:
        parent: Parent window for error dialog
    """
    show_error(
        parent,
        "Connection Error",
        "Failed to connect to Twitch. Please check your internet connection and try again.",
    )


def handle_chat_connection_error(parent):
    """
    Handles Twitch chat connection failures.
    Could be due to invalid credentials or network issues.

    Args:
        parent: Parent window for error dialog
    """
    show_error(
        parent,
        "Chat Connection Error",
        "Failed to connect to Twitch chat. Please check your login information and try again.",
    )
