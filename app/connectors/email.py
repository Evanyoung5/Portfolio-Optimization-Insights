from __future__ import annotations

import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Protocol

LOGGER = logging.getLogger(__name__)


class EmailSender(Protocol):
    def send(self, *, to_email: str, subject: str, body: str) -> None:
        """Send a transactional email."""


class ConsoleEmailSender:
    def send(self, *, to_email: str, subject: str, body: str) -> None:
        LOGGER.info("Email to %s: %s\n%s", to_email, subject, body)


class SmtpEmailSender:
    def __init__(self) -> None:
        self.host = os.environ["SMTP_HOST"]
        self.port = int(os.getenv("SMTP_PORT", "587"))
        self.username = os.getenv("SMTP_USERNAME")
        self.password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM_EMAIL", self.username or "no-reply@example.com")
        self.use_tls = os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true"

    def send(self, *, to_email: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            if self.use_tls:
                smtp.starttls()
            if self.username and self.password:
                smtp.login(self.username, self.password)
            smtp.send_message(message)


def create_email_sender() -> EmailSender:
    if os.getenv("SMTP_HOST"):
        return SmtpEmailSender()
    return ConsoleEmailSender()


def public_app_url() -> str:
    return os.getenv("PUBLIC_APP_URL", "http://localhost:3000").rstrip("/")


def send_password_reset_email(*, to_email: str, token: str, sender: EmailSender | None = None) -> None:
    reset_url = f"{public_app_url()}/reset-password?token={token}"
    (sender or create_email_sender()).send(
        to_email=to_email,
        subject="Reset your portfolio account password",
        body=(
            "Use this link to reset your password:\n\n"
            f"{reset_url}\n\n"
            "If you did not request this, you can ignore this message."
        ),
    )


def send_email_verification_email(*, to_email: str, token: str, sender: EmailSender | None = None) -> None:
    verify_url = f"{public_app_url()}/verify-email?token={token}"
    (sender or create_email_sender()).send(
        to_email=to_email,
        subject="Verify your portfolio account email",
        body=(
            "Use this link to verify your email address:\n\n"
            f"{verify_url}\n\n"
            "If you did not create this account, you can ignore this message."
        ),
    )
