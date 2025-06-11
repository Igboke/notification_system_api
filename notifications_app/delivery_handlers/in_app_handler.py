"""
In app handler
"""

import logging
from channels.layers import get_channel_layer  # To interact with the Channels layer
from asgiref.sync import (
    async_to_sync,
)  # A helper to call async functions from sync code

from notifications_app.delivery_handlers.delivery_handler_abc import (
    AbstractDeliveryHandler,
)

logger = logging.getLogger(__name__)


class InAppDeliveryHandler(AbstractDeliveryHandler):
    """
    Handles sending real-time in-app notifications via Django Channels WebSockets.
    """

    @classmethod
    def send(cls, recipient_id: int, message_data: dict):
        """
        Sends an in-app notification to the appropriate WebSocket group for the recipient.
        """
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.error(
                "Channel layer is not configured. Cannot send in-app notifications."
            )

            raise Exception("Channel layer not configured.")

        # Construct the unique group name for this user.
        user_group_name = f"user_{recipient_id}_notifications"

        try:
            # We need to call an async function (group_send) from sync code (our worker).
            # async_to_sync helps bridge this gap.
            async_to_sync(channel_layer.group_send)(
                user_group_name,  # The group to which we're sending the message
                {
                    # 'type' maps to a method name in your consumer.
                    # The consumer will have an `async def send_notification(self, event):` method.
                    "type": "send_notification",
                    # 'message' is the actual payload that will be passed to the consumer.
                    "message": message_data,
                },
            )
            logger.info(
                f"In-app notification pushed to channel layer for user ID: {recipient_id} in group: {user_group_name}"
            )
        except Exception as e:
            logger.error(
                f"Failed to push in-app notification to channel layer for user ID: {recipient_id}: {e}"
            )
            raise
