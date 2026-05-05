from datetime import timedelta

from django.db.models import (
    CharField,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Sum,
    Value,
)
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from inventory.models import Inventory
from itertools import chain
from purchases.models import PurchaseHeader
from sales.models import Sale, TransactionHeader

from .serializers import lowstockSerializer


@api_view(["GET"])
def totalsale_profit_transcation(request):
    today = timezone.now().date()
    queryset = Sale.objects.filter(created_at__date=today)
    result = queryset.aggregate(
        total_sale=Sum("subtotal"),
        profit = Sum(
            ExpressionWrapper(
                F("revenue"),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            )
        ),
        transcation=Count("transaction", distinct=True),
    )
    data = {
        "total_sales": result["total_sale"] or 0,
        "total_sale": result["total_sale"] or 0,
        "total_profit": result["profit"] or 0,
        "profit": result["profit"] or 0,
        "total_transactions": result["transcation"] or 0,
        "transcation": result["transcation"] or 0,
    }
    return Response(data)


@api_view(["GET"])
def rollingdailysale(request):
    today = timezone.now().date()
    start_date = today - timedelta(days=6)
    queryset = (
        TransactionHeader.objects.filter(trans_date__date__range=[start_date, today])
        .annotate(date=TruncDate("trans_date"))
        .values("date")
        .annotate(total=Sum("total_amount"))
        .order_by("date")
    )

    result_map = {row["date"]: row["total"] for row in queryset}
    final_data = []

    for i in range(7):
        day = start_date + timedelta(days=i)
        final_data.append({
            "date": day,
            "total": result_map.get(day, 0),
        })

    return Response(final_data)


@api_view(["GET"])
def lowstock(request):
    queryset = Inventory.objects.filter(
        stock_quantity__lte=F("reorder_level")
    )
    serializer = lowstockSerializer(queryset, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def topsellings(request):
    queryset = (
        Sale.objects.values("product_id", "product__name")
        .annotate(total_quantity=Sum("quantity"))
        .annotate(revenue=Sum("subtotal"))
        .order_by("-total_quantity")[:5]
    )
    return Response(queryset)


@api_view(["GET"])
def recentactivity(request):
    sales = TransactionHeader.objects.values(
        "trans_id", "user_id", "trans_date", "total_amount"
    ).annotate(
        activity_type=Value("SALE", output_field=CharField()),
        activity_id=F("trans_id"),
        activity_date=F("trans_date"),
        amount=F("total_amount"),
    )
    purchases = PurchaseHeader.objects.values(
        "purchase_id", "user_id", "purchase_date", "supplier_name", "total_cost"
    ).annotate(
        activity_type=Value("PURCHASE", output_field=CharField()),
        activity_id=F("purchase_id"),
        activity_date=F("purchase_date"),
        amount=F("total_cost"),
    )
    data = sorted(
        chain(sales, purchases),
        key=lambda item: item["activity_date"],
        reverse=True,
    )[:20]
    return Response(data)
