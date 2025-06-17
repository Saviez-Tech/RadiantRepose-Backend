from django.db import models
from luxury.models import Product

# Create your models here.

class BuyersInfo(models.Model):
    full_name=models.CharField(max_length=50)
    email=models.EmailField()
    phone=models.CharField(max_length=16)
    street_address= models.CharField(max_length=50)
    zip_code=models.CharField(max_length=50)
    city=models.CharField(max_length=50)
    state= models.CharField(max_length=50)
    country= models.CharField(max_length=50)
    reference = models.CharField(max_length=100, blank=True, null=True, unique=True)
    


class Order(models.Model):
    transaction = models.ForeignKey(BuyersInfo, on_delete=models.CASCADE)  # Link to the transaction
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Link to the product
    quantity = models.PositiveIntegerField()  # Quantity of the item
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    status = models.CharField(max_length=10,default='pending')
    payment=models.BooleanField(default=False)
    



class ContactMessage(models.Model):
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=30, blank=True, null=True)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.full_name} - {self.subject}"
    
class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email