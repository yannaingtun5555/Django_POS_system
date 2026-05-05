from django.db import models

# Create your models here.
class Inventory(models.Model):
    product_id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255)
    plu_code = models.CharField(max_length=20, unique=True, null=True, blank=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=100, blank=True)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    reorder_level = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "inventory"
        ordering = ["name"]
        indexes = [
        models.Index(fields=["barcode"]),
        models.Index(fields=["name"]),
        models.Index(fields=["plu_code"]),
        ]

    @property
    def needs_reorder(self):
        return self.stock_quantity <= self.reorder_level

    def __str__(self):
        return f"{self.name} ({self.barcode})"
