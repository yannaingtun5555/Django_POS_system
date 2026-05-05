from pyexpat import model
from rest_framework import serializers
from .models import Inventory

class InventorySearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = [
            "product_id",
            "name",
            "unit_price"
        ]

class InventorySerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)

    class Meta:
        model = Inventory
        fields = [
            "product_id",
            "name",
            "plu_code",
            "barcode",
            "brand",
            "category",
            "unit_cost",
            "unit_price",
            "stock_quantity",
            "reorder_level",
            "needs_reorder",
        ]
        read_only_fields = ["created_at", "updated_at","needs_reorder"]

    def validate(self, attrs):
        attrs = super().validate(attrs)

        unit_cost = attrs.get("unit_cost", getattr(self.instance, "unit_cost", None))
        unit_price = attrs.get(
            "unit_price",
            getattr(self.instance, "unit_price", None),
        )

        if unit_cost is not None and unit_cost < 0:
            raise serializers.ValidationError(
                {"unit_cost": "Unit cost must be greater than or equal to 0."}
            )

        if unit_price is not None and unit_price < 0:
            raise serializers.ValidationError(
                {"unit_price": "Unit price must be greater than or equal to 0."}
            )

        if unit_cost is not None and unit_price is not None and unit_price < unit_cost:
            raise serializers.ValidationError(
                {"unit_price": "Unit price must be greater than or equal to unit cost."}
            )

        return attrs
