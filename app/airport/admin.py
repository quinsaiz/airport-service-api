from django.contrib import admin

from airport.models import Airplane, AirplaneType, Airport, Crew, Flight, Order, Route, Ticket


@admin.register(AirplaneType)
class AirplaneTypeAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


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
    search_fields = ("first_name", "last_name")


@admin.register(Route)
class RouteAdmin(admin.ModelAdmin):
    list_display = ("source", "destination", "distance")
    list_filter = ("source", "destination")
    list_select_related = ("source", "destination")
    search_fields = ("source__name", "destination__name", "source__closest_big_city")


@admin.register(Flight)
class FlightAdmin(admin.ModelAdmin):
    list_display = ("route", "airplane", "departure_time", "arrival_time")
    list_filter = ("departure_time", "route__source")
    list_select_related = ("route__source", "route__destination", "airplane")
    filter_horizontal = ("crew",)
    autocomplete_fields = ("route", "airplane")


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ("flight", "row", "seat", "order")
    list_select_related = ("flight__route__source", "flight__route__destination", "order__user")
    search_fields = ("order__user__email",)


class TicketInline(admin.TabularInline):
    model = Ticket
    extra = 1


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    @admin.display(description="Order ID")
    def id_display(self, obj: Order) -> str:
        return str(obj.uuid)[:8]

    @admin.display(description="Created At")
    def created_at_formatted(self, obj: Order) -> str:
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    list_display = ("id_display", "user", "created_at_formatted")
    list_select_related = ("user",)
    list_filter = ("created_at",)
    search_fields = ("user__email", "uuid")
    inlines = (TicketInline,)
