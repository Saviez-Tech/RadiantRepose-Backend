from django.db import models
from django.contrib.auth.models import User
import secrets
import string
from luxury.models import Worker

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='customer_profile')
    phone_number = models.CharField(max_length=15, unique=True)
    referral_id = models.CharField(max_length=30, unique=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.referral_id:
            self.referral_id = self.generate_unique_referral_id()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_unique_referral_id():
        while True:
            # Generates a unique string like RADIANT-9X42L1
            suffix = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))
            referral_id = f"RADIANT-{suffix}"
            if not CustomerProfile.objects.filter(referral_id=referral_id).exists():
                return referral_id

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.referral_id})"


class CustomerPointLog(models.Model):
    customer = models.ForeignKey(CustomerProfile, on_delete=models.CASCADE, related_name='point_logs')
    title = models.CharField(max_length=255)  # e.g., "Purchase: Luxury Silk Robe" or "Welcome Bonus"
    points = models.IntegerField()           # Positive for incoming (+150), Negative for spent (-500)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        sign = "+" if self.points >= 0 else ""
        return f"{self.customer.phone_number}: {self.title} ({sign}{self.points} pts)"


class POSReferralRecord(models.Model):
    phone_number = models.CharField(max_length=15, unique=True)  # Unregistered customer phone
    referral_code = models.CharField(max_length=30)             # Code they brought
    referred_by_profile = models.ForeignKey(
        'CustomerProfile', 
        on_delete=models.CASCADE, 
        related_name='pos_referral_records'
    )                                                           # The registered user who gets the 5 pts
    staff = models.ForeignKey(Worker, on_delete=models.SET_NULL, null=True, blank=True)
    note = models.CharField(max_length=255, default="Referral")
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"POS Referral: {self.phone_number} -> {self.referred_by_profile.referral_id}"


class ClaimedTransaction(models.Model):
    customer = models.ForeignKey(
        'CustomerProfile', 
        on_delete=models.CASCADE, 
        related_name='claimed_transactions'
    )
    transaction_id = models.IntegerField()
    transaction_type = models.CharField(max_length=20)  # "luxury" or "spa"
    claimed_at = models.DateTimeField(auto_now_add=True)
    points_awarded = models.IntegerField(default=0)  # Points awarded for this claim

    class Meta:
        unique_together = ('transaction_id', 'transaction_type')  # Prevents double-claiming

    def __str__(self):
        return f"{self.transaction_type.upper()} Transaction #{self.transaction_id} claimed by {self.customer.phone_number}"