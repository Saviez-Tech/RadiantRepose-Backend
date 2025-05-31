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
    
    path('worker-update/<int:pk>/', WorkerUpdateAPIView.as_view(), name='worker-update'),
    path('worker-disable/<int:pk>/', WorkerDisableAPIView.as_view(), name='worker-disable'),
    path('worker-enable/<int:pk>/', WorkerEnableAPIView.as_view(), name='worker-disable'),
    path('worker-list/',WorkerListAPIView.as_view(),name="worker-list"),
    
    path('weekly-sales/', WeeklySalesGraphView.as_view(), name='weekly-sales'),



    #SPA ENDPOINTS
    path('spa/total-goods-sold/',TotalSpaProductsSoldView.as_view(),name="spa-dashboard"),
    path('spa/sales/',SpaListAllSalesView.as_view(),name='spa-sales'),
    path('spa/category-sales-report/',SpaCategorySalesReportView.as_view(),name='sales-category-report'),
    path('spa/products/', SpaProductView.as_view(), name='product-listss'),  # For listing and creating products
    path('spa/products/<int:product_id>/', SpaProductView.as_view(), name='product-detailss'),  # For retrieving, updating, and deleting a specific product

] 



