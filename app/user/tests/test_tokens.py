from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from user.tests.helpers import create_active_user, create_inactive_user

TOKEN_URL = reverse("user:token_obtain_pair")

class TokenTests(APITestCase):
    def test_token_login_success(self) -> None:
        create_active_user(email="test@email.com", password="password123")

        res = self.client.post(TOKEN_URL, {"email": "test@email.com", "password": "password123"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)
        self.assertIn("refresh", res.data)

    def test_token_login_inactive_user_fails(self) -> None:
        """Unverified (is_active=False) users must be rejected at login."""

        create_inactive_user(email="inactive@email.com", password="password123")

        res = self.client.post(TOKEN_URL, {"email": "inactive@email.com", "password": "password123"})

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", res.data)

    def test_token_login_wrong_password(self) -> None:
        create_active_user(email="test@email.com", password="correctpass")

        res = self.client.post(TOKEN_URL, {"email": "test@email.com", "password": "wrongpass"})

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", res.data)

    def test_token_login_nonexistent_user(self) -> None:
        res = self.client.post(TOKEN_URL, {"email": "ghost@email.com", "password": "password123"})

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)
