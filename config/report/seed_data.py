import argparse
import os
import random
from decimal import Decimal, ROUND_HALF_UP

import django
from faker import Faker
from django.utils import timezone

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from accounts.models import PosUser
from inventory.models import Inventory
from purchases.models import PurchaseHeader, PurchaseItem
from sales.models import Sale, TransactionHeader


fake = Faker()


def d2(value: float) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def create_users(count: int) -> list[PosUser]:
    users = []
    for i in range(count):
        username = f"{fake.user_name()}_{i}"
        user = PosUser.objects.create_user(
            username=username,
            email=fake.email(),
            password="password123",
            role=PosUser.ROLE_ADMIN if i == 0 else PosUser.ROLE_CASHIER,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
        )
        users.append(user)
    return users


def create_inventory(count: int) -> list[Inventory]:
    categories = ["Beverage", "Snack", "Grocery", "Personal Care", "Household"]
    products = []
    for i in range(count):
        cost = d2(random.uniform(0.5, 30.0))
        markup = Decimal(str(random.uniform(1.2, 2.2)))
        price = (cost * markup).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        product = Inventory.objects.create(
            name=fake.word().title() + f" {i+1}",
            plu_code=f"PLU{i+1000}",
            barcode=fake.unique.ean13(),
            brand=fake.company()[:100],
            category=random.choice(categories),
            unit_cost=cost,
            unit_price=price,
            stock_quantity=random.randint(30, 300),
            reorder_level=random.randint(5, 25),
        )
        products.append(product)
    return products


def create_purchases(users: list[PosUser], products: list[Inventory], count: int) -> None:
    payment_methods = [x[0] for x in PurchaseHeader.PAYMENT_METHODS]
    statuses = [x[0] for x in PurchaseHeader.STATUS_CHOICES]
    for _ in range(count):
        user = random.choice(users)
        purchase_date = fake.date_time_between(start_date="-90d", end_date="now", tzinfo=timezone.get_current_timezone())
        item_count = random.randint(1, 6)
        chosen = random.sample(products, k=min(item_count, len(products)))
        lines = []
        total_cost = Decimal("0.00")
        for p in chosen:
            qty = random.randint(1, 20)
            unit_cost = p.unit_cost
            subtotal = (unit_cost * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            lines.append((p, qty, unit_cost, subtotal))
            total_cost += subtotal
            p.stock_quantity += qty
            p.save(update_fields=["stock_quantity"])

        header = PurchaseHeader.objects.create(
            user=user,
            purchase_date=purchase_date,
            supplier_name=fake.company(),
            total_cost=total_cost,
            payment_method=random.choice(payment_methods),
            payment=total_cost,
            status=random.choice(statuses),
        )
        for p, qty, unit_cost, subtotal in lines:
            PurchaseItem.objects.create(
                purchase=header,
                product=p,
                user=user,
                quantity=qty,
                unit_cost=unit_cost,
                subtotal=subtotal,
            )


def create_sales(users: list[PosUser], products: list[Inventory], count: int) -> None:
    payment_methods = [x[0] for x in TransactionHeader.PAYMENT_METHODS]
    tx_statuses = [x[0] for x in TransactionHeader.STATUS_CHOICES]
    sale_statuses = [x[0] for x in Sale.SALE_STATUS_CHOICES]
    for _ in range(count):
        user = random.choice(users)
        trans_date = fake.date_time_between(start_date="-90d", end_date="now", tzinfo=timezone.get_current_timezone())
        item_count = random.randint(1, 5)
        sellable = [p for p in products if p.stock_quantity > 0]
        if not sellable:
            break
        chosen = random.sample(sellable, k=min(item_count, len(sellable)))
        lines = []
        total = Decimal("0.00")
        for p in chosen:
            qty = random.randint(1, min(5, p.stock_quantity))
            discount = d2(random.uniform(0.0, 1.5))
            gross = (p.unit_price * qty).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            subtotal = max(Decimal("0.00"), gross - discount)
            revenue = (subtotal - (p.unit_cost * qty)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            lines.append((p, qty, discount, subtotal, revenue))
            total += subtotal
            p.stock_quantity -= qty
            p.save(update_fields=["stock_quantity"])

        payment = total + d2(random.uniform(0.0, 10.0))
        change = (payment - total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        tx = TransactionHeader.objects.create(
            user=user,
            trans_date=trans_date,
            total_amount=total,
            payment_method=random.choice(payment_methods),
            payment=payment,
            change=change,
            status=random.choice(tx_statuses),
        )
        for p, qty, discount, subtotal, revenue in lines:
            Sale.objects.create(
                transaction=tx,
                product=p,
                user=user,
                quantity=qty,
                discount=discount,
                unit_cost_sale=p.unit_cost,
                unit_price_sale=p.unit_price,
                revenue=revenue,
                subtotal=subtotal,
                sale_status=random.choice(sale_statuses),
            )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed POS database with Faker data")
    parser.add_argument("--users", type=int, default=8)
    parser.add_argument("--products", type=int, default=50)
    parser.add_argument("--purchases", type=int, default=120)
    parser.add_argument("--sales", type=int, default=200)
    parser.add_argument("--clear", action="store_true", help="Delete existing data before seeding")
    args = parser.parse_args()

    if args.clear:
        Sale.objects.all().delete()
        TransactionHeader.objects.all().delete()
        PurchaseItem.objects.all().delete()
        PurchaseHeader.objects.all().delete()
        Inventory.objects.all().delete()
        PosUser.objects.exclude(is_superuser=True).delete()

    users = list(PosUser.objects.all())
    if not users:
        users = create_users(args.users)
    products = list(Inventory.objects.all())
    if not products:
        products = create_inventory(args.products)

    create_purchases(users, products, args.purchases)
    create_sales(users, products, args.sales)
    print("Seeding completed.")


if __name__ == "__main__":
    main()
