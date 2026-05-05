from django.urls import path

from .views import (
    inventory_create,
    inventory_delete,
    inventory_detail,
    inventory_list,
    inventory_lookup,
    inventory_low_stock,
    inventory_search,
    inventory_update,
    inventory_list_all,
    inventory_export,
    inventory_bar_search,
    inventory_list_cat,
)

urlpatterns = [
    path("list/", inventory_list, name="inventory-list"),
    path("detail/<int:product_id>/", inventory_detail, name="inventory-detail"),
    path("lookup/", inventory_lookup, name="inventory-lookup"),
    path("search/", inventory_search, name="inventory-search"),
    path("create/", inventory_create, name="inventory-create"),
    path("update/<int:product_id>/", inventory_update, name="inventory-update"),
    path("delete/<int:product_id>/", inventory_delete, name="inventory-delete"),
    path("low-stock/", inventory_low_stock, name="inventory-low-stock"),
    path("list_all/",inventory_list_all,name = "inventory-list-all"),
    path("export/",inventory_export,name = "inventory-export"),
    path("bar_search/",inventory_bar_search,name = "inventory-bar-search"),
    path("list_category/",inventory_list_cat,name = "inventory-list-cat"),
]
