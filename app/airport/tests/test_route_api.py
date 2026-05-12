from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Route
from airport.tests.helpers import detail_url, sample_airport, sample_route

ROUTE_URL = reverse("airport:route-list")


class RouteApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="test@email.com", password="password123")
        self.client.force_authenticate(self.user)

        self.airport_kyiv = sample_airport(name="Boryspil", closest_big_city="Kyiv")
        self.airport_lviv = sample_airport(name="Lviv", closest_big_city="Lviv")
        self.airport_paris = sample_airport(name="CDG", closest_big_city="Paris")

    def test_create_route_forbidden(self) -> None:
        payload = {"source": self.airport_kyiv.pk, "destination": self.airport_lviv.pk, "distance": 500}

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_routes(self) -> None:
        sample_route(source=self.airport_kyiv, destination=self.airport_paris)
        sample_route(source=self.airport_lviv, destination=self.airport_paris)

        res = self.client.get(ROUTE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_list_uses_name_for_source_and_destination(self) -> None:
        """List serializer should return source/destination as name strings, not ids."""

        sample_route(source=self.airport_kyiv, destination=self.airport_paris)

        res = self.client.get(ROUTE_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        result = res.data["results"][0]
        self.assertEqual(result["source"], self.airport_kyiv.name)
        self.assertEqual(result["destination"], self.airport_paris.name)

    def test_filter_routes_by_source(self) -> None:
        sample_route(source=self.airport_kyiv, destination=self.airport_paris)
        sample_route(source=self.airport_lviv, destination=self.airport_paris)

        res = self.client.get(ROUTE_URL, {"source": "bory"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["source"], self.airport_kyiv.name)

    def test_filter_routes_by_destination(self) -> None:
        sample_route(source=self.airport_kyiv, destination=self.airport_paris)
        sample_route(source=self.airport_kyiv, destination=self.airport_lviv)

        res = self.client.get(ROUTE_URL, {"destination": "cdg"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["destination"], self.airport_paris.name)


class AdminRouteApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="admin@test.com", password="password123", is_staff=True)
        self.client.force_authenticate(self.user)

        self.airport_1 = sample_airport(name="Boryspil")
        self.airport_2 = sample_airport(name="CDG")

    def test_create_route(self) -> None:
        payload = {
            "source": self.airport_1.pk,
            "destination": self.airport_2.pk,
            "distance": 2500,
        }

        res = self.client.post(ROUTE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        route = Route.objects.get(pk=res.data["id"])
        self.assertEqual(route.source, self.airport_1)
        self.assertEqual(route.destination, self.airport_2)
        self.assertEqual(route.distance, 2500)

    def test_delete_route(self) -> None:
        route = Route.objects.create(source=self.airport_1, destination=self.airport_2, distance=2500)

        res = self.client.delete(detail_url("route", route.pk))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Route.objects.filter(pk=route.pk).exists())
