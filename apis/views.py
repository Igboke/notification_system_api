"""
Views
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from notifications_app.utils import decode_verification_token
from notifications_app.backends.database_queue import notification_backend
from notifications_app.models import NotificationJob
from articles.models import Article
from .serializers import UserRegistrationSerializer, ArticleSerializer


User = get_user_model()


class UserRegistrationView(generics.CreateAPIView):
    """
    API view for user registration.
    Allows any user (authentication not required) to create a new account.
    """

    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]


class EmailVerificationView(APIView):
    """
    API view to verify user's email address.
    Accepts a token from the URL query parameters.
    """

    permission_classes = [permissions.AllowAny]

    def get(self, request, *args, **kwargs):
        """
        Get function
        """
        token = request.query_params.get("token")
        if not token:
            return Response(
                {"error": "Verification token is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = decode_verification_token(token)

        if not user:
            return Response(
                {"error": "Invalid or expired verification token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.is_verified:
            return Response(
                {"message": "Email has already been verified."},
                status=status.HTTP_200_OK,
            )

        user.is_verified = True
        user.save()

        return Response(
            {"message": "Email successfully verified. You can now log in."},
            status=status.HTTP_200_OK,
        )


class ArticleCreateView(generics.CreateAPIView):
    """
    API view to create a new article.
    Only authenticated users can create articles.
    """

    queryset = Article.objects.all()
    serializer_class = ArticleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Save the article with the current user as the author and
        enqueue notifications.
        """
        article = serializer.save(author=self.request.user)

        # Now, enqueue notifications for the author
        user = self.request.user

        # Enqueue an email notification
        email_data = {
            "subject": "Your Article Has Been Published!",
            "body_text": f"Hi {user.email},\n\nYour article '{article.title}' has been successfully published.",
            "body_html": f"<p>Hi {user.email},</p><p>Your article '<b>{article.title}</b>' has been successfully published.</p>",
        }
        notification_backend.enqueue(
            recipient_id=user.id,
            channel=NotificationJob.CHANNEL_EMAIL,
            message_data=email_data,
            notification_type="article_published_email",
        )

        # Enqueue an in-app notification
        in_app_data = {
            "title": "Article Published!",
            "body": f"Your new article '{article.title}' is now live.",
        }
        notification_backend.enqueue(
            recipient_id=user.id,
            channel=NotificationJob.CHANNEL_IN_APP,
            message_data=in_app_data,
            notification_type="article_published_in_app",
        )
