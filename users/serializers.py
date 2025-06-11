from django.contrib.auth import get_user_model
from rest_framework import serializers
from .signals import user_registered

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, style={"input_type": "password"}
    )

    class Meta:
        model = User
        fields = ("id", "email", "password")
        read_only_fields = ("id",)

    def create(self, validated_data):
        """
        Create the user, hash the password, and send the registration signal.
        """
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )

        # Fire the signal to trigger notifications
        user_registered.send(sender=self.__class__, user=user)

        return user
