import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings
from app.logger import logger


def send_otp_email(to_email: str, otp_code: str, username: str) -> bool:
    """Send OTP code to the user's email address.

    Returns True if email was sent successfully, False otherwise.
    Falls back to console logging if SMTP is not configured.
    """
    if not settings.smtp_configured:
        logger.warning(
            f"SMTP not configured. OTP for {username}: {otp_code}. "
            "Configure SMTP settings in .env to enable email delivery."
        )
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your ESL App Verification Code"
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email

        text_body = (
            f"Hello {username},\n\n"
            f"Your verification code is: {otp_code}\n\n"
            f"This code expires in 5 minutes.\n\n"
            f"If you did not request this code, please ignore this email."
        )

        html_body = (
            f"<div style='font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto;'>"
            f"<h2 style='color: #2c3e50;'>ESL Verification Code</h2>"
            f"<p>Hello {username},</p>"
            f"<p>Your verification code is:</p>"
            f"<div style='background: #f0f4f8; border-radius: 8px; padding: 16px; "
            f"text-align: center; font-size: 28px; letter-spacing: 4px; font-weight: bold; "
            f"color: #2c3e50;'>{otp_code}</div>"
            f"<p style='color: #7f8c8d; font-size: 14px;'>This code expires in 5 minutes.</p>"
            f"<p style='color: #95a5a6; font-size: 12px;'>"
            f"If you did not request this code, please ignore this email.</p>"
            f"</div>"
        )

        msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        if settings.smtp_use_tls:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP(settings.smtp_host, settings.smtp_port)

        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_from_email, to_email, msg.as_string())
        server.quit()

        logger.info(f"OTP email sent to {to_email} for user {username}")
        return True

    except smtplib.SMTPException as e:
        logger.error(f"Failed to send OTP email to {to_email}: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending OTP email to {to_email}: {e}")
        return False
