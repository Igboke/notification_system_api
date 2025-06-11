import logging
from typing import Dict, Any

from notifications_app.backends.notifications_abc import AbstractNotificationBackend
from notifications_app.models import NotificationJob, UserCommunicationPreference

logger = logging.getLogger(__name__)


class DatabaseQueueBackend(AbstractNotificationBackend):
    """
    Implementation of the notification backend that uses a database table as a queue.
    The `enqueue` method simply creates a record in the NotificationJob table.
    The actual sending will be handled by a separate worker process.
    """

    def enqueue(
        self,
        recipient_id: int,
        channel: str,
        message_data: Dict[str, Any],
        notification_type: str = "general",
    ):
        """
        Enqueues a notification by creating a NotificationJob entry in the database.
        """
        try:
            try:
                prefs = UserCommunicationPreference.objects.get(user_id=recipient_id)
                if channel == NotificationJob.CHANNEL_EMAIL and not prefs.prefers_email:
                    logger.info(f"Skipping email for user {recipient_id}: opted out.")
                    return None
                if (
                    channel == NotificationJob.CHANNEL_IN_APP
                    and not prefs.prefers_in_app
                ):
                    logger.info(f"Skipping in-app for user {recipient_id}: opted out.")
                    return None
            except UserCommunicationPreference.DoesNotExist:
                # Handle cases where preferences don't exist (e.g., new user, default to sending)
                logger.info(
                    f"User with user id {recipient_id} does not have a preference"
                )
                pass

            job = NotificationJob.objects.create(
                recipient_id=recipient_id,
                channel=channel,
                notification_type=notification_type,
                message_data=message_data,
                status=NotificationJob.STATUS_PENDING,
            )
            logger.info(
                f"Notification job {job.id} enqueued for user {recipient_id} via {channel}."
            )
            return job.id
        except Exception as e:
            logger.error(
                f"Failed to enqueue notification for user {recipient_id} (Type: {notification_type}, Channel: {channel}): {e}"
            )
            raise


# Create a global instance of our notifier backend
# This is what other parts of your Django app will use
notification_backend = DatabaseQueueBackend()
