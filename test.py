from desktop_notifier import DesktopNotifier, Notification, Button

DesktopNotifier = Notification(mode="dark")  # or "light"

notification = Notification(
    title="My Notification",
    message="This is a test notification.",
    buttons=[Button(title="OK")],
)

notifier.send(notification)