# views.py
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from .serializers import BuyersInfoSerializer
from rest_framework import generics,permissions
from .models import BuyersInfo,Order
from .serializers import OrderSerializer,NewOrderSerializer
from rest_framework.views import APIView


@api_view(['POST'])
@permission_classes([AllowAny])
def create_order(request):
    serializer = BuyersInfoSerializer(data=request.data)

    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # Handle flattened custom errors for "product" and "message"
    errors = serializer.errors
    if "order" in errors:
        order_errors = errors["order"]
        for item in order_errors:
            if isinstance(item, dict):
                if "product" in item:
                    return Response({"detail": item["product"][0]}, status=status.HTTP_400_BAD_REQUEST)
                if "message" in item:
                    return Response({"detail": item["message"][0]}, status=status.HTTP_400_BAD_REQUEST)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class BuyersWithPendingOrdersList(generics.ListAPIView):
    serializer_class = BuyersInfoSerializer

    def get_queryset(self):
        return BuyersInfo.objects.filter(
            order__status='pending'
        ).distinct()
    

class BuyerOrdersDetail(generics.ListAPIView):
    serializer_class = NewOrderSerializer

    def get_queryset(self):
        buyer_id = self.kwargs['pk']
        return Order.objects.filter(transaction_id=buyer_id)
    


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