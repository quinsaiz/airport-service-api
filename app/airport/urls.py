from django.urls import path, include
from rest_framework import routers

from airport.views import (
    AirplaneTypeViewSet,
    AirplaneViewSet,
    AirportViewSet,
    CrewViewSet,
    RouteViewSet,
)

router = routers.DefaultRouter()

router.register(r"airplane-types", AirplaneTypeViewSet)
router.register(r"airplanes", AirplaneViewSet)
router.register(r"airports", AirportViewSet)
router.register(r"crews", CrewViewSet)
router.register(r"routes", RouteViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

app_name = "airport"
