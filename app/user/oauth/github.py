import httpx
from django.conf import settings

from user.oauth.base import OAuthUserData


def verify_github_token(code: str) -> OAuthUserData:
    with httpx.Client() as client:
        token_response = client.post(
            "https://github.com/login/oauth/access_token",
            json={"client_id": settings.GITHUB_CLIENT_ID, "client_secret": settings.GITHUB_CLIENT_SECRET, "code": code},
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()
        if "error" in token_data:
            raise ValueError(f"GitHub token error: {token_data}")
        access_token = token_data["access_token"]

        user_response = client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
        )
        user_response.raise_for_status()
        user_data = user_response.json()

        if not user_data.get("email"):
            emails_response = client.get(
                "https://api.github.com/user/emails",
                headers={"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            )
            emails_response.raise_for_status()
            emails = emails_response.json()
            primary = next(email for email in emails if email["primary"] and email["verified"])
            email = primary["email"]
        else:
            email = user_data["email"]

        name_parts = (user_data.get("name") or "").split(" ", 1)

        return OAuthUserData(
            email=email,
            first_name=name_parts[0],
            last_name=name_parts[1] if len(name_parts) > 1 else "",
        )
