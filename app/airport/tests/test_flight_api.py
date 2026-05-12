import datetime

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Order
from airport.tests.helpers import (
    detail_url,
    sample_airplane,
    sample_airport,
    sample_crew,
    sample_flight,
    sample_route,
    sample_ticket,
)

FLIGHT_URL = reverse("airport:flight-list")


class PublicFlightApiTests(APITestCase):
    def test_filter_flights_by_source(self) -> None:
        route_1 = sample_route(source=sample_airport(name="Kyiv"))
        route_2 = sample_route(source=sample_airport(name="Lviv"))

        flight_1 = sample_flight(route=route_1)
        sample_flight(route=route_2)

        res = self.client.get(FLIGHT_URL, {"source": "kyiv"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], flight_1.pk)

    def test_tickets_available_count(self) -> None:
        """Ensure tickets_available is calculated correctly (capacity - booked tickets)."""

        airplane = sample_airplane(name="Small", rows=2, seats_in_row=2)
        flight = sample_flight(airplane=airplane)

        user = get_user_model().objects.create_user(email="test@email.com", password="password123")
        order = Order.objects.create(user=user)

        sample_ticket(flight=flight, order=order)
        sample_ticket(row=1, seat=2, flight=flight, order=order)

        res = self.client.get(FLIGHT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"][0]["tickets_available"], 2)

    def test_filter_flights_by_date(self) -> None:
        date_str = "2026-05-27"
        departure_time = datetime.datetime(2026, 5, 27, 10, 0, tzinfo=datetime.UTC)

        flight_1 = sample_flight(departure_time=departure_time)
        sample_flight(departure_time=departure_time + datetime.timedelta(days=1))

        res = self.client.get(FLIGHT_URL, {"date": date_str})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], flight_1.pk)

    def test_filter_flights_by_route_id(self) -> None:
        route_1 = sample_route()
        route_2 = sample_route()

        flight_1 = sample_flight(route=route_1)
        sample_flight(route=route_2)

        res = self.client.get(FLIGHT_URL, {"route": route_1.pk})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], flight_1.pk)

    def test_filter_flights_by_invalid_route_id_returns_all(self) -> None:
        """An invalid (noninteger) route filter should not crash — returns all flights."""

        sample_flight()

        res = self.client.get(FLIGHT_URL, {"route": "not-an-int"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_flight_detail_view(self) -> None:
        """Ensure detailed flight view returns nested airplane and crew data."""

        flight = sample_flight()
        crew_member = sample_crew(first_name="John", last_name="Pilot")
        flight.crew.add(crew_member)

        res = self.client.get(detail_url("flight", flight.pk))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["airplane"]["name"], flight.airplane.name)
        self.assertEqual(res.data["crew"][0]["full_name"], crew_member.full_name)

    def test_flight_detail_contains_route_info(self) -> None:
        flight = sample_flight()

        res = self.client.get(detail_url("flight", flight.pk))

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("route", res.data)
        self.assertIn("source", res.data["route"])
        self.assertIn("destination", res.data["route"])

    def test_create_flight_unauthenticated(self) -> None:
        res = self.client.post(FLIGHT_URL, {})
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class AuthenticatedFlightApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="user@test.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_create_flight_forbidden_for_regular_user(self) -> None:
        res = self.client.post(FLIGHT_URL, {})
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_flight_forbidden_for_regular_user(self) -> None:
        flight = sample_flight()
        res = self.client.delete(detail_url("flight", flight.pk))
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminFlightApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="admin@test.com", password="password123", is_staff=True)
        self.client.force_authenticate(user=self.user)

    def test_create_flight(self) -> None:
        route = sample_route()
        airplane = sample_airplane()
        crew = sample_crew()

        payload = {
            "route": route.pk,
            "airplane": airplane.pk,
            "departure_time": "2030-06-01T10:00:00Z",
            "arrival_time": "2030-06-01T14:00:00Z",
            "crew": [crew.pk],
        }

        res = self.client.post(FLIGHT_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_delete_flight(self) -> None:
        from airport.models import Flight

        flight = sample_flight()

        res = self.client.delete(detail_url("flight", flight.pk))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Flight.objects.filter(pk=flight.pk).exists())
