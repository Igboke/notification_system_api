from django.urls import re_path

from . import consumers

# Define URL patterns specifically for WebSocket connections.
# This list will be used by `URLRouter` in  `asgi.py`.
websocket_urlpatterns = [
    # This path will handle all WebSocket connections to 'ws://mydomain.com/ws/notifications/'
    # The `as_asgi()` method creates an ASGI application instance from the consumer class.
    re_path(r"ws/notifications/$", consumers.NotificationConsumer.as_asgi()),
]
