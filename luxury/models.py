from django.db import models
from django.contrib.auth.models import User
import supabase
from decouple import config
from supabase import create_client
from django.conf import settings
import os
import random
from django.utils import timezone



supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
# Create your models here.
class LuxuryBranch(models.Model):
    name = models.CharField(max_length=100)  # Name of the branch
    location = models.CharField(max_length=255)  # Location of the branch
    contact_number = models.CharField(max_length=15)  # Contact number for the branch

    def __str__(self):
        return self.name
    
    
class Worker(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # Associate worker with user
    name = models.CharField(max_length=100)  # Worker’s name
    phone_number = models.CharField(max_length=15)  # Worker’s phone number
    address = models.CharField(max_length=255)  # Worker’s address
    branch = models.ForeignKey(LuxuryBranch, on_delete=models.CASCADE)  # Branch assigned to the worker

    def __str__(self):
        return self.name
    
    
class Product(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='temp/', blank=True, null=True)  # Temporary storage
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    barcode = models.CharField(max_length=100, unique=True)
    branch = models.ForeignKey(LuxuryBranch, on_delete=models.CASCADE)

    def upload_image_to_supabase(self):
        try:
            if self.image:

                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

                file_path = self.image.path
                file_name = f"products/{self.id}/{os.path.basename(file_path)}"

                with open(file_path, "rb") as f:
                    res = supabase.storage.from_("media").upload(file_name, f)

                
                self.image_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/media/{file_name}"
                self.save()
        except:
            pass

            
    def __str__(self):
        return self.name
    
    
class Transaction(models.Model):
    staff = models.ForeignKey(Worker, on_delete=models.CASCADE)  # Link to the staff (worker) who completed the transaction
    timestamp = models.DateTimeField(auto_now_add=True)  # Timestamp of the transaction
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)  # Subtotal before discount
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # Discount amount
    customer_name = models.CharField(max_length=255, blank=True, null=True)  # Optional customer name
    customer_contact = models.CharField(max_length=15, blank=True, null=True)  # Optional customer contact

    def __str__(self):
        return f"Transaction  by {self.staff.user.username} on {self.timestamp}"

class ScannedItem(models.Model):
    transaction = models.ForeignKey(Transaction, related_name='scanned_items', on_delete=models.CASCADE)  # Link to the transaction
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Link to the product
    quantity = models.PositiveIntegerField()  # Quantity of the item
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2,default=0)

   

    def __str__(self):
        return f"{self.product.name}"



# Spa modesl

# this section is for all the spa models

class SpaProduct(models.Model):
    name = models.CharField(max_length=255)
    image = models.ImageField(upload_to='temp/', blank=True, null=True)  # Temporary storage
    image_url = models.URLField(blank=True, null=True)
    category = models.CharField(max_length=20, blank=True, null=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    barcode = models.CharField(max_length=100, unique=True)
    branch = models.ForeignKey(LuxuryBranch, on_delete=models.CASCADE)

    def upload_image_to_supabase(self):
        try:
            if self.image:

                supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)

                file_path = self.image.path
                file_name = f"products/{self.id}/{os.path.basename(file_path)}"

                with open(file_path, "rb") as f:
                    res = supabase.storage.from_("media").upload(file_name, f)

                
                self.image_url = f"{settings.SUPABASE_URL}/storage/v1/object/public/media/{file_name}"
                self.save()
        except:
            pass

            
    def __str__(self):
        return self.name

class Service(models.Model):
    branch=models.ForeignKey(LuxuryBranch,null=True, blank=True,on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    time_in_minutes = models.PositiveIntegerField()  # Duration of the service
    image = models.URLField(null=True,blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name
    

class Booking(models.Model):
    customer_name = models.CharField(max_length=100)
    customer_phone = models.CharField(max_length=17)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Booking by {self.customer_name}"

class BookedService(models.Model):
    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='booked_services')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    time = models.DateTimeField()
    code = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return f"{self.service.name} for {self.booking.customer_name} @ {self.time}"

    def save(self, *args, **kwargs):
        if not self.code and self.time:
            # Find existing booked service with same booking and same time (exclude self)
            existing = BookedService.objects.filter(
                booking=self.booking,
                time=self.time
            ).exclude(pk=self.pk).first()
            
            if existing and existing.code:
                self.code = existing.code
            else:
                self.code = self.generate_unique_code()
        super().save(*args, **kwargs)


    def generate_unique_code(self):
        prefix = "SPA-BK"
        date_str = self.time.strftime("%Y%m%d")  # Use the time field on this model

        while True:
            rand_digits = random.randint(1000, 9999)
            code = f"{prefix}-{date_str}-{rand_digits}"
            if not BookedService.objects.filter(code=code).exists():
                return code
            

class SPATransaction(models.Model):
    staff = models.ForeignKey(Worker, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    customer_name = models.CharField(max_length=255, blank=True, null=True)
    customer_contact = models.CharField(max_length=15, blank=True, null=True)
    code = models.CharField(max_length=30, unique=True, blank=True, null=True)

    def __str__(self):
        return f"SPA Transaction by {self.staff.user.username} on {self.timestamp}"

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = self.generate_unique_code()
        super().save(*args, **kwargs)

    def generate_unique_code(self):
        prefix = "SPA-POS"
        date_str = timezone.now().strftime("%Y%m%d")
        while True:
            rand_digits = random.randint(1000, 9999)
            code = f"{prefix}-{date_str}-{rand_digits}"
            if not SPATransaction.objects.filter(code=code).exists():
                return code


class SPAScannedItem(models.Model):
    transaction = models.ForeignKey(SPATransaction, related_name='scanned_items', on_delete=models.CASCADE)
    product = models.ForeignKey(SpaProduct, on_delete=models.CASCADE, null=True, blank=True)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField()
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        item = self.product.name if self.product else self.service.name
        return f"SPA Item: {item}"
