"""
Urls
"""

from django.urls import path
from .views import UserRegistrationView, EmailVerificationView, ArticleCreateView

urlpatterns = [
    path("register/", UserRegistrationView.as_view(), name="user-register"),
    path("verify-email/", EmailVerificationView.as_view(), name="verify-email"),
    path("article/", ArticleCreateView.as_view(), name="article-create"),
]
