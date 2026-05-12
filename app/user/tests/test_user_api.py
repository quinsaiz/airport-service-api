from typing import Any

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from user.tests.helpers import create_active_user

USER_CREATE_URL = reverse("user:create")
MANAGE_URL = reverse("user:manage")


class CreateUserTests(APITestCase):
    def test_create_user_success(self) -> None:
        payload = {"email": "test@email.com", "password": "password123"}

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_create_user_is_inactive_by_default(self) -> None:
        """Serializer.create() sets is_active=False — user must confirm email first."""

        payload = {"email": "new@email.com", "password": "password123"}

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertFalse(user.is_active)

    def test_create_user_with_existing_email_fail(self) -> None:
        payload = {"email": "test@email.com", "password": "password123"}
        get_user_model().objects.create_user(**payload)

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_password_too_short(self) -> None:
        payload = {"email": "short@email.com", "password": "abc"}

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(get_user_model().objects.filter(email=payload["email"]).exists())

    def test_create_user_is_staff_is_readonly(self) -> None:
        payload = {"email": "hacker@email.com", "password": "password123", "is_staff": True}

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(email=payload["email"])
        self.assertFalse(user.is_staff)

    def test_create_user_missing_email(self) -> None:
        payload: dict[str, Any] = {"password": "password123"}

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_missing_password(self) -> None:
        payload: dict[str, Any] = {"email": "nopass@email.com"}

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)


class ManageUserTests(APITestCase):
    def setUp(self) -> None:
        self.user = create_active_user(email="test@email.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_manage_user_unauthorized(self) -> None:
        self.client.logout()
        res = self.client.get(MANAGE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manage_user_returns_own_data(self) -> None:
        res = self.client.get(MANAGE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], self.user.email)

    def test_manage_response_has_no_password_field(self) -> None:
        res = self.client.get(MANAGE_URL)

        self.assertNotIn("password", res.data)
        self.assertIn("email", res.data)
        self.assertIn("is_staff", res.data)

    def test_patch_email(self) -> None:
        res = self.client.patch(MANAGE_URL, {"email": "updated@email.com"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "updated@email.com")

    def test_patch_password(self) -> None:
        res = self.client.patch(MANAGE_URL, {"password": "newpassword123"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("newpassword123"))

    def test_patch_password_too_short_rejected(self) -> None:
        res = self.client.patch(MANAGE_URL, {"password": "abc"})

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("abc"))

    def test_patch_is_staff_is_ignored(self) -> None:
        """is_staff is read_only in the serializer — must not be changeable via API."""

        res = self.client.patch(MANAGE_URL, {"is_staff": True})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)

    def test_put_updates_user(self) -> None:
        payload: dict[str, Any] = {"email": "put@email.com", "password": "newpassword123"}

        res = self.client.put(MANAGE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "put@email.com")
        self.assertTrue(self.user.check_password("newpassword123"))
