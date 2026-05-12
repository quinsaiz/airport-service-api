from datetime import timedelta

import jwt
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from airport.ticket_token import ALGORITHM, generate_ticket_token, verify_ticket_token


class TicketTokenTests(TestCase):
    def test_generate_token_returns_string(self) -> None:
        token = generate_ticket_token(ticket_id=42)
        self.assertIsInstance(token, str)
        self.assertTrue(len(token) > 0)

    def test_verify_token_returns_correct_ticket_id(self) -> None:
        ticket_id = 99
        token = generate_ticket_token(ticket_id=ticket_id)
        result = verify_ticket_token(token)
        self.assertEqual(result, ticket_id)

    def test_token_payload_contains_expected_fields(self) -> None:
        token = generate_ticket_token(ticket_id=7)
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

        self.assertIn("ticket_id", payload)
        self.assertIn("iat", payload)
        self.assertIn("exp", payload)
        self.assertEqual(payload["ticket_id"], 7)

    def test_token_expires_after_lifetime(self) -> None:
        """Token with exp in the past should raise ExpiredSignatureError."""

        past = timezone.now() - timedelta(seconds=1)
        payload = {
            "ticket_id": 1,
            "iat": int((past - timedelta(days=365)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

        with self.assertRaises(jwt.ExpiredSignatureError):
            verify_ticket_token(expired_token)

    def test_invalid_token_raises_error(self) -> None:
        with self.assertRaises(jwt.InvalidTokenError):
            verify_ticket_token("this.is.not.a.valid.token")

    def test_token_tampered_signature_raises_error(self) -> None:
        token = generate_ticket_token(ticket_id=5)
        tampered = token[:-5] + "XXXXX"

        with self.assertRaises(jwt.InvalidTokenError):
            verify_ticket_token(tampered)

    def test_token_signed_with_wrong_key_raises_error(self) -> None:
        payload = {
            "ticket_id": 1,
            "iat": int(timezone.now().timestamp()),
            "exp": int((timezone.now() + timedelta(days=365)).timestamp()),
        }
        token_wrong_key = jwt.encode(payload, "wrong-secret", algorithm=ALGORITHM)

        with self.assertRaises(jwt.InvalidSignatureError):
            verify_ticket_token(token_wrong_key)
