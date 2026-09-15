from django.urls import path
from .views import *

urlpatterns = [
    path('register/', CustomerRegisterView.as_view(), name='customer-register'),
    path('login/', CustomerLoginView.as_view(), name='customer-login'),
    
    path("points/claim/", ClaimTransactionPointsView.as_view(), name="claim-transaction-points"),
    path("referrals/submit/", SubmitReferralView.as_view(), name="submit-referral"),

    path("me/referrals-and-points/", MyReferralsAndPointsHistoryView.as_view(), name="my-referrals-and-points"),
    path("points/reduce/", ReducePointsView.as_view(), name="reduce-points"),

]