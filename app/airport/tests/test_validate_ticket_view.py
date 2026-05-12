from datetime import timedelta

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Order
from airport.tests.helpers import sample_flight, sample_ticket
from airport.ticket_token import ALGORITHM, generate_ticket_token


def validate_url(token: str) -> str:
    return reverse("airport:ticket-validate", kwargs={"token": token})


class ValidateTicketViewTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(
            email="passenger@test.com",
            password="password123",
            first_name="Ivan",
            last_name="Franko",
        )

        self.flight = sample_flight()
        self.order = Order.objects.create(user=self.user)
        self.ticket = sample_ticket(flight=self.flight, order=self.order)

    def test_valid_token_returns_200(self) -> None:
        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_valid_token_returns_correct_ticket_data(self) -> None:
        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["id"], self.ticket.pk)
        self.assertEqual(res.data["row"], self.ticket.row)
        self.assertEqual(res.data["seat"], self.ticket.seat)

    def test_valid_token_returns_passenger_name(self) -> None:
        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["passenger_name"], self.user.get_full_name())

    def test_valid_token_returns_passenger_email(self) -> None:
        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["passenger_email"], self.user.email)

    def test_valid_token_returns_order_uuid(self) -> None:
        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["order_uuid"], str(self.order.uuid))

    def test_is_valid_true_for_future_flight(self) -> None:
        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertTrue(res.data["is_valid"])

    def test_is_valid_false_for_past_flight(self) -> None:
        past_departure = timezone.now() - timedelta(hours=5)
        past_arrival = timezone.now() - timedelta(hours=2)
        self.flight.departure_time = past_departure
        self.flight.arrival_time = past_arrival
        self.flight.save()

        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_valid"])

    def test_expired_token_returns_400(self) -> None:
        past = timezone.now() - timedelta(seconds=1)
        payload = {
            "ticket_id": self.ticket.pk,
            "iat": int((past - timedelta(days=365)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

        res = self.client.get(validate_url(expired_token))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("expired", res.data["detail"].lower())

    def test_invalid_token_returns_400(self) -> None:
        res = self.client.get(validate_url("totally.invalid.token"))

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("invalid", res.data["detail"].lower())

    def test_valid_token_nonexistent_ticket_returns_404(self) -> None:
        token = generate_ticket_token(ticket_id=99999)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_endpoint_accessible_without_authentication(self) -> None:
        """validate_ticket_view is a public endpoint — no auth required."""

        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_explicit_passenger_name_overrides_user_name(self) -> None:
        """If ticket has passenger_name set, it should be returned instead of user's name."""

        self.ticket.passenger_name = "Custom Name"
        self.ticket.save()

        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["passenger_name"], "Custom Name")

    def test_explicit_passenger_email_overrides_user_email(self) -> None:
        self.ticket.passenger_email = "custom@email.com"
        self.ticket.save()

        token = generate_ticket_token(self.ticket.pk)
        res = self.client.get(validate_url(token))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["passenger_email"], "custom@email.com")
