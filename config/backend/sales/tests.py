from datetime import timedelta
from decimal import Decimal
import json

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from inventory.models import Inventory

from .models import Sale, TransactionHeader


User = get_user_model()


class SalesAPITestCase(APITestCase):
    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="salesadmin",
            password="AdminPass123",
            role="admin",
            is_staff=True,
        )
        self.cashier_user = User.objects.create_user(
            username="salescashier",
            password="CashierPass123",
            role="cashier",
        )
        self.product_one = Inventory.objects.create(
            name="Coca Cola",
            plu_code="PLU100",
            barcode="880100001001",
            brand="Coke",
            category="Drink",
            unit_cost="1.00",
            unit_price="2.50",
            stock_quantity=10,
            reorder_level=2,
        )
        self.product_two = Inventory.objects.create(
            name="Potato Chips",
            plu_code="PLU200",
            barcode="880100001002",
            brand="Crunch",
            category="Snack",
            unit_cost="0.50",
            unit_price="1.50",
            stock_quantity=5,
            reorder_level=1,
        )

        self.create_url = reverse("sales-create")
        self.list_url = reverse("sales-list")
        self.load_1k_items_url = reverse("sales-load-1k-items")
        self.search_item_price_url = reverse("sales-search-item-price")
        self.today_url = reverse("sales-today")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def create_sale(self):
        return self.client.post(
            self.create_url,
            {
                "payment_method": "cash",
                "payment": "7.00",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 2,
                        "discount": "0.00",
                    },
                    {
                        "product_id": self.product_two.product_id,
                        "quantity": 1,
                        "discount": "0.50",
                    },
                ],
            },
            format="json",
        )

    def test_sales_create_requires_authentication(self):
        response = self.client.post(self.create_url, {}, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_cashier_can_create_sale_and_stock_is_reduced(self):
        self.authenticate(self.cashier_user)

        response = self.create_sale()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["status"], "completed")
        self.assertEqual(Decimal(response.data["total_amount"]), Decimal("6.00"))
        self.assertEqual(Decimal(response.data["change"]), Decimal("1.00"))
        self.assertEqual(len(response.data["items"]), 2)

        self.product_one.refresh_from_db()
        self.product_two.refresh_from_db()
        self.assertEqual(self.product_one.stock_quantity, 8)
        self.assertEqual(self.product_two.stock_quantity, 4)
        self.assertEqual(TransactionHeader.objects.count(), 1)
        self.assertEqual(Sale.objects.count(), 2)

    def test_sales_create_rejects_insufficient_stock(self):
        self.authenticate(self.cashier_user)

        response = self.client.post(
            self.create_url,
            {
                "payment_method": "cash",
                "payment": "30.00",
                "items": [
                    {
                        "product_id": self.product_two.product_id,
                        "quantity": 100,
                        "discount": "0.00",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(TransactionHeader.objects.count(), 0)
        self.product_two.refresh_from_db()
        self.assertEqual(self.product_two.stock_quantity, 5)

    def test_sales_create_rejects_underpayment_for_cash(self):
        self.authenticate(self.cashier_user)

        response = self.client.post(
            self.create_url,
            {
                "payment_method": "cash",
                "payment": "2.00",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 2,
                        "discount": "0.00",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_sales_create_requires_exact_payment_for_card(self):
        self.authenticate(self.cashier_user)

        response = self.client.post(
            self.create_url,
            {
                "payment_method": "card",
                "payment": "6.50",
                "items": [
                    {
                        "product_id": self.product_one.product_id,
                        "quantity": 2,
                        "discount": "0.00",
                    }
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("detail", response.data)

    def test_sales_list_returns_transactions(self):
        self.authenticate(self.cashier_user)
        self.create_sale()

        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["item_count"], 2)

    def test_sales_detail_returns_transaction_with_items(self):
        self.authenticate(self.cashier_user)
        create_response = self.create_sale()

        response = self.client.get(
            reverse("sales-detail", kwargs={"trans_id": create_response.data["trans_id"]})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["trans_id"], create_response.data["trans_id"])
        self.assertEqual(len(response.data["items"]), 2)

    def test_sales_today_returns_only_today_transactions(self):
        self.authenticate(self.cashier_user)
        create_response = self.create_sale()
        transaction_header = TransactionHeader.objects.get(
            trans_id=create_response.data["trans_id"]
        )
        TransactionHeader.objects.create(
            user=self.cashier_user,
            trans_date=timezone.now() - timedelta(days=1),
            total_amount="1.00",
            payment_method="cash",
            payment="1.00",
            change="0.00",
            status=TransactionHeader.STATUS_COMPLETED,
        )

        response = self.client.get(self.today_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["trans_id"], transaction_header.trans_id)

    def test_search_item_price_returns_barcode_match(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(
            self.search_item_price_url,
            {"q": "880100001001", "type": "barcode"},
        )

        print("\nsearch_item_price barcode response:")
        print(json.dumps(response.data, indent=2))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.product_one.product_id)
        self.assertEqual(response.data[0]["price"], "2.50")
        self.assertEqual(response.data[0]["stock"], 10)

    def test_search_item_price_returns_plu_match(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(
            self.search_item_price_url,
            {"q": "PLU200", "type": "plu"},
        )

        print("\nsearch_item_price plu response:")
        print(json.dumps(response.data, indent=2))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.product_two.product_id)

    def test_search_item_price_returns_name_matches(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(
            self.search_item_price_url,
            {"q": "Coca", "type": "name"},
        )

        print("\nsearch_item_price name response:")
        print(json.dumps(response.data, indent=2))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Coca Cola")

    def test_search_item_price_requires_query(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(self.search_item_price_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_search_item_price_rejects_invalid_type(self):
        self.authenticate(self.cashier_user)

        response = self.client.get(
            self.search_item_price_url,
            {"q": "Coca", "type": "unknown"},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_load_1k_items_requires_authentication(self):
        response = self.client.get(self.load_1k_items_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_load_1k_items_returns_lowest_stock_first(self):
        Inventory.objects.create(
            name="Instant Noodles",
            plu_code="PLU050",
            barcode="880100001003",
            brand="Quick",
            category="Food",
            unit_cost="0.30",
            unit_price="0.80",
            stock_quantity=2,
            reorder_level=1,
        )
        self.authenticate(self.cashier_user)

        response = self.client.get(self.load_1k_items_url)

        print("\nload_1k_items response (first 5):")
        print(json.dumps(response.data[:5], indent=2))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["name"], "Instant Noodles")
        self.assertEqual(response.data[1]["name"], "Potato Chips")
        self.assertEqual(response.data[2]["name"], "Coca Cola")

    def test_load_1k_items_limits_response_to_1000_items(self):
        for index in range(3, 1008):
            Inventory.objects.create(
                name=f"Item {index}",
                plu_code=f"LOAD{index}",
                barcode=f"LOAD99010000{index:04d}",
                brand="Bulk",
                category="General",
                unit_cost="1.00",
                unit_price="2.00",
                stock_quantity=index,
                reorder_level=1,
            )

        self.authenticate(self.cashier_user)

        response = self.client.get(self.load_1k_items_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1000)
