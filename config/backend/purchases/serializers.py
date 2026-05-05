from rest_framework import serializers

from .models import PurchaseHeader, PurchaseItem


class PurchaseItemCreateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(required=False)
    product_name = serializers.CharField(required=False)
    barcode = serializers.CharField(required=False,allow_blank=True, allow_null=True)
    plu_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    brand = serializers.CharField(required=False, allow_blank=True)
    category = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.IntegerField(min_value=1)
    unit_cost = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0,
    )
    unit_price = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        required=False,
        min_value=0,
    )
    reorder_level = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs):
        product_id = attrs.get("product_id")

        if product_id is not None:
            return attrs

        if not attrs.get("product_name"):
            raise serializers.ValidationError({"product_name": "This field is required when product_id is not provided."})
        if not attrs.get("unit_price"):
            raise serializers.ValidationError({"unit_price": "This field is required when product_id is not provided."})

        return attrs


class CreateSerializers(serializers.Serializer):
    supplier = serializers.CharField()
    payment_method = serializers.ChoiceField(
        choices=[choice[0] for choice in PurchaseHeader.PAYMENT_METHODS]
    )
    payment = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    items = PurchaseItemCreateSerializer(many=True)

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError("At least one item must be added")
        return value
    
class PurchasesItemSerilizer(serializers.ModelSerializer):
    purchase_item_id = serializers.IntegerField(read_only=True)
    product_id = serializers.IntegerField(source="product.product_id", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = PurchaseItem
        fields = [
            "purchase_item_id",
            "product_id",
            "product_name",
            "quantity",
            "unit_cost",
            "subtotal"
        ]

class PurchaseDetailSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.pk", read_only=True)
    items = PurchasesItemSerilizer(many = True)
    class Meta:
        model = PurchaseHeader
        fields = [
            "purchase_id",
            "user_id",
            "purchase_date",
            "supplier_name",
            "payment_method",
            "payment",
            "status",
            "items",
            "total_cost",
            "created_at"
        ]
class PurchaseHeaderListSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.pk", read_only=True)
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseHeader
        fields = [
            "purchase_id",
            "user_id",
            "purchase_date",
            "created_at",
            "supplier_name",
            "payment_method",
            "payment",
            "total_cost",
            "status",
            "item_count",
        ]

    def get_item_count(self, obj):
        return obj.items.count()
