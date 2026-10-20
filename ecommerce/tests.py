import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group, User
from django.test import TestCase
from rest_framework.test import APIClient

from ecommerce.models import BuyersInfo, Order, Preorder
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


class PreorderProductsListTests(TestCase):
    def setUp(self):
        self.branch = LuxuryBranch.objects.create(
            name='Preorder test branch',
            location='Test location',
            contact_number='0000000000',
        )
        self.preorder_product = Product.objects.create(
            name='Silk Robe',
            price='30.00',
            category='Loungewear',
            preorder=True,
            preorder_price='25.00',
            stock_quantity=0,
            barcode='TEST-PREORDER-001',
            branch=self.branch,
        )
        Product.objects.create(
            name='Regular product',
            price='20.00',
            preorder=False,
            stock_quantity=5,
            barcode='TEST-PREORDER-002',
            branch=self.branch,
        )
        other_branch = LuxuryBranch.objects.create(
            name='Another preorder branch',
            location='Another location',
            contact_number='0000000001',
        )
        self.other_branch_preorder_product = Product.objects.create(
            name='Preorder product from another branch',
            price='40.00',
            preorder=True,
            preorder_price='35.00',
            stock_quantity=0,
            barcode='TEST-PREORDER-003',
            branch=other_branch,
        )

    def test_lists_only_preorder_products_for_public_access(self):
        response = APIClient().get('/api/ecommerce/products/preorder/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {product['id'] for product in response.data},
            {self.preorder_product.id, self.other_branch_preorder_product.id},
        )
        self.assertTrue(all(product['preorder'] for product in response.data))

    def test_search_autocompletes_preorder_products_by_name_or_category(self):
        client = APIClient()
        food_flask = Product.objects.create(
            name='Food Flask',
            price='45.00',
            category='Kitchenware',
            preorder=True,
            preorder_price='40.00',
            stock_quantity=0,
            barcode='TEST-PREORDER-FLASK',
            branch=self.branch,
        )

        name_response = client.get(
            '/api/ecommerce/products/preorder/search/',
            {'q': 'sil'},
        )
        middle_of_name_response = client.get(
            '/api/ecommerce/products/preorder/search/',
            {'q': 'flask'},
        )
        category_response = client.get(
            '/api/ecommerce/products/preorder/search/',
            {'q': 'loun'},
        )

        self.assertEqual(name_response.status_code, 200)
        self.assertEqual(
            [product['id'] for product in name_response.data],
            [self.preorder_product.id],
        )
        self.assertEqual(middle_of_name_response.status_code, 200)
        self.assertEqual(
            [product['id'] for product in middle_of_name_response.data],
            [food_flask.id],
        )
        self.assertEqual(category_response.status_code, 200)
        self.assertEqual(
            [product['id'] for product in category_response.data],
            [self.preorder_product.id],
        )

    def test_search_is_case_insensitive_and_excludes_non_preorder_products(self):
        response = APIClient().get(
            '/api/ecommerce/products/preorder/search/',
            {'q': 'PRE'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            {product['id'] for product in response.data},
            {self.other_branch_preorder_product.id},
        )

    def test_search_without_query_returns_no_products(self):
        response = APIClient().get('/api/ecommerce/products/preorder/search/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, [])

    def test_preorder_record_stores_buyer_and_single_product(self):
        preorder = Preorder.objects.create(
            full_name='Preorder Buyer',
            email='preorder@example.test',
            phone='0000000000',
            street_address='Test street',
            zip_code='00000',
            city='Test city',
            state='Test state',
            country='Test country',
            product=self.preorder_product,
            quantity=2,
            price_at_order=self.preorder_product.preorder_price,
        )

        self.assertEqual(preorder.product, self.preorder_product)
        self.assertEqual(preorder.quantity, 2)
        self.assertEqual(preorder.price_at_order, self.preorder_product.preorder_price)
        self.assertFalse(preorder.payment)
        self.assertEqual(preorder.status, 'pending')


class PreorderPaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.branch = LuxuryBranch.objects.create(
            name='Preorder payment branch',
            location='Test location',
            contact_number='0000000000',
        )
        self.product = Product.objects.create(
            name='Preorder payment product',
            price='100.00',
            preorder=True,
            preorder_price='25.50',
            stock_quantity=0,
            barcode='TEST-PREORDER-PAYMENT-001',
            branch=self.branch,
        )
        self.payload = {
            'full_name': 'Preorder Buyer',
            'email': 'preorder@example.test',
            'phone': '0000000000',
            'street_address': 'Test street',
            'zip_code': '00000',
            'city': 'Test city',
            'state': 'Test state',
            'country': 'Test country',
            'product': self.product.pk,
            'quantity': 2,
            'note': 'Please contact me before delivery.',
        }

    @patch('ecommerce.views.requests.post')
    def test_creates_preorder_and_returns_paystack_checkout(self, post_payment):
        post_payment.return_value.json.return_value = {
            'status': True,
            'data': {
                'authorization_url': 'https://checkout.example.test/preorder',
                'reference': 'preorder-reference',
            },
        }

        response = self.client.post(
            '/api/ecommerce/preorders/',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data['payment']['data']['authorization_url'],
            'https://checkout.example.test/preorder',
        )
        post_payment.assert_called_once()
        self.assertEqual(
            post_payment.call_args.kwargs['json']['amount'],
            5100,
        )
        preorder = Preorder.objects.get(reference='preorder-reference')
        self.assertEqual(preorder.price_at_order, Decimal('25.50'))
        self.assertEqual(preorder.note, self.payload['note'])
        self.assertFalse(preorder.payment)

    @patch('ecommerce.views.requests.post')
    def test_rejects_product_not_available_for_preorder(self, post_payment):
        self.product.preorder = False
        self.product.save(update_fields=['preorder'])

        response = self.client.post(
            '/api/ecommerce/preorders/',
            self.payload,
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        post_payment.assert_not_called()
        self.assertFalse(Preorder.objects.exists())

    def post_preorder_success(self, amount=5100):
        preorder = Preorder.objects.create(
            full_name='Preorder Buyer',
            email='preorder@example.test',
            phone='0000000000',
            street_address='Test street',
            zip_code='00000',
            city='Test city',
            state='Test state',
            country='Test country',
            product=self.product,
            quantity=2,
            price_at_order='25.50',
            reference='preorder-reference',
        )
        body = json.dumps({
            'event': 'charge.success',
            'data': {
                'reference': preorder.reference,
                'status': 'success',
                'amount': amount,
            },
        }).encode()
        signature = hmac.new(
            settings.PAYSTACK_SECRET_KEY.encode(),
            body,
            hashlib.sha512,
        ).hexdigest()
        response = self.client.generic(
            'POST',
            '/api/ecommerce/webhook/paystack/',
            body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        return response, preorder

    def test_webhook_confirms_preorder_without_changing_stock(self):
        response, preorder = self.post_preorder_success()

        self.assertEqual(response.status_code, 200)
        preorder.refresh_from_db()
        self.product.refresh_from_db()
        self.assertTrue(preorder.payment)
        self.assertEqual(self.product.stock_quantity, 0)

    def test_webhook_rejects_wrong_amount_and_leaves_preorder_unpaid(self):
        response, preorder = self.post_preorder_success(amount=1)

        self.assertEqual(response.status_code, 400)
        preorder.refresh_from_db()
        self.assertFalse(preorder.payment)

    def test_webhook_replay_keeps_preorder_confirmed(self):
        first_response, preorder = self.post_preorder_success()
        second_response = self.client.generic(
            'POST',
            '/api/ecommerce/webhook/paystack/',
            json.dumps({
                'event': 'charge.success',
                'data': {
                    'reference': preorder.reference,
                    'status': 'success',
                    'amount': 5100,
                },
            }).encode(),
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=hmac.new(
                settings.PAYSTACK_SECRET_KEY.encode(),
                json.dumps({
                    'event': 'charge.success',
                    'data': {
                        'reference': preorder.reference,
                        'status': 'success',
                        'amount': 5100,
                    },
                }).encode(),
                hashlib.sha512,
            ).hexdigest(),
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        preorder.refresh_from_db()
        self.assertTrue(preorder.payment)


class AdminPreorderManagementTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin_user = User.objects.create_user(
            username='preorder-admin',
            password='test-password',
        )
        admin_group, _ = Group.objects.get_or_create(name='Administrator')
        self.admin_user.groups.add(admin_group)
        self.branch = LuxuryBranch.objects.create(
            name='Admin preorder branch',
            location='Test location',
            contact_number='0000000000',
        )
        self.product = Product.objects.create(
            name='Admin preorder product',
            price='50.00',
            preorder=True,
            preorder_price='40.00',
            stock_quantity=0,
            barcode='TEST-ADMIN-PREORDER-001',
            branch=self.branch,
        )
        self.preorder = Preorder.objects.create(
            full_name='Admin Test Buyer',
            email='admin-buyer@example.test',
            phone='0000000000',
            street_address='Test street',
            zip_code='00000',
            city='Test city',
            state='Test state',
            country='Test country',
            reference='admin-preorder-reference',
            product=self.product,
            quantity=1,
            price_at_order='40.00',
            payment=True,
        )

    def test_admin_can_list_all_preorders(self):
        response = self.client.get('/api/admin/preorders/')
        self.assertEqual(response.status_code, 401)
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get('/api/admin/preorders/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.preorder.id)

    def test_admin_can_mark_paid_preorder_delivered(self):
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            f'/api/admin/preorders/{self.preorder.id}/deliver/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['status'], 'delivered')
        self.preorder.refresh_from_db()
        self.assertEqual(self.preorder.status, 'delivered')

    def test_unpaid_preorder_cannot_be_marked_delivered(self):
        self.preorder.payment = False
        self.preorder.save(update_fields=['payment'])
        self.client.force_authenticate(user=self.admin_user)

        response = self.client.patch(
            f'/api/admin/preorders/{self.preorder.id}/deliver/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, 409)
        self.preorder.refresh_from_db()
        self.assertEqual(self.preorder.status, 'pending')

    def test_non_admin_cannot_list_preorders(self):
        ordinary_user = User.objects.create_user(
            username='ordinary-user',
            password='test-password',
        )
        self.client.force_authenticate(user=ordinary_user)

        response = self.client.get('/api/admin/preorders/')

        self.assertEqual(response.status_code, 403)

    @patch('ecommerce.views.requests.get')
    def test_reference_verification_confirms_preorder(self, get_payment):
        preorder = Preorder.objects.create(
            full_name='Preorder Buyer',
            email='preorder@example.test',
            phone='0000000000',
            street_address='Test street',
            zip_code='00000',
            city='Test city',
            state='Test state',
            country='Test country',
            product=self.product,
            quantity=2,
            price_at_order='25.50',
            reference='preorder-verify-reference',
        )
        get_payment.return_value.json.return_value = {
            'status': True,
            'data': {
                'status': 'success',
                'reference': preorder.reference,
                'amount': 5100,
                'currency': 'NGN',
                'customer': {'email': preorder.email},
                'transaction_date': '2026-10-20T00:00:00Z',
                'gateway_response': 'Successful',
            },
        }

        response = self.client.get(
            f'/api/ecommerce/preorders/verify/{preorder.reference}/'
        )

        self.assertEqual(response.status_code, 200)
        preorder.refresh_from_db()
        self.assertTrue(preorder.payment)
