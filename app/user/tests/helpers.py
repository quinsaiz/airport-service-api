from typing import Any

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser


def create_active_user(**params: Any) -> AbstractUser:
    defaults = {"email": "test@email.com", "password": "password123"}
    defaults.update(params)
    user = get_user_model().objects.create_user(**defaults)
    user.is_active = True
    user.save()

    return user


def create_inactive_user(**params: Any) -> AbstractUser:
    defaults = {"email": "inactive@email.com", "password": "password123"}
    defaults.update(params)
    user = get_user_model().objects.create_user(**defaults)
    user.is_active = False
    user.save()

    return user
