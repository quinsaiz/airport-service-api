import datetime

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import (
    Airport,
    Route,
    AirplaneType,
    Airplane,
    Order,
    Ticket,
    Crew,
)
from airport.tests.helpers import sample_flight

FLIGHT_URL = reverse("airport:flight-list")


class PublicFlightApiTests(APITestCase):
    def test_filter_flights_by_source(self):
        airport_1 = Airport.objects.create(name="Kyiv", closest_big_city="Kyiv")
        airport_2 = Airport.objects.create(name="Paris", closest_big_city="Paris")
        airport_3 = Airport.objects.create(name="Lviv", closest_big_city="Lviv")

        route_1 = Route.objects.create(
            source=airport_1, destination=airport_2, distance=2000
        )
        route_2 = Route.objects.create(
            source=airport_3, destination=airport_2, distance=500
        )

        flight_1 = sample_flight(route=route_1)
        sample_flight(route=route_2)

        res = self.client.get(FLIGHT_URL, {"source": "kyiv"})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], flight_1.pk)

    def test_tickets_available_count(self):
        """Ensure tickets_available is calculated correctly (capacity - booked tickets)."""

        airplane = Airplane.objects.create(
            name="Small",
            rows=2,
            seats_in_row=2,
            airplane_type=AirplaneType.objects.create(name="Cargo"),
        )
        flight = sample_flight(airplane=airplane)

        user = get_user_model().objects.create_user(
            email="test@test.com", password="password123"
        )
        order = Order.objects.create(user=user)

        Ticket.objects.create(row=1, seat=1, flight=flight, order=order)
        Ticket.objects.create(row=1, seat=2, flight=flight, order=order)

        res = self.client.get(FLIGHT_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"][0]["tickets_available"], 2)

    def test_filter_flights_by_date(self):
        date_str = "2026-05-27"
        naive_datetime = datetime.datetime(2026, 5, 27, 10, 0)
        departure_time = timezone.make_aware(naive_datetime)

        flight_1 = sample_flight(departure_time=departure_time)
        sample_flight(departure_time=departure_time + datetime.timedelta(days=1))

        res = self.client.get(FLIGHT_URL, {"date": date_str})

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)
        self.assertEqual(res.data["results"][0]["id"], flight_1.pk)

    def test_flight_detail_view(self):
        """Ensure detailed flight view returns nested airplane and crew data."""

        flight = sample_flight()
        crew_member = Crew.objects.create(first_name="Ivan", last_name="Sirko")
        flight.crew.add(crew_member)

        url = reverse("airport:flight-detail", args=[flight.pk])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["airplane"]["name"], flight.airplane.name)
        self.assertEqual(res.data["crew"][0]["full_name"], crew_member.full_name)
