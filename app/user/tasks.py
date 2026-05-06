import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework.reverse import reverse

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, default_retry_delay=300, max_retries=3)
def send_verification_email(self, user_id: int) -> None:
    try:
        user = User.objects.get(pk=user_id)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)

        relative_link = reverse("user:verify-email", kwargs={"uidb64": uid, "token": token})
        verification_link = f"http://{settings.FULL_SITE_DOMAIN}{relative_link}"

        subject = "Confirmation of registration at Airport Service"

        context = {
            "user": user,
            "verification_link": verification_link,
        }
        html_message = render_to_string("emails/verify_account.html", context)

        text_message = f"Hello! To activate your account, please follow this link: {verification_link}"

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
        logger.error("User with id %s does not exist", user_id)
    except Exception as exc:
        logger.error("Error sending email for user_id %s. Retrying...", user_id)
        raise self.retry(exc=exc)
