from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth.models import User
from luxury.models import Worker

class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        user = authenticate(username=username, password=password)

        if user is None:
            # Check if username exists but account is disabled
            try:
                user_obj = User.objects.get(username=username)
                if not user_obj.is_active:
                    raise serializers.ValidationError("Your account has been disabled.")
            except User.DoesNotExist:
                pass

            raise serializers.ValidationError("Invalid credentials")
        
        return user

class RegisterSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    branch_id = serializers.IntegerField(required=True)  # Assuming branch is identified by ID
    userfullname = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'userfullname', 'phone_number', 'address', 'branch_id']  # Include 'name' instead of first and last name

    def create(self, validated_data):
        # Extract worker details
        phone_number = validated_data.pop('phone_number')
        address = validated_data.pop('address')
        branch_id = validated_data.pop('branch_id')
        userfullname = validated_data.pop('userfullname')  # Get the full name

        # Create the user
        user = User(**validated_data)
        user.set_password(validated_data['password'])  # Hash the password
        user.save()

        # Create the worker associated with the user
        Worker.objects.create(
            user=user,
            phone_number=phone_number,
            address=address,
            branch_id=branch_id,
            name=userfullname  # Store the full name in the Worker model
        )

        return user 