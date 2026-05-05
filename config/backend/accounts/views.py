from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import status
from constance import config
from django.conf import settings
from .permissions import IsPosAdmin
from .serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
)


class LoginView(TokenObtainPairView):
    serializer_class = LoginSerializer


@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPosAdmin])
def register(request):
    serializer = RegisterSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_view(request):
    refresh_token = request.data.get("refresh")
    if refresh_token:
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

    return Response(
        {"detail": "Logout successful."},
        status=status.HTTP_200_OK,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def change_password(request):
    serializer = ChangePasswordSerializer(
        data=request.data,
        context={"request": request},
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(
        {"detail": "Password changed successfully."},
        status=status.HTTP_200_OK,
    )

@api_view(["POST"])
@permission_classes([IsAuthenticated, IsPosAdmin])
def UpdateConfig(request):
    new_values = request.data

    for key, new_value in new_values.items():
        if key in getattr(settings, "CONSTANCE_CONFIG", {}):
            setattr(config, key, new_value)
        else:
            return Response(
                {"error": f"Invalid setting key: {key}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

    return Response(
        {"message": "Settings updated successfully", "updated": new_values},
        status=status.HTTP_200_OK,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_config(request):
    return Response(
        {
            "data": {
                "settings": {
                    "SHOP_NAME": config.SHOP_NAME,
                    "CURRENCY_PREFIX": config.CURRENCY_PREFIX,
                }
            }
        },
        status=status.HTTP_200_OK,
    )
