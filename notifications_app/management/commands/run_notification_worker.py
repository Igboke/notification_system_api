import time
import logging
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from notifications_app.models import NotificationJob
from notifications_app.delivery_handlers.email_handler import EmailDeliveryHandler
from notifications_app.delivery_handlers.in_app_handler import InAppDeliveryHandler

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Runs the notification worker to process pending jobs from the database queue."
    )

    def add_arguments(self, parser):
        # Add an optional argument to run the command just once for testing
        parser.add_argument(
            "--run-once",
            action="store_true",
            help="Run one batch of jobs and exit.",
        )

    def handle(self, *args, **options):
        # If the --run-once flag is used, just process jobs and exit.
        if options["run_once"]:
            self.stdout.write(self.style.SUCCESS("Running one-time job processing..."))
            self.process_pending_jobs()
            self.stdout.write(self.style.SUCCESS("One-time job processing complete."))
            return

        self.stdout.write(
            self.style.SUCCESS("Starting notification worker... Press Ctrl+C to stop.")
        )

        # This loop keeps the worker running continuously
        while True:
            try:
                self.process_pending_jobs()
                time.sleep(10)  # Poll every 10 seconds for new jobs
            except KeyboardInterrupt:
                self.stdout.write(self.style.SUCCESS("Notification worker stopped."))
                break
            except Exception as e:
                logger.error(f"An unhandled error occurred in the worker loop: {e}")
                time.sleep(30)

    def process_pending_jobs(self):
        """
        Fetches and processes a batch of pending notification jobs.
        """

        jobs_to_process = NotificationJob.objects.filter(
            status=NotificationJob.STATUS_PENDING,
            scheduled_at__lte=timezone.now(),
        ).order_by("scheduled_at")[
            :10
        ]  # Process a batch of 10 jobs at a time

        if not jobs_to_process:
            logger.debug(
                "No pending notification jobs found."
            )  # comment if you do not want to see this often
            return

        logger.info(f"Found {len(jobs_to_process)} pending notification jobs.")

        for job in jobs_to_process:
            # Use a separate atomic transaction for each job to ensure its status update is committed
            # even if other jobs in the batch fail.
            with transaction.atomic():
                try:
                    current_job = NotificationJob.objects.select_for_update().get(
                        id=job.id
                    )
                    if current_job.status != NotificationJob.STATUS_PENDING:
                        logger.warning(
                            f"Job {current_job.id} was already processed or is no longer pending. Skipping."
                        )
                        continue

                    current_job.status = (
                        NotificationJob.STATUS_SENDING
                    )  # Mark as sending
                    current_job.save(update_fields=["status"])

                    if current_job.channel == NotificationJob.CHANNEL_EMAIL:
                        EmailDeliveryHandler.send(
                            current_job.recipient_id, current_job.message_data
                        )
                    elif current_job.channel == NotificationJob.CHANNEL_IN_APP:
                        InAppDeliveryHandler.send(
                            current_job.recipient_id, current_job.message_data
                        )
                    else:
                        logger.warning(
                            f"Unknown channel '{current_job.channel}' for job {current_job.id}. Marking as failed."
                        )
                        current_job.status = NotificationJob.STATUS_FAILED
                        current_job.failed_reason = "Unknown notification channel."
                        current_job.save(update_fields=["status", "failed_reason"])
                        continue

                    # If successful, update job status
                    current_job.status = NotificationJob.STATUS_SENT
                    current_job.sent_at = timezone.now()
                    current_job.save(update_fields=["status", "sent_at"])
                    logger.info(
                        f"Notification job {current_job.id} processed successfully."
                    )

                except Exception as e:
                    # If an error occurs, update job status to failed or retry
                    current_job.retries_count += 1
                    current_job.failed_reason = str(e)

                    if current_job.retries_count >= current_job.max_retries:
                        current_job.status = NotificationJob.STATUS_FAILED
                        logger.error(
                            f"Notification job {current_job.id} permanently failed after {current_job.max_retries} retries: {e}"
                        )
                    else:
                        current_job.status = (
                            NotificationJob.STATUS_PENDING
                        )  # Mark for retry later
                        logger.warning(
                            f"Notification job {current_job.id} failed, retrying ({current_job.retries_count}/{current_job.max_retries}): {e}"
                        )
                    current_job.save(
                        update_fields=["status", "retries_count", "failed_reason"]
                    )
