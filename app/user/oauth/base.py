from dataclasses import dataclass


@dataclass
class OAuthUserData:
    email: str
    first_name: str = ""
    last_name: str = ""
