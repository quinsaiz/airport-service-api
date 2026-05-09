import logging
from datetime import timedelta
from typing import Any

import jwt
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
TOKEN_LIFETIME_DAYS = 365


def generate_ticket_token(ticket_id: int) -> str:
    now = timezone.now()

    payload: dict[str, Any] = {
        "ticket_id": ticket_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=TOKEN_LIFETIME_DAYS)).timestamp()),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_ticket_token(token: str) -> int:
    payload: dict[str, Any] = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    return int(payload["ticket_id"])
