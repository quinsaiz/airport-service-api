from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Airport
from airport.tests.helpers import detail_url, sample_airport

AIRPORT_URL = reverse("airport:airport-list")


class UnauthenticatedAirportApiTests(APITestCase):
    def test_auth_not_required(self) -> None:
        res = self.client.get(AIRPORT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AuthenticatedAirportApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="test@email.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_list_airports(self) -> None:
        sample_airport()
        sample_airport(name="Boryspil")

        res = self.client.get(AIRPORT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_create_airport_forbidden(self) -> None:
        payload = {"name": "Boryspil", "closest_big_city": "Kyiv"}

        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="test@email.com", password="password123", is_staff=True)
        self.client.force_authenticate(user=self.user)

    def test_create_airport(self) -> None:
        payload = {"name": "Boryspil", "closest_big_city": "Kyiv"}

        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        airport = Airport.objects.get(pk=res.data["id"])
        for key, value in payload.items():
            self.assertEqual(value, getattr(airport, key))

    def test_delete_airport(self) -> None:
        airport = sample_airport()
        url = detail_url("airport", airport.pk)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Airport.objects.filter(pk=airport.pk).exists())
