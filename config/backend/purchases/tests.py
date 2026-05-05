from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import Inventory

from .models import PurchaseHeader, PurchaseItem


User = get_user_model()


class PurchaseAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="purchasecashier",
            password="CashierPass123",
            role="cashier",
        )
        self.product_one = Inventory.objects.create(
            name="Coca Cola",
            plu_code="PUR100",
            barcode="990100001001",
            brand="Coke",
            category="Drink",
            unit_cost="1.00",
            unit_price="2.50",
            stock_quantity=10,
            reorder_level=2,
        )
        self.product_two = Inventory.objects.create(
            name="Potato Chips",
            plu_code="PUR200",
            barcode="990100001002",
            brand="Crunch",
            category="Snack",
            unit_cost="0.50",
            unit_price="1.50",
            stock_quantity=5,
            reorder_level=1,
        )

        self.create_url = reverse("purchase-header-create")
        self.list_url = reverse("purchase-header-list")
        self.return_url_name = "purchase-header-return"

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def create_purchase(self):
        return self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "4.75",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "product_name": self.product_one.name,
                        "quantity": 2,
                        "unit_cost": "1.25",
                    },
                    {
                        "product_id": self.product_two.product_id,
                        "product_name": self.product_two.name,
                        "quantity": 3,
                        "unit_cost": "0.75",
                    },
                ],
            },
            format="json",
        )

    def create_purchase_with_new_item(self):
        return self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "8.50",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "product_name": self.product_one.name,
                        "quantity": 2,
                        "unit_cost": "1.25",
                    },
                    {
                        "product_name": "Milo 3 in 1",
                        "barcode": "990100009999",
                        "plu_code": "PUR999",
                        "brand": "Nestle",
                        "category": "Drink Mix",
                        "quantity": 4,
                        "unit_cost": "1.50",
                        "unit_price": "2.25",
                        "reorder_level": 3,
                    },
                ],
            },
            format="json",
        )

    def test_purchase_create_requires_authentication(self):
        response = self.client.post(self.create_url, {}, format="json")

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_purchase_create_increases_stock_and_creates_records(self):
        self.authenticate()

        response = self.create_purchase()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["supplier_name"], "City Supplier")
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(PurchaseHeader.objects.count(), 1)
        self.assertEqual(PurchaseItem.objects.count(), 2)

        purchase = PurchaseHeader.objects.get(purchase_id=response.data["purchase_id"])
        self.assertEqual(purchase.supplier_name, "City Supplier")
        self.assertEqual(purchase.payment_method, "cash")
        self.assertEqual(purchase.payment, Decimal("4.75"))
        self.assertEqual(purchase.total_cost, Decimal("4.75"))
        self.assertEqual(purchase.status, PurchaseHeader.STATUS_COMPLETED)

        self.product_one.refresh_from_db()
        self.product_two.refresh_from_db()
        self.assertEqual(self.product_one.stock_quantity, 12)
        self.assertEqual(self.product_two.stock_quantity, 8)

    def test_purchase_create_can_add_brand_new_inventory_item(self):
        self.authenticate()

        response = self.create_purchase_with_new_item()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(PurchaseHeader.objects.count(), 1)
        self.assertEqual(PurchaseItem.objects.count(), 2)

        new_product = Inventory.objects.get(barcode="990100009999")
        self.assertEqual(new_product.name, "Milo 3 in 1")
        self.assertEqual(new_product.brand, "Nestle")
        self.assertEqual(new_product.category, "Drink Mix")
        self.assertEqual(new_product.unit_cost, Decimal("1.50"))
        self.assertEqual(new_product.unit_price, Decimal("2.25"))
        self.assertEqual(new_product.stock_quantity, 4)
        self.assertEqual(new_product.reorder_level, 3)

        purchase = PurchaseHeader.objects.get(purchase_id=response.data["purchase_id"])
        self.assertEqual(purchase.total_cost, Decimal("8.50"))
        self.assertEqual(response.data["purchase_id"], purchase.purchase_id)
        self.assertEqual(response.data["user_id"], self.user.pk)

    def test_purchase_create_rejects_empty_items(self):
        self.authenticate()

        response = self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "4.75",
                "items": [],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)
        self.assertEqual(PurchaseHeader.objects.count(), 0)

    def test_purchase_create_rejects_new_item_without_required_fields(self):
        self.authenticate()

        response = self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "1.00",
                "items": [
                    {
                        "product_name": "Broken Item",
                        "quantity": 1,
                        "unit_cost": "1.00",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)
        self.assertEqual(Inventory.objects.count(), 2)
        self.assertEqual(PurchaseHeader.objects.count(), 0)

    def test_purchase_create_rejects_payment_greater_than_total_cost(self):
        self.authenticate()

        response = self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "100.00",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 1,
                        "unit_cost": "1.25",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["payment"][0],
            "Payment cannot be greater than the total cost.",
        )
        self.product_one.refresh_from_db()
        self.assertEqual(self.product_one.stock_quantity, 10)
        self.assertEqual(PurchaseHeader.objects.count(), 0)

    def test_purchase_create_rejects_invalid_payment_method(self):
        self.authenticate()

        response = self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "bank",
                "payment": "1.25",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 1,
                        "unit_cost": "1.25",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("payment_method", response.data)

    def test_purchase_create_rejects_negative_unit_cost(self):
        self.authenticate()

        response = self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "0.00",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 1,
                        "unit_cost": "-1.00",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)

    def test_purchase_create_rejects_zero_quantity(self):
        self.authenticate()

        response = self.client.post(
            self.create_url,
            {
                "supplier": "City Supplier",
                "payment_method": "cash",
                "payment": "0.00",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 0,
                        "unit_cost": "1.00",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("items", response.data)

    def test_purchase_detail_returns_items(self):
        self.authenticate()
        create_response = self.create_purchase_with_new_item()

        response = self.client.get(
            reverse(
                "purchase-header-detail",
                kwargs={"purchase_id": create_response.data["purchase_id"]},
            )
        )

        print("\nPurchase detail JSON:")
        print(json.dumps(response.data, indent=2, default=str))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["supplier_name"], "City Supplier")
        self.assertEqual(len(response.data["items"]), 2)
        self.assertEqual(Decimal(response.data["total_cost"]), Decimal("8.50"))

    def test_purchase_list_returns_created_purchases(self):
        self.authenticate()
        create_response = self.create_purchase()

        response = self.client.get(self.list_url)

        print("\nPurchase list JSON:")
        print(json.dumps(response.data, indent=2, default=str))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["purchase_id"],
            create_response.data["purchase_id"],
        )

    def test_purchase_list_filters_by_supplier_and_status(self):
        self.authenticate()
        create_response = self.create_purchase()
        purchase_id = create_response.data["purchase_id"]
        self.client.post(
            reverse(self.return_url_name, kwargs={"purchase_id": purchase_id}),
            format="json",
        )
        self.client.post(
            self.create_url,
            {
                "supplier": "Other Supplier",
                "payment_method": "cash",
                "payment": "1.00",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 1,
                        "unit_cost": "1.00",
                    }
                ],
            },
            format="json",
        )

        response = self.client.get(
            self.list_url,
            {"supplier": "City", "status": "returned"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["supplier_name"], "City Supplier")
        self.assertEqual(response.data[0]["status"], "returned")

    def test_purchase_list_filters_by_product(self):
        self.authenticate()
        first_response = self.create_purchase()
        self.client.post(
            self.create_url,
            {
                "supplier": "Milo Supplier",
                "payment_method": "cash",
                "payment": "6.00",
                "items": [
                    {
                        "product_name": "Milo 3 in 1",
                        "barcode": "990100009999",
                        "quantity": 4,
                        "unit_cost": "1.50",
                        "unit_price": "2.25",
                    }
                ],
            },
            format="json",
        )

        response = self.client.get(
            self.list_url,
            {"product_id": self.product_two.product_id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["purchase_id"],
            first_response.data["purchase_id"],
        )

    def test_purchase_return_reverses_stock_and_updates_status(self):
        self.authenticate()
        create_response = self.create_purchase()

        response = self.client.post(
            reverse(
                self.return_url_name,
                kwargs={"purchase_id": create_response.data["purchase_id"]},
            ),
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "returned")

        self.product_one.refresh_from_db()
        self.product_two.refresh_from_db()
        self.assertEqual(self.product_one.stock_quantity, 10)
        self.assertEqual(self.product_two.stock_quantity, 5)

        purchase = PurchaseHeader.objects.get(purchase_id=create_response.data["purchase_id"])
        self.assertEqual(purchase.status, PurchaseHeader.STATUS_RETURNED)

    def test_purchase_return_rejects_already_returned_purchase(self):
        self.authenticate()
        create_response = self.create_purchase()
        return_url = reverse(
            self.return_url_name,
            kwargs={"purchase_id": create_response.data["purchase_id"]},
        )

        self.client.post(return_url, format="json")
        response = self.client.post(return_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Purchase has already been returned.",
        )
