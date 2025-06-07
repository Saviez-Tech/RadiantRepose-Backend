from rest_framework import status,permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from .models import Transaction, ScannedItem, Product,Service,Booking,BookedService,SPAScannedItem,SPATransaction,SpaProduct
from .serializers import SaleSerializer,SaleSerializerr,ScannedItemSerializer,ProductSerializer,ScannedItemWithTransactionSerializer,BookingSerializer,ServiceSerializer,ListBookingSerializer,ListBookedServiceSerializer,SPAScannedItemInputSerializer,SPAScannedItemWithTransactionSerializer,SPATransactionSerializer,SpaProductSerializer,ServiceItemSerializer,SpaProductItemSerializer
from .models import Worker
from django.utils import timezone
from django.db import transaction
from rest_framework import generics
from django.http import Http404
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework.generics import ListAPIView
from rest_framework.exceptions import NotFound

# All Codes For the Luxury Section
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
    permission_classes = [IsAuthenticated]  # We'll handle admin logic in the view
    serializer_class = ProductSerializer

    def get_queryset(self):
        search_query = self.request.query_params.get('search', None)

        # If user is admin, search all products
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = Product.objects.all()
        else:
            try:
                worker = Worker.objects.get(user=self.request.user)
                queryset = Product.objects.filter(branch=worker.branch)
            except Worker.DoesNotExist:
                # Return empty queryset if worker profile is not found
                return Product.objects.none()

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(barcode__icontains=search_query)
            )

        return queryset
    


##### SPA APIS THIS SECTION CONTAINS APIS FOR SPA


# Booking Endpoints
class CreateBookingView(APIView):
    permission_classes = []
    def post(self, request):
        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class BookingDetailView(APIView):
    permission_classes = []

    def get(self, request, id):
        booking = get_object_or_404(Booking, id=id)
        serializer = ListBookingSerializer(booking)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ServiceListView(ListAPIView):
    permission_classes = []
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer


# POS ENDPOINTS

class BookedServiceSearchView(APIView):
    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return Response({"error": "Code query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)

        booked_services = BookedService.objects.filter(code=code)
        if not booked_services.exists():
            raise NotFound(detail="No booked services found with the given code.")

        serializer = ListBookedServiceSerializer(booked_services, many=True)
        return Response(serializer.data)


class SPASalesView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            worker = Worker.objects.get(user=request.user)
            worker_branch = worker.branch
        except Worker.DoesNotExist:
            return Response({"detail": "User is not a worker."}, status=status.HTTP_403_FORBIDDEN)

        request.data['staff'] = worker.id
        scanned_items_data = request.data.get('scanned_items', [])

        with transaction.atomic():
            products_cache = {}

            # Validate products and services without saving
            for item in scanned_items_data:
                if 'product_id' in item:
                    try:
                        product = SpaProduct.objects.get(id=item['product_id'])
                        if product.branch != worker_branch:
                            return Response({
                                "detail": f"Product '{product.name}' does not belong to your branch."
                            }, status=status.HTTP_400_BAD_REQUEST)
                        if item['quantity'] > product.stock_quantity:
                            return Response({
                                "detail": f"Insufficient stock for {product.name}. Available: {product.stock_quantity}."
                            }, status=status.HTTP_400_BAD_REQUEST)
                        products_cache[item['product_id']] = product
                    except SpaProduct.DoesNotExist:
                        return Response({"detail": f"Product ID {item['product_id']} not found."}, status=status.HTTP_400_BAD_REQUEST)

                elif 'service_id' in item:
                    try:
                        service = Service.objects.get(id=item['service_id'])
                        if service.branch != worker_branch:
                            return Response({
                                "detail": f"Service '{service.name}' does not belong to your branch."
                            }, status=status.HTTP_400_BAD_REQUEST)
                    except Service.DoesNotExist:
                        return Response({"detail": f"Service ID {item['service_id']} not found."}, status=status.HTTP_400_BAD_REQUEST)

            # Delegate saving to serializer
            serializer = SPATransactionSerializer(data=request.data)
            if serializer.is_valid():
                transaction_instance = serializer.save()

                # Decrease product stock only after successful save
                for item in scanned_items_data:
                    if 'product_id' in item:
                        product = products_cache[item['product_id']]
                        product.stock_quantity -= item['quantity']
                        product.save()

                response_data = SPATransactionSerializer(transaction_instance).data
                return Response(response_data, status=status.HTTP_201_CREATED)



            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def get(self, request):
        today = timezone.now().date()
        try:
            worker = Worker.objects.get(user=request.user)
            transactions = SPATransaction.objects.filter(staff=worker, timestamp__date=today)
            scanned_items = SPAScannedItem.objects.filter(transaction__in=transactions).select_related('transaction', 'product', 'service')
            serializer = SPAScannedItemWithTransactionSerializer(scanned_items, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Worker.DoesNotExist:
            return Response({"detail": "User is not a worker."}, status=status.HTTP_403_FORBIDDEN)
        


class SpaProductDetailListView(APIView):
    permission_classes = []

    def get(self, request, product_id=None, branch_id=None):
        if product_id:
            try:
                product = SpaProduct.objects.get(id=product_id)

                if request.user.is_authenticated:
                    try:
                        worker = Worker.objects.get(user=request.user)
                        if product.branch != worker.branch:
                            return Response(
                                {"detail": "Access denied. Product not in your branch."},
                                status=status.HTTP_403_FORBIDDEN
                            )
                    except Worker.DoesNotExist:
                        pass  # User is authenticated but not a worker; allow or deny as needed

                serializer = SpaProductSerializer(product)
                return Response(serializer.data, status=status.HTTP_200_OK)

            except SpaProduct.DoesNotExist:
                return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

        else:
            if request.user.is_authenticated:
                try:
                    worker = Worker.objects.get(user=request.user)
                    products = SpaProduct.objects.filter(branch=worker.branch)
                except Worker.DoesNotExist:
                    products = SpaProduct.objects.all()
            elif branch_id:
                products = SpaProduct.objects.filter(branch_id=branch_id)
            else:
                products = SpaProduct.objects.all()

            serializer = SpaProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)



class SpaProductSearchView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]  # We'll handle admin logic in the view
    serializer_class = SpaProductSerializer

    def get_queryset(self):
        search_query = self.request.query_params.get('search', None)

        # If user is admin, search all products
        if self.request.user.is_staff or self.request.user.is_superuser:
            queryset = SpaProduct.objects.all()
        else:
            try:
                worker = Worker.objects.get(user=self.request.user)
                queryset = SpaProduct.objects.filter(branch=worker.branch)
            except Worker.DoesNotExist:
                # Return empty queryset if worker profile is not found
                return SpaProduct.objects.none()

        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(category__icontains=search_query) |
                Q(barcode__icontains=search_query)
            )

        return queryset
    
class ServiceListByTransactionCode(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, code):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response({'error': 'Worker profile not found'}, status=status.HTTP_403_FORBIDDEN)

        try:
            transaction = SPATransaction.objects.get(code=code)
        except SPATransaction.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if transaction's staff branch == worker branch
        if transaction.staff.branch != worker.branch:
            return Response({'error': 'You do not have access to this transaction'}, status=status.HTTP_403_FORBIDDEN)

        services = SPAScannedItem.objects.filter(transaction=transaction, service__isnull=False)
        serializer = ServiceItemSerializer(services, many=True)  # Use ServiceItemSerializer, not ServiceSerializer!
        return Response(serializer.data, status=status.HTTP_200_OK)


class ProductListByTransactionCode(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, code):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response({'error': 'Worker profile not found'}, status=status.HTTP_403_FORBIDDEN)

        try:
            transaction = SPATransaction.objects.get(code=code)
        except SPATransaction.DoesNotExist:
            return Response({'error': 'Transaction not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if transaction's staff branch == worker branch
        if transaction.staff.branch != worker.branch:
            return Response({'error': 'You do not have access to this transaction'}, status=status.HTTP_403_FORBIDDEN)

        products = SPAScannedItem.objects.filter(transaction=transaction, product__isnull=False)
        serializer = SpaProductItemSerializer(products, many=True)  # Use ProductItemSerializer, not SpaProductSerializer!
        return Response(serializer.data, status=status.HTTP_200_OK)
    
class MarkSPAItemDone(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, item_id):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response({'error': 'Worker profile not found'}, status=status.HTTP_403_FORBIDDEN)

        try:
            item = SPAScannedItem.objects.select_related('transaction__staff__branch').get(id=item_id)
        except SPAScannedItem.DoesNotExist:
            return Response({'error': 'SPA item not found'}, status=status.HTTP_404_NOT_FOUND)

        # Check if worker belongs to same branch as transaction staff
        if item.transaction.staff.branch != worker.branch:
            return Response({'error': 'You do not have access to this item'}, status=status.HTTP_403_FORBIDDEN)

        # Mark as Done
        item.status = "Done"
        item.done_by = worker
        item.done_at = timezone.now()
        item.save()

        return Response({'message': 'SPA item marked as Done'}, status=status.HTTP_200_OK)


