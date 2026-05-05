import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from celery import shared_task
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.reverse import reverse

logger = logging.getLogger(__name__)

User = get_user_model()


@shared_task
def send_verification_email(user_id: int) -> None:
    try:
        user = User.objects.get(pk=user_id)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        relative_link = reverse("user:verify-email", kwargs={"uidb64": uid, "token": token})
        verification_link = f"http://{settings.FULL_SITE_DOMAIN}{relative_link}"

        send_mail(
            subject="Registration Confirmation",
            message=f"Hello! To activate your account, please follow this link: {verification_link}",
            from_email=None,
            recipient_list=[user.email],
        )
        logger.info("Verification email sent to %s", user.email)
    except User.DoesNotExist:
        logger.error("User with id %s does not exist", user_id)
