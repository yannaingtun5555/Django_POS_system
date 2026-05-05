from django.contrib.auth.models import AbstractUser
from django.db import models


class PosUser(AbstractUser):
    ROLE_ADMIN = "admin"
    ROLE_CASHIER = "cashier"
    ROLE_CHOICES = [
        (ROLE_ADMIN, "Admin"),
        (ROLE_CASHIER, "Cashier"),
    ]

    user_id = models.BigAutoField(primary_key=True)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_CASHIER,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "users"
        ordering = ["username"]

    def __str__(self):
        return self.username
