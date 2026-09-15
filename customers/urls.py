from django.urls import path
from .views import CustomerRegisterView, CustomerLoginView,ClaimTransactionPointsView, SubmitReferralView

urlpatterns = [
    path('register/', CustomerRegisterView.as_view(), name='customer-register'),
    path('login/', CustomerLoginView.as_view(), name='customer-login'),
    
    path("points/claim/", ClaimTransactionPointsView.as_view(), name="claim-transaction-points"),
    path("referrals/submit/", SubmitReferralView.as_view(), name="submit-referral"),

]