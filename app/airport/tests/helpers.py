from datetime import timedelta
from typing import Any

from django.utils import timezone

from airport.models import Airplane, AirplaneType, Airport, Flight, Route


def sample_airport(**params: Any) -> Airport:
    defaults = {
        "name": "Sample Airport",
        "closest_big_city": "Sample City",
    }
    defaults.update(params)
    return Airport.objects.create(**defaults)


def sample_flight(**params: Any) -> Flight:
    if "route" not in params:
        airport_1 = Airport.objects.create(name="Source", closest_big_city="City 1")
        airport_2 = Airport.objects.create(
            name="Destination", closest_big_city="City 2"
        )
        route = Route.objects.create(
            source=airport_1, destination=airport_2, distance=100
        )
        params["route"] = route

    if "airplane" not in params:
        airplane_type = AirplaneType.objects.create(name="Cargo")
        airplane = Airplane.objects.create(
            name="An-225", rows=10, seats_in_row=5, airplane_type=airplane_type
        )
        params["airplane"] = airplane

    defaults = {
        "departure_time": timezone.now() + timedelta(hours=1),
        "arrival_time": timezone.now() + timedelta(hours=3),
    }
    defaults.update(params)

    return Flight.objects.create(**defaults)
