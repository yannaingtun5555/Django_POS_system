from decimal import Decimal
import csv
from rest_framework import status
from rest_framework.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
import io
from inventory.models import Inventory

from .models import PurchaseHeader, PurchaseItem
from .serializers import (
    CreateSerializers,
    PurchaseHeaderListSerializer,
    PurchaseDetailSerializer,
)


def _purchase_queryset():
    return PurchaseHeader.objects.select_related("user").prefetch_related(
        Prefetch("items", queryset=PurchaseItem.objects.select_related("product", "user")),
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_header_create(request):
    serializer = CreateSerializers(data=request.data)
    serializer.is_valid(raise_exception=True)

    data = serializer.validated_data
    item_data = data.pop("items")
    total_cost = Decimal("0.00")

    with transaction.atomic():
        purchase = PurchaseHeader.objects.create(
            user=request.user,
            purchase_date=timezone.now(),
            supplier_name=data["supplier"],
            payment_method=data["payment_method"],
            payment=data["payment"],
            total_cost=Decimal("0.00"),
            status=PurchaseHeader.STATUS_COMPLETED,
        )

        for each_item in item_data:
            product_id = each_item.get("product_id")
            quantity = each_item.get("quantity")
            unit_cost = each_item.get("unit_cost")
            barcode = each_item.get("barcode")
            if product_id is not None:
                inventory = get_object_or_404(Inventory, product_id=product_id)
            elif barcode is not None:
                inventory, created = Inventory.objects.get_or_create(
                    barcode=barcode,
                    defaults={
                        "name": each_item["product_name"],
                        "plu_code": each_item.get("plu_code"),
                        "brand": each_item.get("brand", ""),
                        "category": each_item.get("category", ""),
                        "unit_cost": unit_cost,
                        "unit_price": each_item["unit_price"],
                        "stock_quantity": 0,
                        "reorder_level": each_item.get("reorder_level", 0),
                    },
                )
                if not created:
                    inventory.name = each_item.get("product_name", inventory.name)
                    inventory.plu_code = each_item.get("plu_code", inventory.plu_code)
                    inventory.brand = each_item.get("brand", inventory.brand)
                    inventory.category = each_item.get("category", inventory.category)
                    inventory.unit_cost = unit_cost
                    inventory.unit_price = each_item.get(
                        "unit_price",
                        inventory.unit_price,
                    )
                    inventory.reorder_level = each_item.get(
                        "reorder_level",
                        inventory.reorder_level,
                    )
                    inventory.save(
                        update_fields=[
                            "name",
                            "plu_code",
                            "brand",
                            "category",
                            "unit_cost",
                            "unit_price",
                            "reorder_level",
                            "updated_at",
                        ]
                    )
            else:
                # No product_id and no barcode → create product with barcode = NULL
                inventory = Inventory.objects.create(
                    name=each_item["product_name"],
                    plu_code=each_item.get("plu_code"),
                    brand=each_item.get("brand", ""),
                    category=each_item.get("category", ""),
                    unit_cost=unit_cost,
                    unit_price=each_item["unit_price"],
                    stock_quantity=0,
                    reorder_level=each_item.get("reorder_level", 0),
                    barcode=None, 
                )   
            

            line_total = unit_cost * quantity

            inventory.stock_quantity += quantity
            inventory.save(update_fields=["stock_quantity", "updated_at"])

            PurchaseItem.objects.create(
                purchase=purchase,
                product=inventory,
                user=request.user,
                quantity=quantity,
                unit_cost=unit_cost,
                subtotal=line_total,
            )
            total_cost += line_total

        if purchase.payment > total_cost:
            raise ValidationError(
                {"payment": ["Payment cannot be greater than the total cost."]}
            )

        purchase.total_cost = total_cost
        purchase.save(update_fields=["total_cost"])

    purchase = _purchase_queryset().get(purchase_id=purchase.purchase_id)
    return Response(PurchaseDetailSerializer(purchase).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def purchase_header_list(request):
    queryset = _purchase_queryset()

    supplier = request.query_params.get("supplier")
    status_value = request.query_params.get("status")
    product_id = request.query_params.get("product_id")
    user_id = request.query_params.get("user_id")
    date_from = request.query_params.get("date_from")
    date_to = request.query_params.get("date_to")

    if supplier:
        queryset = queryset.filter(supplier_name__icontains=supplier)
    if status_value:
        queryset = queryset.filter(status=status_value)
    if product_id:
        queryset = queryset.filter(items__product_id=product_id)
    if user_id:
        queryset = queryset.filter(user_id=user_id)
    if date_from:
        queryset = queryset.filter(purchase_date__date__gte=date_from)
    if date_to:
        queryset = queryset.filter(purchase_date__date__lte=date_to)

    queryset = queryset.distinct()
    return Response(PurchaseHeaderListSerializer(queryset, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def purchase_header_detail(request, purchase_id):
    purchase = get_object_or_404(_purchase_queryset(), purchase_id=purchase_id)
    return Response(PurchaseDetailSerializer(purchase).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def purchase_header_return(request, purchase_id):
    with transaction.atomic():
        purchase = get_object_or_404(
            PurchaseHeader.objects.select_for_update().prefetch_related(
                Prefetch(
                    "items",
                    queryset=PurchaseItem.objects.select_related("product").select_for_update(),
                )
            ),
            purchase_id=purchase_id,
        )

        if purchase.status == PurchaseHeader.STATUS_RETURNED:
            return Response(
                {"detail": "Purchase has already been returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if purchase.status == PurchaseHeader.STATUS_CANCELLED:
            return Response(
                {"detail": "Cancelled purchases cannot be returned."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for item in purchase.items.all():
            if item.product.stock_quantity < item.quantity:
                return Response(
                    {
                        "detail": (
                            f"Insufficient stock to return product "
                            f"{item.product.product_id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        for item in purchase.items.all():
            item.product.stock_quantity -= item.quantity
            item.product.save(update_fields=["stock_quantity", "updated_at"])

        purchase.status = PurchaseHeader.STATUS_RETURNED
        purchase.save(update_fields=["status"])

    purchase = _purchase_queryset().get(purchase_id=purchase_id)
    return Response(PurchaseDetailSerializer(purchase).data)

#@api_view(["POST"])
#def purchase_import(request):
    