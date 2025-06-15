"""
Notifications app model
"""

from django.conf import settings
from django.db import models


class NotificationJob(models.Model):
    """
    Notification Class
    """

    # Status Choices
    # These are the possible states a notification job can be in.
    STATUS_PENDING = "pending"  # Waiting to be picked up by the worker
    STATUS_SENDING = "sending"  # Currently being processed by the worker
    STATUS_SENT = "sent"  # Successfully sent
    STATUS_FAILED = "failed"  # Failed after max retries
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENDING, "Sending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    # Channel Choices
    # The different ways a notification can be delivered.
    CHANNEL_EMAIL = "email"
    CHANNEL_IN_APP = "in_app"
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, "Email"),
        (CHANNEL_IN_APP, "In-App"),
    ]

    # why didnt i make it a foreign key with the user model?
    recipient_id = models.IntegerField(
        db_index=True, help_text="ID of the user who will receive the notification."
    )
    channel = models.CharField(
        max_length=10,
        choices=CHANNEL_CHOICES,
        help_text="The delivery method (email or in-app).",
    )

    # What kind of notification is this? (e.g., 'welcome_email', 'new_message', 'order_update')
    notification_type = models.CharField(
        max_length=50,
        default="general",
        help_text="A specific type identifier for the notification.",
    )

    # This field stores all the actual content for the notification (subject, body, title, etc.)
    message_data = models.JSONField(
        help_text="JSON payload containing all notification content (e.g., {'subject': '...', 'body': '...'} or {'title': '...', 'message': '...'})."
    )

    # Job Management Fields
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        help_text="Current status of the notification job.",
    )

    retries_count = models.PositiveIntegerField(
        default=0, help_text="Number of times this notification has been retried."
    )
    max_retries = models.PositiveIntegerField(
        default=3, help_text="Maximum allowed retries before marking as failed."
    )
    failed_reason = models.TextField(
        blank=True, null=True, help_text="Reason for the last failure, if any."
    )

    # Timestamps
    scheduled_at = models.DateTimeField(
        auto_now_add=True, help_text="When the notification job was created/scheduled."
    )
    sent_at = models.DateTimeField(
        null=True, blank=True, help_text="When the notification was successfully sent."
    )

    created_at = models.DateTimeField(
        auto_now_add=True, help_text="Timestamp of when the record was created."
    )
    updated_at = models.DateTimeField(
        auto_now=True, help_text="Timestamp of the last update to the record."
    )
    is_read = models.BooleanField(
        default=False,
        help_text="For in-app notifications, indicates if the client has acknowledged receipt via WebSocket.",
    )

    class Meta:
        """
        More Information about the database model
        """

        # Order jobs by creation time (FIFO - First In, First Out)
        ordering = ["created_at"]
        # Add a database index to make polling queries faster
        indexes = [
            models.Index(fields=["status", "scheduled_at"]),
        ]
        verbose_name = "Notification Job"
        verbose_name_plural = "Notification Jobs"

    def __str__(self):
        return f"Job {self.id} for user {self.recipient_id} ({self.channel}) - Type: {self.notification_type} - Status: {self.status}"

    def is_pending(self):
        return self.status == self.STATUS_PENDING

    def is_sent(self):
        return self.status == self.STATUS_SENT

    def is_failed(self):
        return self.status == self.STATUS_FAILED


class NotificationChannel(models.TextChoices):
    """
    Add other channels like SMS, PUSH if needed in the future
    """

    EMAIL = "email", "Email"
    IN_APP = "in_app", "In-App"


class UserCommunicationPreference(models.Model):
    """
    User Communication Preferences Model
    This model allows users to specify their preferred notification channels.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,  # Uses the setting.AUTH_USER_MODEL custom user model
        # prevents circular imports by avoiding get_user_model
        on_delete=models.CASCADE,
        related_name="notification_preferences",
        help_text="The user associated with these preferences.",
    )

    # Booleans for enabling/disabling notifications by channel
    prefers_email = models.BooleanField(
        default=True, help_text="Does the user prefer email notifications?"
    )
    prefers_in_app = models.BooleanField(
        default=True, help_text="Does the user prefer in-app notifications?"
    )

    default_channel = models.CharField(
        max_length=10,
        choices=NotificationChannel.choices,
        default=NotificationChannel.IN_APP,
        help_text="The primary channel for non-critical notifications.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Communication Preference"
        verbose_name_plural = "User Communication Preferences"

    def __str__(self):
        return f"Preferences for {self.user.email}"
