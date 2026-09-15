from django.db import models
from django.contrib.auth.models import User
import secrets
import string

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