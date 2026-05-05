from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


User = get_user_model()


class AccountsAPITestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="adminuser",
            password="AdminPass123",
            role="admin",
            is_staff=True,
        )
        self.cashier_user = User.objects.create_user(
            username="cashier1",
            password="CashierPass123",
            role="cashier",
        )

        self.login_url = reverse("login")
        self.register_url = reverse("register")
        self.refresh_url = reverse("refresh")
        self.me_url = reverse("me")
        self.logout_url = reverse("logout")
        self.change_password_url = reverse("change-password")

    def authenticate(self, username, password):
        response = self.client.post(
            self.login_url,
            {"username": username, "password": password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {response.data['access']}"
        )
        return response.data

    def test_login_returns_tokens_and_user_payload(self):
        response = self.client.post(
            self.login_url,
            {"username": "cashier1", "password": "CashierPass123"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertEqual(response.data["user"]["username"], "cashier1")
        self.assertEqual(response.data["user"]["role"], "cashier")

    def test_me_requires_authentication(self):
        response = self.client.get(self.me_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_me_returns_current_user(self):
        self.authenticate("cashier1", "CashierPass123")

        response = self.client.get(self.me_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["username"], "cashier1")
        self.assertEqual(response.data["role"], "cashier")

    def test_register_requires_admin_user(self):
        self.authenticate("cashier1", "CashierPass123")

        response = self.client.post(
            self.register_url,
            {
                "username": "newcashier",
                "password": "NewCashier123",
                "role": "cashier",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_can_register_new_user(self):
        self.authenticate("adminuser", "AdminPass123")

        response = self.client.post(
            self.register_url,
            {
                "username": "newcashier",
                "password": "NewCashier123",
                "email": "newcashier@example.com",
                "first_name": "New",
                "last_name": "Cashier",
                "role": "cashier",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["username"], "newcashier")
        self.assertEqual(response.data["role"], "cashier")
        self.assertTrue(User.objects.filter(username="newcashier").exists())
        self.assertTrue(
            User.objects.get(username="newcashier").check_password("NewCashier123")
        )

    def test_change_password_updates_credentials(self):
        self.authenticate("cashier1", "CashierPass123")

        response = self.client.post(
            self.change_password_url,
            {
                "old_password": "CashierPass123",
                "new_password": "UpdatedPass123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.client.credentials()

        login_response = self.client.post(
            self.login_url,
            {"username": "cashier1", "password": "UpdatedPass123"},
            format="json",
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_logout_blacklists_refresh_token(self):
        tokens = self.authenticate("cashier1", "CashierPass123")

        logout_response = self.client.post(
            self.logout_url,
            {"refresh": tokens["refresh"]},
            format="json",
        )

        self.assertEqual(logout_response.status_code, status.HTTP_200_OK)

        refresh_response = self.client.post(
            self.refresh_url,
            {"refresh": tokens["refresh"]},
            format="json",
        )
        self.assertEqual(refresh_response.status_code, status.HTTP_401_UNAUTHORIZED)
