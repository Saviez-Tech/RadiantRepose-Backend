from django.urls import path
from .views import *

urlpatterns = [
    # WORKER LUXURY ENDPOINTS
    path('sales/', SalesView.as_view(), name='sales'),  # Endpoint for selling and viewing sales
    path('sales/<int:transaction_id>/', TransactionDetailView.as_view(), name='transaction-detail'),  # Endpoint for transaction details
    path('products/search/', ProductSearchView.as_view(), name='product-search'),  # New endpoint for product search


    #SPA ENDPOINTS
    path("create-booking/",CreateBookingView.as_view(),name="create-booking"),
    path('bookings/<int:id>/', BookingDetailView.as_view()),
    path('services/',ServiceListView.as_view(),name="services"),


    #SPA POS ENDPOINTS
    path('search-booked-services/', BookedServiceSearchView.as_view(), name='search-booked-services'),

    path('spa/sales/', SPASalesView.as_view(), name='spa-sales'),
    path('spa/products/', SpaProductDetailListView.as_view(), name='spa-product-list'),
    path('spa/product/search/',SpaProductSearchView.as_view(),name="search-spa-product"),
    path('spa/services/<str:code>/', ServiceListByTransactionCode.as_view(), name='spa-services-by-code'),
    path('spa/products/<str:code>/', ProductListByTransactionCode.as_view(), name='spa-products-by-code'),
    path('spa/mark_done/<int:item_id>/', MarkSPAItemDone.as_view(), name='mark_spa_item_done'),

] 