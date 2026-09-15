from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from .serializers import CustomerRegisterSerializer, CustomerLoginSerializer
from django.db import transaction as db_transaction, IntegrityError
from django.shortcuts import get_object_or_404


from .models import (
    CustomerProfile,
    CustomerPointLog,
    POSReferralRecord,
    ClaimedTransaction
)
from .serializers import ClaimTransactionPointsSerializer, SubmitReferralSerializer
from .utils import calculate_points, get_point_balance, REFERRAL_BONUS_POINTS
from luxury.models import Worker,Transaction,SPATransaction


TRANSACTION_MODEL_MAP = {
    "luxury": Transaction,
    "spa": SPATransaction,
}



class CustomerRegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerRegisterSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            
            profile = getattr(user, 'customer_profile', None)
            referral_id = profile.referral_id if profile else None

            return Response({
                "message": "Customer registration successful.",
                "id": user.id,
                "phone_number": user.username,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "referral_id": referral_id,
                "auth_token": token.key
            }, status=status.HTTP_201_CREATED)

        except ValidationError as e:
            # Flatten the DRF validation error structure into a clean 'message' key
            detail = e.detail
            if isinstance(detail, dict):
                first_key = list(detail.keys())[0]
                first_error = detail[first_key]
                error_message = str(first_error[0]) if isinstance(first_error, list) and first_error else str(first_error)
            else:
                error_message = str(detail)

            return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)


class CustomerLoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data
            token, _ = Token.objects.get_or_create(user=user)
            
            profile = getattr(user, 'customer_profile', None)
            referral_id = profile.referral_id if profile else None

            return Response({
                "message": "Customer login successful.",
                "id": user.id,
                "phone_number": user.username,
                "full_name": f"{user.first_name} {user.last_name}".strip(),
                "referral_id": referral_id,
                "auth_token": token.key
            }, status=status.HTTP_200_OK)

        except ValidationError as e:
            error_message = str(e)
            if 'Invalid password' in error_message:
                return Response({'message': 'Invalid password.'}, status=status.HTTP_401_UNAUTHORIZED)
            elif 'does not exist' in error_message:
                return Response({'message': 'User with this phone number does not exist.'}, status=status.HTTP_404_NOT_FOUND)
            elif 'disabled' in error_message:
                return Response({'message': 'Your account has been disabled.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                # Fallback flat error message
                detail = e.detail
                if isinstance(detail, dict):
                    first_key = list(detail.keys())[0]
                    first_error = detail[first_key]
                    error_message = str(first_error[0]) if isinstance(first_error, list) and first_error else str(first_error)
                return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)

class ClaimTransactionPointsView(APIView):
    """
    A registered customer claims loyalty points for a purchase they made,
    identifying themselves by their referral_id and pointing at the
    transaction they paid for.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ClaimTransactionPointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        referral_id = data["referral_id"]
        transaction_id = data["transaction_id"]
        transaction_type = data["transaction_type"]

        customer = get_object_or_404(CustomerProfile, referral_id=referral_id)

        # Already claimed? (unique_together also enforces this at the DB level)
        if ClaimedTransaction.objects.filter(
            transaction_id=transaction_id, transaction_type=transaction_type
        ).exists():
            return Response(
                {"detail": "This transaction has already been claimed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        model = TRANSACTION_MODEL_MAP[transaction_type]
        txn = get_object_or_404(model, id=transaction_id)

        amount_spent = txn.subtotal - txn.discount
        points = calculate_points(amount_spent)

        if points <= 0:
            return Response(
                {"detail": "This transaction doesn't qualify for any points."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with db_transaction.atomic():
                ClaimedTransaction.objects.create(
                    customer=customer,
                    transaction_id=transaction_id,
                    transaction_type=transaction_type,
                    points_awarded=points,
                )
                CustomerPointLog.objects.create(
                    customer=customer,
                    title=f"Purchase: {transaction_type.title()} Transaction #{transaction_id}",
                    points=points,
                )
        except IntegrityError:
            # Race condition guard: two requests hit the unique_together at once.
            return Response(
                {"detail": "This transaction has already been claimed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "Points claimed successfully.",
                "points_awarded": points,
                "new_balance": get_point_balance(customer),
            },
            status=status.HTTP_201_CREATED,
        )


class SubmitReferralView(APIView):
    """
    Registers a walk-in / unregistered phone number as having been referred
    by an existing customer's referral code, and pays the referrer their
    bonus points. Rejects the referral if the phone number is already a
    registered customer, or has already been logged as a referral before.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SubmitReferralSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        phone_number = data["phone_number"].strip()
        referral_code = data["referral_code"].strip()
        staff_id = data.get("staff_id")

        referred_by_profile = get_object_or_404(CustomerProfile, referral_id=referral_code)

        if phone_number == referred_by_profile.phone_number:
            return Response(
                {"detail": "You can't refer yourself."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Not already a registered customer.
        if CustomerProfile.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"detail": "This phone number is already registered as a customer."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Not already referred before (by anyone).
        if POSReferralRecord.objects.filter(phone_number=phone_number).exists():
            return Response(
                {"detail": "This phone number has already been referred."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        staff = None
        if staff_id:
            staff = get_object_or_404(Worker, id=staff_id)

        try:
            with db_transaction.atomic():
                record = POSReferralRecord.objects.create(
                    phone_number=phone_number,
                    referral_code=referral_code,
                    referred_by_profile=referred_by_profile,
                    staff=staff,
                )
                CustomerPointLog.objects.create(
                    customer=referred_by_profile,
                    title=f"Referral Bonus: {phone_number}",
                    points=REFERRAL_BONUS_POINTS,
                )
        except IntegrityError:
            return Response(
                {"detail": "This phone number has already been referred."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "detail": "Referral recorded successfully.",
                "points_awarded_to_referrer": REFERRAL_BONUS_POINTS,
                "referrer_new_balance": get_point_balance(referred_by_profile),
                "referral_record_id": record.id,
            },
            status=status.HTTP_201_CREATED,
        )