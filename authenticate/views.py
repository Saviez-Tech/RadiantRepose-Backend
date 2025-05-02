from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import LoginSerializer, RegisterSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Group
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny

# Create your views here.

class LoginView(APIView):
    authentication_classes = []  # prevent auth check
    permission_classes = [AllowAny]  # allow anyone

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data

            token, _ = Token.objects.get_or_create(user=user)
            response_data = {
                'id': user.id,
                'username': user.username,
                'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip(),
                'group': user.groups.first().name if user.groups.exists() else None,
                'auth_token': token.key,
            }
            return Response(response_data, status=status.HTTP_200_OK)

        except ValidationError as e:
            # Flatten the error message
            error_message = str(e)  # This will return the plain message, not the ErrorDetail object

            # Check if the message is the default "Invalid credentials" or more specific errors
            if 'Invalid password' in error_message:
                return Response({'message': 'Invalid password.'}, status=status.HTTP_401_UNAUTHORIZED)
            elif 'does not exist' in error_message:
                return Response({'message': 'User with this username does not exist.'}, status=status.HTTP_404_NOT_FOUND)
            elif 'disabled' in error_message:
                return Response({'message': 'Your account has been disabled.'}, status=status.HTTP_403_FORBIDDEN)
            else:
                return Response({'message': error_message}, status=status.HTTP_400_BAD_REQUEST)

        except Exception:
            return Response({'message': 'An unexpected error occurred.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

class RegisterView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure the user is authenticated

    def post(self, request):
        # Check if the user is in the "Administrators" group
        # if not request.user.groups.filter(name='administrator').exists():
        #     return Response({"detail": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response({"id": user.id, "username": user.username}, status=status.HTTP_201_CREATED)


    
    


