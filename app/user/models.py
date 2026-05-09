from typing import Any

from django.contrib.auth.models import AbstractUser
from django.contrib.auth.models import UserManager as CustomUserManager
from django.db import models


class UserManager(CustomUserManager["User"]):
    """Custom user model manager where email is the unique identifiers
    for authentication instead of usernames.
    """

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields: Any) -> "User":
        if not email:
            raise ValueError("Email must be set")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(
        self, username: str | None = None, email: str | None = None, password: str | None = None, **extra_fields: Any
    ) -> "User":
        if not password:
            raise ValueError("Password must be set")

        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

        return self._create_user(email or "", password, **extra_fields)

    def create_superuser(
        self, username: str | None = None, email: str | None = None, password: str | None = None, **extra_fields: Any
    ) -> "User":
        if not password:
            raise ValueError("Superuser must have a password")

        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email or "", password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("Email address", unique=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self) -> str:
        return str(self.email)
