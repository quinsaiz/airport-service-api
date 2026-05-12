import logging

import jwt
from django.db.models import Count, F, QuerySet
from django.db.models.functions import Greatest
from django.utils.dateparse import parse_date
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import mixins, serializers, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer

from airport.models import Airplane, AirplaneType, Airport, Crew, Flight, Order, Route, Ticket
from airport.paginations import DefaultPagination
from airport.permissions import IsAdminOrReadOnly
from airport.serializers import (
    AirplaneListSerializer,
    AirplaneSerializer,
    AirplaneTypeSerializer,
    AirportSerializer,
    CrewSerializer,
    FlightDetailSerializer,
    FlightListSerializer,
    FlightSerializer,
    OrderSerializer,
    RouteListSerializer,
    RouteSerializer,
    TicketValidationSerializer,
)
from airport.ticket_token import verify_ticket_token

logger = logging.getLogger(__name__)


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminOrReadOnly,)


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.select_related("airplane_type").order_by("id")
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = DefaultPagination

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        if self.action in ("list", "retrieve"):
            return AirplaneListSerializer
        return AirplaneSerializer


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.order_by("id")
    serializer_class = AirportSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = DefaultPagination


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.order_by("last_name", "first_name")
    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = DefaultPagination


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter("source", type=str, description="Filter by source airport name (e.g. Kyiv)."),
            OpenApiParameter("destination", type=str, description="Filter by destination airport name (e.g. Paris)."),
        ]
    )
)
class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related("source", "destination").order_by("id")
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = DefaultPagination

    def get_queryset(self) -> QuerySet[Route]:
        """Retrieve the routes with optional filtering by source or destination airport names."""

        queryset = self.queryset
        source = self.request.query_params.get("source")
        destination = self.request.query_params.get("destination")

        if source:
            queryset = queryset.filter(source__name__icontains=source)

        if destination:
            queryset = queryset.filter(destination__name__icontains=destination)

        return queryset

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        if self.action in ("list", "retrieve"):
            return RouteListSerializer
        return RouteSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "date", type={"type": "string", "format": "date"}, description="Filter by departure date (YYYY-MM-DD)."
            ),
            OpenApiParameter("route", type=int, description="Filter by route id."),
            OpenApiParameter("source", type=str, description="Filter by airport name."),
        ]
    )
)
class FlightViewSet(viewsets.ModelViewSet):
    queryset = (
        Flight.objects
        .select_related("route__source", "route__destination", "airplane")
        .prefetch_related("crew")
        .annotate(
            tickets_available=Greatest(
                F("airplane__rows") * F("airplane__seats_in_row") - Count("tickets", distinct=True), 0
            )
        )
        .order_by("-departure_time")
    )
    permission_classes = (IsAdminOrReadOnly,)
    pagination_class = DefaultPagination

    def get_queryset(self) -> QuerySet[Flight]:
        """Retrieve flights with optional filtering by date, route ID, and source airport name."""

        queryset = self.queryset

        date = self.request.query_params.get("date")
        route_id = self.request.query_params.get("route")
        source = self.request.query_params.get("source")

        if date:
            departure_date = parse_date(date)
            if departure_date:
                queryset = queryset.filter(departure_time__date=departure_date)

        if route_id:
            try:
                queryset = queryset.filter(route_id=int(route_id))
            except (TypeError, ValueError):
                logger.warning("Invalid route_id received: %s", route_id)

        if source:
            queryset = queryset.filter(route__source__name__icontains=source)

        return queryset.distinct()

    def get_serializer_class(self) -> type[serializers.BaseSerializer]:
        if self.action == "list":
            return FlightListSerializer
        if self.action == "retrieve":
            return FlightDetailSerializer
        return FlightSerializer


@extend_schema_view(
    list=extend_schema(description="Returns a list of orders for the current user."),
    create=extend_schema(
        description=(
            "Creates a new order with one or more tickets (max 6). "
            "Each ticket requires: row, seat, flight. "
            "passenger_name and passenger_email are optional — "
            "if not provided, the account holder's details will be used. "
        )
    ),
)
class OrderViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = Order.objects.select_related("user").prefetch_related(
        "tickets__flight__route__source", "tickets__flight__route__destination", "tickets__flight__airplane"
    )
    serializer_class = OrderSerializer
    permission_classes = (IsAuthenticated,)
    pagination_class = DefaultPagination

    def get_queryset(self) -> QuerySet[Order]:
        """Return orders for the current user only (unless staff)."""

        queryset = self.queryset
        user = self.request.user

        if not user.is_staff:
            queryset = queryset.filter(user=user)

        return queryset.distinct()

    def perform_create(self, serializer: BaseSerializer) -> None:
        """Assign the order to the current user upon creation."""

        serializer.save(user=self.request.user)


@extend_schema(
    description=(
        "Public endpoint called when a passenger's QR code is scanned. "
        "Verifies the signed JWT and returns the order details. "
    ),
    responses={
        200: TicketValidationSerializer,
        400: {"description": "Token is expired or invalid"},
        404: {"description": "Order not found"},
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
def validate_ticket_view(request: Request, token: str) -> Response:
    try:
        ticket_id = verify_ticket_token(token)
    except jwt.ExpiredSignatureError:
        logger.warning("Expired ticket token presented")
        return Response(
            {"detail": "This ticket QR code has expired."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    except jwt.InvalidTokenError:
        logger.warning("Invalid ticket token presented")
        return Response(
            {"detail": "Invalid ticket QR code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        ticket = Ticket.objects.select_related(
            "order__user",
            "flight__route__source",
            "flight__route__destination",
            "flight__airplane",
        ).get(pk=ticket_id)
    except Ticket.DoesNotExist:
        return Response(
            {"detail": "Ticket not found."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serializer = TicketValidationSerializer(ticket, context={"request": request})

    return Response(serializer.data, status=status.HTTP_200_OK)
