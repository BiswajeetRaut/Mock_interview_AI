from typing import Optional

class AuthUser:
    def __init__(
        self,
        uid: str,
        email: Optional[str] = None,
        name: Optional[str] = None,
        picture: Optional[str] = None,
        provider: Optional[str] = "google",
    ):
        self.uid = uid
        self.email = email
        self.name = name
        self.picture = picture
        self.provider = provider

    @classmethod
    def from_firebase(cls, decoded_token: dict):
        """
        Create AuthUser from Firebase decoded token
        """
        return cls(
            uid=decoded_token.get("uid"),
            email=decoded_token.get("email"),
            name=decoded_token.get("name"),
            picture=decoded_token.get("picture"),
            provider=decoded_token.get("firebase", {})
                .get("sign_in_provider", "google"),
        )

    def to_dict(self):
        return {
            "uid": self.uid,
            "email": self.email,
            "name": self.name,
            "picture": self.picture,
            "provider": self.provider,
        }
