import logging

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from user.serializers import UserSerializer

logger = logging.getLogger(__name__)

User = get_user_model()

class CreateUserView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = (AllowAny,)

    def perform_create(self, serializer):
        user = serializer.save()
        logger.info("NEW USER REGISTERED: %s (ID: %s)", user.email, user.id)


class VerifyEmailView(APIView):
    permission_classes = (AllowAny,)

    def get(self, request: Request, uidb64: str, token: str) -> Response:
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            user = None

        if user is not None and default_token_generator.check_token(user, token):
            if not user.is_active:
                user.is_active = True
                user.save()

                return Response({"detail": "Email verified successfully."}, status=status.HTTP_200_OK)
            return Response({"detail": "Account already active."}, status=status.HTTP_400_BAD_REQUEST)

        return Response({"detail": "Invalid or expired link."}, status=status.HTTP_400_BAD_REQUEST)

class ManageUserView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user
