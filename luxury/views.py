from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Transaction, ScannedItem, Product
from .serializers import SaleSerializer,SaleSerializerr,ScannedItemSerializer,ProductSerializer,ScannedItemWithTransactionSerializer
from .models import Worker
from django.utils import timezone
from django.db import transaction
from rest_framework import generics
from django.http import Http404
from django.db.models import Q

class SalesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response({"detail": "User is not a worker."}, status=status.HTTP_403_FORBIDDEN)

        request.data['staff'] = worker.id
        scanned_items_data = request.data.get('scanned_items', [])

        with transaction.atomic():
            # 1. First, check if all products exist and have enough stock
            products = {}
            for item in scanned_items_data:
                try:
                    product = Product.objects.get(id=item['product_id'])
                    products[item['product_id']] = product  # cache it so we don't re-query
                except Product.DoesNotExist:
                    return Response(
                        {"detail": f"Product with ID {item['product_id']} does not exist."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                if item['quantity'] > product.stock_quantity:
                    return Response(
                        {"detail": f"Insufficient stock for {product.name}. Available stock: {product.stock_quantity}."},
                        status=status.HTTP_400_BAD_REQUEST
                    )

            # 2. Now save the sale transaction
            serializer = SaleSerializerr(data=request.data)
            if serializer.is_valid():
                transaction_instance = serializer.save()

                # 3. Now create the scanned items and update stock
                for item in scanned_items_data:
                    product = products[item['product_id']]

                    ScannedItem.objects.create(
                        transaction=transaction_instance,
                        product=product,
                        quantity=item['quantity'],
                        price_at_sale=product.price
                    )

                    product.stock_quantity -= item['quantity']
                    product.save()

                return Response({"transaction_id": transaction_instance.id}, status=status.HTTP_201_CREATED)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
    def get(self, request):
        today = timezone.now().date()
        try:
            worker = Worker.objects.get(user=request.user)
            # Get all scanned items for this worker's transactions today
            transactions = Transaction.objects.filter(staff=worker, timestamp__date=today)
            scanned_items = ScannedItem.objects.filter(transaction__in=transactions).select_related('transaction', 'product')
            serializer = ScannedItemWithTransactionSerializer(scanned_items, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Worker.DoesNotExist:
            return Response({"detail": "User is not a worker."}, status=status.HTTP_403_FORBIDDEN)

class TransactionDetailView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, transaction_id):
        # Get the transaction for the authenticated worker
        try:
            worker = Worker.objects.get(user=self.request.user)
            transaction = Transaction.objects.get(id=transaction_id, staff=worker)
            scanned_items = ScannedItem.objects.filter(transaction=transaction)  # Get scanned items for the transaction
            serializer = ScannedItemSerializer(scanned_items, many=True)  # Serialize the scanned items
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Worker.DoesNotExist:
            raise Http404("User is not a worker.")
        except Transaction.DoesNotExist:
            raise Http404("Transaction not found.")
        
        

class ProductSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        queryset = Product.objects.all()
        search_query = self.request.query_params.get('search', None)

        if search_query:
            # Use Q objects to filter by name, category, or barcode
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(barcode__icontains=search_query)
            )

        return queryset