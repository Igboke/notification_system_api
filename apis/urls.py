"""
Urls
"""

from django.urls import path
from .views import UserRegistrationView, EmailVerificationView

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
]
