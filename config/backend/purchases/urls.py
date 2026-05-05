from django.urls import path
from .views import(
    purchase_header_create,
    purchase_header_list,
    purchase_header_detail,
    purchase_header_return,
    #purchase_import,
)
urlpatterns = [
    path("create/",purchase_header_create,name = "purchase-header-create"),
    path("list/",purchase_header_list,name = "purchase-header-list"),
    path("detail/<int:purchase_id>/",purchase_header_detail,name = "purchase-header-detail"),
    path("return/<int:purchase_id>/",purchase_header_return,name = "purchase-header-return"),
    #path("import/",purchase_import,name = "purchase-import")
]
