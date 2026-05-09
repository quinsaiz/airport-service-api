import base64
import io
import logging
from typing import Any

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


def build_validation_url(ticket_id: int) -> str:
    scheme = "https" if not settings.DEBUG else "http"
    token = generate_ticket_token(ticket_id)
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
def send_ticket_email(self: Any, order_id: int) -> None:
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

        passenger_name = user.get_full_name() or user.email

        short_uuid = str(order.uuid)[:8]
        pdf_filename = f"Ticket_{short_uuid}_{passenger_name}.pdf"

        tickets_with_qr = []
        for ticket in tickets:
            url = build_validation_url(ticket.id)
            tickets_with_qr.append({
                "ticket": ticket,
                "qr_code": make_qr_png_base64(url),
                "validation_url": url,
            })

        context = {
            "user": user,
            "passenger_name": passenger_name,
            "tickets_with_qr": tickets_with_qr,
            "order": order,
            "order_id_display": str(order.uuid)[:8].upper(),
            "support_email": settings.SUPPORT_EMAIL,
        }

        pdf_html = render_to_string("emails/ticket_pdf.html", context)
        pdf_file = HTML(string=pdf_html).write_pdf()

        subject = f"Your Flight Ticket - Order #{str(order.uuid)[:8].upper()}"
        html_message = render_to_string("emails/ticket_confirmation.html", context)
        text_message = (
            f"Thank you for your order #{str(order.uuid)[:8].upper()}. "
            f"Your tickets have been confirmed. "
            f"Please check the attached PDF for your boarding passes."
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
        logger.exception("Order with id %s not found", order_id)
    except Exception as exc:
        logger.exception("Error sending email for Order %s. Retrying...", order_id)
        raise self.retry(exc=exc) from exc
