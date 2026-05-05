from rest_framework.permissions import BasePermission, SAFE_METHODS

from accounts.models import PosUser


class IsInventoryAdminOrReadOnly(BasePermission):
    message = "Only admin users can perform this action."

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        if request.method in SAFE_METHODS:
            return True

        return bool(
            getattr(user, "role", None) == PosUser.ROLE_ADMIN
            or user.is_staff
            or user.is_superuser
        )
