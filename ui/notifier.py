"""
System tray notification handler for WifeAlert. Manages desktop notifications,
custom sound effects, and system tray icon functionality. Provides visual and
audio alerts when streamers go live.
"""

import os
import asyncio
from pathlib import Path
from desktop_notifier import DesktopNotifier, Urgency
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu, QApplication, QStyle
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QSoundEffect, QMediaDevices
from utils.paths import get_asset_file


class WifeAlertNotifier(QSystemTrayIcon):
    """
    System tray icon with notification capabilities. Handles:
    - Desktop notifications when streamers go live
    - Custom sound effects per streamer
    - System tray menu and actions
    - Click-to-open stream functionality
    """

    def __init__(self, window, icon=None, parent=None):
        super().__init__(parent)
        self.window = window
        self.desktop_notifier = DesktopNotifier(
            app_name="WifeAlert", notification_limit=10
        )
        if icon:
            self.setIcon(icon)
        else:
            self.setIcon(
                QApplication.style().standardIcon(
                    QStyle.StandardPixmap.SP_MessageBoxInformation
                )
            )
        self.sound_effects = {}
        menu = QMenu()
        show_action = menu.addAction("Show")
        show_action.triggered.connect(self.window.show)
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        self.setContextMenu(menu)
        self.show()
        self.initialize_sound_effects()

    def initialize_sound_effects(self):
        """
        Sets up sound effects for all monitored streamers at startup.
        Loads custom sounds if configured, otherwise uses default alert sound.
        Checks audio device availability before initializing.
        """
        try:
            if not QMediaDevices.audioOutputs():
                return

            default_sound = get_asset_file("Alert.wav")
            for i in range(self.window.streamer_list.count()):
                item = self.window.streamer_list.item(i)
                widget = self.window.streamer_list.itemWidget(item)
                if (
                    hasattr(widget, "streamer_name")
                    and widget.sound_checkbox.isChecked()
                ):
                    sound_path = (
                        widget.sound_path if widget.sound_path else default_sound
                    )
                    if os.path.exists(sound_path):
                        if widget.streamer_name.lower() not in self.sound_effects:
                            sound_effect = QSoundEffect()
                            sound_effect.setSource(QUrl.fromLocalFile(sound_path))
                            sound_effect.setVolume(1.0)
                            self.sound_effects[widget.streamer_name.lower()] = (
                                sound_effect
                            )
        except Exception:
            pass

    async def notify(
        self,
        title: str,
        message: str,
        streamer_name: str = None,
        profile_image: str = None,
    ):
        """
        Shows a desktop notification with optional sound effect.

        Args:
            title: Notification title text
            message: Main notification message
            streamer_name: Name of streamer for custom sound/click handling
            profile_image: Path to streamer's profile image for notification

        Returns:
            bool: True if notification was sent successfully
        """
        try:
            if streamer_name:
                await self.play_streamer_sound(streamer_name)
                widget = None
                for i in range(self.window.streamer_list.count()):
                    item = self.window.streamer_list.item(i)
                    w = self.window.streamer_list.itemWidget(item)
                    if (
                        hasattr(w, "streamer_name")
                        and w.streamer_name.lower() == streamer_name.lower()
                    ):
                        widget = w
                        break
                    if widget and not widget.notify_checkbox.isChecked():
                        return False

            icon_path = (
                profile_image
                if profile_image and os.path.exists(profile_image)
                else None
            )
            if icon_path:
                icon_path = Path(icon_path)

            def open_stream():
                if streamer_name:
                    import webbrowser

                    stream_url = f"https://twitch.tv/{streamer_name}"
                    webbrowser.open(stream_url)

            await self.desktop_notifier.send(
                title=title,
                message=message,
                urgency=Urgency.Normal,
                icon=icon_path,
                on_clicked=open_stream,
            )
            return True
        except Exception:
            return False

    async def play_streamer_sound(self, streamer_name: str):
        """
        Plays notification sound for a specific streamer.
        Uses custom sound if configured, falls back to default alert.
        Handles sound effect lifecycle and volume control.

        Args:
            streamer_name: Name of streamer to play sound for
        """
        try:
            if self.window.suppress_sounds_checkbox.isChecked():
                return

            streamer_name = streamer_name.lower()
            widget = None
            for i in range(self.window.streamer_list.count()):
                item = self.window.streamer_list.item(i)
                w = self.window.streamer_list.itemWidget(item)
                if (
                    hasattr(w, "streamer_name")
                    and w.streamer_name.lower() == streamer_name
                ):
                    widget = w
                    break
            if not widget:
                return
            if not widget.sound_checkbox.isChecked():
                return
            default_sound = os.path.join(
                os.path.dirname(os.path.dirname(__file__)), "assets", "Alert.wav"
            )
            sound_path = widget.sound_path if widget.sound_path else default_sound
            if not os.path.exists(sound_path):
                return
            sound_effect = QSoundEffect()
            sound_effect.setSource(QUrl.fromLocalFile(sound_path))
            sound_effect.setVolume(1.0)
            if streamer_name in self.sound_effects:
                old_effect = self.sound_effects[streamer_name]
                old_effect.stop()
            self.sound_effects[streamer_name] = sound_effect
            sound_effect.play()
            await asyncio.sleep(0.1)
        except Exception:
            pass

    async def cleanup_sound_effects(self):
        """
        Properly disposes of all sound effects on shutdown.
        Stops any playing sounds and clears the effects cache
        to prevent resource leaks.
        """
        for sound in list(self.sound_effects.values()):
            try:
                sound.stop()
            except Exception:
                pass
        self.sound_effects.clear()

    def __del__(self):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(self.cleanup_sound_effects())

        if hasattr(self, "icon_path") and self.icon_path:
            try:
                os.remove(self.icon_path)
            except:
                pass
