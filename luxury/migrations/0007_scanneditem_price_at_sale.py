# Generated by Django 5.1.7 on 2025-04-26 15:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("luxury", "0006_product_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="scanneditem",
            name="price_at_sale",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
    ]
