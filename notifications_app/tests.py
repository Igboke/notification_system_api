"""
notifications_app - tests
"""

from unittest.mock import patch
import smtplib

from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model
from .models import NotificationJob, UserCommunicationPreference
from .backends.database_queue import notification_backend

User = get_user_model()


class NotificationBackendTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com", password="password"
        )

    def test_enqueue_creates_job(self):
        """
        Ensure the backend's enqueue method creates a NotificationJob record.
        """
        self.assertEqual(NotificationJob.objects.count(), 0)

        job_id = notification_backend.enqueue(
            recipient_id=self.user.id,
            channel=NotificationJob.CHANNEL_EMAIL,
            message_data={"subject": "Test"},
            notification_type="test_email",
        )

        self.assertEqual(NotificationJob.objects.count(), 1)
        job = NotificationJob.objects.get(id=job_id)
        self.assertEqual(job.status, NotificationJob.STATUS_PENDING)
        self.assertEqual(job.recipient_id, self.user.id)

    def test_enqueue_respects_user_preferences_off(self):
        """
        Ensure no job is created if the user has opted out of a channel.
        """
        UserCommunicationPreference.objects.create(user=self.user, prefers_email=False)

        job_id = notification_backend.enqueue(
            recipient_id=self.user.id,
            channel=NotificationJob.CHANNEL_EMAIL,
            message_data={"subject": "Test"},
            notification_type="test_email_opt_out",
        )

        self.assertIsNone(job_id)
        self.assertEqual(NotificationJob.objects.count(), 0)
