from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from .serializers import LoginSerializer, RegisterSerializer
from rest_framework.authtoken.models import Token
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.models import Group


# Create your views here.

class LoginView(APIView):
    permission_classes = []  # Ensure the user is authenticated
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        # Get or create the auth token
        token, created = Token.objects.get_or_create(user=user)

        # Prepare the response data
        response_data = {
            'id': user.id,
            'username': user.username,
            'group': user.groups.first().name if user.groups.exists() else None,
            'auth_token': token.key,
        }
        return Response(response_data, status=status.HTTP_200_OK)

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


    
    


