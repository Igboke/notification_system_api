"""
Views
"""

from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import get_user_model
from notifications_app.utils import decode_verification_token
from .serializers import UserRegistrationSerializer


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
