from django.db.models import F, Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Inventory
from .permissions import IsInventoryAdminOrReadOnly
from .serializers import  InventorySerializer,InventorySearchSerializer
from openpyxl import Workbook
from django.http import HttpResponse

def _serialize_inventory_queryset(queryset):
    return InventorySerializer(queryset, many=True).data

def _serialize_search(queryset):
    return InventorySearchSerializer(queryset,many = True).data


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInventoryAdminOrReadOnly])
def inventory_list(request):
    queryset = Inventory.objects.all()

    category = request.query_params.get("category")
    brand = request.query_params.get("brand")

    if category:
        queryset = queryset.filter(category__iexact=category)

    if brand:
        queryset = queryset.filter(brand__iexact=brand)

    return Response(_serialize_inventory_queryset(queryset))

@api_view(["GET"])
def inventory_list_all(request):
    queryset = Inventory.objects.all()
    serializer = InventorySerializer(queryset,many = True)
    return Response(serializer.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInventoryAdminOrReadOnly])
def inventory_detail(request, product_id):
    product = get_object_or_404(Inventory, product_id=product_id)
    return Response(InventorySerializer(product).data)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInventoryAdminOrReadOnly])
def inventory_lookup(request):
    barcode = request.query_params.get("barcode", "").strip()
    plu_code = request.query_params.get("plu_code", "").strip()

    if not barcode and not plu_code:
        return Response(
            {"detail": "Provide either barcode or plu_code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if barcode and plu_code:
        return Response(
            {"detail": "Provide only one lookup field: barcode or plu_code."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    filters = {"barcode": barcode} if barcode else {"plu_code": plu_code}
    product = get_object_or_404(Inventory, **filters)
    return Response(InventorySerializer(product).data)


@api_view(["GET"])
@permission_classes([])
def inventory_search(request):
    query = request.query_params.get("q", "").strip()

    queryset = Inventory.objects.all()
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query)
            | Q(plu_code__icontains=query)
            | Q(barcode__icontains=query)
        )

    return Response(_serialize_inventory_queryset(queryset))

@api_view(["GET"])
@permission_classes([])
def inventory_bar_search(request):
    query = request.query_params.get("q", "").strip()

    queryset = Inventory.objects.all()
    if query:
        exact_matches = queryset.filter(
            Q(barcode__iexact=query) | Q(plu_code__iexact=query)
        )
        if exact_matches.exists():
            return Response(_serialize_inventory_queryset(exact_matches))

        queryset = queryset.filter(
            Q(barcode__istartswith=query) | Q(plu_code__istartswith=query)
        )
    else:
        queryset = queryset.none()

    return Response(_serialize_inventory_queryset(queryset))

@api_view(["GET"])
def inventory_list_cat(request):
    query = Inventory.objects.values_list('category',flat=True).distinct()
    return Response(query)

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsInventoryAdminOrReadOnly])
def inventory_low_stock(request):
    queryset = Inventory.objects.filter(stock_quantity__lte=F("reorder_level"))
    return Response(_serialize_inventory_queryset(queryset))


@api_view(["POST"])
@permission_classes([])
def inventory_create(request):
    serializer = InventorySerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    product = serializer.save()
    return Response(InventorySerializer(product).data, status=status.HTTP_201_CREATED)


@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def inventory_update(request, product_id):
    product = get_object_or_404(Inventory, product_id=product_id)
    serializer = InventorySerializer(
        product,
        data=request.data,
        partial=request.method == "PATCH",
    )
    serializer.is_valid(raise_exception=True)
    product = serializer.save()
    return Response(InventorySerializer(product).data)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated, IsInventoryAdminOrReadOnly])
def inventory_delete(request, product_id):
    product = get_object_or_404(Inventory, product_id=product_id)

    if product.sales.exists() or product.purchase_items.exists():
        return Response(
            {
                "detail": (
                    "Cannot delete a product that has sales or purchase history."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    product.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(["GET"])
def inventory_export(request):
    products = Inventory.objects.all().values(
            'name', 'plu_code', 'barcode', 'brand',
            'category', 'stock_quantity', 'unit_cost',
            'unit_price', 'reorder_level'
        )

    wb = Workbook()
    ws = wb.active
    ws.title = "Inventory Report"

    headers =['Name', 'PLU Code', 'Barcode', 'Brand', 
                'Category', 'Stock Quantity', 'Unit Cost', 
               ' Unit Price', 'Reorder Level']
    ws.append(headers)

    for product in products:
        row = [
            product['name'],
            product['plu_code'],
            product['barcode'],
            product['brand'],
            product['category'],
            product['stock_quantity'],
            product['unit_cost'],
            product['unit_price'],
            product['reorder_level'],
        ]
        ws.append(row)

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=inventory_export.xlsx'
    wb.save(response)
    return response
