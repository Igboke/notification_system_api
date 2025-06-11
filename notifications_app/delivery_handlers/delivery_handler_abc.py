"""
Abstract method
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


class AbstractDeliveryHandler(ABC):
    """
    Abstract base class for specific notification delivery mechanisms (e.g., email, in-app).
    Defines a generic interface for sending a notification.
    """

    @classmethod
    @abstractmethod
    def send(cls, recipient_id: int, message_data: Dict[str, Any]):
        """
        Sends the notification content to the specified recipient via this handler's channel.

        Args:
            recipient_id (int): The ID of the user who is the recipient.
            message_data (Dict[str, Any]): A dictionary containing the notification content.
        """
        pass
