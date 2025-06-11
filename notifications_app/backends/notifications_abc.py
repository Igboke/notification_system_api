from abc import ABC, abstractmethod
from typing import Dict, Any


class AbstractNotificationBackend(ABC):
    """
    Abstract base class for notification backend implementations.
    Defines the interface for how notifications are enqueued for later processing.
    """

    @abstractmethod
    def enqueue(
        self,
        recipient_id: int,
        channel: str,
        message_data: Dict[str, Any],
        notification_type: str = "general",
    ):
        """
        Enqueues a notification job.

        Args:
            recipient_id (int): The ID of the user who will receive the notification.
            channel (str): The desired delivery channel (e.g., 'email', 'in_app').
            message_data (Dict[str, Any]): A dictionary containing all the content for the notification.
            notification_type (str): A string identifying the type of notification (e.g., 'welcome_email').

        Returns:
            int: The ID of the created notification job.
        """
        pass
