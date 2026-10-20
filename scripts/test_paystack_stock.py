import hashlib
import hmac
import json
import os
import sys
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RadiantRepose.test_settings')

import django

django.setup()

from django.conf import settings
from django.db import transaction
from rest_framework.test import APIClient

from ecommerce.models import BuyersInfo, Order
from luxury.models import Product


class RollbackTest(Exception):
    pass


def main():
    if not (BASE_DIR / 'db.sqlite').exists():
        raise SystemExit('db.sqlite is missing; run scripts/copy_products_to_test_db.py first.')

    client = APIClient()
    reference = f'test-{uuid.uuid4()}'

    try:
        with transaction.atomic():
            product = Product.objects.select_for_update().order_by('pk').first()
            if product is None:
                raise SystemExit('db.sqlite contains no products to test.')

            if product.stock_quantity < 1:
                product.stock_quantity = 1
                product.save(update_fields=['stock_quantity'])
            original_stock = product.stock_quantity

            buyer = BuyersInfo.objects.create(
                full_name='Local Test Buyer',
                email='test@example.test',
                phone='0000000000',
                street_address='Local test',
                zip_code='00000',
                city='Local test',
                state='Local test',
                country='Local test',
                reference=reference,
            )
            order = Order.objects.create(
                transaction=buyer,
                product=product,
                quantity=1,
                price_at_sale=product.price,
            )

            body = json.dumps({
                'event': 'charge.success',
                'data': {'reference': reference, 'status': 'success'},
            }).encode()
            signature = hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode(),
                body,
                hashlib.sha512,
            ).hexdigest()

            response = client.generic(
                'POST',
                '/api/ecommerce/webhook/paystack/',
                body,
                content_type='application/json',
                HTTP_X_PAYSTACK_SIGNATURE=signature,
            )
            if response.status_code != 200:
                raise AssertionError(f'Expected HTTP 200, got {response.status_code}: {response.content!r}')

            product.refresh_from_db()
            order.refresh_from_db()
            if product.stock_quantity != original_stock - 1 or not order.payment:
                raise AssertionError('Successful payment did not atomically reduce stock and mark the order paid.')

            replay_response = client.generic(
                'POST',
                '/api/ecommerce/webhook/paystack/',
                body,
                content_type='application/json',
                HTTP_X_PAYSTACK_SIGNATURE=signature,
            )
            product.refresh_from_db()
            if replay_response.status_code != 200 or product.stock_quantity != original_stock - 1:
                raise AssertionError('Webhook replay changed stock a second time.')

            raise RollbackTest()
    except RollbackTest:
        pass

    print('PASS: simulated Paystack webhook reduced local stock once; all test writes were rolled back.')


if __name__ == '__main__':
    main()
