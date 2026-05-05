from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Inventory


User = get_user_model()


class InventoryAPITestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="inventoryadmin",
            password="AdminPass123",
            role="admin",
            is_staff=True,
        )
        self.cashier_user = User.objects.create_user(
            username="inventorycashier",
            password="CashierPass123",
            role="cashier",
        )
        self.product = Inventory.objects.create(
            name="Coca Cola",
            plu_code="PLU100",
            barcode="880100000001",
            brand="Coke",
            category="Drink",
            unit_cost="1.00",
            unit_price="1.50",
            stock_quantity=3,
            reorder_level=5,
        )

        self.list_url = reverse("inventory-list")
        self.detail_url = reverse(
            "inventory-detail",
            kwargs={"product_id": self.product.product_id},
        )
        self.search_url = reverse("inventory-search")
        self.lookup_url = reverse("inventory-lookup")
        self.create_url = reverse("inventory-create")
        self.update_url = reverse(
            "inventory-update",
            kwargs={"product_id": self.product.product_id},
        )
        self.delete_url = reverse(
            "inventory-delete",
            kwargs={"product_id": self.product.product_id},
        )
        self.low_stock_url = reverse("inventory-low-stock")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_inventory_list_requires_authentication(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cashier_can_list_inventory(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Coca Cola")
        self.assertTrue(response.data[0]["needs_reorder"])

    def test_inventory_detail_returns_single_product(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(self.detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["barcode"], "880100000001")

    def test_inventory_search_matches_name_barcode_and_plu(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(self.search_url, {"q": "PLU100"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["product_id"], self.product.product_id)

    def test_inventory_lookup_returns_product_by_barcode(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(self.lookup_url, {"barcode": "880100000001"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["product_id"], self.product.product_id)

    def test_inventory_lookup_returns_product_by_plu_code(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(self.lookup_url, {"plu_code": "PLU100"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["barcode"], "880100000001")

    def test_inventory_lookup_requires_exactly_one_lookup_field(self):
        self.authenticate(self.cashier_user)

        missing_response = self.client.get(self.lookup_url)
        self.assertEqual(missing_response.status_code, status.HTTP_400_BAD_REQUEST)

        duplicate_response = self.client.get(
            self.lookup_url,
            {"barcode": "880100000001", "plu_code": "PLU100"},
        )
        self.assertEqual(duplicate_response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_low_stock_returns_only_products_at_or_below_reorder_level(self):
        Inventory.objects.create(
            name="Rice Bag",
            plu_code="PLU200",
            barcode="880100000002",
            brand="House",
            category="Grocery",
            unit_cost="10.00",
            unit_price="15.00",
            stock_quantity=10,
            reorder_level=4,
        )
        self.authenticate(self.cashier_user)

        response = self.client.get(self.low_stock_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["product_id"], self.product.product_id)

    def test_admin_can_create_inventory_product(self):
        self.authenticate(self.admin_user)

        response = self.client.post(
            self.create_url,
            {
                "name": "Orange Juice",
                "plu_code": "PLU300",
                "barcode": "880100000003",
                "brand": "Fresh",
                "category": "Drink",
                "unit_cost": "2.00",
                "unit_price": "3.00",
                "stock_quantity": 12,
                "reorder_level": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["name"], "Orange Juice")
        self.assertTrue(
            Inventory.objects.filter(barcode="880100000003").exists()
        )

    def test_cashier_cannot_create_inventory_product(self):
        self.authenticate(self.cashier_user)

        response = self.client.post(
            self.create_url,
            {
                "name": "Orange Juice",
                "plu_code": "PLU300",
                "barcode": "880100000003",
                "unit_cost": "2.00",
                "unit_price": "3.00",
                "stock_quantity": 12,
                "reorder_level": 4,
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_validates_unit_price_not_below_unit_cost(self):
        self.authenticate(self.admin_user)

        response = self.client.patch(
            self.update_url,
            {"unit_price": "0.50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("unit_price", response.data)

    def test_admin_can_delete_unused_product(self):
        deletable = Inventory.objects.create(
            name="Water Bottle",
            plu_code="PLU400",
            barcode="880100000004",
            brand="Clear",
            category="Drink",
            unit_cost="0.40",
            unit_price="0.80",
            stock_quantity=8,
            reorder_level=2,
        )
        self.authenticate(self.admin_user)

        response = self.client.delete(
            reverse("inventory-delete", kwargs={"product_id": deletable.product_id})
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Inventory.objects.filter(product_id=deletable.product_id).exists())
