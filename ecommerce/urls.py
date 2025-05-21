from django.urls import path
from .views import *

urlpatterns = [
    path('make-order',create_order_and_initialize_payment, name='order'),
    path('buyers/pending/', BuyersWithPendingOrdersList.as_view(), name='buyers-with-pending-orders'),
    path('buyers/<int:pk>/orders/', BuyerOrdersDetail.as_view(), name='buyer-orders-detail'),
    path('buyers/<int:buyer_id>/fulfill-orders/', FulfillBuyerOrdersAPIView.as_view(), name='fulfill-orders'),


    path("paystack/init/", initialize_payment, name="initialize-payment"),
    path("paystack/verify/<str:reference>/", verify_payment, name="verify-payment"),
    path('webhook/paystack/', paystack_webhook, name='paystack-webhook'),
] 