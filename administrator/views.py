from django.shortcuts import render
from rest_framework import generics
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from luxury.models import Product, LuxuryBranch,ScannedItem,Transaction
from luxury.serializers import ProductSerializer, LuxuryBranchSerializer,ScannedItemSerializer,SaleSerializer
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdminUser  # Import the custom permission
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum
# Create your views here.

class ProductView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]  # Ensure the user is authenticated and is an admin

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

    def post(self, request):
        serializer = ProductSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
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

        return Response({
            "total_goods_sold": total_sold_quantity,
            "total_price": total_sold_price
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
        filter_type = self.request.query_params.get('filter', None)
        category_name = self.request.query_params.get('category', None)
        name = self.request.query_params.get('name', None)

        # Filter by date range
        if filter_type:
            today = timezone.now().date()
            if filter_type == 'day':
                queryset = queryset.filter(timestamp__date=today)
            elif filter_type == 'week':
                start_date = today - timedelta(days=today.weekday())
                end_date = start_date + timedelta(days=7)
                queryset = queryset.filter(timestamp__range=(start_date, end_date))
            elif filter_type == 'month':
                start_date = today.replace(day=1)
                end_date = (start_date + timedelta(days=31)).replace(day=1)
                queryset = queryset.filter(timestamp__range=(start_date, end_date))

        # Filter by category
        if category_name:
            queryset = queryset.filter(scanned_items__product__category__name__icontains=category_name)

        # Filter by name
        if name:
            queryset = queryset.filter(customer_name__icontains=name)

        return queryset
    
class FilterProductsByQuantityView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ProductSerializer

    def get_queryset(self):
        # Filter for quantities of 2, 1, or 0
        return Product.objects.filter(stock_quantity__in=[0, 1, 2])