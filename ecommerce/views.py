# views.py
import hashlib
import hmac

from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.db import transaction
from django.db.models import Q
from .serializers import BuyersInfoSerializer
from rest_framework import generics,permissions
from .models import BuyersInfo, Order, Preorder
from .serializers import (
    OrderSerializer,
    NewOrderSerializer,
    ProductSummarySerializer,
    CustomerOrdersSerializer,
    ContactMessageSerializer,
    NewsletterSubscriberSerializer,
    PreorderCheckoutSerializer,
    PreorderSerializer,
)
from rest_framework.views import APIView
from luxury.models import Product
from luxury.serializers import ProductSerializer

import requests
from django.views.decorators.csrf import csrf_exempt

@api_view(['POST'])
@permission_classes([AllowAny])
def create_order_and_initialize_payment(request):
    serializer = BuyersInfoSerializer(data=request.data)

    if serializer.is_valid():
        scanned_items_data = serializer.validated_data.pop('order')

        total_amount = 0
        for item in scanned_items_data:
            product = item['product']
            quantity = item['quantity']
            total_amount += product.price * quantity

        # Create the buyer without reference first
        buyer = BuyersInfo.objects.create(**serializer.validated_data)

        # Create the orders (payment=False)
        for item in scanned_items_data:
            Order.objects.create(
                transaction=buyer,
                product=item['product'],
                quantity=item['quantity'],
                price_at_sale=item['product'].price,
                payment=False
            )

        # Initialize Paystack payment
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        headers["Authorization"] = f"Bearer {settings.PAYSTACK_SECRET_KEY}"
        data = {
            "email": buyer.email,
            "amount": int(total_amount * 100),  # convert to kobo
            # Optional: "callback_url": "https://yourdomain.com/payment/verify/"
        }

        try:
            response = requests.post(
                "https://api.paystack.co/transaction/initialize",
                json=data,
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
            paystack_data = response.json()
        except requests.RequestException:
            buyer.delete()
            return Response(
                {"detail": "Could not connect to Paystack to initialize payment."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError:
            buyer.delete()
            return Response(
                {"detail": "Paystack returned an invalid payment initialization response."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        if not paystack_data.get('status'):
            buyer.delete()
            return Response(
                {"detail": paystack_data.get('message') or "Paystack could not initialize payment."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Extract the payment reference and save it to the buyer
        payment_data = paystack_data.get('data') or {}
        reference = payment_data.get('reference')
        if not reference or not payment_data.get('authorization_url'):
            buyer.delete()
            return Response(
                {"detail": "Paystack did not return a payment reference and checkout URL."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        buyer.reference = reference
        buyer.save()

        return Response({
            "buyer": BuyersInfoSerializer(buyer).data,
            "payment": paystack_data
        }, status=201)

    return Response(serializer.errors, status=400)




@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def paystack_webhook(request):
    signature = request.headers.get('x-paystack-signature', '')
    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode(),
        request.body,
        hashlib.sha512,
    ).hexdigest()
    if not hmac.compare_digest(signature, expected_signature):
        return Response({'detail': 'Invalid Paystack signature'}, status=status.HTTP_401_UNAUTHORIZED)

    event = request.data

    if event.get('event') == 'charge.success':
        event_data = event.get('data') or {}
        reference = event_data.get('reference')

        if not reference:
            return Response({'detail': 'Reference not found in webhook data'}, status=status.HTTP_400_BAD_REQUEST)

        if event_data.get('status') != 'success':
            return Response({'detail': 'Event ignored'}, status=status.HTTP_200_OK)

        if Preorder.objects.filter(reference=reference).exists():
            return confirm_preorder_payment(reference, event_data.get('amount'))

        return confirm_paid_orders(reference)

    return Response({'detail': 'Event ignored'}, status=status.HTTP_200_OK)


def confirm_paid_orders(reference):
    with transaction.atomic():
        try:
            buyer = BuyersInfo.objects.select_for_update().get(reference=reference)
        except BuyersInfo.DoesNotExist:
            return Response({'detail': 'Order with this reference not found'}, status=status.HTTP_404_NOT_FOUND)

        orders = list(
            Order.objects.select_for_update()
            .filter(transaction=buyer)
            .order_by('product_id', 'id')
        )
        if not orders:
            return Response({'detail': 'No orders found for this payment'}, status=status.HTTP_404_NOT_FOUND)

        if all(order.payment for order in orders):
            return Response({'detail': 'Payment already confirmed'}, status=status.HTTP_200_OK)

        quantities_by_product = {}
        unpaid_orders = [order for order in orders if not order.payment]
        for order in unpaid_orders:
            quantities_by_product[order.product_id] = (
                quantities_by_product.get(order.product_id, 0) + order.quantity
            )

        products = {
            product.pk: product
            for product in Product.objects.select_for_update()
            .filter(pk__in=quantities_by_product)
            .order_by('pk')
        }
        for product_id, quantity in quantities_by_product.items():
            product = products[product_id]
            if quantity > product.stock_quantity:
                return Response(
                    {
                        'detail': (
                            f'Payment succeeded, but there is insufficient stock for '
                            f'{product.name}. The order requires manual follow-up.'
                        )
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        for product_id, quantity in quantities_by_product.items():
            product = products[product_id]
            product.stock_quantity -= quantity
            product.save(update_fields=['stock_quantity'])

        Order.objects.filter(pk__in=[order.pk for order in unpaid_orders]).update(payment=True)

    return Response({'detail': 'Payment confirmed, orders updated, and stock reduced'}, status=status.HTTP_200_OK)


def confirm_preorder_payment(reference, paid_amount):
    try:
        paid_amount = int(paid_amount)
    except (TypeError, ValueError):
        return Response(
            {'detail': 'Payment amount is missing or invalid'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    with transaction.atomic():
        try:
            preorder = Preorder.objects.select_for_update().get(reference=reference)
        except Preorder.DoesNotExist:
            return Response({'detail': 'Preorder with this reference not found'}, status=status.HTTP_404_NOT_FOUND)

        expected_amount = int(preorder.price_at_order * preorder.quantity * 100)
        if paid_amount != expected_amount:
            return Response(
                {'detail': 'Payment amount does not match the preorder total'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if preorder.payment:
            return Response({'detail': 'Preorder payment already confirmed'}, status=status.HTTP_200_OK)

        preorder.payment = True
        preorder.save(update_fields=['payment'])

    return Response(
        {'detail': 'Preorder payment confirmed', 'reference': reference},
        status=status.HTTP_200_OK,
    )


class BuyersWithPendingOrdersList(generics.ListAPIView):
    serializer_class = BuyersInfoSerializer

    def get_queryset(self):
        return BuyersInfo.objects.filter(
            order__status='pending', order__payment=True
        ).distinct()


class PreorderProductsList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(preorder=True).select_related('branch').order_by('id')


class PreorderProductSearchList(generics.ListAPIView):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    result_limit = 10

    def get_queryset(self):
        query = self.request.query_params.get('q', '').strip()
        if not query:
            return Product.objects.none()

        return (
            Product.objects.filter(preorder=True)
            .filter(Q(name__icontains=query) | Q(category__icontains=query))
            .select_related('branch')
            .order_by('name', 'id')[:self.result_limit]
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def create_preorder_and_initialize_payment(request):
    serializer = PreorderCheckoutSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    validated_data = serializer.validated_data
    product = validated_data['product']
    amount = int(product.preorder_price * validated_data['quantity'] * 100)
    headers = {
        'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}',
        'Content-Type': 'application/json',
    }
    try:
        response = requests.post(
            'https://api.paystack.co/transaction/initialize',
            json={'email': validated_data['email'], 'amount': amount},
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        paystack_data = response.json()
    except requests.RequestException:
        return Response(
            {'detail': 'Could not connect to Paystack to initialize preorder payment.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError:
        return Response(
            {'detail': 'Paystack returned an invalid payment initialization response.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    if not paystack_data.get('status'):
        return Response(
            {'detail': paystack_data.get('message') or 'Paystack could not initialize preorder payment.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    payment_data = paystack_data.get('data') or {}
    reference = payment_data.get('reference')
    if not reference or not payment_data.get('authorization_url'):
        return Response(
            {'detail': 'Paystack did not return a preorder reference and checkout URL.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    preorder = serializer.save(
        reference=reference,
        price_at_order=product.preorder_price,
    )
    return Response(
        {
            'preorder': PreorderSerializer(preorder).data,
            'payment': paystack_data,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_preorder_payment(request, reference):
    headers = {'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'}
    try:
        response = requests.get(
            f'https://api.paystack.co/transaction/verify/{reference}',
            headers=headers,
            timeout=15,
        )
        response.raise_for_status()
        result = response.json()
    except requests.RequestException:
        return Response(
            {'detail': 'Could not connect to Paystack to verify preorder payment.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except ValueError:
        return Response(
            {'detail': 'Paystack returned an invalid verification response.'},
            status=status.HTTP_502_BAD_GATEWAY,
        )

    payment_data = result.get('data') or {}
    if (
        not result.get('status')
        or payment_data.get('status') != 'success'
        or payment_data.get('reference') != reference
    ):
        return Response(
            {
                'status': 'failed',
                'message': payment_data.get('gateway_response', 'Payment not successful'),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    confirmation = confirm_preorder_payment(reference, payment_data.get('amount'))
    if confirmation.status_code != status.HTTP_200_OK:
        return confirmation

    return Response({
        'status': 'success',
        'reference': reference,
        'amount': payment_data.get('amount', 0) / 100,
        'currency': payment_data.get('currency'),
        'email': (payment_data.get('customer') or {}).get('email'),
        'transaction_date': payment_data.get('transaction_date'),
        'gateway_response': payment_data.get('gateway_response'),
    })
    

class BuyerOrdersDetail(generics.GenericAPIView):
    serializer_class = CustomerOrdersSerializer

    def get(self, request, *args, **kwargs):
        buyer_id = self.kwargs['pk']
        orders = Order.objects.filter(transaction_id=buyer_id)

        if not orders.exists():
            return Response({"detail": "No orders found."}, status=404)

        # Extract the customer info from one of the orders (they all have same customer)
        customer_data = BuyersInfoSerializer(orders.first().transaction).data
        products_data = ProductSummarySerializer(orders, many=True).data

        
        data = {
            "customer": customer_data,
            "products": products_data
        }
        return Response(data)

    


class FulfillBuyerOrdersAPIView(APIView):
    permission_classes = [permissions.AllowAny]  # No auth required

    def patch(self, request, buyer_id):
        try:
            buyer = BuyersInfo.objects.get(id=buyer_id)
        except BuyersInfo.DoesNotExist:
            return Response({"message": "Buyer not found."}, status=status.HTTP_404_NOT_FOUND)

        orders = Order.objects.filter(transaction=buyer)

        if not orders.exists():
            return Response({"message": "No orders found for this buyer."}, status=status.HTTP_404_NOT_FOUND)

        orders.update(status="fulfilled")

        return Response({
            "message": f"All orders for '{buyer.full_name}' have been marked as fulfilled."
        }, status=status.HTTP_200_OK)
    



#PAYMENT 


@api_view(['POST'])
@permission_classes([AllowAny])
def initialize_payment(request):
    email = request.data.get("email")
    amount = int(request.data.get("amount")) * 100  # in kobo
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
        "Content-Type": "application/json",
    }
    data = {
        "email": email,
        "amount": amount,
    }
    response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
    return Response(response.json())



@api_view(['GET'])
@permission_classes([AllowAny])
def verify_payment(request, reference):
    headers = {
        "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
    }
    headers["Authorization"] = f"Bearer {settings.PAYSTACK_SECRET_KEY}"
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    try:
        response = requests.get(url, headers=headers)
        result = response.json()

        if result["status"] and result["data"]["status"] == "success":
            data = result["data"]
            if BuyersInfo.objects.filter(reference=reference).exists():
                confirmation = confirm_paid_orders(reference)
                if confirmation.status_code != status.HTTP_200_OK:
                    return confirmation

            return Response({
                "status": "success",
                "reference": data["reference"],
                "amount": data["amount"] / 100,  # Convert from kobo to naira
                "currency": data["currency"],
                "email": data["customer"]["email"],
                "transaction_date": data["transaction_date"],
                "gateway_response": data["gateway_response"]
            })

        return Response({
            "status": "failed",
            "message": result["data"].get("gateway_response", "Payment not successful")
        }, status=400)

    except Exception as e:
        return Response({"status": "error", "message": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([])
def contact_message_create(request):
    serializer = ContactMessageSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Your message has been sent successfully.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
@permission_classes([])
def subscribe_newsletter(request):
    serializer = NewsletterSubscriberSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Successfully subscribed to newsletter.'}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)