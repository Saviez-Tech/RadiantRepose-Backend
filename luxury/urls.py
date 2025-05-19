from django.urls import path
from .views import *

urlpatterns = [
    path('sales/', SalesView.as_view(), name='sales'),  # Endpoint for selling and viewing sales
    path('sales/<int:transaction_id>/', TransactionDetailView.as_view(), name='transaction-detail'),  # Endpoint for transaction details
    path('products/search/', ProductSearchView.as_view(), name='product-search'),  # New endpoint for product search


    #SPA ENDPOINTS
    path("create-booking/",CreateBookingView.as_view(),name="create-booking"),
    path('services/',ServiceListView.as_view(),name="services")
] 