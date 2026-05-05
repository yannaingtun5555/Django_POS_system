from django.urls import path

from .views import dashboard_page, login_page,purchase_page,inventory_page,sale_page,history_page,setting_page,report_redirect


urlpatterns = [
    path("", login_page, name="login-page"),
    path("login/", login_page, name="login-page-alt"),
    path("dashboard/", dashboard_page, name="dashboard-page"),
    path("purchase/",purchase_page,name = "purchase-page"),
    path("inventory/",inventory_page,name = "inventory-page"),
    path("sale/",sale_page,name = "sale-page"),
    path("history/",history_page,name = "history-page"),
    path("setting/",setting_page,name = "setting-page"),  
    path('report/', report_redirect, name='report'),
        
]
