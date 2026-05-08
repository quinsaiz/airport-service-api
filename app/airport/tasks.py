import base64
import io
import logging

import qrcode
from celery import shared_task
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.reverse import reverse
from weasyprint import HTML

from airport.models import Order
from airport.ticket_token import generate_ticket_token

logger = logging.getLogger(__name__)
User = get_user_model()


def build_validation_url(order_id: int) -> str:
    scheme = "https" if not settings.DEBUG else "http"
    token = generate_ticket_token(order_id)
    relative_url = reverse("airport:ticket-validate", kwargs={"token": token})
    base_url = getattr(settings, "BASE_URL", "localhost:8000").rstrip("/")

    return f"{scheme}://{base_url}{relative_url}"


def make_qr_png_base64(data: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=4,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return base64.b64encode(buf.getvalue()).decode()


@shared_task(bind=True, default_retry_delay=30, max_retries=3)
def send_ticket_email(self, order_id: int) -> None:
    try:
        order = (
            Order.objects
            .select_related("user")
            .prefetch_related(
                "tickets__flight__route__source", "tickets__flight__route__destination", "tickets__flight__airplane"
            )
            .get(pk=order_id)
        )

        user = order.user
        tickets = order.tickets.all()

        if user.first_name and user.last_name:
            passenger_name = f"{user.first_name} {user.last_name}"
        else:
            passenger_name = user.email

        short_uuid = str(order.uuid)[:8]
        pdf_filename = f"Ticket_{short_uuid}_{passenger_name}.pdf"

        validation_url = build_validation_url(order_id)
        qr_base64 = make_qr_png_base64(validation_url)

        context = {
            "user": user,
            "passenger_name": passenger_name,
            "tickets": tickets,
            "order": order,
            "order_id_display": str(order.uuid)[:8].upper(),
            "qr_code": qr_base64,
            "validation_url": validation_url,
            "support_email": settings.SUPPORT_EMAIL,
        }

        pdf_html = render_to_string("emails/ticket_pdf.html", context)
        pdf_file = HTML(string=pdf_html).write_pdf()

        subject = f"Your Flight Ticket - Order #{order_id}"
        html_message = render_to_string("emails/ticket_confirmation.html", context)
        text_message = (
            f"Thank you for your order #{order.id}. "
            f"Your tickets have been confirmed.\n\n"
            f"Validate your ticket: {validation_url}"
        )

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_message,
            from_email=None,
            to=[user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.attach(pdf_filename, pdf_file, "application/pdf")
        email.send()

        logger.info("Ticket email sent for Order #%s to %s", order_id, user.email)

    except Order.DoesNotExist:
        logger.error("Order with id %s not found", order_id)
    except Exception as exc:
        logger.error("Error sending email for Order %s. Retrying...", order_id)
        raise self.retry(exc=exc)
