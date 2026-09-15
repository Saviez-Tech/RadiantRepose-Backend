"""
Small shared helpers for the points/referral endpoints.
Drop into your app as utils.py, or merge into an existing utils module.
"""

from django.db.models import Sum

from .models import CustomerPointLog

POINTS_PER_UNIT_SPENT = 100  # 1 point per 100 currency units spent
REFERRAL_BONUS_POINTS = 5


def calculate_points(amount_spent):
    """1 point per POINTS_PER_UNIT_SPENT currency units spent, rounded down."""
    if amount_spent <= 0:
        return 0
    return int(amount_spent // POINTS_PER_UNIT_SPENT)


def get_point_balance(customer):
    total = CustomerPointLog.objects.filter(customer=customer).aggregate(total=Sum("points"))["total"]
    return total or 0