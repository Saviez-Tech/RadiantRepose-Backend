from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.exceptions import ValidationError
from .serializers import CustomerRegisterSerializer, CustomerLoginSerializer

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