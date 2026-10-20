from django.urls import path
from .views import *

urlpatterns = [
    path('make-order',create_order_and_initialize_payment, name='order'),
    path('products/preorder/', PreorderProductsList.as_view(), name='preorder-products'),
    path('products/preorder/search/', PreorderProductSearchList.as_view(), name='preorder-product-search'),
    path('preorders/', create_preorder_and_initialize_payment, name='create-preorder'),
    path('preorders/verify/<str:reference>/', verify_preorder_payment, name='verify-preorder-payment'),
    path('buyers/pending/', BuyersWithPendingOrdersList.as_view(), name='buyers-with-pending-orders'),
    path('buyers/<int:pk>/orders/', BuyerOrdersDetail.as_view(), name='buyer-orders-detail'),
    path('buyers/<int:buyer_id>/fulfill-orders/', FulfillBuyerOrdersAPIView.as_view(), name='fulfill-orders'),


    path("paystack/init/", initialize_payment, name="initialize-payment"),
    path("paystack/verify/<str:reference>/", verify_payment, name="verify-payment"),
    path('webhook/paystack/', paystack_webhook, name='paystack-webhook'),
    path('contact/', contact_message_create, name='contact-message-create'),
    path('newsletter/subscribe/', subscribe_newsletter, name='subscribe-newsletter'),
] 