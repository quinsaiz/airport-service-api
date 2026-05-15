from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

from user.oauth.base import OAuthUserData


def verify_google_token(token: str) -> OAuthUserData:
    client_id = settings.GOOGLE_CLIENT_ID
    payload = id_token.verify_oauth2_token(token, google_requests.Request(), client_id)

    return OAuthUserData(
        email=payload["email"],
        first_name=payload.get("given_name", ""),
        last_name=payload.get("family_name", ""),
    )
