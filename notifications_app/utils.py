"""
Utility
"""

from datetime import datetime, timedelta, timezone
from django.conf import settings

import jwt


SECRET_KEY = settings.SECRET_KEY


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
