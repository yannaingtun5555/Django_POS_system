from rest_framework.permissions import BasePermission

from .models import PosUser


class IsPosAdmin(BasePermission):
    message = "Only admin users can perform this action."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, "role", None) == PosUser.ROLE_ADMIN
                or user.is_staff
                or user.is_superuser
            )
        )
