from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QCheckBox,
    QApplication,
    QFileDialog,
    QDialog,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QIcon
from utils.paths import get_asset_file, get_data_file
from ui.emote_config_dialog import EmoteConfigDialog
import json
import os


class StreamerListItem(QWidget):
    def __init__(self, streamer_name, sound_path=None, parent=None):
        super().__init__(parent)
        self.streamer_name = streamer_name
        self.sound_path = sound_path
        self._sound_effect = None
        self._handling_shift_click = False
        self.mod_view = False
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(8)

        self.live_indicator = QLabel("●")
        self.live_indicator.setFixedWidth(15)
        self.live_indicator.setStyleSheet(
            "color: rgba(255, 255, 255, 0); font-size: 18px;"
        )
        layout.addWidget(self.live_indicator)

        self.name_label = QLabel(streamer_name)
        self.name_label.setFixedWidth(110)
        self.name_label.setStyleSheet("color: white;")

        metrics = self.name_label.fontMetrics()
        elided_text = metrics.elidedText(
            streamer_name, Qt.TextElideMode.ElideRight, 160
        )
        self.name_label.setText(elided_text)
        self.name_label.setToolTip(streamer_name)
        layout.addWidget(self.name_label)
        layout.addSpacing(15)
        self.notify_checkbox = QCheckBox()
        self.notify_checkbox.setFixedWidth(35)
        self.notify_checkbox.setChecked(True)
        self.notify_checkbox.setToolTip("Enable desktop notifications")
        layout.addWidget(self.notify_checkbox)
        self.sound_checkbox = QCheckBox()
        self.sound_checkbox.setFixedWidth(35)
        self.sound_checkbox.setChecked(sound_path is not None)
        self.sound_checkbox.setToolTip(
            "Notification Sound\nShift+Click to select WAV file"
        )
        self.sound_checkbox.toggled.connect(self.toggle_sound)
        layout.addWidget(self.sound_checkbox)
        self.open_checkbox = QCheckBox()
        self.open_checkbox.setFixedWidth(35)
        self.open_checkbox.setToolTip("Automatically open\nShift+Click for mod view")
        self.open_checkbox.toggled.connect(self.toggle_open)
        layout.addWidget(self.open_checkbox)
        self.emote_checkbox = QCheckBox()
        self.emote_checkbox.setFixedWidth(35)
        self.emote_checkbox.setToolTip(
            "Send chat message\nShift+Click to configure message and settings"
        )
        self.emote_checkbox.toggled.connect(self.toggle_emote)
        layout.addWidget(self.emote_checkbox)
        layout.addStretch()
        self.setLayout(layout)

    def set_live_status(self, is_live: bool):
        if is_live:
            self.live_indicator.setStyleSheet("color: #FF0000; font-size: 18px;")
        else:
            self.live_indicator.setStyleSheet(
                "color: rgba(255, 255, 255, 0); font-size: 18px;"
            )

    def toggle_sound(self, checked):
        if self._handling_shift_click:
            return

        modifiers = QApplication.keyboardModifiers()
        shift_pressed = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)

        if shift_pressed:
            self._handling_shift_click = True
            self.sound_checkbox.setChecked(not checked)
            self._handling_shift_click = False

            file_name, _ = QFileDialog.getOpenFileName(
                self, "Select Sound File", "", "Sound Files (*.wav)"
            )
            if file_name:
                try:
                    self.sound_path = file_name
                    self.sound_checkbox.setChecked(True)

                    main_window = self.window()
                    if main_window.__class__.__name__ == "MainWindow":
                        if hasattr(main_window.tray_icon, "initialize_sound_effects"):
                            main_window.tray_icon.initialize_sound_effects()
                except Exception:
                    self.sound_path = None
        else:
            if checked:
                default_sound = get_asset_file("Alert.wav")
                if os.path.exists(default_sound):
                    self.sound_path = None
                else:
                    self.sound_checkbox.setChecked(False)
                    self.sound_path = None
            else:
                self.sound_path = None

            main_window = self.window()
            if main_window.__class__.__name__ == "MainWindow":
                main_window.save_settings()
                if hasattr(main_window.tray_icon, "initialize_sound_effects"):
                    main_window.tray_icon.initialize_sound_effects()

    def toggle_emote(self, checked):
        if self._handling_shift_click:
            return
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._handling_shift_click = True
            self.emote_checkbox.setChecked(not checked)
            self._handling_shift_click = False
            dialog = EmoteConfigDialog(self.streamer_name, self)
            try:
                emote_settings_path = get_data_file("emote_settings.json")
                if os.path.exists(emote_settings_path):
                    with open(emote_settings_path, "r") as f:
                        emote_settings = json.load(f)
                        streamer_settings = emote_settings.get(self.streamer_name, {})
                        dialog.message_input.setPlainText(
                            streamer_settings.get("message", "")
                        )
                        dialog.msg_delay_input.setText(
                            str(streamer_settings.get("message_delay", 500))
                        )
                        dialog.initial_delay_input.setText(
                            str(streamer_settings.get("initial_delay", 0))
                        )
            except Exception:
                pass

            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.emote_checkbox.setChecked(True)
                try:
                    emote_settings_path = get_data_file("emote_settings.json")
                    if not os.path.exists(emote_settings_path):
                        emote_settings = {}
                    else:
                        with open(emote_settings_path, "r") as f:
                            emote_settings = json.load(f)
                    emote_settings[self.streamer_name] = {
                        "enabled": True,
                        "message": dialog.message_input.toPlainText().strip(),
                        "message_delay": int(dialog.msg_delay_input.text() or "500"),
                        "initial_delay": int(dialog.initial_delay_input.text() or "0"),
                    }
                    os.makedirs(os.path.dirname(emote_settings_path), exist_ok=True)
                    with open(emote_settings_path, "w") as f:
                        json.dump(emote_settings, f, indent=4)
                except Exception:
                    pass
        else:
            try:
                emote_settings_path = get_data_file("emote_settings.json")
                if os.path.exists(emote_settings_path):
                    with open(emote_settings_path, "r") as f:
                        emote_settings = json.load(f)
                    if self.streamer_name in emote_settings:
                        emote_settings[self.streamer_name]["enabled"] = checked
                        with open(emote_settings_path, "w") as f:
                            json.dump(emote_settings, f, indent=4)
            except Exception:
                pass

    def toggle_open(self, checked):
        if self._handling_shift_click:
            return
        modifiers = QApplication.keyboardModifiers()
        shift_pressed = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        if shift_pressed:
            self._handling_shift_click = True
            self.mod_view = True
            self.open_checkbox.setToolTip(
                "Automatically open\nShift+Click for mod view"
            )
            self._handling_shift_click = False
        else:
            self.mod_view = False
            self.open_checkbox.setToolTip(
                "Automatically open\nShift+Click for mod view"
            )
        main_window = self.window()
        if main_window.__class__.__name__ == "MainWindow":
            main_window.save_settings()
