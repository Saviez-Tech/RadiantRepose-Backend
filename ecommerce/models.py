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
    


class Order(models.Model):
    transaction = models.ForeignKey(BuyersInfo, on_delete=models.CASCADE)  # Link to the transaction
    product = models.ForeignKey(Product, on_delete=models.CASCADE)  # Link to the product
    quantity = models.PositiveIntegerField()  # Quantity of the item
    price_at_sale = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    status = models.CharField(max_length=10,default='pending')



