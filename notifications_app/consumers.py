import json
import logging
from channels.generic.websocket import (
    AsyncWebsocketConsumer,
)

from django.contrib.auth import get_user_model

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
