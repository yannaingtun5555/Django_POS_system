from django.urls import path
from .views import (
    create_trans_header,
    detail_trans_header,
    list_trans_header,
    load_1k_items,
    search_item_price,
    today_trans_header,
)

urlpatterns = [
    path("create/", create_trans_header, name="sales-create"),
    path("list/", list_trans_header, name="sales-list"),
    path("detail/<int:trans_id>/", detail_trans_header, name="sales-detail"),
    path("today/", today_trans_header, name="sales-today"),
    path("search_item_price/", search_item_price, name="sales-search-item-price"),
    path("load_1k_items/", load_1k_items, name="sales-load-1k-items"),
]
