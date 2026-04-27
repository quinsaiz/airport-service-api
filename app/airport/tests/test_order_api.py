from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Order
from airport.tests.helpers import sample_flight

ORDER_URL = reverse("airport:order-list")


class OrderApiTest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email="test@test.com", password="password123"
        )
        self.client.force_authenticate(user=self.user)

    def test_list_orders_only_owner(self):
        Order.objects.create(user=self.user)

        other_user = get_user_model().objects.create_user(
            email="other_test@test.com", password="password123"
        )
        Order.objects.create(user=other_user)

        res = self.client.get(ORDER_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_order(self):
        flight = sample_flight()
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "flight": flight.pk},
                {"row": 1, "seat": 2, "flight": flight.pk},
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders[0].tickets.count(), 2)

    def test_create_order_invalid_seat(self):
        flight = sample_flight()
        payload = {
            "tickets": [
                {"row": 11, "seat": 1, "flight": flight.pk},
            ]
        }

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("row", res.data["tickets"][0])

    def test_cannot_book_same_seat_twice(self):
        """Ensure unique constraint prevents double booking of the same seat."""

        flight = sample_flight()
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "flight": flight.pk},
            ]
        }
        self.client.post(ORDER_URL, payload, format="json")

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_atomic_transaction(self):
        """
        Verify that no order is created if any ticket within it is invalid.
        Ensures database integrity via atomic transactions.
        """

        flight = sample_flight()
        payload = {
            "tickets": [
                {"row": 1, "seat": 1, "flight": flight.pk},
                {"row": 100, "seat": 1, "flight": flight.pk},
            ]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
