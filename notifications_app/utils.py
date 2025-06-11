"""
Utility
"""

from datetime import datetime, timedelta, timezone
from django.contrib.auth import get_user_model
from django.conf import settings

import jwt
import logging

User = get_user_model()
SECRET_KEY = settings.SECRET_KEY
logger = logging.getLogger(__name__)


def generate_verification_url(user) -> str:
    """
    JWT for Email Verification
    """
    payload = {
        "user_id": user.id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=24),
    }
    verification_token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    return verification_token


def decode_verification_token(token: str):
    """
    Decodes the verification token and returns the user.
    Handles expired or invalid tokens.
    Returns: User object or None if token is invalid.
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.objects.get(id=payload["user_id"])
        return user
    except jwt.ExpiredSignatureError:
        logger.warning("Verification token expired.")
        return None
    except (jwt.InvalidTokenError, User.DoesNotExist):
        logger.warning("Invalid verification token or user not found.")
        return None
