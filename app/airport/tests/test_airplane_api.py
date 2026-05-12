from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Airplane
from airport.tests.helpers import detail_url, sample_airplane, sample_airplane_type

AIRPLANE_URL = reverse("airport:airplane-list")


class UnauthenticatedAirplaneApiTests(APITestCase):
    def test_auth_not_required_for_list(self) -> None:
        res = self.client.get(AIRPLANE_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AuthenticatedAirplaneApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="test@email.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_list_airplanes(self) -> None:
        sample_airplane(name="Boeing 737")
        sample_airplane(name="Airbus A320")

        res = self.client.get(AIRPLANE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_list_uses_slug_for_airplane_type(self) -> None:
        """List serializer should return airplane_type as a name string, not an id."""

        airplane_type = sample_airplane_type(name="Passenger")
        sample_airplane(airplane_type=airplane_type)

        res = self.client.get(AIRPLANE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"][0]["airplane_type"], "Passenger")

    def test_capacity_is_returned(self) -> None:
        sample_airplane(rows=10, seats_in_row=6)

        res = self.client.get(AIRPLANE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"][0]["capacity"], 60)

    def test_create_airplane_forbidden(self) -> None:
        airplane_type = sample_airplane_type()
        payload = {
            "name": "Boeing 737",
            "rows": 30,
            "seats_in_row": 6,
            "airplane_type": airplane_type.pk,
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_airplane_forbidden(self) -> None:
        airplane = sample_airplane()

        res = self.client.delete(detail_url("airplane", airplane.pk))

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirplaneApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="admin@test.com", password="password123", is_staff=True)
        self.client.force_authenticate(user=self.user)

    def test_create_airplane(self) -> None:
        airplane_type = sample_airplane_type()
        payload = {
            "name": "Boeing 737",
            "rows": 30,
            "seats_in_row": 6,
            "airplane_type": airplane_type.pk,
        }

        res = self.client.post(AIRPLANE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        airplane = Airplane.objects.get(pk=res.data["id"])
        self.assertEqual(airplane.name, payload["name"])
        self.assertEqual(airplane.rows, payload["rows"])
        self.assertEqual(airplane.seats_in_row, payload["seats_in_row"])
        self.assertEqual(airplane.airplane_type.pk, airplane_type.pk)

    def test_delete_airplane(self) -> None:
        airplane = sample_airplane()

        res = self.client.delete(detail_url("airplane", airplane.pk))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Airplane.objects.filter(pk=airplane.pk).exists())

    def test_update_airplane(self) -> None:
        airplane = sample_airplane(name="Old Name")
        airplane_type = sample_airplane_type(name="New Type")
        payload = {
            "name": "New Name",
            "rows": 20,
            "seats_in_row": 4,
            "airplane_type": airplane_type.pk,
        }

        res = self.client.put(detail_url("airplane", airplane.pk), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        airplane.refresh_from_db()
        self.assertEqual(airplane.name, "New Name")
