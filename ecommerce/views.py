# views.py
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import BuyersInfoSerializer
from rest_framework import generics,permissions
from .models import BuyersInfo,Order
from .serializers import OrderSerializer,NewOrderSerializer,ProductSummarySerializer,CustomerOrdersSerializer,ContactMessageSerializer,NewsletterSubscriberSerializer
from rest_framework.views import APIView
from luxury.models import Product

import requests
from django.conf import settings
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
        data = {
            "email": buyer.email,
            "amount": int(total_amount * 100),  # convert to kobo
            # Optional: "callback_url": "https://yourdomain.com/payment/verify/"
        }

        response = requests.post("https://api.paystack.co/transaction/initialize", json=data, headers=headers)
        paystack_data = response.json()

        # Extract the payment reference and save it to the buyer
        reference = paystack_data.get('data', {}).get('reference')
        if reference:
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
    # Paystack sends event data in request body
    event = request.data

    # You might want to verify event['event'] is 'charge.success'
    if event.get('event') == 'charge.success':
        # Extract reference from the event data
        reference = event['data'].get('reference')

        if not reference:
            return Response({'detail': 'Reference not found in webhook data'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Find the buyer using the reference
            buyer = BuyersInfo.objects.get(reference=reference)
        except BuyersInfo.DoesNotExist:
            return Response({'detail': 'Order with this reference not found'}, status=status.HTTP_404_NOT_FOUND)

        # Update payment status on buyer and orders
        # You can add extra checks like payment amount, currency, status etc.
        buyer_payment_success = event['data'].get('status') == 'success'

        if buyer_payment_success:
            buyer.save()  # if you want to update any buyer fields
            orders = Order.objects.filter(transaction=buyer)
            orders.update(payment=True)

            return Response({'detail': 'Payment confirmed and orders updated'}, status=status.HTTP_200_OK)

    # For other event types or failed payments, just acknowledge
    return Response({'detail': 'Event ignored'}, status=status.HTTP_200_OK)


class BuyersWithPendingOrdersList(generics.ListAPIView):
    serializer_class = BuyersInfoSerializer

    def get_queryset(self):
        return BuyersInfo.objects.filter(
            order__status='pending', order__payment=True
        ).distinct()
    

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
    url = f"https://api.paystack.co/transaction/verify/{reference}"
    try:
        response = requests.get(url, headers=headers)
        result = response.json()

        if result["status"] and result["data"]["status"] == "success":
            data = result["data"]
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