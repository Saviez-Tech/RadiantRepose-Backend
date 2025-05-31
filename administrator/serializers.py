from rest_framework import serializers
from luxury.models import Product, LuxuryBranch, Transaction, ScannedItem,Worker,Service
from luxury.serializers import WorkerSerializer, ProductSerializer,SPATransaction,SPAScannedItem,SpaProductSerializer


class TransactionNestedSerializer(serializers.ModelSerializer):
    staff = WorkerSerializer()
    class Meta:
        model = Transaction
        fields = [
            "id", "staff", "timestamp", "subtotal", 
            "discount", "customer_name", "customer_contact"
        ]

class ScannedItemWithTransactionSerializer(serializers.ModelSerializer):
    transaction = TransactionNestedSerializer()
    product =ProductSerializer()
    class Meta:
        model = ScannedItem
        fields = ['id', 'product', 'quantity', 'price_at_sale', 'transaction']

class SpaTransactionNestedSerializer(serializers.ModelSerializer):
    staff = WorkerSerializer()
    class Meta:
        model = SPATransaction
        fields = [
            "id", "staff", "timestamp", "subtotal", 
            "discount", "customer_name", "customer_contact"]
        
class SpaServiceSerializer(serializers.ModelSerializer):

    class Meta:
        model= Service
        fields="__all__"
        
class SpaScannedItemWithTransactionSerializer(serializers.ModelSerializer):
    transaction = TransactionNestedSerializer()
    product =SpaProductSerializer()
    service= SpaServiceSerializer()
    class Meta:
        model = SPAScannedItem
        fields = ['id', 'product', 'service','quantity', 'price_at_sale', 'transaction']