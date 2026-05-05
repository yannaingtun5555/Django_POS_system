from django.db import models
from inventory.models import Inventory
from accounts.models import PosUser

class TransactionHeader(models.Model):
    STATUS_COMPLETED = "completed"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"
    STATUS_CHOICES = [
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_REFUNDED, "Refunded"),
    ]

    trans_id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        PosUser,
        on_delete=models.PROTECT,
        related_name="transactions",
        db_column="user_id",
    )
    trans_date = models.DateTimeField()
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)

    PAYMENT_METHODS = [
    ("cash", "Cash"),
    ("card", "Card"),
    ("mobile", "Mobile"),
    ]

    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)

    payment = models.DecimalField(max_digits=12, decimal_places=2)
    change = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    class Meta:
        db_table = "transaction_header"
        ordering = ["-trans_date"]

    def __str__(self):
        return f"Transaction {self.trans_id}"


class Sale(models.Model):
    sale_pid = models.BigAutoField(primary_key=True)
    transaction = models.ForeignKey(
        TransactionHeader,
        on_delete=models.CASCADE,
        related_name="sales",
        db_column="trans_id",
    )
    product = models.ForeignKey(
        Inventory,
        on_delete=models.PROTECT,
        related_name="sales",
        db_column="product_id",
    )
    user = models.ForeignKey(
        PosUser,
        on_delete=models.PROTECT,
        related_name="sales",
        db_column="user_id",
    )
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    discount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_cost_sale = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price_sale = models.DecimalField(max_digits=12, decimal_places=2)
    revenue = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    
    SALE_STATUS_CHOICES = [
    ("completed", "Completed"),
    ("cancelled", "Cancelled"),
    ("refunded", "Refunded"),
    ]

    sale_status = models.CharField(max_length=20, choices=SALE_STATUS_CHOICES)

    class Meta:
        db_table = "sales"
        ordering = ["-created_at"]
        indexes = [models.Index(fields = ["created_at"])]

    def __str__(self):
        return f"Sale {self.sale_pid}"
