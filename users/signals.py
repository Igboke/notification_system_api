"""
Defining Signals for events.
You can define other signals here for different events, e.g.:
order_status_updated = Signal()
new_message_received = Signal()
"""

from django.dispatch import Signal

user_registered = Signal()
