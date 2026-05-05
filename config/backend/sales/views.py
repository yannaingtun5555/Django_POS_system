from decimal import Decimal
from django.db.models import Case, IntegerField, Q, Value, When
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from inventory.models import Inventory
from .models import Sale, TransactionHeader
from .serializers import (
    ItemLoadSerializer,
    SaleCreateSerializer,
    TransactionHeaderSerializer,
    TransactionListSerializer,
)


def _build_sale_line(product, quantity, discount):
    line_total = (product.unit_price * quantity) - discount
    revenue = ((product.unit_price - product.unit_cost) * quantity) - discount

    return {
        "product": product,
        "quantity": quantity,
        "discount": discount,
        "unit_cost_sale": product.unit_cost,
        "unit_price_sale": product.unit_price,
        "subtotal": line_total,
        "revenue": revenue,
    }


def _search_inventory_items(query, search_type):
    queryset = Inventory.objects.all()

    if search_type == "barcode":
        queryset = queryset.annotate(
            match_rank=Case(
                When(barcode__iexact=query, then=Value(0)),
                When(barcode__istartswith=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).filter(barcode__icontains=query)
    elif search_type == "plu":
        queryset = queryset.annotate(
            match_rank=Case(
                When(plu_code__iexact=query, then=Value(0)),
                When(plu_code__istartswith=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).filter(plu_code__icontains=query)
    else:
        words = [word for word in query.split() if word]
        name_filter = Q()
        for word in words:
            name_filter &= Q(name__icontains=word)

        queryset = queryset.annotate(
            match_rank=Case(
                When(name__iexact=query, then=Value(0)),
                When(name__istartswith=query, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).filter(name_filter if words else Q())

    return queryset.order_by("match_rank", "name")


def _validate_item_search_params(request):
    query = request.query_params.get("q", "").strip()
    search_type = request.query_params.get("type", "name").strip().lower()

    if not query:
        return None, None, Response(
            {"detail": "Query parameter 'q' is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if search_type not in {"barcode", "plu", "name"}:
        return None, None, Response(
            {"detail": "Query parameter 'type' must be barcode, plu, or name."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return query, search_type, None


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_trans_header(request):
    serializer = SaleCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    payment_method = serializer.validated_data["payment_method"]
    payment = serializer.validated_data.get("payment")
    client_total = serializer.validated_data.get("total")
    client_change = serializer.validated_data.get("change")
    requested_items = serializer.validated_data["items"]

    with transaction.atomic():
        product_ids = [item["product_id"] for item in requested_items]
        locked_products = {
            product.product_id: product
            for product in Inventory.objects.select_for_update().filter(
                product_id__in=product_ids
            )
        }
        sale_lines = []
        total_amount = Decimal("0.00")

        for item in requested_items:
            product = locked_products.get(item["product_id"])
            if product is None:
                return Response(
                    {"detail": f"Product {item['product_id']} does not exist."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            quantity = item["quantity"]
            discount = item.get("discount", Decimal("0.00"))

            if quantity > product.stock_quantity:
                return Response(
                    {
                        "detail": (
                            f"Insufficient stock for product {product.product_id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            line = _build_sale_line(product, quantity, discount)
            if line["subtotal"] < 0:
                return Response(
                    {
                        "detail": (
                            f"Discount cannot exceed subtotal for product "
                            f"{product.product_id}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            sale_lines.append(line)
            total_amount += line["subtotal"]

        if client_total is not None and client_total != total_amount:
            return Response(
                {
                    "detail": (
                        "Submitted total does not match the calculated total."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payment_method == "cash":
            if payment is None:
                return Response(
                    {"detail": "Payment is required for cash transactions."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if payment < total_amount:
                return Response(
                    {"detail": "Payment must be greater than or equal to total."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            change = payment - total_amount
        else:
            payment = total_amount if payment is None else payment
            if payment != total_amount:
                return Response(
                    {
                        "detail": (
                            "Payment must exactly match the total for card or "
                            "mobile transactions."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            change = Decimal("0.00")

        if client_change is not None and client_change != change:
            return Response(
                {
                    "detail": (
                        "Submitted change does not match the calculated change."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        transaction_header = TransactionHeader.objects.create(
            user=request.user,
            trans_date=timezone.now(),
            total_amount=total_amount,
            payment_method=payment_method,
            payment=payment,
            change=change,
            status=TransactionHeader.STATUS_COMPLETED,
        )

        for line in sale_lines:
            Sale.objects.create(
                transaction=transaction_header,
                product=line["product"],
                user=request.user,
                quantity=line["quantity"],
                discount=line["discount"],
                unit_cost_sale=line["unit_cost_sale"],
                unit_price_sale=line["unit_price_sale"],
                revenue=line["revenue"],
                subtotal=line["subtotal"],
                sale_status=TransactionHeader.STATUS_COMPLETED,
            )
            line["product"].stock_quantity -= line["quantity"]
            line["product"].save(update_fields=["stock_quantity", "updated_at"])

    return Response(
        TransactionHeaderSerializer(transaction_header).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_trans_header(request):
    queryset = TransactionHeader.objects.select_related("user").prefetch_related(
        "sales",
        "sales__product",
    )
    return Response(TransactionListSerializer(queryset, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def detail_trans_header(request, trans_id):
    transaction_header = get_object_or_404(
        TransactionHeader.objects.select_related("user").prefetch_related(
            "sales",
            "sales__product",
        ),
        trans_id=trans_id,
    )
    return Response(TransactionHeaderSerializer(transaction_header).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def today_trans_header(request):
    today = timezone.localdate()
    queryset = (
        TransactionHeader.objects.select_related("user")
        .prefetch_related("sales", "sales__product")
        .filter(trans_date__date=today)
    )
    return Response(TransactionListSerializer(queryset, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_item_price(request):
    query, search_type, error_response = _validate_item_search_params(request)
    if error_response is not None:
        return error_response

    queryset = _search_inventory_items(query, search_type)[:1000]
    return Response(ItemLoadSerializer(queryset, many=True).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def load_1k_items(request):
    queryset = Inventory.objects.order_by("stock_quantity", "name")[:1000]
    return Response(ItemLoadSerializer(queryset, many=True).data)
