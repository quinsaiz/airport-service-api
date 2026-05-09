from datetime import timedelta
from typing import Any

import jwt
from django.conf import settings
from django.utils import timezone

ALGORITHM = "HS256"
TOKEN_LIFETIME_HOURS = 24


def generate_verification_token(user_id: int) -> str:
    now = timezone.now()

    payload = {
        "user_id": user_id,
        "purpose": "email_verification",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_LIFETIME_HOURS)).timestamp()),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def verify_verification_token(token: str) -> int:
    payload: dict[str, Any] = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])

    if payload.get("purpose") != "email_verification":
        raise jwt.InvalidTokenError("Wrong token purpose")

    return int(payload["user_id"])
