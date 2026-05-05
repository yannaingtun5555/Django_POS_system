from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import LoginView, UpdateConfig, change_password, get_config, logout_view, me, register

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('register/', register, name='register'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('me/', me, name='me'),
    path('logout/', logout_view, name='logout'),
    path('change-password/', change_password, name='change-password'),
    path('config/', get_config, name='frontend-setting'),
    path('update_config/',UpdateConfig,name = 'update-config'),
]
