import smtplib
import ssl
from email.message import EmailMessage

from app.config import settings


def send_magic_link_email(to_email: str, deep_link: str) -> None:
    message = EmailMessage()
    message["Subject"] = "Your DrinkingBuddy sign-in link"
    message["From"] = settings.email_from
    message["To"] = to_email
    message.set_content(
        f"Tap to sign in to DrinkingBuddy:\n\n{deep_link}\n\n"
        f"This link expires in {settings.magic_link_ttl_minutes} minutes and can only be used once."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)


def send_verification_waitlist_welcome_back_email(to_email: str) -> None:
    message = EmailMessage()
    message["Subject"] = "You're up — verify your age now"
    message["From"] = settings.email_from
    message["To"] = to_email
    message.set_content(
        "This month's age-verification slots have opened back up. "
        "Open DrinkingBuddy and try enabling video again to verify."
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls(context=ssl.create_default_context())
        if settings.smtp_user:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(message)
