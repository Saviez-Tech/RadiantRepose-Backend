from rest_framework import serializers
from .models import Product, LuxuryBranch, Transaction, ScannedItem,Worker


class WorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ['id', 'name', 'phone_number', 'address']  # Include relevant fields


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'  # Include all fields from the Product model

    def validate_branch(self, value):
        # Ensure the branch exists
        if not LuxuryBranch.objects.filter(id=value.id).exists():
            raise serializers.ValidationError("The specified branch does not exist.")
        return value

class LuxuryBranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LuxuryBranch
        fields = '__all__'  # Include all fields from the LuxuryBranch model


    
class SaleSerializerr(serializers.ModelSerializer): 
    
    class Meta:
        model = Transaction
        fields = ['staff', 'subtotal', 'discount',  'customer_name', 'customer_contact']  # Removed scanned_items

    def validate(self, data):
        # You can add custom validation logic here if needed
        return data 

class ScannedItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer() 
    
    class Meta:
        model = ScannedItem
        fields = ['product', 'quantity']  # Include product and quantity, you can add more fields if needed
        
        
class SaleSerializer(serializers.ModelSerializer):
    staff = WorkerSerializer()  
    scanned_items = ScannedItemSerializer(many=True)
    class Meta:
        model = Transaction
        fields = ['staff', 'subtotal', 'discount',  'customer_name', 'customer_contact','scanned_items']  # Removed scanned_items

    def validate(self, data):
        # You can add custom validation logic here if needed
        return data 