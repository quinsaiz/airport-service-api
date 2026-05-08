import logging
from datetime import timedelta
from typing import TypedDict

import jwt
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
TOKEN_LIFETIME_DAYS = 365


class TokenPayload(TypedDict):
    ticket_id: int
    iat: int
    exp: int


def generate_ticket_token(ticket_id: int) -> str:
    now = timezone.now()

    payload: TokenPayload = {
        "ticket_id": ticket_id,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=TOKEN_LIFETIME_DAYS)).timestamp()),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_ticket_token(token: str) -> int:
    payload: TokenPayload = jwt.decode(
        token,
        settings.SECRET_KEY,
        algorithms=[ALGORITHM],
    )

    return payload["ticket_id"]
