import hashlib
import hmac
import json
from unittest.mock import patch

from django.conf import settings
from django.test import TestCase
from rest_framework.test import APIClient

from ecommerce.models import BuyersInfo, Order
from luxury.models import LuxuryBranch, Product


class PaystackWebhookStockTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = LuxuryBranch.objects.create(
            name='Test branch',
            location='Test location',
            contact_number='0000000000',
        )
        self.product = Product.objects.create(
            name='Test product',
            price='10.00',
            stock_quantity=8,
            barcode='TEST-STOCK-001',
            branch=self.branch,
        )
        self.buyer = BuyersInfo.objects.create(
            full_name='Test Buyer',
            email='buyer@example.test',
            phone='0000000000',
            street_address='Test street',
            zip_code='00000',
            city='Test city',
            state='Test state',
            country='Test country',
            reference='test-reference',
        )
        self.order = Order.objects.create(
            transaction=self.buyer,
            product=self.product,
            quantity=3,
            price_at_sale=self.product.price,
        )

    def post_charge_success(self, reference='test-reference', **extra):
        payload = {
            'event': 'charge.success',
            'data': {'reference': reference, 'status': 'success', **extra},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        return self.client.generic(
            'POST',
            '/api/ecommerce/webhook/paystack/',
            body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

    def test_successful_payment_reduces_stock_and_marks_order_paid(self):
        response = self.post_charge_success()

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertTrue(self.order.payment)


class PaystackOrderInitializationTests(TestCase):
    def setUp(self):
        self.branch = LuxuryBranch.objects.create(
            name='Checkout test branch',
            location='Test location',
            contact_number='0000000000',
        )
        self.product = Product.objects.create(
            name='Checkout test product',
            price='25.00',
            stock_quantity=4,
            barcode='TEST-CHECKOUT-001',
            branch=self.branch,
        )
        self.payload = {
            'full_name': 'Checkout Test Buyer',
            'email': 'checkout@example.test',
            'phone': '0000000000',
            'street_address': 'Test street',
            'zip_code': '00000',
            'city': 'Test city',
            'state': 'Test state',
            'country': 'Test country',
            'order': [{'product': self.product.pk, 'quantity': 1}],
        }

    @patch('ecommerce.views.requests.post')
    def test_successful_initialization_returns_checkout_url(self, post_payment):
        post_payment.return_value.json.return_value = {
            'status': True,
            'message': 'Authorization URL created',
            'data': {
                'authorization_url': 'https://checkout.example.test/pay',
                'reference': 'checkout-reference',
            },
        }

        response = APIClient().post(
            '/api/ecommerce/make-order',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data['payment']['data']['authorization_url'],
            'https://checkout.example.test/pay',
        )
        post_payment.assert_called_once()
        headers = post_payment.call_args.kwargs['headers']
        self.assertEqual(
            headers['Authorization'],
            f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        )
        buyer = BuyersInfo.objects.get(reference='checkout-reference')
        self.assertEqual(Order.objects.filter(transaction=buyer).count(), 1)

    @patch('ecommerce.views.requests.post')
    def test_failed_initialization_does_not_leave_pending_order(self, post_payment):
        post_payment.return_value.json.return_value = {
            'status': False,
            'message': 'Invalid key',
            'data': {},
        }

        response = APIClient().post(
            '/api/ecommerce/make-order',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.data['detail'], 'Invalid key')
        self.assertFalse(BuyersInfo.objects.exists())
        self.assertFalse(Order.objects.exists())

class PaystackWebhookFollowupTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = LuxuryBranch.objects.create(
            name='Test branch',
            location='Test location',
            contact_number='0000000000',
        )
        self.product = Product.objects.create(
            name='Test product',
            price='10.00',
            stock_quantity=8,
            barcode='TEST-STOCK-002',
            branch=self.branch,
        )
        self.buyer = BuyersInfo.objects.create(
            full_name='Test Buyer',
            email='buyer@example.test',
            phone='0000000000',
            street_address='Test street',
            zip_code='00000',
            city='Test city',
            state='Test state',
            country='Test country',
            reference='test-reference',
        )
        self.order = Order.objects.create(
            transaction=self.buyer,
            product=self.product,
            quantity=3,
            price_at_sale=self.product.price,
        )

    def post_charge_success(self, reference='test-reference', **extra):
        payload = {
            'event': 'charge.success',
            'data': {'reference': reference, 'status': 'success', **extra},
        }
        body = json.dumps(payload).encode()
        signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        return self.client.generic(
            'POST',
            '/api/ecommerce/webhook/paystack/',
            body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

    def test_replayed_success_webhook_does_not_reduce_stock_twice(self):
        self.post_charge_success()
        response = self.post_charge_success()

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_insufficient_stock_does_not_partially_confirm_order(self):
        self.product.stock_quantity = 2
        self.product.save(update_fields=['stock_quantity'])

        response = self.post_charge_success()

        self.assertEqual(response.status_code, 409)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 2)
        self.assertFalse(self.order.payment)

    def test_invalid_signature_does_not_confirm_or_change_stock(self):
        payload = json.dumps({
            'event': 'charge.success',
            'data': {'reference': 'test-reference', 'status': 'success'},
        }).encode()
        response = self.client.generic(
            'POST',
            '/api/ecommerce/webhook/paystack/',
            payload,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='invalid',
        )

        self.assertEqual(response.status_code, 401)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 8)
        self.assertFalse(self.order.payment)

    @patch('ecommerce.views.requests.get')
    def test_successful_payment_verification_reduces_stock(self, get_payment):
        get_payment.return_value.json.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': 'test-reference',
                'amount': 3000,
                'currency': 'NGN',
                'customer': {'email': 'buyer@example.test'},
                'transaction_date': '2026-10-20T00:00:00Z',
                'gateway_response': 'Successful',
            },
        }

        response = self.client.get('/api/ecommerce/paystack/verify/test-reference/')

        self.assertEqual(response.status_code, 200)
        self.product.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertTrue(self.order.payment)
