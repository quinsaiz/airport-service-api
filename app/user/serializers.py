from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import serializers

from user.tasks import send_verification_email

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "password", "is_staff")
        read_only_fields = ("id", "is_staff")
        extra_kwargs = {"password": {"write_only": True, "min_length": 6, "style": {"input_type": "password"}}}

    def create(self, validated_data: dict[str, Any]) -> User:
        """Create a new user with encrypted password and email verification."""

        user = User.objects.create_user(**validated_data, is_active=False)

        send_verification_email.delay(user.id)

        return user

    def update(self, instance: User, validated_data: dict[str, Any]) -> User:
        """Update a user with encrypted password."""

        password = validated_data.pop("password", None)
        user = super().update(instance, validated_data)

        if password:
            user.set_password(password)
            user.save()

        return user
