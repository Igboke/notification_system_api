import json
import logging
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)

from django.contrib.auth import get_user_model

from notifications_app.models import NotificationJob
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for real-time in-app notifications.
    """

    async def connect(self):
        """
        Called when a new WebSocket connection is established.
        Authenticates the user and adds them to a specific user-group in the channel layer.
        """
        self.user = self.scope[
            "user"
        ]  # User object from AuthMiddlewareStack in asgi.py

        logger.info(
            f"WebSocket connect attempt: User authenticated = {self.user.is_authenticated}"
        )
        if self.user.is_authenticated:
            logger.info(
                f"Authenticated user ID: {self.user.id}, Username: {self.user.username}"
            )
        else:
            logger.info("User is not authenticated (AnonymousUser).")

        if self.user.is_authenticated:
            # Create a unique group name for this user based on their ID.
            # This is how the worker will target messages to this specific user.
            self.user_group_name = f"user_{self.user.id}_notifications"
            logger.info(
                f"User {self.user.id} connected to WebSocket. Adding to group '{self.user_group_name}'."
            )

            # Add this consumer's channel to the user's group in the channel layer.
            # `self.channel_name` is a unique ID for this specific WebSocket connection.
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            await self.accept()  # Accept the WebSocket connection
            await self.send_missed_notifications()
        else:
            logger.warning(
                "Anonymous user attempted to connect to WebSocket. Connection rejected."
            )
            await self.close()  # Reject anonymous connections

    async def disconnect(self, close_code):
        """
        Called when a WebSocket connection is closed or disconnected.
        Removes the consumer from its associated user group.
        """
        if self.user.is_authenticated:
            logger.info(
                f"User {self.user.id} disconnected from WebSocket. Removing from group '{self.user_group_name}'."
            )
            # Remove this consumer's channel from the user's group.
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )

    async def receive(self, text_data):
        """
        Called when a message is received from the WebSocket client (browser/app).
        For notifications, the client typically doesn't send messages back to the server,
        but this method is part of the consumer's interface.
        """
        # You could parse `text_data` if your frontend sends messages (e.g., to mark notification as read).
        # For a simple push notification system, you might not use this much.
        logger.debug(f"Received message from client {self.user.id}: {text_data}")

    async def send_notification(self, event):
        """
        Custom handler method called by the channel layer when a message is sent
        to this consumer's group (e.g., by the Notification Worker).
        This method will take the `message` payload and send it down the WebSocket to the client.
        """
        notification_data = event[
            "message"
        ]  # The actual notification content from the worker
        job_id = notification_data.get("job_id")

        logger.info(
            f"Sending in-app notification to client {self.user.id}: {notification_data}"
        )
        # Send the notification data as a JSON string over the WebSocket.
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",  # A type identifier for the frontend
                    "data": notification_data,  # The actual notification content
                }
            )
        )
        if job_id:
            await self._mark_notification_as_read(job_id)

    async def send_missed_notifications(self):
        """
        Fetch notifications that were sent by the worker but not yet marked as read for this user
        """
        # Database queries must be run in a separate thread, hence sync_to_async
        missed_notifications = await sync_to_async(list)(
            NotificationJob.objects.filter(
                recipient_id=self.user.id,
                channel="in_app",
                status="sent",  # Only notifications successfully sent by worker
                is_read=False,
            ).order_by(
                "created_at"
            )  # Send oldest first
        )

        if missed_notifications:
            logger.info(
                f"Found {len(missed_notifications)} missed notifications for user {self.user.id}. Sending now."
            )
            for job in missed_notifications:
                # Send each missed notification
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "notification_missed",  # Differentiate type for frontend
                            "data": job.message_data,
                            "job_id": job.id,
                        }
                    )
                )
                # Mark as read after sending. This prevents re-sending on subsequent reconnects.
                await self._mark_notification_as_read(job.id)
        else:
            logger.info(f"No missed notifications for user {self.user_id}.")

    # Helper method to mark notification as read in the database
    @sync_to_async
    def _mark_notification_as_read(self, job_id):
        try:
            job = NotificationJob.objects.get(id=job_id)
            if not job.is_read:  # Only update if not already marked
                job.is_read = True
                job.save()
                logger.debug(f"Notification Job {job_id} marked as read.")
        except NotificationJob.DoesNotExist:
            logger.error(
                f"Notification Job {job_id} not found when trying to mark as read."
            )
        except Exception as e:
            logger.error(f"Error marking Notification Job {job_id} as read: {e}")
