from rest_framework import serializers
from .models import Product, LuxuryBranch, Transaction, ScannedItem,Worker,Booking, BookedService, Service


class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = LuxuryBranch
        fields = "__all__"

class WorkerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Worker
        fields = ['id', 'name', 'phone_number', 'address']  # Include relevant fields
        
class WorkerSerializerr(serializers.ModelSerializer):
    branch = BranchSerializer()
    class Meta:
        model = Worker
        fields = "__all__" # Include relevant fields


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields ="__all__"
    
    def update(self, instance, validated_data):
        image = validated_data.get("image", None)

        # Update the instance with the rest of the fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        # If image is updated, upload it to Supabase
        if image:
            try:
                instance.upload_image_to_supabase()
            except Exception as e:
                raise serializers.ValidationError({"image": "Failed to upload image to Supabase."})

        return instance


    def create(self, validated_data):
        image_file = validated_data.pop('image', None)
        product = Product.objects.create(**validated_data)

        if image_file:
            product.image = image_file
            product.save()
            product.upload_image_to_supabase()  # Upload to Supabase, then save image_url

        return product
      
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
        fields = ['staff', 'subtotal', 'discount',  'customer_name','timestamp', 'customer_contact','scanned_items']  # Removed scanned_items

    def validate(self, data):
        # You can add custom validation logic here if needed
        return data 
    
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'staff', 'timestamp', 'subtotal', 'discount', 'customer_name', 'customer_contact']


class ScannedItemWithTransactionSerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer()
    product = ProductSerializer() 
    class Meta:
        model = ScannedItem
        fields = ['id', 'product', 'quantity', 'price_at_sale', 'transaction']



##### SPA SECTION SERIALIZERS #####

class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name', 'description', 'price', 'image']

class BookedServiceSerializer(serializers.ModelSerializer):
    service_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = BookedService
        fields = ['service_id', 'time']

class BookingSerializer(serializers.ModelSerializer):
    use_same_time_for_all = serializers.BooleanField(write_only=True)
    time = serializers.DateTimeField(required=False, write_only=True)
    services = serializers.ListField(child=serializers.JSONField(), write_only=True)

    class Meta:
        model = Booking
        fields = ['id','customer_name', 'customer_phone', 'use_same_time_for_all', 'time', 'services']

    def create(self, validated_data):
        services_data = validated_data.pop('services')
        use_same_time = validated_data.pop('use_same_time_for_all')
        shared_time = validated_data.pop('time', None)

        # Collect service IDs to validate
        if use_same_time:
            service_ids = services_data
        else:
            service_ids = [item['service_id'] for item in services_data]

        # Validate all service IDs exist
        existing_ids = set(Service.objects.filter(id__in=service_ids).values_list('id', flat=True))
        invalid_ids = [sid for sid in service_ids if sid not in existing_ids]
        if invalid_ids:
            raise serializers.ValidationError({"services": f"Invalid service IDs: {invalid_ids}"})

        # All services are valid, proceed
        booking = Booking.objects.create(**validated_data)

        if use_same_time:
            for service_id in services_data:
                service = Service.objects.get(id=service_id)
                BookedService.objects.create(
                    booking=booking,
                    service=service,
                    time=shared_time
                )
        else:
            for item in services_data:
                service = Service.objects.get(id=item['service_id'])
                BookedService.objects.create(
                    booking=booking,
                    service=service,
                    time=item['time']
                )

        return booking




class ListBookedServiceSerializer(serializers.ModelSerializer):
    service = ServiceSerializer(read_only=True)

    class Meta:
        model = BookedService
        fields = ['id', 'service', 'time']

class ListBookingSerializer(serializers.ModelSerializer):
    booked_services = ListBookedServiceSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = ['id', 'customer_name', 'customer_phone', 'created_at', 'booked_services']
