from datetime import timedelta
from typing import Any

from django.utils import timezone
from rest_framework.reverse import reverse

from airport.models import Airplane, AirplaneType, Airport, Crew, Flight, Order, Route, Ticket


def detail_url(view_name: str, instance_id: int) -> str:
    """Return detail URL for a specific model."""

    return reverse(f"airport:{view_name}-detail", args=[instance_id])


def sample_crew(**params: Any) -> Crew:
    defaults = {"first_name": "Ivan", "last_name": "Pilot"}
    defaults.update(params)

    return Crew.objects.create(**defaults)


def sample_airplane_type(**params: Any) -> AirplaneType:
    defaults = {"name": "Cargo"}
    defaults.update(params)

    return AirplaneType.objects.create(**defaults)


def sample_airplane(**params: Any) -> Airplane:
    if "airplane_type" not in params:
        params["airplane_type"] = sample_airplane_type()

    defaults = {"name": "Sample Airplane", "rows": 10, "seats_in_row": 6}
    defaults.update(params)

    return Airplane.objects.create(**defaults)


def sample_airport(**params: Any) -> Airport:
    defaults = {"name": "Sample Airport", "closest_big_city": "Sample City"}
    defaults.update(params)

    return Airport.objects.create(**defaults)


def sample_route(**params: Any) -> Route:
    if "source" not in params:
        params["source"] = sample_airport(name="Source")

    if "destination" not in params:
        params["destination"] = sample_airport(name="Destination")

    defaults = {"distance": 100}
    defaults.update(params)

    return Route.objects.create(**defaults)


def sample_flight(**params: Any) -> Flight:
    if "route" not in params:
        params["route"] = sample_route()

    if "airplane" not in params:
        params["airplane"] = sample_airplane()

    defaults = {
        "departure_time": timezone.now() + timedelta(hours=1),
        "arrival_time": timezone.now() + timedelta(hours=3),
    }
    defaults.update(params)

    return Flight.objects.create(**defaults)


def sample_ticket(flight: Flight, order: Order, **params: Any) -> Ticket:
    defaults = {"row": 1, "seat": 1, "flight": flight, "order": order}
    defaults.update(params)

    return Ticket.objects.create(**defaults)
