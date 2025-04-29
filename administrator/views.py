from django.shortcuts import render
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from luxury.models import Product, LuxuryBranch,ScannedItem,Transaction,Worker
from luxury.serializers import ProductSerializer, LuxuryBranchSerializer,ScannedItemSerializer,SaleSerializer,WorkerSerializer
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminUser  # Import the custom permission
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.conf import settings
from supabase import create_client
from rest_framework.authentication import TokenAuthentication
import urllib.parse

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Create your views here.

class ProductView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # Ensure the user is authenticated and is an admin
    authentication_classes = [TokenAuthentication]
    
    def get(self, request, product_id=None, branch_id=None):
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                serializer = ProductSerializer(product)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            # If branch_id is provided, filter products by branch
            if branch_id:
                products = Product.objects.filter(branch_id=branch_id)
            else:
                products = Product.objects.all()
            serializer = ProductSerializer(products, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        serializer = ProductSerializer(data=request.data)

        if serializer.is_valid():
            product = serializer.save()

            return Response(ProductSerializer(product).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def put(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            serializer = ProductSerializer(product, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)
            serializer = ProductSerializer(product, data=request.data, partial=True)  # Set partial=True for partial updates
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, product_id):
        try:
            product = Product.objects.get(id=product_id)

            # Delete image from Supabase Storage if image_url exists
            if product.image_url:

                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

                # Extract path from image_url
                # e.g. https://xyz.supabase.co/storage/v1/object/public/media/products/1/img.jpg
                public_url_prefix = f"{settings.SUPABASE_URL}/storage/v1/object/public/media/"
                if product.image_url.startswith(public_url_prefix):
                    file_path = urllib.parse.unquote(product.image_url.replace(public_url_prefix, ""))
                    supabase.storage.from_("media").remove([file_path])

            product.delete()
            return Response({"detail": "Product deleted."}, status=status.HTTP_204_NO_CONTENT)

        except Product.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

class LuxuryBranchView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # Ensure the user is authenticated and is an admin

    def get(self, request, branch_id=None):
        if branch_id:
            try:
                branch = LuxuryBranch.objects.get(id=branch_id)
                serializer = LuxuryBranchSerializer(branch)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except LuxuryBranch.DoesNotExist:
                return Response({"detail": "LuxuryBranch not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            branches = LuxuryBranch.objects.all()
            serializer = LuxuryBranchSerializer(branches, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = LuxuryBranchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, branch_id):
        try:
            branch = LuxuryBranch.objects.get(id=branch_id)
            serializer = LuxuryBranchSerializer(branch, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LuxuryBranch.DoesNotExist:
            return Response({"detail": "LuxuryBranch not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, branch_id):
        try:
            branch = LuxuryBranch.objects.get(id=branch_id)
            serializer = LuxuryBranchSerializer(branch, data=request.data, partial=True)  # Set partial=True for partial updates
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except LuxuryBranch.DoesNotExist:
            return Response({"detail": "LuxuryBranch not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, branch_id):
        try:
            branch = LuxuryBranch.objects.get(id=branch_id)
            branch.delete()
            return Response({"detail": "LuxuryBranch deleted."}, status=status.HTTP_204_NO_CONTENT)
        except LuxuryBranch.DoesNotExist:
            return Response({"detail": "LuxuryBranch not found."}, status=status.HTTP_404_NOT_FOUND)





class TotalGoodsSoldView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Get the filter parameter (day, week, month)
        filter_type = request.query_params.get('filter', 'day')
        today = timezone.now().date()

        if filter_type == 'day':
            start_date = today
            end_date = today + timedelta(days=1)
        elif filter_type == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=7)
        elif filter_type == 'month':
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=31)).replace(day=1)
        else:
            return Response({"detail": "Invalid filter type."}, status=status.HTTP_400_BAD_REQUEST)

        # Calculate total goods sold
        total_sold_quantity = ScannedItem.objects.filter(
            transaction__timestamp__range=(start_date, end_date)
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        # Calculate total price of sold items
        total_sold_price = Transaction.objects.filter(
            timestamp__range=(start_date, end_date)
        ).aggregate(total_price=Sum('subtotal'))['total_price'] or 0
        
        low_stock_count = Product.objects.filter(stock_quantity__in=[0, 1, 2]).count()


        return Response({
            "total_goods_sold": total_sold_quantity,
            "total_price": total_sold_price,
            "low_stock":low_stock_count
        }, status=status.HTTP_200_OK)
    
class FilterScannedItemsByCategoryView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ScannedItemSerializer

    def get_queryset(self):
        category_name = self.request.query_params.get('category', None)
        if category_name:
            # Filter based on the category field in the Product model
            return ScannedItem.objects.filter(product__category__icontains=category_name)
        return ScannedItem.objects.none()  # Return an empty queryset if no category is provided

class ListAllSalesView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SaleSerializer

    def get_queryset(self):
        queryset = Transaction.objects.all()
        date_str = self.request.query_params.get('date', None)  # Get the date parameter

        # Filter by specific date
        if date_str:
            try:
                selected_date = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                queryset = queryset.filter(timestamp__date=selected_date)
            except ValueError:
                return Transaction.objects.none()  # Return an empty queryset if the date format is invalid

        # Order by timestamp descending (most recent first)
        queryset = queryset.order_by('-timestamp')

        return queryset
    
class FilterProductsByQuantityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Filter for quantities of 2, 1, or 0
        return Product.objects.filter(stock_quantity__in=[0, 1, 2])
    
    
class CategorySalesReportView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        filter_type = request.query_params.get('filter', 'day')
        today = timezone.now().date()

        if filter_type == 'day':
            start_date = today
            end_date = today + timedelta(days=1)
        elif filter_type == 'week':
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=7)
        elif filter_type == 'month':
            start_date = today.replace(day=1)
            end_date = (start_date + timedelta(days=31)).replace(day=1)
        else:
            return Response({"detail": "Invalid filter type."}, status=status.HTTP_400_BAD_REQUEST)

        scanned_items = ScannedItem.objects.filter(
            transaction__timestamp__range=(start_date, end_date)
        ).select_related('product')

        category_data = {}

        for item in scanned_items:
            # Normalize category: lowercase and remove surrounding spaces
            category_name = (item.product.category or 'Uncategorized').strip().lower()

            item_total_price = item.quantity * item.price_at_sale

            if category_name not in category_data:
                category_data[category_name] = {
                    "total_quantity_sold": 0,
                    "total_amount_made": 0
                }

            category_data[category_name]["total_quantity_sold"] += item.quantity
            category_data[category_name]["total_amount_made"] += float(item_total_price)

        return Response(category_data, status=status.HTTP_200_OK)
    
    
class WorkerUpdateAPIView(generics.UpdateAPIView):
    queryset = Worker.objects.all()
    serializer_class = WorkerSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    

class WorkerDisableAPIView(APIView):
    permission_classes = [IsAuthenticated,IsAdminUser]

    def post(self, request, pk):
        worker = get_object_or_404(Worker, pk=pk)
        user = worker.user
        user.is_active = False
        user.save()
        return Response({"message": "Worker account disabled successfully."}, status=status.HTTP_200_OK)
    
class WorkerEnableAPIView(APIView):
    permission_classes = [IsAuthenticated,IsAdminUser]

    def post(self, request, pk):
        worker = get_object_or_404(Worker, pk=pk)
        user = worker.user
        user.is_active = True
        user.save()
        return Response({"message": "Worker account enabled successfully."}, status=status.HTTP_200_OK)