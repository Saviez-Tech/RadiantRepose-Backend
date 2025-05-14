# serializers.py
from rest_framework import serializers
from .models import BuyersInfo, Order
from django.db import transaction
from luxury.serializers import ProductSerializer



class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['product', 'quantity', 'price_at_sale']

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity')

        if product is None:
            raise serializers.ValidationError({
                "message": "Product not found."
            })

        # If quantity exceeds stock
        if quantity > product.stock_quantity:
            raise serializers.ValidationError({
                "message": f"Requested quantity for '{product.name}' exceeds available stock ({product.stock_quantity})."
            })

        # If stock is zero
        if product.stock_quantity == 0:
            raise serializers.ValidationError({
                "message": f"The product '{product.name}' is out of stock."
            })

        # Assign price at sale from product
        data['price_at_sale'] = product.price

        return data
class BuyersInfoSerializer(serializers.ModelSerializer):
    order = OrderSerializer(many=True, write_only=True)

    class Meta:
        model = BuyersInfo
        fields = ['id','full_name', 'email', 'phone', 'street_address', 'zip_code', 'city', 'state', 'country', 'order']

    
    def create(self, validated_data):
        scanned_items_data = validated_data.pop('order')

        with transaction.atomic():
            buyer = BuyersInfo.objects.create(**validated_data)

            for item in scanned_items_data:
                product = item['product']
                quantity = item['quantity']

                # Create Order object
                Order.objects.create(
                    transaction=buyer,
                    product=product,
                    quantity=quantity,
                    price_at_sale=product.price
                )

        return buyer


class NewOrderSerializer(serializers.ModelSerializer):
    product= ProductSerializer()
    customer=BuyersInfoSerializer(source='transaction')
    class Meta:
        model = Order
        fields = ['id','customer','product', 'quantity', 'price_at_sale']


class ProductSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id','product', 'quantity', 'price_at_sale']
    
    product = ProductSerializer()

class CustomerOrdersSerializer(serializers.Serializer):
    customer = BuyersInfoSerializer()
    products = ProductSummarySerializer(many=True)

