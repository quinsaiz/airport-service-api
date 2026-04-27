from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Airport
from airport.serializers import AirportSerializer
from airport.tests.helpers import sample_airport

AIRPORT_URL = reverse("airport:airport-list")


def detail_url(airport_id: int) -> str:
    return reverse("airport:airport-detail", args=[airport_id])


class UnauthenticatedAirportApiTests(APITestCase):
    def test_auth_not_required(self):
        res = self.client.get(AIRPORT_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AuthenticatedAirportApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_airports(self):
        sample_airport()
        sample_airport(name="Boryspil")

        res = self.client.get(AIRPORT_URL)

        airports = Airport.objects.all()
        serializer = AirportSerializer(airports, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_create_airport_forbidden(self):
        payload = {
            "name": "Boryspil",
            "closest_big_city": "Kyiv",
        }

        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminAirportApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com",
            password="password123",
            is_staff=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_create_airport(self):
        payload = {
            "name": "Boryspil",
            "closest_big_city": "Kyiv",
        }

        res = self.client.post(AIRPORT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        airport = Airport.objects.get(pk=res.data["id"])
        for key in payload:
            self.assertEqual(payload[key], getattr(airport, key))

    def test_delete_airport(self):
        airport = sample_airport()
        url = detail_url(airport.pk)

        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Airport.objects.filter(pk=airport.pk).exists())
