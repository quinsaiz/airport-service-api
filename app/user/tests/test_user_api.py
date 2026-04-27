from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

USER_CREATE_URL = reverse("user:create")
TOKEN_URL = reverse("user:token_obtain_pair")


class UserApiTests(APITestCase):
    def test_create_user_success(self):
        payload = {
            "email": "test@test.com",
            "password": "password123",
        }

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=payload["email"])

        self.assertTrue(user.check_password(payload["password"]))
        self.assertNotIn("password", res.data)

    def test_token_login(self):
        payload = {"email": "test@test.com", "password": "password123"}

        get_user_model().objects.create_user(**payload)

        res = self.client.post(TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("access", res.data)

    def test_create_user_with_existing_email_fail(self):
        payload = {"email": "test@test.com", "password": "password123"}

        get_user_model().objects.create_user(**payload)

        res = self.client.post(USER_CREATE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_manage_user_unauthorized(self):
        url = reverse("user:manage")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_manage_user_authorized(self):
        user = get_user_model().objects.create_user(
            email="test@test.com", password="password123"
        )

        self.client.force_authenticate(user=user)

        url = reverse("user:manage")

        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], user.email)
