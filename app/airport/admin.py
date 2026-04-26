from django.contrib import admin

from airport.models import AirplaneType, Airplane, Airport, Crew, Route, Flight


@admin.register(AirplaneType)
class AirplaneTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Airplane)
class AirplaneAdmin(admin.ModelAdmin):
    list_display = ("name", "airplane_type", "rows", "seats_in_row", "capacity")
    list_filter = ("airplane_type",)
    search_fields = ("name",)


@admin.register(Airport)
class AirportAdmin(admin.ModelAdmin):
    list_display = ("name", "closest_big_city")
    search_fields = ("name", "closest_big_city")


@admin.register(Crew)
class CrewAdmin(admin.ModelAdmin):
    list_display = ("full_name",)
    search_fields = ("full_name", "first_name", "last_name")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("source", "destination", "distance")
    list_filter = ("source", "destination")


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ("route", "airplane", "departure_time", "arrival_time")
    list_filter = ("departure_time", "route")
    filter_horizontal = ("crew",)
