from django.shortcuts import render
from rest_framework import generics
from rest_framework import status,permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from luxury.models import Product, LuxuryBranch,ScannedItem,Transaction,Worker,SPAScannedItem,SPATransaction,SpaProduct
from luxury.serializers import ProductSerializer, LuxuryBranchSerializer,ScannedItemSerializer,SaleSerializer,WorkerSerializer,WorkerSerializerr,ScannedItemWithTransactionSerializer,SpaProductSerializer
from rest_framework.permissions import IsAuthenticated, AllowAny
from .permissions import IsAdminUser  # Import the custom permission
from django.utils import timezone
from datetime import datetime, timedelta
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.conf import settings
from supabase import create_client
from rest_framework.authentication import TokenAuthentication
import urllib.parse
from rest_framework.exceptions import ValidationError
from .serializers import ScannedItemWithTransactionSerializer,SpaScannedItemWithTransactionSerializer

from django.db.models import Sum, F
import calendar

supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

# Create your views here.

class ProductView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # Ensure the user is authenticated and is an admin
    authentication_classes = [TokenAuthentication]

    def get_permissions(self):
        if self.request.method == 'GET':
            # For GET request, allow any user (public access)
            return [AllowAny()]
        # For other methods (e.g., POST, PUT, DELETE), enforce the default permissions
        return super().get_permissions()
    
    def get(self, request, product_id=None, branch_id=None):
        if product_id:
            try:
                product = Product.objects.get(id=product_id)
                if request.user.is_authenticated:
                    try:
                        worker = Worker.objects.get(user=request.user)
                        # Check if product belongs to user's branch
                        if product.branch != worker.branch:
                            return Response({"detail": "Access denied. Product not in your branch."}, status=status.HTTP_403_FORBIDDEN)
                    except Worker.DoesNotExist:
                        product = Product.objects.get(id=product_id)
                # If not authenticated or authorized, return product details
                serializer = ProductSerializer(product)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Product.DoesNotExist:
                return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            if request.user.is_authenticated:
                try:
                    worker = Worker.objects.get(user=request.user)
                    products = Product.objects.filter(branch=worker.branch)
                except Worker.DoesNotExist:
                    products = Product.objects.all()
            elif branch_id:
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

        # Flatten and return the first error message in a clean format
        first_error = next(iter(serializer.errors.values()))[0]
        raise ValidationError({"detail": str(first_error)})
    
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

    def get_permissions(self):
        if self.request.method == 'GET':
            # For GET request, allow any user (public access)
            return [AllowAny()]
        # For other methods (e.g., POST, PUT, DELETE), enforce the default permissions
        return super().get_permissions()
    
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
    permission_classes = []

    def get(self, request):
        filter_value = request.query_params.get('filter', 'day')
        today = timezone.now().date()

        # Try to parse filter_value as a date
        try:
            specific_date = datetime.strptime(filter_value, "%Y-%m-%d").date()
            start_date = specific_date
            end_date = specific_date + timedelta(days=1)
        except ValueError:
            # Not a date, so treat it as a filter type
            if filter_value == 'day':
                start_date = today
                end_date = today + timedelta(days=1)
            elif filter_value == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif filter_value == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
            elif filter_value == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                return Response({"detail": "Invalid filter value. Use day, week, month, year, or a valid date (YYYY-MM-DD)."},
                                status=status.HTTP_400_BAD_REQUEST)

        total_sold_quantity = ScannedItem.objects.filter(
            transaction__timestamp__range=(start_date, end_date)
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        total_sold_price = Transaction.objects.filter(
            timestamp__range=(start_date, end_date)
        ).aggregate(total_price=Sum('subtotal'))['total_price'] or 0

        low_stock_count = Product.objects.filter(stock_quantity__in=[0]).count()

        return Response({
            "total_goods_sold": total_sold_quantity,
            "total_price": total_sold_price,
            "low_stock": low_stock_count
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
    permission_classes = []
    serializer_class = ScannedItemWithTransactionSerializer

    def get_queryset(self):
        queryset = ScannedItem.objects.select_related('transaction').order_by('-transaction__id')
        filter_value = self.request.query_params.get('date', 'day')
        today = timezone.now().date()

        try:
            # Try parsing as a date
            selected_date = datetime.strptime(filter_value, '%Y-%m-%d').date()
            return queryset.filter(transaction__timestamp__date=selected_date)
        except ValueError:
            # Not a date, treat as keyword
            if filter_value == 'day':
                start_date = today
                end_date = today + timedelta(days=1)
            elif filter_value == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif filter_value == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
            elif filter_value == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                return ScannedItem.objects.none()  # Invalid filter

            return queryset.filter(transaction__timestamp__date__range=(start_date, end_date))
    
class FilterProductsByQuantityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Filter for quantities of 2, 1, or 0
        return Product.objects.filter(stock_quantity__in=[0, 1, 2])
    
    
class CategorySalesReportView(generics.GenericAPIView):
    permission_classes = []

    def get(self, request):
        filter_value = request.query_params.get('filter', 'day')
        today = timezone.now().date()

        try:
            # Try parsing as a date
            specific_date = datetime.strptime(filter_value, "%Y-%m-%d").date()
            start_date = specific_date
            end_date = specific_date + timedelta(days=1)
        except ValueError:
            # Not a date, treat as keyword filter
            if filter_value == 'day':
                start_date = today
                end_date = today + timedelta(days=1)
            elif filter_value == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif filter_value == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
            elif filter_value == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                return Response({"detail": "Invalid filter type or date format. Use YYYY-MM-DD or one of: day, week, month, year."}, status=status.HTTP_400_BAD_REQUEST)

        scanned_items = ScannedItem.objects.filter(
            transaction__timestamp__range=(start_date, end_date)
        ).select_related('product')

        category_data = {}

        for item in scanned_items:
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
    
    
class WorkerListAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        workers = Worker.objects.all()
        data = []
        for worker in workers:
            serialized = WorkerSerializerr(worker).data
            serialized["status"] = "Active" if worker.user.is_active else "Inactive"
            serialized["usernamae"] = worker.user.username
            data.append(serialized)
        return Response(data, status=status.HTTP_200_OK)


class WeeklySalesGraphView(APIView):
    def get(self, request):
        # Get optional week_start date from query params (format: YYYY-MM-DD)
        week_start_str = request.query_params.get('week_start')

        if week_start_str:
            try:
                week_start = datetime.strptime(week_start_str, '%Y-%m-%d').date()
            except ValueError:
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Default to current week (start from Monday)
            today = datetime.today().date()
            week_start = today - timedelta(days=today.weekday())

        week_end = week_start + timedelta(days=6)

        # Query transactions in the week and annotate actual amount made (subtotal - discount)
        transactions = Transaction.objects.filter(timestamp__date__range=(week_start, week_end))\
            .annotate(amount_made=F('subtotal') - F('discount'))

        # Group by day
        daily_data = {}
        for i in range(7):
            day = week_start + timedelta(days=i)
            daily_data[day.strftime('%A')] = 0  # e.g., 'Monday': 0

        for t in transactions:
            day_name = t.timestamp.strftime('%A')
            daily_data[day_name] += float(t.amount_made)

        return Response({
            "week_start": str(week_start),
            "week_end": str(week_end),
            "data": daily_data
        })
    





# SPA SECTIONS ADMIN FUNCTIONALITIES

class TotalSpaProductsSoldView(generics.GenericAPIView):
    permission_classes = []

    def get(self, request):
        filter_value = request.query_params.get('filter', 'day')
        today = timezone.now().date()

        try:
            specific_date = datetime.strptime(filter_value, "%Y-%m-%d").date()
            start_date = specific_date
            end_date = specific_date + timedelta(days=1)
        except ValueError:
            if filter_value == 'day':
                start_date = today
                end_date = today + timedelta(days=1)
            elif filter_value == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif filter_value == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
            elif filter_value == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                return Response({
                    "detail": "Invalid filter value. Use day, week, month, year, or a valid date (YYYY-MM-DD)."
                }, status=status.HTTP_400_BAD_REQUEST)

        total_sold_quantity = SPAScannedItem.objects.filter(
            product__isnull=False,
            transaction__timestamp__range=(start_date, end_date)
        ).aggregate(total_quantity=Sum('quantity'))['total_quantity'] or 0

        total_sold_price = SPAScannedItem.objects.filter(
            product__isnull=False,
            transaction__timestamp__range=(start_date, end_date)
        ).aggregate(total_price=Sum('price_at_sale'))['total_price'] or 0

        low_stock_count = SpaProduct.objects.filter(stock_quantity__lte=0).count()

        return Response({
            "total_products_sold": total_sold_quantity,
            "total_sales_amount": total_sold_price,
            "low_stock_count": low_stock_count
        }, status=status.HTTP_200_OK)
    

class SpaListAllSalesView(generics.ListAPIView):
    permission_classes = []
    serializer_class = SpaScannedItemWithTransactionSerializer

    def get_queryset(self):
        filter_value = self.request.query_params.get('date', 'day')
        today = timezone.now().date()
        queryset = SPAScannedItem.objects.select_related('transaction', 'product', 'service').order_by('-transaction__id')

        try:
            # If 'date' param is an actual date string
            selected_date = datetime.strptime(filter_value, '%Y-%m-%d').date()
            return queryset.filter(transaction__timestamp__date=selected_date)
        except ValueError:
            # If 'date' param is a keyword
            if filter_value == 'day':
                start_date = today
                end_date = today + timedelta(days=1)
            elif filter_value == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif filter_value == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
            elif filter_value == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                return SPAScannedItem.objects.none()

            return queryset.filter(transaction__timestamp__date__range=(start_date, end_date))
        
class SpaCategorySalesReportView(generics.GenericAPIView):
    permission_classes = []

    def get(self, request):
        filter_value = request.query_params.get('filter', 'day')
        today = timezone.now().date()

        try:
            specific_date = datetime.strptime(filter_value, "%Y-%m-%d").date()
            start_date = specific_date
            end_date = specific_date + timedelta(days=1)
        except ValueError:
            if filter_value == 'day':
                start_date = today
                end_date = today + timedelta(days=1)
            elif filter_value == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
            elif filter_value == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
            elif filter_value == 'year':
                start_date = today.replace(month=1, day=1)
                end_date = start_date.replace(year=start_date.year + 1)
            else:
                return Response({
                    "detail": "Invalid filter type or date format. Use YYYY-MM-DD or one of: day, week, month, year."
                }, status=status.HTTP_400_BAD_REQUEST)

        scanned_items = SPAScannedItem.objects.filter(
            product__isnull=False,
            transaction__timestamp__range=(start_date, end_date)
        ).select_related('product')

        category_data = {}

        for item in scanned_items:
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
    

class SpaProductView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # Ensure the user is authenticated and is an admin
    authentication_classes = [TokenAuthentication]


    def get(self, request, product_id=None, branch_id=None):
        if product_id:
            try:
                product = SpaProduct.objects.get(id=product_id)
                if request.user.is_authenticated:
                    try:
                        worker = Worker.objects.get(user=request.user)
                        # Check if product belongs to user's branch
                        if product.branch != worker.branch:
                            return Response({"detail": "Access denied. Product not in your branch."}, status=status.HTTP_403_FORBIDDEN)
                    except Worker.DoesNotExist:
                        product = SpaProduct.objects.get(id=product_id)
                # If not authenticated or authorized, return product details
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
        

    def post(self, request, *args, **kwargs):
        serializer = SpaProductSerializer(data=request.data)

        if serializer.is_valid():
            product = serializer.save()
            return Response(SpaProductSerializer(product).data, status=status.HTTP_201_CREATED)

        # Flatten and return the first error message in a clean format
        first_error = next(iter(serializer.errors.values()))[0]
        raise ValidationError({"detail": str(first_error)})
    
    def put(self, request, product_id):
        try:
            product = SpaProduct.objects.get(id=product_id)
            serializer = SpaProductSerializer(product, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SpaProduct.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, product_id):
        try:
            product = SpaProduct.objects.get(id=product_id)
            serializer = SpaProductSerializer(product, data=request.data, partial=True)  # Set partial=True for partial updates
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SpaProduct.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, product_id):
        try:
            product = SpaProduct.objects.get(id=product_id)

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

        except SpaProduct.DoesNotExist:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        

#  for listing all services and products sold and the worker that did it
class CompletedSPAItemsList(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        try:
            worker = Worker.objects.get(user=request.user)
        except Worker.DoesNotExist:
            return Response({'error': 'Worker profile not found'}, status=status.HTTP_403_FORBIDDEN)

        # Get all done items for this worker's branch
        items = SPAScannedItem.objects.filter(
            status="Done",
            transaction__staff__branch=worker.branch
        ).select_related('transaction', 'service', 'done_by')

        # Build response
        data = []
        for item in items:
            service_name = item.service.name if item.service else (item.product.name if item.product else "")
            done_time = item.done_at.strftime("%I:%M %p") if item.done_at else ""
            done_date = item.done_at.strftime("%b %d, %Y") if item.done_at else ""
            done_by_name = item.done_by.name if item.done_by else ""

            data.append({
                'unique_code': item.transaction.code,
                'service': service_name,
                'time': done_time,
                'date': done_date,
                'staff': done_by_name,
                'amount': f"N{item.price_at_sale}",
            })

        return Response(data, status=status.HTTP_200_OK)

