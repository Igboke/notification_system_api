"""
Notification Worker
"""

from datetime import timedelta
import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction, DatabaseError
from django.utils import timezone
from django.conf import settings

from notifications_app.models import NotificationJob
from notifications_app.delivery_handlers.email_handler import EmailDeliveryHandler
from notifications_app.delivery_handlers.in_app_handler import InAppDeliveryHandler

logger = logging.getLogger(__name__)

# Mapping channels to their respective handlers
DELIVERY_HANDLERS = {
    NotificationJob.CHANNEL_EMAIL: EmailDeliveryHandler,
    NotificationJob.CHANNEL_IN_APP: InAppDeliveryHandler,
}


class Command(BaseCommand):
    help = (
        "Runs the notification worker to process pending jobs from the database queue."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--run-once",
            action="store_true",
            help="Run one batch of jobs and exit.",
        )

    def handle(self, *args, **options):
        # Define default settings if not already in settings.py
        if not hasattr(settings, "NOTIFICATION_WORKER_POLL_INTERVAL"):
            settings.NOTIFICATION_WORKER_POLL_INTERVAL = 10  # Default to 10 seconds
        if not hasattr(settings, "NOTIFICATION_WORKER_ERROR_RETRY_INTERVAL"):
            settings.NOTIFICATION_WORKER_ERROR_RETRY_INTERVAL = (
                30  # Default to 30 seconds on error
            )
        if not hasattr(settings, "NOTIFICATION_WORKER_BATCH_SIZE"):
            settings.NOTIFICATION_WORKER_BATCH_SIZE = 10  # Default to 10 jobs per batch

        if options["run_once"]:
            self.stdout.write(self.style.SUCCESS("Running one-time job processing..."))
            self.process_pending_jobs()
            self.stdout.write(self.style.SUCCESS("One-time job processing complete."))
            return

        self.stdout.write(
            self.style.SUCCESS("Starting notification worker... Press Ctrl+C to stop.")
        )

        while True:
            try:
                self.process_pending_jobs()
                time.sleep(settings.NOTIFICATION_WORKER_POLL_INTERVAL)
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("Notification worker stopped."))
                break
            except Exception as e:
                logger.exception(
                    f"An unhandled error occurred in the main worker loop: {e}"
                )
                time.sleep(settings.NOTIFICATION_WORKER_ERROR_RETRY_INTERVAL)

    def process_pending_jobs(self):
        """
        Fetches and processes a batch of pending notification jobs,
        using select_for_update to prevent concurrent processing.
        """
        # Wrap the entire batch fetch and processing in a single atomic transaction.
        # This ensures that either all fetched jobs are processed and their status updated,
        # or if an unhandled error occurs within the batch, all changes are rolled back,
        # making the jobs available again.
        try:
            with transaction.atomic():
                jobs_to_process = (
                    NotificationJob.objects.select_for_update(skip_locked=True)
                    .filter(
                        status=NotificationJob.STATUS_PENDING,
                        scheduled_at__lte=timezone.now(),
                    )
                    .order_by("scheduled_at")[: settings.NOTIFICATION_WORKER_BATCH_SIZE]
                )

                if not jobs_to_process:
                    logger.debug("No pending notification jobs found.")
                    return

                logger.info(
                    f"Picked up {len(jobs_to_process)} pending notification jobs."
                )

                for job in jobs_to_process:
                    if job.status != NotificationJob.STATUS_PENDING:
                        logger.warning(
                            f"Job {job.id} was already processed or is no longer pending at time of locking. Skipping."
                        )
                        continue

                    job.status = NotificationJob.STATUS_SENDING
                    job.save(update_fields=["status"])
                    logger.info(f"Job {job.id} status updated to SENDING.")

                    try:
                        handler_class = DELIVERY_HANDLERS.get(job.channel)
                        if not handler_class:
                            logger.warning(
                                f"No delivery handler found for channel: {job.channel} (Job ID: {job.id}). Marking as failed."
                            )
                            job.status = NotificationJob.STATUS_FAILED
                            job.failed_reason = "No handler found for channel."
                            job.save(update_fields=["status", "failed_reason"])
                            continue

                        message_payload = job.message_data
                        handler_class.send(job.recipient_id, message_payload, job.id)

                        job.status = NotificationJob.STATUS_SENT
                        job.sent_at = timezone.now()
                        job.save(update_fields=["status", "sent_at"])
                        logger.info(
                            f"Notification job {job.id} processed successfully."
                        )

                    except Exception as e:
                        job.retries_count = (job.retries_count or 0) + 1
                        job.failed_reason = str(e)[:255]

                        if job.retries_count >= job.max_retries:
                            job.status = NotificationJob.STATUS_FAILED
                            logger.error(
                                f"Notification job {job.id} permanently failed after {job.max_retries} retries: {e}",
                                exc_info=True,
                            )
                        else:
                            job.status = NotificationJob.STATUS_PENDING
                            job.scheduled_at = timezone.now() + timedelta(minutes=5)
                            logger.warning(
                                f"Notification job {job.id} failed, retrying ({job.retries_count}/{job.max_retries}): {e}"
                            )

                        # Save the updated status (PENDING for retry)
                        job.save(
                            update_fields=["status", "retries_count", "failed_reason"]
                        )

        except DatabaseError as e:
            logger.error(f"Database error during job processing: {e}", exc_info=True)
        except Exception as e:
            logger.exception(f"Unexpected error in process_pending_jobs batch: {e}")
