"""
Receiver
"""

import logging
from django.dispatch import receiver
from django.conf import settings
from django.urls import reverse_lazy
from django.contrib.auth import get_user_model
from notifications_app.models import NotificationJob
from notifications_app.utils import generate_verification_url
from users.signals import user_registered
from .backends.database_queue import notification_backend


logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(user_registered)
def handle_user_registration_notification(sender, user, **kwargs):
    """
    Signal receiver for user registration. Enqueues a welcome email notification.
    """
    logger.info(
        f"Received user_registered signal for user ID: {user.id}, email: {user.email}"
    )

    verification_token = generate_verification_url(user)
    verification_url = (
        f"{settings.BASE_URL}{reverse_lazy('verify_email')}?token={verification_token}"
    )

    # Define the content for the welcome email
    email_message_data = {
        "subject": "Welcome to Your Awesome App!",
        "body_text": f"Hi {user.email},\n\nWelcome to our app! Please verify your email by clicking the link below:\n\n{verification_url}\n\nThanks,\nYour App Team",
        "body_html": f"<p>Hi <b>{user.email}</b>,</p><p>Welcome to our app! Please verify your email by clicking the link below:</p><p><a href='{verification_url}'>Verify Your Email Now!</a></p><p>Thanks,</p><p>Your App Team</p>",
    }

    try:
        # Check user preferences before enqueueing email
        prefs = getattr(user, "notification_preferences", None)
        if prefs and not prefs.prefers_email:
            logger.info(
                f"User {user.id} has opted out of email notifications. Skipping welcome email."
            )
        else:
            # Enqueue the email notification using our backend
            job_id = notification_backend.enqueue(
                recipient_id=user.id,
                channel=NotificationJob.CHANNEL_EMAIL,
                message_data=email_message_data,
                notification_type="welcome_email",
            )
            logger.info(
                f"Welcome email enqueued for user {user.email} (Job ID: {job_id})."
            )

        # Enqueue a generic in-app notification for new users ---
        in_app_message_data = {
            "title": "Welcome to the App!",
            "body": f"Hi {user.email}, explore our features!",
        }

        # Check user preferences before enqueueing in-app
        if prefs and not prefs.prefers_in_app:
            logger.info(
                f"User {user.id} has opted out of in-app notifications. Skipping welcome in-app message."
            )
        else:
            job_id_in_app = notification_backend.enqueue(
                recipient_id=user.id,
                channel=NotificationJob.CHANNEL_IN_APP,
                message_data=in_app_message_data,
                notification_type="welcome_in_app",
            )
            logger.info(
                f"Welcome in-app notification enqueued for user {user.email} (Job ID: {job_id_in_app})."
            )

    except Exception as e:
        logger.error(f"Error handling user registration for {user.email}: {e}")
