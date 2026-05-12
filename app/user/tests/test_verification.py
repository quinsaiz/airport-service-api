from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from user.tests.helpers import create_inactive_user
from user.verification_token import ALGORITHM, generate_verification_token, verify_verification_token

TOKEN_URL = reverse("user:token_obtain_pair")


def verify_email_url(token: str) -> str:
    return reverse("user:verify-email", kwargs={"token": token})


class VerifyEmailViewTests(APITestCase):
    def setUp(self) -> None:
        self.user = create_inactive_user(email="verify@email.com", password="password123")

    def test_valid_token_activates_user(self) -> None:
        token = generate_verification_token(self.user.pk)

        res = self.client.get(verify_email_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)

    def test_valid_token_returns_success_message(self) -> None:
        token = generate_verification_token(self.user.pk)

        res = self.client.get(verify_email_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("verified", res.data["detail"].lower())

    def test_already_active_user_returns_400(self) -> None:
        self.user.is_active = True
        self.user.save()
        token = generate_verification_token(self.user.pk)

        res = self.client.get(verify_email_url(token))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already", res.data["detail"].lower())

    def test_expired_token_returns_400(self) -> None:
        past = timezone.now() - timedelta(seconds=1)
        payload = {
            "user_id": self.user.pk,
            "purpose": "email_verification",
            "iat": int((past - timedelta(hours=24)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

        res = self.client.get(verify_email_url(expired_token))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", res.data["detail"].lower())

    def test_invalid_token_returns_400(self) -> None:
        res = self.client.get(verify_email_url("totally.invalid.token"))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_with_wrong_purpose_returns_400(self) -> None:
        """A structurally valid JWT but with wrong purpose must be rejected."""

        payload = {
            "user_id": self.user.pk,
            "purpose": "something_else",
            "iat": int(timezone.now().timestamp()),
            "exp": int((timezone.now() + timedelta(hours=24)).timestamp()),
        }
        wrong_purpose_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

        res = self.client.get(verify_email_url(wrong_purpose_token))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_nonexistent_user_returns_400(self) -> None:
        token = generate_verification_token(user_id=99999)

        res = self.client.get(verify_email_url(token))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_accessible_without_authentication(self) -> None:
        """verify-email is a public endpoint — no auth header required."""

        token = generate_verification_token(self.user.pk)
        self.client.logout()

        res = self.client.get(verify_email_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_user_can_log_in_after_verification(self) -> None:
        """After verifying email the user should be able to obtain a JWT."""

        token = generate_verification_token(self.user.pk)
        self.client.get(verify_email_url(token))

        res = self.client.post(TOKEN_URL, {"email": "verify@email.com", "password": "password123"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)


class VerificationTokenTests(APITestCase):
    def test_generate_returns_string(self) -> None:
        token = generate_verification_token(user_id=1)
        self.assertIsInstance(token, str)

    def test_verify_returns_correct_user_id(self) -> None:
        token = generate_verification_token(user_id=42)
        self.assertEqual(verify_verification_token(token), 42)

    def test_expired_token_raises(self) -> None:
        past = timezone.now() - timedelta(seconds=1)
        payload = {
            "user_id": 1,
            "purpose": "email_verification",
            "iat": int((past - timedelta(hours=24)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

        with self.assertRaises(jwt.ExpiredSignatureError):
            verify_verification_token(expired_token)

    def test_wrong_purpose_raises(self) -> None:
        payload = {
            "user_id": 1,
            "purpose": "something_else",
            "iat": int(timezone.now().timestamp()),
            "exp": int((timezone.now() + timedelta(hours=24)).timestamp()),
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

        with self.assertRaises(jwt.InvalidTokenError):
            verify_verification_token(token)

    def test_tampered_token_raises(self) -> None:
        token = generate_verification_token(user_id=5)
        tampered = token[:-5] + "XXXXX"

        with self.assertRaises(jwt.InvalidTokenError):
            verify_verification_token(tampered)
