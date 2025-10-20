from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import settings
from typing import Optional

async def _get_mail_config() -> ConnectionConfig:
    """Lazy-load config to avoid startup crashes if .env partial."""
    if not all([settings.MAIL_USERNAME, settings.MAIL_PASSWORD, settings.MAIL_FROM, settings.MAIL_SERVER]):
        raise ValueError("Email config incomplete—check MAIL_* in .env (e.g., Brevo/SMTP details).")
    
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,    
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS, 
        USE_CREDENTIALS=True
    )

async def send_email(email: str, reset_link: str):
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"Click the link to reset your password: {reset_link}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_invitation_email(email_to: str, invitation_code: str):
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="You have been invited to join TeamIQ",
        recipients=[email_to],
        body=f"You have been invited to join TeamIQ. Your invitation code is: {invitation_code}",
        subtype="plain",
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_daily_digest(email: str, summary: str):
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="TeamIQ Daily Summary",
        recipients=[email],
        body=summary,
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)