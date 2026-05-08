"""Notification service with FCM stub.

When Firebase credentials are configured, this service sends real push
notifications via Firebase Cloud Messaging. Otherwise, it logs notifications
to the console in development mode.
"""
from app.config import settings
from app.logger import logger
from typing import Optional


class NotificationService:
    """Abstraction layer for push notifications."""

    @property
    def is_available(self) -> bool:
        return settings.firebase_configured

    def send_push_notification(
        self,
        fcm_token: str,
        title: str,
        message: str,
        data: Optional[dict] = None,
    ) -> bool:
        """Send a push notification to a device via FCM.

        Returns True if sent successfully, False otherwise.
        In stub mode, logs the notification to console.
        """
        if not fcm_token:
            logger.warning("No FCM token provided, skipping notification")
            return False

        if self.is_available:
            try:
                from firebase_admin import messaging as fcm_messaging

                notification = fcm_messaging.Notification(title=title, body=message)
                android = fcm_messaging.AndroidConfig(priority="high")
                message_obj = fcm_messaging.Message(
                    notification=notification,
                    token=fcm_token,
                    android=android,
                    data=data or {},
                )
                fcm_messaging.send(message_obj)
                logger.info(f"Push notification sent to {fcm_token[:20]}...")
                return True
            except ImportError:
                logger.warning("firebase-admin package not installed. Using stub notifications.")
            except Exception as e:
                logger.error(f"FCM push notification failed: {e}")
                return False

        # Stub mode
        if settings.is_development:
            logger.info(
                f"[STUB] Push notification: token={fcm_token[:20]}..., "
                f"title='{title}', message='{message}'"
            )
            return True

        return False

    def send_reminder(self, user_id: str, fcm_token: str) -> bool:
        """Send a learning reminder notification."""
        return self.send_push_notification(
            fcm_token=fcm_token,
            title="Time to practice English!",
            message="Keep your streak going. Open the app for a quick lesson.",
            data={"type": "reminder", "user_id": user_id},
        )


# Singleton instance
notification_service = NotificationService()
