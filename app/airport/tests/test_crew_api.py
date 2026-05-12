from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Crew
from airport.tests.helpers import detail_url, sample_crew

CREW_URL = reverse("airport:crew-list")


class UnauthenticatedCrewApiTests(APITestCase):
    def test_auth_not_required_for_list(self) -> None:
        res = self.client.get(CREW_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class AuthenticatedCrewApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="test@email.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_list_crew(self) -> None:
        sample_crew()
        sample_crew(first_name="John", last_name="Pilot")

        res = self.client.get(CREW_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 2)

    def test_full_name_is_returned(self) -> None:
        sample_crew()

        res = self.client.get(CREW_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["results"][0]["full_name"], "Ivan Pilot")

    def test_create_crew_forbidden(self) -> None:
        payload = {"first_name": "Ivan", "last_name": "Sirko"}

        res = self.client.post(CREW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_crew_forbidden(self) -> None:
        crew = sample_crew()

        res = self.client.delete(detail_url("crew", crew.pk))

        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)


class AdminCrewApiTests(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="admin@test.com", password="password123", is_staff=True)
        self.client.force_authenticate(user=self.user)

    def test_create_crew(self) -> None:
        payload = {"first_name": "Ivan", "last_name": "Sirko"}

        res = self.client.post(CREW_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        crew = Crew.objects.get(pk=res.data["id"])
        self.assertEqual(crew.first_name, payload["first_name"])
        self.assertEqual(crew.last_name, payload["last_name"])

    def test_delete_crew(self) -> None:
        crew = sample_crew()

        res = self.client.delete(detail_url("crew", crew.pk))

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Crew.objects.filter(pk=crew.pk).exists())

    def test_update_crew(self) -> None:
        crew = sample_crew(first_name="OldName", last_name="OldLast")
        payload = {"first_name": "NewName", "last_name": "NewLast"}

        res = self.client.patch(detail_url("crew", crew.pk), payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        crew.refresh_from_db()
        self.assertEqual(crew.first_name, "NewName")
        self.assertEqual(crew.last_name, "NewLast")
