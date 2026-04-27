from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Airport

ROUTE_URL = reverse("airport:route-list")


class RouteApiTests(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="password123"
        )
        self.client.force_authenticate(self.user)
        self.airport_1 = Airport.objects.create(
            name="Boryspil", closest_big_city="Kyiv"
        )
        self.airport_2 = Airport.objects.create(name="Lviv", closest_big_city="Lviv")

    def test_create_route_forbidden(self):
        payload = {
            "source": self.airport_1.pk,
            "destination": self.airport_2.pk,
            "distance": 500,
        }
        res = self.client.post(ROUTE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)
