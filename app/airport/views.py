import logging

from django.db.models import QuerySet, F, Count
from django.db.models.functions import Greatest
from django.utils.dateparse import parse_date
from drf_spectacular.utils import extend_schema, OpenApiParameter, extend_schema_view
from rest_framework import viewsets, mixins
from rest_framework.permissions import IsAuthenticated

from airport.models import Airplane, AirplaneType, Airport, Crew, Route, Flight, Order
from airport.paginations import DefaultPagination
from airport.permissions import IsAdminOrReadOnly
from airport.serializers import (
    AirplaneTypeSerializer,
    AirplaneSerializer,
    AirplaneListSerializer,
    AirportSerializer,
    CrewSerializer,
    RouteSerializer,
    RouteListSerializer,
    FlightSerializer,
    FlightListSerializer,
    FlightDetailSerializer,
    OrderSerializer,
)
from airport.tasks import notify_order_created

logger = logging.getLogger("airport_service_api")


class AirplaneTypeViewSet(viewsets.ModelViewSet):
    queryset = AirplaneType.objects.all()
    serializer_class = AirplaneTypeSerializer
    permission_classes = (IsAdminOrReadOnly,)


class AirplaneViewSet(viewsets.ModelViewSet):
    queryset = Airplane.objects.select_related("airplane_type")
    permission_classes = (IsAdminOrReadOnly,)

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return AirplaneListSerializer
        return AirplaneSerializer


class AirportViewSet(viewsets.ModelViewSet):
    queryset = Airport.objects.all()
    serializer_class = AirportSerializer
    permission_classes = (IsAdminOrReadOnly,)


class CrewViewSet(viewsets.ModelViewSet):
    queryset = Crew.objects.all()
    serializer_class = CrewSerializer
    permission_classes = (IsAdminOrReadOnly,)


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "source",
                type=str,
                description="Filter by source airport name (e.g. Kyiv)",
            ),
            OpenApiParameter(
                "destination",
                type=str,
                description="Filter by destination airport name (e.g. Paris)",
            ),
        ]
    )
)
class RouteViewSet(viewsets.ModelViewSet):
    queryset = Route.objects.select_related("source", "destination")
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

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return RouteListSerializer
        return RouteSerializer


@extend_schema_view(
    list=extend_schema(
        parameters=[
            OpenApiParameter(
                "date",
                type={"type": "string", "format": "date"},
                description="Filter by departure date (YYYY-MM-DD)",
            ),
            OpenApiParameter(
                "route",
                type=int,
                description="Filter by route id",
            ),
            OpenApiParameter(
                "source",
                type=str,
                description="Filter by airport name",
            ),
        ]
    )
)
class FlightViewSet(viewsets.ModelViewSet):
    queryset = (
        Flight.objects.select_related("route__source", "route__destination", "airplane")
        .prefetch_related("crew")
        .annotate(
            tickets_available=Greatest(
                F("airplane__rows") * F("airplane__seats_in_row")
                - Count("tickets", distinct=True),
                0,
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
                logger.warning(f"Invalid route_id received: {route_id}")
                pass

        if source:
            queryset = queryset.filter(route__source__name__icontains=source)

        return queryset.distinct()

    def get_serializer_class(self):
        if self.action == "list":
            return FlightListSerializer
        if self.action == "retrieve":
            return FlightDetailSerializer
        return FlightSerializer


class OrderViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    queryset = Order.objects.prefetch_related(
        "tickets__flight__route", "tickets__flight__airplane"
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

    def perform_create(self, serializer: OrderSerializer) -> None:
        """Assign the order to the current user upon creation."""

        user = self.request.user
        order = serializer.save(user=user)

        logger.info(f"SUCCESS: Order #{order.id} created by user {user.email}")

        notify_order_created.delay(order.id, user.email)
