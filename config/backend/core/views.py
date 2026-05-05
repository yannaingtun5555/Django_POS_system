from django.shortcuts import render
from django.shortcuts import redirect

def login_page(request):
    return render(request, "core/login.html")

def dashboard_page(request):
    return render(request, "core/dashboard.html")

def purchase_page(request):
    return render(request, "core/purchase.html")

def inventory_page(request):
    return render(request,"core/inventory.html")

def sale_page(request):
    return render(request,"core/sale.html")

def history_page(request):
    return render(request,"core/history.html")

def setting_page(request):
    return render(request,"core/settings.html")

from django.shortcuts import redirect

def report_redirect(request):
    return redirect("http://localhost:8501/")