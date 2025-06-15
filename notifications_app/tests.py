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


# Patch the delivery handlers at the location where the worker imports them.
@patch(
    "notifications_app.management.commands.run_notification_worker.InAppDeliveryHandler.send"
)
@patch(
    "notifications_app.management.commands.run_notification_worker.EmailDeliveryHandler.send"
)
class NotificationWorkerTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="workeruser@example.com", password="password"
        )

    def test_worker_processes_pending_email_job(
        self, mock_email_send, mock_in_app_send
    ):
        """
        Ensure the worker finds a pending email job, processes it, and marks it as 'sent'.
        """
        job = NotificationJob.objects.create(
            recipient_id=self.user.id,
            channel=NotificationJob.CHANNEL_EMAIL,
            message_data={"subject": "Hi"},
            status=NotificationJob.STATUS_PENDING,
        )

        # CALL WITH run_once=True
        call_command("run_notification_worker", run_once=True)

        job.refresh_from_db()
        self.assertEqual(job.status, NotificationJob.STATUS_SENT)
        mock_email_send.assert_called_once_with(self.user.id, {"subject": "Hi"}, job.id)
        mock_in_app_send.assert_not_called()

    def test_worker_processes_pending_in_app_job(
        self, mock_email_send, mock_in_app_send
    ):
        """
        Ensure the worker finds a pending in-app job, processes it, and marks it as 'sent'.
        """
        job = NotificationJob.objects.create(
            recipient_id=self.user.id,
            channel=NotificationJob.CHANNEL_IN_APP,
            message_data={"title": "Hello"},
            status=NotificationJob.STATUS_PENDING,
        )

        # CALL WITH run_once=True
        call_command("run_notification_worker", run_once=True)

        job.refresh_from_db()
        self.assertEqual(job.status, NotificationJob.STATUS_SENT)
        mock_in_app_send.assert_called_once_with(
            self.user.id, {"title": "Hello"}, job.id
        )
        mock_email_send.assert_not_called()

    def test_worker_handles_delivery_failure_and_retries(
        self, mock_email_send, mock_in_app_send
    ):
        """
        Ensure that if a delivery fails, the job is marked for retry and its retry count is incremented.
        """
        mock_email_send.side_effect = smtplib.SMTPException("Connection failed")

        job = NotificationJob.objects.create(
            recipient_id=self.user.id,
            channel=NotificationJob.CHANNEL_EMAIL,
            message_data={"subject": "Failing Email"},
            status=NotificationJob.STATUS_PENDING,
            max_retries=3,
        )

        # CALL WITH run_once=True for each attempt
        # First attempt
        call_command("run_notification_worker", run_once=True)
        job.refresh_from_db()
        self.assertEqual(job.status, NotificationJob.STATUS_PENDING)
        self.assertEqual(job.retries_count, 1)
        self.assertIn("Connection failed", job.failed_reason)

        # Second attempt
        call_command("run_notification_worker", run_once=True)
        job.refresh_from_db()
        self.assertEqual(job.status, NotificationJob.STATUS_PENDING)
        self.assertEqual(job.retries_count, 2)

        # Final attempt
        call_command("run_notification_worker", run_once=True)
        job.refresh_from_db()
        self.assertEqual(job.status, NotificationJob.STATUS_FAILED)
        self.assertEqual(job.retries_count, 3)

        # Use a proper assertion for the call count
        self.assertEqual(mock_email_send.call_count, 3)
