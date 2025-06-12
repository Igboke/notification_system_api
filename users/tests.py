"""
User -Tests
"""

from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from notifications_app.models import NotificationJob
from notifications_app.utils import generate_verification_url

User = get_user_model()


class UserAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse("user-register")
        self.verify_url = reverse("verify-email")
        self.user_data = {
            "email": "test@example.com",
            "password": "a-strong-password123",
        }

    def test_user_registration_success(self):
        """
        Ensure a new user can be created and welcome notifications are enqueued.
        """
        response = self.client.post(self.register_url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(User.objects.get().email, self.user_data["email"])

        # Check that notification jobs were created
        self.assertEqual(NotificationJob.objects.count(), 2)

        email_job = NotificationJob.objects.get(channel=NotificationJob.CHANNEL_EMAIL)
        in_app_job = NotificationJob.objects.get(channel=NotificationJob.CHANNEL_IN_APP)

        self.assertEqual(email_job.notification_type, "welcome_email")
        self.assertEqual(in_app_job.notification_type, "welcome_in_app")
        self.assertFalse(User.objects.get().is_verified)

    def test_user_registration_duplicate_email(self):
        """
        Ensure registration fails if the email already exists.
        """
        # Create the user first
        User.objects.create_user(**self.user_data)

        response = self.client.post(self.register_url, self.user_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(User.objects.count(), 1)  # No new user should be created

    def test_email_verification_success(self):
        """
        Ensure the verification endpoint correctly verifies a user.
        """
        user = User.objects.create_user(**self.user_data)
        self.assertFalse(user.is_verified)

        token = generate_verification_url(user)
        response = self.client.get(f"{self.verify_url}?token={token}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user.refresh_from_db()
        self.assertTrue(user.is_verified)

    def test_email_verification_invalid_token(self):
        """
        Ensure the verification endpoint rejects an invalid token.
        """
        response = self.client.get(f"{self.verify_url}?token=invalid-token")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_email_verification_already_verified(self):
        """
        Ensure a user who is already verified is handled gracefully.
        """
        user = User.objects.create_user(**self.user_data)
        user.is_verified = True
        user.save()

        token = generate_verification_url(user)
        response = self.client.get(f"{self.verify_url}?token={token}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("already been verified", response.data["message"])
