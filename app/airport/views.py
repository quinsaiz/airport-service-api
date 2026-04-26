from django.db.models import QuerySet
from rest_framework import viewsets

from airport.models import Airplane, AirplaneType, Airport, Crew, Route
from airport.paginations import DefaultPagination
from airport.permissions import IsAdminOrReadOnly
from airport.serializers import (
    AirplaneTypeSerializer,
    AirplaneSerializer,
    AirplaneListSerializer,
    AirportSerializer,
    CrewSerializer,
    RouteListSerializer,
    RouteSerializer,
)


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
        if self.action == "list":
            return RouteListSerializer
        return RouteSerializer
