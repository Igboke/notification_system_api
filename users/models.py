"""
Django User Model
"""

import logging
from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, BaseUserManager


logger = logging.getLogger(__name__)


class CustomUserManager(BaseUserManager):
    """
    Custom user manager where email is the unique identifier (USERNAME_FIELD).
    Provides methods to create users and superusers.
    """

    def create_user(self, email, password=None, **extra_fields):
        """
        Creates and saves a regular user with the given email and password.
        Additional fields can be passed via extra_fields.
        """
        if not email:
            logger.error("The Email field must be set")
            raise ValueError("The Email field must be set")

        email = self.normalize_email(email)  # Normalize the email address

        # Get the User model dynamically. Required in managers.
        user_model = get_user_model()
        username = email

        # Create the user instance.
        # Note: AbstractUser still has a 'username' field.
        # Since REQUIRED_FIELDS is empty, createsuperuser won't prompt for it,
        # The AbstractUser base class handles defaults for fields like is_active, etc.
        user = user_model(
            username=username, email=email, **extra_fields
        )  # Set email directly

        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Creates and saves a superuser with the given email and password.
        Sets necessary staff and superuser flags.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            logger.error("Superuser must have is_staff=True.")
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            logger.error("Superuser must have is_superuser=True.")
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    User Model for the client
    """

    email = models.EmailField(
        unique=True, help_text="Required. Enter a valid email address."
    )
    is_verified = models.BooleanField(
        ("verified"),
        default=False,
        help_text=("Designates whether the user has verified their email address."),
    )
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        """
        Information about the information
        """

        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return self.email
