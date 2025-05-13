from django.urls import path
from .views import create_order,BuyersWithPendingOrdersList,BuyerOrdersDetail,FulfillBuyerOrdersAPIView

urlpatterns = [
    path('make-order',create_order, name='order'),
    path('buyers/pending/', BuyersWithPendingOrdersList.as_view(), name='buyers-with-pending-orders'),
    path('buyers/<int:pk>/orders/', BuyerOrdersDetail.as_view(), name='buyer-orders-detail'),
    path('buyers/<int:buyer_id>/fulfill-orders/', FulfillBuyerOrdersAPIView.as_view(), name='fulfill-orders'),
] 