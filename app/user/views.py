import logging
from typing import Any

import jwt
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.serializers import UserSerializer
from user.verification_token import verify_verification_token

logger = logging.getLogger(__name__)
User = get_user_model()


class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer: BaseSerializer) -> None:
        user = serializer.save()
        logger.info("New user registered: %s (ID: %s)", user.email, user.id)


class VerifyEmailView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        responses={200: {"type": "object", "properties": {"detail": {"type": "string"}}}},
        description="Verify user email via JWT token.",
    )
    def get(self, request: Request, token: str) -> Response:
        try:
            user_id = verify_verification_token(token)
            user = User.objects.get(pk=user_id)

        except jwt.ExpiredSignatureError:
            return Response({"detail": "Verification link has expired."}, status=status.HTTP_400_BAD_REQUEST)
        except (jwt.InvalidTokenError, User.DoesNotExist):
            return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({"detail": "Account already active."}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()

        return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> Any:
        return self.request.user
