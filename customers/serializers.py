from django.contrib.auth import authenticate
from rest_framework import serializers
from django.contrib.auth.models import User
from .models import CustomerProfile

class CustomerRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    full_name = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate_phone_number(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with this phone number already exists.")
        return value

    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        full_name = validated_data['full_name'].strip()
        password = validated_data['password']

        # Split full name into first and last name
        names = full_name.split()
        first_name = names[0] if names else ''
        last_name = ' '.join(names[1:]) if len(names) > 1 else ''

        # 1. Create the base Django User (using phone number as username)
        user = User.objects.create_user(
            username=phone_number,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        # 2. Create the CustomerProfile (this triggers referral_id generation)
        CustomerProfile.objects.create(
            user=user,
            phone_number=phone_number
        )

        return user


class CustomerLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        phone_number = attrs.get('phone_number')
        password = attrs.get('password')

        user = authenticate(username=phone_number, password=password)
        if not user:
            if not User.objects.filter(username=phone_number).exists():
                raise serializers.ValidationError("User with this phone number does not exist.")
            raise serializers.ValidationError("Invalid password.")

        if not user.is_active:
            raise serializers.ValidationError("Your account has been disabled.")

        return user



TRANSACTION_TYPE_CHOICES = ("luxury", "spa")


class ClaimTransactionPointsSerializer(serializers.Serializer):
    referral_id = serializers.CharField()
    transaction_id = serializers.IntegerField()
    transaction_type = serializers.ChoiceField(choices=TRANSACTION_TYPE_CHOICES)


class SubmitReferralSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    referral_code = serializers.CharField(max_length=30)
    staff_id = serializers.IntegerField(required=False, allow_null=True)