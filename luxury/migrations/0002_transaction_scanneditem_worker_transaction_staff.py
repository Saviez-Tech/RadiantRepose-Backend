# Generated by Django 5.1.7 on 2025-04-18 09:50

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("luxury", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("subtotal", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "discount",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                ("amount_paid", models.DecimalField(decimal_places=2, max_digits=10)),
                ("balance_due", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "customer_name",
                    models.CharField(blank=True, max_length=255, null=True),
                ),
                (
                    "customer_contact",
                    models.CharField(blank=True, max_length=15, null=True),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ScannedItem",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("item_name", models.CharField(max_length=255)),
                ("quantity", models.PositiveIntegerField()),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "total_per_item",
                    models.DecimalField(decimal_places=2, max_digits=10),
                ),
                (
                    "transaction",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="scanned_items",
                        to="luxury.transaction",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="Worker",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=100)),
                ("phone_number", models.CharField(max_length=15)),
                ("address", models.CharField(max_length=255)),
                (
                    "branch",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="luxury.luxurybranch",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="transaction",
            name="staff",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE, to="luxury.worker"
            ),
        ),
    ]
