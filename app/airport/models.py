from django.db import models


class AirplaneType(models.Model):
    name = models.CharField(max_length=55)

    def __str__(self) -> str:
        return self.name


class Airplane(models.Model):
    name = models.CharField(max_length=55)
    rows = models.PositiveIntegerField()
    seats_in_row = models.PositiveIntegerField()
    airplane_type = models.ForeignKey(
        AirplaneType, on_delete=models.CASCADE, related_name="airplanes"
    )

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

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name_plural = "Crew"


class Route(models.Model):
    source = models.ForeignKey(
        Airport, on_delete=models.CASCADE, related_name="departure_routes"
    )
    destination = models.ForeignKey(
        Airport, on_delete=models.CASCADE, related_name="arrival_routes"
    )
    distance = models.PositiveIntegerField()

    def __str__(self) -> str:
        return f"{self.source.name} -> {self.destination.name}"
