# Generated by Django 5.1.7 on 2025-05-21 11:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecommerce', '0003_order_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='payment',
            field=models.BooleanField(default=False),
        ),
    ]
