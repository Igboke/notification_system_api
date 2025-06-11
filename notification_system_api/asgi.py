"""
ASGI config for notification_system_api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from channels.auth import (
    AuthMiddlewareStack,
)  # For authenticating users over WebSockets
from channels.routing import (
    ProtocolTypeRouter,
    URLRouter,
)  # For routing different protocols (HTTP, WebSocket)

import notifications_app.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "notification_system_api.settings")

django_asgi_app = (
    get_asgi_application()
)  # Get Django's standard ASGI application for HTTP

application = ProtocolTypeRouter(
    {
        # "http" protocol will be handled by Django's default ASGI app (for regular HTTP requests)
        "http": django_asgi_app,
        # "websocket" protocol will be handled by Channels.
        # AuthMiddlewareStack integrates Django's authentication system with WebSockets,
        # so you can access `self.scope['user']` in your consumers.
        "websocket": AuthMiddlewareStack(
            # URLRouter maps WebSocket paths to specific consumers.
            URLRouter(
                notifications_app.routing.websocket_urlpatterns  # Our WebSocket URL patterns
            )
        ),
    }
)
