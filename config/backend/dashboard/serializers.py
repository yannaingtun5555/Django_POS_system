from itertools import product

from rest_framework import serializers
from sales.models import Sale, TransactionHeader
from inventory.models import Inventory
from purchases.models import PurchaseHeader


class lowstockSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventory
        fields = [
            "product_id",
            "name",
            "stock_quantity",
        ] 
