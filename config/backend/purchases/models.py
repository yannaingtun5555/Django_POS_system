from django.db import models

from accounts.models import PosUser
from inventory.models import Inventory


class PurchaseHeader(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_RETURNED = "returned"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_RETURNED, "Returned"),
    ]

    PAYMENT_METHODS = [
        ("cash", "Cash"),
        ("card", "Card"),
        ("mobile", "Mobile"),
    ]

    purchase_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        PosUser,
        on_delete=models.PROTECT,
        related_name="purchases",
        db_column="user_id",
    )
    purchase_date = models.DateTimeField()
    supplier_name = models.CharField(max_length=255)
    total_cost = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    payment = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_COMPLETED,
    )

    class Meta:
        db_table = "purchase_header"
        ordering = ["-purchase_date"]
    

    def __str__(self):
        return f"Purchase {self.purchase_id}"


class PurchaseItem(models.Model):
    purchase_item_id = models.BigAutoField(primary_key=True)
    purchase = models.ForeignKey(
        PurchaseHeader,
        on_delete=models.CASCADE,
        related_name="items",
        db_column="purchase_id",
    )
    product = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name="purchase_items",
        db_column="product_id",
    )
    user = models.ForeignKey(
        PosUser,
        on_delete=models.PROTECT,
        related_name="purchase_items",
        db_column="user_id",
    )
    quantity = models.PositiveIntegerField()
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        db_table = "purchase_items"

    def __str__(self):
        return f"Purchase item {self.purchase_item_id}"
