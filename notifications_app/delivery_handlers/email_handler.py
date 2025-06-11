"""
Email implementation of Abstract delivery handler
"""

from abc import abstractmethod
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.contrib.auth import get_user_model

from notifications_app.delivery_handlers.delivery_handler_abc import (
    AbstractDeliveryHandler,
)

logger = logging.getLogger(__name__)
User = get_user_model()


class EmailDeliveryHandler(AbstractDeliveryHandler):
    """
    Handles sending email notifications using Python's smtplib.
    """

    @classmethod
    @abstractmethod
    def send(cls, recipient_id: int, message_data: dict):
        """
        Sends an email notification to the specified user.
        """
        try:
            user = User.objects.get(id=recipient_id)
            recipient_email = user.email

            # Extract content from message_data, providing defaults
            subject = message_data.get("subject", "No Subject")
            body_text = message_data.get("body_text", "No text content.")
            body_html = message_data.get("body_html", None)

            # Create the email message object
            msg = MIMEMultipart(
                "alternative"
            )  # 'alternative' means it contains multiple versions (text/html)
            msg["Subject"] = subject
            msg["From"] = settings.DEFAULT_FROM_EMAIL
            msg["To"] = recipient_email

            # Attach the plain text version
            msg.attach(MIMEText(body_text, "plain"))

            if body_html:
                msg.attach(MIMEText(body_html, "html"))

            # Establish an SMTP connection and send the email
            # Use SMTP_SSL for encrypted connections, or starttls()
            # if your server requires it after connection.
            with smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
                server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
                server.send_message(msg)

            logger.info(
                f"Successfully sent email to {recipient_email} for user ID: {recipient_id}."
            )

        except User.DoesNotExist:
            logger.error(f"User with ID {recipient_id} not found for email delivery.")
            raise
        except smtplib.SMTPAuthenticationError:
            logger.error(
                f"SMTP authentication failed for user ID {recipient_id}. Check EMAIL_HOST_USER/PASSWORD."
            )
            raise
        except smtplib.SMTPException as e:
            logger.error(
                f"SMTP error sending email to {recipient_email} for user ID {recipient_id}: {e}"
            )
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error sending email to {recipient_email} for user ID {recipient_id}: {e}"
            )
            raise
