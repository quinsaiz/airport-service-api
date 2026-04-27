from django.conf import settings
from django.contrib import admin
from django.db import models
from django.db.models import UniqueConstraint
from django.utils import timezone


class AirplaneType(models.Model):
    name = models.CharField(max_length=55)

    def __str__(self) -> str:
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=55)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()
    airplane_type = models.ForeignKey(
        "AirplaneType", on_delete=models.CASCADE, related_name="airplanes"
    )

    @property
    def capacity(self) -> int:
        return self.rows * self.seats_in_row

    def __str__(self) -> str:
        return f"{self.name} (Type: {self.airplane_type.name})"


class Airport(models.Model):
    name = models.CharField(max_length=55)
    closest_big_city = models.CharField(max_length=55)

    def __str__(self) -> str:
        return f"{self.name} ({self.closest_big_city})"


class Crew(models.Model):
    first_name = models.CharField(max_length=55)
    last_name = models.CharField(max_length=55)

    @property
    @admin.display(ordering="first_name", description="Full Name")
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def __str__(self) -> str:
        return self.full_name

    class Meta:
        verbose_name_plural = "Crew"


class Route(models.Model):
    source = models.ForeignKey(
        "Airport", on_delete=models.CASCADE, related_name="departure_routes"
    )
    destination = models.ForeignKey(
        "Airport", on_delete=models.CASCADE, related_name="arrival_routes"
    )
    distance = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.source.name} -> {self.destination.name}"


class Flight(models.Model):
    route = models.ForeignKey("Route", on_delete=models.CASCADE, related_name="flights")
    airplane = models.ForeignKey(
        "Airplane", on_delete=models.CASCADE, related_name="flights"
    )
    crew = models.ManyToManyField("Crew", related_name="flights")
    departure_time = models.DateTimeField()
    arrival_time = models.DateTimeField()

    class Meta:
        ordering = ["-departure_time"]

    def __str__(self) -> str:
        return f"{self.route} ({self.departure_time.strftime('%Y-%m-%d %H:%M')})"


class Order(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders"
    )

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {self.user.email}"


class Ticket(models.Model):
    row = models.PositiveIntegerField()
    seat = models.PositiveIntegerField()
    flight = models.ForeignKey(
        "Flight", on_delete=models.CASCADE, related_name="tickets"
    )
    order = models.ForeignKey("Order", on_delete=models.CASCADE, related_name="tickets")

    class Meta:
        ordering = ["row", "seat"]
        constraints = [
            UniqueConstraint(
                fields=["row", "seat", "flight"], name="unique_row_seat_flight"
            ),
        ]

    @staticmethod
    def validate_ticket(
        row: int, seat: int, flight: Flight, error_to_raise: type[Exception]
    ) -> None:
        """
        Validates the ticket booking:
        - Checks if the flight hasn't departed yet.
        - Checks if the chosen row and seat are within the airplane's capacity.
        """

        if flight.departure_time < timezone.now():
            raise error_to_raise(
                {
                    "departure_time": "Cannot book a ticket for a flight that has already departed."
                }
            )

        airplane = flight.airplane

        for ticket_attr_value, ticket_attr_name, airplane_attr_name in [
            (row, "row", "rows"),
            (seat, "seat", "seats_in_row"),
        ]:
            count_attrs = getattr(airplane, airplane_attr_name)
            if not (1 <= ticket_attr_value <= count_attrs):
                raise error_to_raise(
                    {
                        ticket_attr_name: f"{ticket_attr_name} must be between 1 and {count_attrs}"
                    }
                )

    def __str__(self) -> str:
        return f"{self.flight} (row: {self.row}, seat: {self.seat})"
