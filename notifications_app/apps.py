from django.apps import AppConfig


class NotificationsAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notifications_app"

    def ready(self):
        """
        Import your receivers module here to connect them to signals.
        """

        import notifications_app.receiver
