# Generated by Django 5.1.7 on 2025-04-19 02:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("luxury", "0005_product_category"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="Luxury-Images"),
        ),
    ]
