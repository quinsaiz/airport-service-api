from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from airport.models import Airplane, AirplaneType, Airport, Crew, Flight, Order, Route, Ticket
from airport.tasks import send_ticket_email

class AirplaneTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AirplaneType
        fields = ("id", "name")


class AirplaneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airplane
        fields = ("id", "name", "rows", "seats_in_row", "airplane_type", "capacity")
        read_only_fields = ("id", "capacity")


class AirplaneListSerializer(AirplaneSerializer):
    airplane_type = serializers.SlugRelatedField(slug_field="name", read_only=True)


class AirportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Airport
        fields = ("id", "name", "closest_big_city")


class CrewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Crew
        fields = ("id", "first_name", "last_name", "full_name")
        read_only_fields = ("id", "full_name")


class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = ("id", "source", "destination", "distance")


class RouteListSerializer(RouteSerializer):
    source = serializers.SlugRelatedField(slug_field="name", read_only=True)
    destination = serializers.SlugRelatedField(slug_field="name", read_only=True)


class FlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = Flight
        fields = ("id", "route", "airplane", "crew", "departure_time", "arrival_time")


class FlightListSerializer(serializers.ModelSerializer):
    route_from = serializers.CharField(source="route.source.name", read_only=True)
    route_to = serializers.CharField(source="route.destination.name", read_only=True)
    airplane_name = serializers.CharField(source="airplane.name", read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = (
            "id",
            "departure_time",
            "arrival_time",
            "route_from",
            "route_to",
            "airplane_name",
            "tickets_available",
        )


class FlightDetailSerializer(serializers.ModelSerializer):
    route = RouteSerializer(read_only=True)
    airplane = AirplaneSerializer(read_only=True)
    crew = CrewSerializer(many=True, read_only=True)
    tickets_available = serializers.IntegerField(read_only=True)

    class Meta:
        model = Flight
        fields = ("id", "route", "airplane", "crew", "departure_time", "arrival_time", "tickets_available")


class TicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight")

    def validate(self, attrs: dict) -> dict:
        """Validate that the chosen row and seat are valid
        for the flight's aircraft capacity.
        """

        data = super().validate(attrs)
        instance = getattr(self, "instance", None)

        row: int | None = attrs.get("row", getattr(instance, "row", None))
        seat: int | None = attrs.get("seat", getattr(instance, "seat", None))
        flight: Flight | None = attrs.get("flight", getattr(instance, "flight", None))

        if flight and row and seat:
            Ticket.validate_ticket(row, seat, flight, ValidationError)

        return data


class OrderSerializer(serializers.ModelSerializer):
    tickets = TicketSerializer(many=True, allow_empty=False)

    class Meta:
        model = Order
        fields = ("uuid", "created_at", "tickets")
        read_only_fields = ("uuid", "created_at")

    def validate_tickets(self, value):
        max_tickets_per_order = 3

        if len(value) > max_tickets_per_order:
            raise ValidationError(f"You cannot book more than {max_tickets_per_order} tickets in one order.")

        return value

    def create(self, validated_data: dict) -> Order:
        with transaction.atomic():
            tickets_data = validated_data.pop("tickets", [])
            order = Order.objects.create(**validated_data)

            for ticket in tickets_data:
                Ticket.objects.create(order=order, **ticket)

            transaction.on_commit(lambda: send_ticket_email.delay(order.id))

            return order


class TicketValidationFlightSerializer(serializers.ModelSerializer):
    route_from = serializers.CharField(source="route.source.closest_big_city", read_only=True)
    route_to = serializers.CharField(source="route.destination.closest_big_city", read_only=True)
    airplane_name = serializers.CharField(source="airplane.name", read_only=True)

    class Meta:
        model = Flight
        fields = ("id", "departure_time", "arrival_time", "route_from", "route_to", "airplane_name")


class TicketValidationItemSerializer(serializers.ModelSerializer):
    flight = TicketValidationFlightSerializer(read_only=True)

    class Meta:
        model = Ticket
        fields = ("id", "row", "seat", "flight")


class TicketValidationSerializer(serializers.ModelSerializer):
    passenger_name = serializers.CharField(source="user.get_full_name", read_only=True)
    passenger_email = serializers.EmailField(source="user.email", read_only=True)
    is_valid = serializers.SerializerMethodField()
    tickets = TicketValidationItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("uuid", "created_at", "passenger_name", "passenger_email", "is_valid", "tickets")

    def get_is_valid(self, obj: Order) -> bool:
        now = timezone.now()

        return obj.tickets.filter(flight__departure_time__gte=now).exists()
