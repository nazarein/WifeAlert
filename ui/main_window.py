import json
import os
import asyncio
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
    QLabel,
    QSystemTrayIcon,
)
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize
from PyQt6.QtGui import QIcon
from core.wife_alert_monitor import WifeAlertMonitor
from core.pubsub import Topic, PubSubRequest
from config import Config
from utils.paths import get_data_file, get_asset_file
from utils.error_handler import handle_streamer_not_found
from ui.notifier import WifeAlertNotifier
from ui.emote_config_dialog import EmoteConfigDialog
from ui.chat_login_dialog import ChatLoginDialog
from ui.streamer_list_item import StreamerListItem


class MainWindow(QMainWindow):
    def __init__(self, monitor=None):
        super().__init__()
        self.monitor = monitor
        self.setWindowTitle("WifeAlert")
        self.setMinimumSize(300, 400)
        self.setFixedWidth(365)
        self._should_start_monitoring = True
        self.dragging = False
        self.drag_position = None
        self.setup_ui()
        self.load_streamers()
        settings = self.load_settings()
        start_minimized = settings.get("start_minimized", False)
        if start_minimized:
            QTimer.singleShot(100, self.hide)
        self.tray_icon = WifeAlertNotifier(self, icon=self.app_icon)
        self.tray_icon.activated.connect(self.trayIconActivated)

    def start_monitoring(self):
        if not self.monitor:
            return

        if hasattr(self.monitor, "_running_task") and self.monitor._running_task:
            if not self.monitor._running_task.done():
                self.monitor._running_task.cancel()
            self.monitor._running_task = None

        self.monitor_btn.setText("Suppress Notifications")
        streamers = []
        for i in range(self.streamer_list.count()):
            streamers.append(
                self.streamer_list.itemWidget(self.streamer_list.item(i)).streamer_name
            )
        self.monitor.usernames = streamers

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                self.monitor._running_task = asyncio.create_task(self.monitor.run())
            else:
                QTimer.singleShot(
                    0,
                    lambda: setattr(
                        self.monitor,
                        "_running_task",
                        asyncio.create_task(self.monitor.run()),
                    ),
                )
        except RuntimeError:
            QTimer.singleShot(
                0,
                lambda: setattr(
                    self.monitor,
                    "_running_task",
                    asyncio.create_task(self.monitor.run()),
                ),
            )

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            clicked_widget = self.childAt(event.pos())
            if isinstance(
                clicked_widget, (QPushButton, QLineEdit, QListWidget, QCheckBox)
            ):
                self.dragging = False
            else:
                self.drag_position = (
                    event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                )
                self.dragging = True
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self.dragging:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def setup_ui(self):
        icon_path = get_asset_file("icon.png")
        self.app_icon = QIcon(icon_path)
        self.setWindowIcon(self.app_icon)
        QApplication.setWindowIcon(self.app_icon)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        title_bar = QHBoxLayout()
        layout.addLayout(title_bar)
        title_bar.addStretch()
        self.streamer_input = QLineEdit()
        self.streamer_input.setPlaceholderText("Enter username")
        layout.addWidget(self.streamer_input)
        self.add_btn = QPushButton("Add")
        self.add_btn.clicked.connect(self.add_streamer)
        layout.addWidget(self.add_btn)
        header_widget = QWidget()
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 2, 5, 2)
        header_layout.setSpacing(8)
        live_header = QLabel("")
        live_header.setFixedWidth(15)
        live_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(live_header)
        name_header = QLabel("Username")
        name_header.setMinimumWidth(110)
        notify_header = QLabel("Notify")
        sound_header = QLabel("Sound")
        open_header = QLabel("Open")
        emote_header = QLabel("Post")
        for header in [notify_header, sound_header, open_header, emote_header]:
            header.setFixedWidth(35)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(name_header)
        header_layout.addSpacing(5)
        header_layout.addWidget(notify_header)
        header_layout.addWidget(sound_header)
        header_layout.addWidget(open_header)
        header_layout.addWidget(emote_header)
        header_layout.addStretch()
        layout.addWidget(header_widget)
        self.streamer_list = QListWidget()
        self.streamer_list.setAlternatingRowColors(True)
        self.streamer_list.setStyleSheet(
            """
            QListWidget {
                background-color: #1a1a1a;
                border: none;
                color: white;
            }
            QListWidget::item:alternate {
                background-color: #2a2a2a;
                color: white;
            }
            QListWidget::item {
                padding: 0px;
                margin: 0px;
                color: white;
                background-color: #1a1a1a;
            }
            QLabel {
                color: white;
            }
            """
        )
        layout.addWidget(self.streamer_list)
        layout.addWidget(self.streamer_list)
        self.remove_btn = QPushButton("Remove Selected")
        self.remove_btn.clicked.connect(self.remove_streamer)
        layout.addWidget(self.remove_btn)
        self.monitor_btn = QPushButton("Allow Notifications")
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        layout.addWidget(self.monitor_btn)

        checkbox_layout_1 = QHBoxLayout()
        self.start_minimized_checkbox = QCheckBox("Start Minimized")
        self.start_minimized_checkbox.setStyleSheet("color: white;")
        self.suppress_sounds_checkbox = QCheckBox("Suppress Alert Sounds")
        self.suppress_sounds_checkbox.setStyleSheet("color: white;")
        checkbox_layout_1.addWidget(self.start_minimized_checkbox)
        checkbox_layout_1.addWidget(self.suppress_sounds_checkbox)
        layout.addLayout(checkbox_layout_1)

        checkbox_layout_2 = QHBoxLayout()
        self.start_with_windows_checkbox = QCheckBox("Start With Windows")
        self.start_with_windows_checkbox.setStyleSheet("color: white;")
        self.start_with_windows_checkbox.toggled.connect(self.toggle_autostart)
        self.prevent_open_checkbox = QCheckBox("Prevent Opening")
        self.prevent_open_checkbox.setStyleSheet("color: white;")
        self.prevent_open_checkbox.setToolTip(
            "Temporarily prevent streams from auto-opening"
        )
        checkbox_layout_2.addWidget(self.start_with_windows_checkbox)
        checkbox_layout_2.addWidget(self.prevent_open_checkbox)
        layout.addLayout(checkbox_layout_2)

        if hasattr(self, "_should_start_monitoring") and self._should_start_monitoring:
            QApplication.instance().processEvents()
            self.monitor_btn.setText("Suppress Notifications")
            streamers = []
            for i in range(self.streamer_list.count()):
                streamers.append(
                    self.streamer_list.itemWidget(
                        self.streamer_list.item(i)
                    ).streamer_name
                )
            self.monitor.usernames = streamers
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self.monitor.run())
                else:
                    QTimer.singleShot(
                        0, lambda: asyncio.create_task(self.monitor.run())
                    )
            except RuntimeError:
                QTimer.singleShot(0, lambda: asyncio.create_task(self.monitor.run()))

    def toggle_monitoring(self):
        if self.monitor_btn.text() == "Allow Notifications":
            if not self.monitor:
                self.monitor = WifeAlertMonitor(Config.CLIENT_ID, [])
                self.monitor.notification_manager = self.tray_icon

            self.monitor.live_channels.clear()
            self.monitor.suppress_actions = False

            streamers = []
            for i in range(self.streamer_list.count()):
                streamers.append(
                    self.streamer_list.itemWidget(
                        self.streamer_list.item(i)
                    ).streamer_name
                )
            self.monitor.usernames = streamers

            async def check_current_status():
                for username in self.monitor.usernames:
                    is_live = await self.monitor.check_stream_status(username)
                    if is_live:
                        channel_id = self.monitor.username_to_id.get(username)
                        if channel_id:
                            self.monitor.live_channels.add(channel_id)
                            await self.monitor.handle_stream_up(
                                channel_id, None, trigger_actions=False
                            )
                self.monitor.update_live_indicators()

            loop = asyncio.get_event_loop()
            loop.create_task(check_current_status())

            self.monitor_btn.setText("Suppress Notifications")
            self.start_monitoring()
        else:
            self.monitor_btn.setText("Allow Notifications")
            if self.monitor:
                self.monitor.suppress_actions = True
                for i in range(self.streamer_list.count()):
                    widget = self.streamer_list.itemWidget(self.streamer_list.item(i))
                    if widget and hasattr(widget, "streamer_name"):
                        widget.set_live_status(False)

    def add_streamer(self):
        streamer = self.streamer_input.text().strip().lower()
        if streamer:
            if not any(
                isinstance(
                    self.streamer_list.itemWidget(self.streamer_list.item(i)),
                    StreamerListItem,
                )
                and self.streamer_list.itemWidget(
                    self.streamer_list.item(i)
                ).streamer_name
                == streamer
                for i in range(self.streamer_list.count())
            ):
                item = QListWidgetItem("")
                widget = StreamerListItem(streamer)
                item.setSizeHint(widget.sizeHint().boundedTo(QSize(16777215, 25)))
                position = 0
                for i in range(self.streamer_list.count()):
                    existing_widget = self.streamer_list.itemWidget(
                        self.streamer_list.item(i)
                    )
                    if existing_widget and streamer < existing_widget.streamer_name:
                        break
                    position += 1
                self.streamer_list.insertItem(position, item)
                self.streamer_list.setItemWidget(item, widget)
                self.streamer_input.clear()

                if self.monitor and self.monitor_btn.text() == "Suppress Notifications":

                    async def add_new_streamer():
                        try:
                            loop = asyncio.get_running_loop()
                            new_ids = await self.monitor.gql_client.lookup_usernames(
                                [streamer]
                            )
                            if not new_ids:
                                for i in range(self.streamer_list.count()):
                                    widget = self.streamer_list.itemWidget(
                                        self.streamer_list.item(i)
                                    )
                                    if (
                                        widget
                                        and hasattr(widget, "streamer_name")
                                        and widget.streamer_name == streamer
                                    ):
                                        self.streamer_list.takeItem(i)
                                        break
                                handle_streamer_not_found(self, streamer)
                                return
                            self.monitor.usernames.append(streamer)
                            self.monitor.username_to_id.update(new_ids)
                            channel_id = new_ids.get(streamer)
                            if channel_id:
                                self.monitor.channel_ids.append(channel_id)
                                is_live = await self.monitor.check_stream_status(
                                    streamer
                                )
                                if is_live:
                                    self.monitor.live_channels.add(channel_id)
                                    await self.monitor.handle_stream_up(
                                        channel_id, None, trigger_actions=False
                                    )
                                    self.monitor.update_live_indicators()
                                if self.monitor.ws:
                                    new_topic = Topic(
                                        "video-playback-by-id", channel_id
                                    )
                                    request = PubSubRequest([new_topic], True)
                                    self.monitor.pending_requests[request.nonce] = (
                                        request
                                    )
                                    await self.monitor.ws.send(
                                        json.dumps(request.get_payload())
                                    )
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(add_new_streamer())

                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_running():
                            asyncio.create_task(add_new_streamer())
                        else:
                            loop.run_until_complete(add_new_streamer())
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(add_new_streamer())

                else:
                    if self.monitor:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(
                                    self.monitor.gql_client.lookup_usernames([streamer])
                                )
                            else:
                                loop.run_until_complete(
                                    self.monitor.gql_client.lookup_usernames([streamer])
                                )
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            loop.run_until_complete(
                                self.monitor.gql_client.lookup_usernames([streamer])
                            )

                self.save_streamers()

    def save_streamers(self):
        data = {
            "monitored_streamers": [],
            "channel_ids": {},
            "is_monitoring": self.monitor_btn.text() == "Suppress Notifications",
        }
        for i in range(self.streamer_list.count()):
            item = self.streamer_list.item(i)
            widget = self.streamer_list.itemWidget(item)
            if isinstance(widget, StreamerListItem):
                streamer = widget.streamer_name
                data["monitored_streamers"].append(streamer)
        if self.monitor and hasattr(self.monitor, "username_to_id"):
            data["channel_ids"] = self.monitor.username_to_id
        try:
            filepath = get_data_file("streamers.json")
            with open(filepath, "w") as f:
                json.dump(data, f, indent=4)
            self.save_settings()
        except Exception:
            pass

    def remove_streamer(self):
        current = self.streamer_list.currentRow()
        if current >= 0:
            widget = self.streamer_list.itemWidget(self.streamer_list.item(current))
            if widget and hasattr(widget, "streamer_name"):
                streamer = widget.streamer_name

                self.streamer_list.takeItem(current)

                if self.monitor and self.monitor_btn.text() == "Suppress Notifications":

                    async def remove_from_monitoring():
                        if streamer in self.monitor.usernames:
                            self.monitor.usernames.remove(streamer)

                        channel_id = self.monitor.username_to_id.get(streamer.lower())
                        if channel_id:
                            if channel_id in self.monitor.channel_ids:
                                self.monitor.channel_ids.remove(channel_id)

                            if self.monitor.ws:
                                topic = Topic("video-playback-by-id", channel_id)
                                request = PubSubRequest([topic], False)
                                self.monitor.pending_requests[request.nonce] = request
                                await self.monitor.ws.send(
                                    json.dumps(request.get_payload())
                                )

                            if channel_id in self.monitor.live_channels:
                                self.monitor.live_channels.remove(channel_id)

                            self.monitor.username_to_id.pop(streamer.lower(), None)

                    asyncio.create_task(remove_from_monitoring())

                self.save_streamers()

    def load_streamers(self):
        try:
            filepath = get_data_file("streamers.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    data = json.load(f)
                    streamers = sorted(data.get("monitored_streamers", []))
                    settings = self.load_settings()
                    start_minimized = settings.get("start_minimized", False)
                    self.start_minimized_checkbox.setChecked(start_minimized)
                    self.suppress_sounds_checkbox.setChecked(
                        settings.get("suppress_sounds", False)
                    )
                    self.prevent_open_checkbox.setChecked(
                        settings.get("prevent_open", False)
                    )
                    from utils.paths import check_autostart

                    self.start_with_windows_checkbox.setChecked(check_autostart())

                    if start_minimized:
                        QTimer.singleShot(100, self.hide)
                    emote_settings_path = get_data_file("emote_settings.json")
                    emote_settings = {}
                    if os.path.exists(emote_settings_path):
                        with open(emote_settings_path, "r") as f:
                            emote_settings = json.load(f)
                    for streamer in streamers:
                        streamer_settings = settings.get(streamer, {})
                        emote_enabled = False
                        if streamer in emote_settings:
                            emote_enabled = emote_settings[streamer].get(
                                "enabled", False
                            )
                        item = QListWidgetItem("")
                        widget = StreamerListItem(
                            streamer, sound_path=streamer_settings.get("sound_path")
                        )
                        widget.notify_checkbox.setChecked(
                            streamer_settings.get("notify_enabled", True)
                        )
                        widget.sound_checkbox.setChecked(
                            streamer_settings.get("sound_enabled", False)
                        )
                        widget.open_checkbox.setChecked(
                            streamer_settings.get("open_enabled", False)
                        )
                        widget.mod_view = streamer_settings.get("open_mod_view", False)
                        if widget.mod_view:
                            widget.open_checkbox.setToolTip(
                                "Automatically open\nShift+Click for mod view"
                            )
                        widget.emote_checkbox.setChecked(emote_enabled)
                        item.setSizeHint(widget.sizeHint())
                        self.streamer_list.addItem(item)
                        self.streamer_list.setItemWidget(item, widget)
                    if self.monitor:
                        self.monitor.username_to_id = data.get("channel_ids", {})
                        if streamers:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(
                                    self.monitor.gql_client.lookup_usernames(streamers)
                                )
                                self.monitor.usernames = streamers
                            else:
                                loop.run_until_complete(
                                    self.monitor.gql_client.lookup_usernames(streamers)
                                )
                                self.monitor.usernames = streamers

                    was_monitoring = data.get("is_monitoring", False)
                    if was_monitoring:
                        self.monitor_btn.setText("Suppress Notifications")
                        QTimer.singleShot(2000, self.start_monitoring)
                        QTimer.singleShot(2500, self.monitor.update_live_indicators)
                    else:
                        self.monitor_btn.setText("Allow Notifications")

        except Exception:
            pass

    def save_settings(self):
        try:
            current_settings = self.load_settings()
            current_settings["start_minimized"] = (
                self.start_minimized_checkbox.isChecked()
            )
            current_settings["start_with_windows"] = (
                self.start_with_windows_checkbox.isChecked()
            )
            current_settings["suppress_sounds"] = (
                self.suppress_sounds_checkbox.isChecked()
            )
            current_settings["prevent_open"] = self.prevent_open_checkbox.isChecked()
            for i in range(self.streamer_list.count()):
                item = self.streamer_list.item(i)
                widget = self.streamer_list.itemWidget(item)
                if isinstance(widget, StreamerListItem):
                    streamer = widget.streamer_name
                    streamer_settings = current_settings.get(streamer, {})
                    streamer_settings.update(
                        {
                            "notify_enabled": widget.notify_checkbox.isChecked(),
                            "sound_enabled": widget.sound_checkbox.isChecked(),
                            "sound_path": widget.sound_path,
                            "open_enabled": widget.open_checkbox.isChecked(),
                            "open_mod_view": widget.mod_view,
                            "emote_enabled": widget.emote_checkbox.isChecked(),
                        }
                    )
                    current_settings[streamer] = streamer_settings
            filepath = get_data_file("settings.json")
            try:
                with open(filepath, "w") as f:
                    json.dump(current_settings, f, indent=4)
            except Exception:
                from utils.error_handler import handle_settings_save_error

                handle_settings_save_error(self)
        except Exception:
            from utils.error_handler import handle_settings_save_error

            handle_settings_save_error(self)

    def toggle_autostart(self, checked):
        from utils.paths import set_autostart

        set_autostart(checked)
        self.save_settings()

    def load_settings(self):
        try:
            filepath = get_data_file("settings.json")
            if os.path.exists(filepath):
                with open(filepath, "r") as f:
                    settings = json.load(f)
                    return settings
            return {}
        except Exception:
            return {}

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if self.windowState() & Qt.WindowState.WindowMinimized:
                event.accept()
                self.hide()
                return
        super().changeEvent(event)

    def trayIconActivated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.setWindowState(Qt.WindowState.WindowActive)
            self.show()
            self.raise_()

    async def shutdown(self):
        if self.monitor:
            self.monitor.should_run = False
            if self.monitor.ws:
                await self.monitor.ws.close()

            self.monitor.live_channels.clear()
            self.monitor.update_live_indicators()

        if hasattr(self, "tray_icon"):
            await self.tray_icon.cleanup_sound_effects()
            self.tray_icon.hide()

        self.save_streamers()
        self.save_settings()

    def closeEvent(self, event):
        self.save_streamers()
        self.save_settings()
        event.accept()
        QApplication.quit()
