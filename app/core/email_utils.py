from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from app.core.config import Settings

conf = ConnectionConfig(
    MAIL_USERNAME=Settings.MAIL_USERNAME,
    MAIL_PASSWORD=Settings.MAIL_PASSWORD,
    MAIL_FROM=Settings.MAIL_FROM,
    MAIL_PORT=Settings.MAIL_PORT,
    MAIL_SERVER=Settings.MAIL_SERVER,
    MAIL_STARTTLS=False,    
    MAIL_SSL_TLS=True, 
    USE_CREDENTIALS=True
)

async def send_email(email: str, reset_link: str):
    message = MessageSchema(
        subject="Password Reset Request",
        recipients=[email],
        body=f"Click the link to reset your password: {reset_link}",
        subtype="plain"
    )
    fm = FastMail(conf)
    await fm.send_message(message)

async def send_invitation_email(email_to: str, invitation_code: str):
    message = MessageSchema(
        subject="You have been invited to join TeamIQ",
        recipients=[email_to],
        body=f"You have been invited to join TeamIQ. Your invitation code is: {invitation_code}",
        subtype="plain",
    )
    fm = FastMail(conf)
    await fm.send_message(message)
