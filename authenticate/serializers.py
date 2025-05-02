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

        if not username or not password:
            raise serializers.ValidationError("Both username and password are required.")

        user = authenticate(username=username, password=password)
        if user:
            if not user.is_active:
                raise serializers.ValidationError("Your account has been disabled.")
            return user

        # Custom error depending on what exists
        try:
            user_obj = User.objects.get(username=username)
            if not user_obj.check_password(password):
                raise serializers.ValidationError("Invalid password.")
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this username does not exist.")

        raise serializers.ValidationError("Invalid credentials.")
    
    
class RegisterSerializer(serializers.ModelSerializer):
    phone_number = serializers.CharField(required=True)
    address = serializers.CharField(required=True)
    branch_id = serializers.IntegerField(required=True)  # Assuming branch is identified by ID
    userfullname = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'userfullname', 'phone_number', 'address', 'branch_id']  # Include 'name' instead of first and last name

    def create(self, validated_data):    
        fullname = validated_data.get('userfullname', '').strip()
        names = fullname.split()
        
        # Extract worker details
        phone_number = validated_data.pop('phone_number')
        address = validated_data.pop('address')
        branch_id = validated_data.pop('branch_id')
        userfullname = validated_data.pop('userfullname')  # Get the full name
        
        
        

        # Basic logic: first word is first name, rest is last name
        first_name = names[0] if names else ''
        last_name = ' '.join(names[1:]) if len(names) > 1 else ''

        user = User(**validated_data)
        user.set_password(validated_data['password'])
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        # Assign to "worker" group
        from django.contrib.auth.models import Group
        worker_group, _ = Group.objects.get_or_create(name='worker')
        user.groups.add(worker_group)
        
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