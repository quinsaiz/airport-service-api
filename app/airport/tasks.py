import logging

from celery import shared_task
from django.contrib.auth import get_user_model
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.template.loader import render_to_string

from airport.models import Order

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, default_retry_delay=30, max_retries=3)
def send_ticket_email(self, order_id: int) -> None:
    try:
        order = Order.objects.select_related("user").prefetch_related(
            "tickets__flight__route__source",
            "tickets__flight__route__destination",
        ).get(pk=order_id)

        user = order.user
        tickets = order.tickets.all()

        subject = f"Your Flight Ticket - Order #{order_id}"

        context = {
            "user": user,
            "tickets": tickets,
            "order": order,
        }

        html_message = render_to_string("emails/ticket_confirmation.html", context)
        text_message = f"Thank you for your order #{order.id}. Your tickets have been confirmed."

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=None,
            to=[user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send()

        logger.info("Ticket email sent for Order #%s to %s", order_id, user.email)

    except Order.DoesNotExist:
        logger.error("Order with id %s not found", order_id)
    except Exception as exc:
        logger.error("Error sending email for user_id %s. Retrying...", order_id)
        raise self.retry(exc=exc)
