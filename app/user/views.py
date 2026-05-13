import logging
from typing import Any

import httpx
import jwt
from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from google.auth.exceptions import GoogleAuthError
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.serializers import BaseSerializer
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.tokens import RefreshToken

from user.oauth.github import verify_github_token
from user.oauth.google import verify_google_token
from user.serializers import UserSerializer
from user.verification_token import verify_verification_token

logger = logging.getLogger(__name__)
User = get_user_model()


def get_or_create_oauth_user(email: str, first_name: str, last_name: str) -> tuple[Any, bool]:
    user, created = User.objects.get_or_create(
        email=email,
        defaults={"first_name": first_name, "last_name": last_name, "is_active": True},
    )

    if created:
        user.set_unusable_password()
        user.save()

    return user, created


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


class GoogleLoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"id_token": {"type": "string"}}}},
        responses={
            200: {"type": "object", "properties": {"access": {"type": "string"}, "refresh": {"type": "string"}}}
        },
    )
    def post(self, request: Request) -> Response:
        id_token_value = request.data.get("id_token")

        if not isinstance(id_token_value, str):
            return Response({"detail": "id_token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            oauth_data = verify_google_token(id_token_value)
        except (GoogleAuthError, ValueError) as e:
            logger.warning("Google OAuth failed %s", e)
            return Response({"detail": "Invalid Google token."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = get_or_create_oauth_user(oauth_data.email, oauth_data.first_name, oauth_data.last_name)

        if created:
            logger.info("New user via Google OAuth: %s", user.email)

        refresh = RefreshToken.for_user(user)

        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class GitHubLoginView(APIView):
    permission_classes = (AllowAny,)

    @extend_schema(
        request={"application/json": {"type": "object", "properties": {"code": {"type": "string"}}}},
        responses={
            200: {"type": "object", "properties": {"access": {"type": "string"}, "refresh": {"type": "string"}}}
        },
    )
    def post(self, request: Request) -> Response:
        code = request.data.get("code")

        if not isinstance(code, str):
            return Response({"detail": "code is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            oauth_data = verify_github_token(code)
        except (httpx.HTTPError, KeyError, StopIteration) as e:
            logger.warning("GitHub OAuth failed %s", e)
            return Response({"detail": "Invalid GitHub code."}, status=status.HTTP_400_BAD_REQUEST)

        user, created = get_or_create_oauth_user(oauth_data.email, oauth_data.first_name, oauth_data.last_name)

        if created:
            logger.info("New user via GitHub OAuth: %s", user.email)

        refresh = RefreshToken.for_user(user)

        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})


class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self) -> Any:
        return self.request.user
