from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from airport.models import Order
from airport.tests.helpers import sample_flight

ORDER_URL = reverse("airport:order-list")


class UnauthenticatedOrderApiTests(APITestCase):
    def test_auth_required(self) -> None:
        res = self.client.get(ORDER_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_order_unauthenticated(self) -> None:
        res = self.client.post(ORDER_URL, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class OrderApiTest(APITestCase):
    def setUp(self) -> None:
        self.user = get_user_model().objects.create_user(email="test@email.com", password="password123")
        self.client.force_authenticate(user=self.user)

    def test_list_orders_only_owner(self) -> None:
        Order.objects.create(user=self.user)

        other_user = get_user_model().objects.create_user(email="other@email.com", password="password123")
        Order.objects.create(user=other_user)

        res = self.client.get(ORDER_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["results"]), 1)

    def test_create_order(self) -> None:
        flight = sample_flight()
        payload = {"tickets": [{"row": 1, "seat": 1, "flight": flight.pk}, {"row": 1, "seat": 2, "flight": flight.pk}]}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        orders = Order.objects.filter(user=self.user)
        self.assertEqual(orders.count(), 1)
        self.assertEqual(orders[0].tickets.count(), 2)

    def test_create_order_invalid_seat(self) -> None:
        flight = sample_flight()
        payload = {"tickets": [{"row": 11, "seat": 1, "flight": flight.pk}]}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Row", res.data["tickets"][0])

    def test_cannot_book_same_seat_twice(self) -> None:
        """Ensure unique constraint prevents double booking of the same seat."""

        flight = sample_flight()
        payload = {"tickets": [{"row": 1, "seat": 1, "flight": flight.pk}]}
        self.client.post(ORDER_URL, payload, format="json")

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_atomic_transaction(self) -> None:
        """Verify that no order is created if any ticket within it is invalid.
        Ensures database integrity via atomic transactions.
        """

        flight = sample_flight()
        payload = {
            "tickets": [{"row": 1, "seat": 1, "flight": flight.pk}, {"row": 100, "seat": 1, "flight": flight.pk}]
        }
        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_exceeds_max_tickets(self) -> None:
        """Ensure that booking more than 6 tickets in one order is rejected."""

        flight = sample_flight()
        tickets = [{"row": 1, "seat": i, "flight": flight.pk} for i in range(1, 8)]
        payload = {"tickets": tickets}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)

    def test_create_order_exactly_max_tickets(self) -> None:
        """Ensure that booking exactly 6 tickets in one order is allowed."""

        flight = sample_flight()
        tickets = [{"row": i, "seat": 1, "flight": flight.pk} for i in range(1, 7)]
        payload = {"tickets": tickets}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_order_empty_tickets_rejected(self) -> None:
        """Ensure an order with no tickets is rejected."""

        payload: dict[str, object] = {"tickets": []}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_order_response_contains_uuid(self) -> None:
        flight = sample_flight()
        payload = {"tickets": [{"row": 1, "seat": 1, "flight": flight.pk}]}

        res = self.client.post(ORDER_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertIn("uuid", res.data)

    def test_staff_sees_all_orders(self) -> None:
        """Admin users should be able to see all orders, not just their own."""

        Order.objects.create(user=self.user)

        admin = get_user_model().objects.create_user(email="admin@test.com", password="password123", is_staff=True)
        self.client.force_authenticate(user=admin)

        res = self.client.get(ORDER_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(res.data["results"]), 1)
