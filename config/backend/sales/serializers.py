from decimal import Decimal
from rest_framework import serializers
from .models import Sale, TransactionHeader
from inventory.models import Inventory


class SaleCreateItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    discount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        default=Decimal("0.00"),
        min_value=Decimal("0.00"),
    )


class SaleCreateSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=[choice[0] for choice in TransactionHeader.PAYMENT_METHODS]
    )
    payment = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.00"),
    )
    total = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.00"),
    )
    change = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=Decimal("0.00"),
    )
    items = SaleCreateItemSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item is required.")
        return value


class SaleLineSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source="product.product_id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Sale
        fields = [
            "sale_pid",
            "product_id",
            "product_name",
            "quantity",
            "discount",
            "unit_cost_sale",
            "unit_price_sale",
            "revenue",
            "subtotal",
            "sale_status",
            "created_at",
        ]


class TransactionHeaderSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.pk", read_only=True)
    items = SaleLineSerializer(source="sales", many=True, read_only=True)

    class Meta:
        model = TransactionHeader
        fields = [
            "trans_id",
            "user_id",
            "trans_date",
            "total_amount",
            "payment_method",
            "payment",
            "change",
            "created_at",
            "status",
            "items",
        ]


class TransactionListSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.pk", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = TransactionHeader
        fields = [
            "trans_id",
            "user_id",
            "trans_date",
            "total_amount",
            "payment_method",
            "payment",
            "change",
            "status",
            "item_count",
        ]

    def get_item_count(self, obj):
        return obj.sales.count()

class ItemLoadSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="product_id", read_only=True)
    price = serializers.DecimalField(
        source="unit_price",
        max_digits=12,
        decimal_places=2,
        read_only=True,
    )
    stock = serializers.IntegerField(source="stock_quantity", read_only=True)

    class Meta:
        model = Inventory
        fields = ["id", "name", "price", "stock"]
