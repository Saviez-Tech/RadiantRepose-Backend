from rest_framework import serializers
from luxury.models import Product, LuxuryBranch, Transaction, ScannedItem,Worker
from luxury.serializers import WorkerSerializer, ProductSerializer,SPATransaction,SPAScannedItem


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
        
class SpaScannedItemWithTransactionSerializer(serializers.ModelSerializer):
    transaction = TransactionNestedSerializer()
    product =ProductSerializer()
    class Meta:
        model = SPAScannedItem
        fields = ['id', 'product', 'quantity', 'price_at_sale', 'transaction']