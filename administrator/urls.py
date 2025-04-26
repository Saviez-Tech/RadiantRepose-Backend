from django.urls import path
from .views import *

urlpatterns = [
    path('products/', ProductView.as_view(), name='product-list'),  # For listing and creating products
    path('products/<int:product_id>/', ProductView.as_view(), name='product-detail'),  # For retrieving, updating, and deleting a specific product
    path('products/branch/<int:branch_id>/', ProductView.as_view(), name='product-list-by-branch'),  # For listing products by branch
    
    
    path('luxury-branches/', LuxuryBranchView.as_view(), name='luxury-branch-list'),  # For listing luxury branches
    path('luxury-branches/<int:branch_id>/', LuxuryBranchView.as_view(), name='luxury-branch-detail'),  # For retrieving, updating, and deleting a specific luxury branch
    
    
    path('total-goods-sold/', TotalGoodsSoldView.as_view(), name='total-goods-sold'),
    path('scanned-items/category/', FilterScannedItemsByCategoryView.as_view(), name='filter-scanned-items'),
    path('sales/', ListAllSalesView.as_view(), name='list-all-sales'),
    path('products/low-quantity/', FilterProductsByQuantityView.as_view(), name='filter-products-by-quantity'),  # New endpoint
    path('category-sales-report/', CategorySalesReportView.as_view(), name='category-sales-report'),
] 



