import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.reverse import reverse

from user.verification_token import generate_verification_token

logger = logging.getLogger(__name__)
User = get_user_model()


def build_verification_url(user: Any) -> str:
    scheme = "https" if not settings.DEBUG else "http"
    token = generate_verification_token(user.id)
    relative_url = reverse("user:verify-email", kwargs={"token": token})
    base_url = getattr(settings, "BASE_URL", "localhost:8000").rstrip("/")

    return f"{scheme}://{base_url}{relative_url}"


@shared_task(bind=True, default_retry_delay=300, max_retries=3)
def send_verification_email(self: Any, user_id: int) -> None:
    try:
        user = User.objects.get(pk=user_id)

        full_name = f"{user.first_name} {user.last_name}" if user.first_name and user.last_name else user.email

        verification_url = build_verification_url(user)

        context = {
            "user": user,
            "full_name": full_name,
            "verification_url": verification_url,
        }

        subject = "Confirmation of registration at Airport Service"
        html_message = render_to_string("emails/verify_account.html", context)
        text_message = f"Hello! To activate your account, please follow this link: {verification_url}"

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=None,
            to=[user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

        logger.info("Verification email sent to %s", user.email)

    except User.DoesNotExist:
        logger.exception("User with id %s does not exist", user_id)
    except Exception as exc:
        logger.exception("Error sending email for user_id %s. Retrying...", user_id)
        raise self.retry(exc=exc) from exc
