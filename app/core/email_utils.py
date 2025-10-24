from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from datetime import datetime
from app.core.config import settings
from pathlib import Path


async def _get_mail_config() -> ConnectionConfig:
    """Lazy-load mail config and dynamically locate template folder."""
    BASE_DIR = Path(__file__).resolve().parent  # app/core/
    TEMPLATE_FOLDER = str(BASE_DIR / "templates")

    if not Path(TEMPLATE_FOLDER).exists():
        raise ValueError(f"Template directory not found at {TEMPLATE_FOLDER}")

    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        TEMPLATE_FOLDER=TEMPLATE_FOLDER
    )


# ------------------------------------------------
# PASSWORD RESET EMAIL
# ------------------------------------------------
async def send_password_reset_email(email: str, reset_link: str):
    """Send password reset link to a user or organization."""
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="Reset Your TeamIQ Password",
        recipients=[email],
        template_body={
            "reset_link": reset_link,
            "current_year": datetime.utcnow().year
        },
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message, template_name="emails/password_reset.html")


# ------------------------------------------------
# INVITATION EMAIL
# ------------------------------------------------
async def send_invitation_email(email_to: str, invitation_link: str, invited_by: str = "your organization"):
    """Send invitation link for user onboarding."""
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="You’ve Been Invited to Join TeamIQ!",
        recipients=[email_to],
        template_body={
            "invitation_link": invitation_link,
            "invited_by": invited_by,
            "current_year": datetime.utcnow().year
        },
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message, template_name="emails/invitation.html")


# ------------------------------------------------
# ORGANIZATION SIGNUP EMAIL
# ------------------------------------------------
async def send_organization_signup_email(email_to: str, organization_name: str):
    """Send success confirmation when an organization signs up."""
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="Welcome to TeamIQ — Your Organization Account is Ready",
        recipients=[email_to],
        template_body={
            "organization_name": organization_name,
            "current_year": datetime.utcnow().year
        },
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message, template_name="emails/organization_signup.html")


# ------------------------------------------------
# ORGANIZATION ONBOARDING COMPLETE EMAIL
# ------------------------------------------------
async def send_onboarding_complete_email(email_to: str, organization_name: str):
    """Send email when organization completes onboarding."""
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="🎉 Your TeamIQ Onboarding Is Complete",
        recipients=[email_to],
        template_body={
            "organization_name": organization_name,
            "current_year": datetime.utcnow().year
        },
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message, template_name="emails/onboarding_complete.html")


# ------------------------------------------------
# DAILY DIGEST EMAIL
# ------------------------------------------------
async def send_daily_digest(email_to: str, summary: str, name: str):
    """Send summary of user or organization activity."""
    conf = await _get_mail_config()
    message = MessageSchema(
        subject="Your TeamIQ Daily Digest",
        recipients=[email_to],
        template_body={
            "summary": summary,
            "name": name,
            "current_year": datetime.utcnow().year
        },
        subtype=MessageType.html
    )
    fm = FastMail(conf)
    await fm.send_message(message, template_name="emails/daily_digest.html")


# ------------------------------------------------
# GENERIC NOTIFICATION EMAIL (Optional Helper)
# ------------------------------------------------
async def send_generic_email(subject: str, email_to: str, content: str):
    """Fallback email function for system notices or plain announcements."""
    conf = await _get_mail_config()
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        body=content,
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)
