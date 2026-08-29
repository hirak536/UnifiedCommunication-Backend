"""
apps/users/views.py
───────────────────
Authentication and user profile views.
"""

from django.contrib.auth.models import update_last_login
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.users.serializers import LoginSerializer, UserDetailSerializer


class LoginView(APIView):
    """
    POST /api/v1/auth/login/
    Authenticates user and returns access/refresh JWT tokens + profile payload.
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        update_last_login(None, user)

        # Generate SimpleJWT tokens
        refresh = RefreshToken.for_user(user)
        # Custom claims in access token
        refresh["role"] = user.role
        refresh["tenant_id"] = str(user.tenant_id) if user.tenant_id else None

        user_data = UserDetailSerializer(user).data

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data,
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    """
    GET /api/v1/auth/me/
    Returns currently authenticated user profile and telephony configuration.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserDetailSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
