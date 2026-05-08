"""Social authentication service with pluggable stub.

When GOOGLE_CLIENT_ID is configured, this service verifies Google tokens
using the google-auth library. Otherwise, it accepts any token in development
mode and creates/finds the user by social_id.
"""
from app.config import settings
from app.logger import logger
from typing import Optional


class SocialAuthService:
    """Abstraction layer for social login (Google, etc.)."""

    @property
    def is_available(self) -> bool:
        return settings.google_client_id is not None

    def verify_google_token(self, token: str) -> Optional[dict]:
        """Verify a Google ID token and return user info.

        Returns None if verification fails.
        In stub mode (no GOOGLE_CLIENT_ID), accepts any token.
        """
        if not settings.is_development and not self.is_available:
            logger.warning("Google social login not configured")
            return None

        if self.is_available:
            try:
                from google.oauth2 import idinfo
                from google.auth.transport import requests as google_requests

                idinfo_obj = idinfo.verify_oauth2_token(
                    token,
                    google_requests.Request(),
                    settings.google_client_id,
                )
                return {
                    "social_id": idinfo_obj.get("sub"),
                    "email": idinfo_obj.get("email"),
                    "name": idinfo_obj.get("name"),
                    "picture": idinfo_obj.get("picture"),
                    "provider": "google",
                }
            except ImportError:
                logger.warning("google-auth package not installed. Using stub social login.")
            except Exception as e:
                logger.error(f"Google token verification failed: {e}")
                return None

        # Stub mode: accept any token in development
        if settings.is_development:
            logger.warning("[STUB] Social login accepting token without verification")
            return {
                "social_id": f"stub_{hash(token) % 10000}",
                "email": f"stub_{hash(token) % 10000}@stub.dev",
                "name": "Stub User",
                "picture": None,
                "provider": "google",
            }

        return None


# Singleton instance
social_auth_service = SocialAuthService()
