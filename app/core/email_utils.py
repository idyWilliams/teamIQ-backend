# """
# Unified Email Service for Team IQ
# Supports both SendGrid (primary) and Brevo/fastapi-mail (fallback)
# """
# from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
# from sendgrid import SendGridAPIClient
# from sendgrid.helpers.mail import Mail, Email, To, Content
# from datetime import datetime
# from typing import Optional, Dict, Any
# import logging
# from pathlib import Path
# from jinja2 import Environment, FileSystemLoader
# from app.core.config import settings

# logger = logging.getLogger(__name__)


# class EmailService:
#     """
#     Unified email service supporting SendGrid and Brevo SMTP
#     Falls back to Brevo if SendGrid fails
#     """

#     def __init__(self):
#         """Initialize email clients"""
#         # SendGrid setup
#         self.sendgrid_enabled = bool(settings.SENDGRID_API_KEY)
#         if self.sendgrid_enabled:
#             try:
#                 self.sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
#                 self.from_email = Email(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME)
#                 logger.info("SendGrid client initialized successfully")
#             except Exception as e:
#                 logger.error(f"Failed to initialize SendGrid: {e}")
#                 self.sendgrid_enabled = False

#         # Template setup
#         self.BASE_DIR = Path(__file__).resolve().parent
#         self.TEMPLATE_FOLDER = str(self.BASE_DIR / "templates")

#         if not Path(self.TEMPLATE_FOLDER).exists():
#             logger.warning(f"Template directory not found at {self.TEMPLATE_FOLDER}")
#             Path(self.TEMPLATE_FOLDER).mkdir(parents=True, exist_ok=True)

#         # Jinja2 for custom rendering if needed
#         self.jinja_env = Environment(loader=FileSystemLoader(self.TEMPLATE_FOLDER))

#     async def _get_brevo_config(self) -> ConnectionConfig:
#         """Get Brevo/fastapi-mail configuration"""
#         return ConnectionConfig(
#             MAIL_USERNAME=settings.MAIL_USERNAME,
#             MAIL_PASSWORD=settings.MAIL_PASSWORD,
#             MAIL_FROM=settings.MAIL_FROM,
#             MAIL_PORT=settings.MAIL_PORT,
#             MAIL_SERVER=settings.MAIL_SERVER,
#             MAIL_STARTTLS=settings.MAIL_STARTTLS,
#             MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
#             USE_CREDENTIALS=True,
#             TEMPLATE_FOLDER=self.TEMPLATE_FOLDER
#         )

#     async def send_email_sendgrid(
#         self,
#         to_email: str,
#         subject: str,
#         html_content: str,
#         plain_text: Optional[str] = None
#     ) -> bool:
#         """Send email via SendGrid"""
#         if not self.sendgrid_enabled:
#             return False

#         try:
#             message = Mail(
#                 from_email=self.from_email,
#                 to_emails=To(to_email),
#                 subject=subject,
#                 html_content=Content("text/html", html_content)
#             )

#             if plain_text:
#                 message.plain_text_content = Content("text/plain", plain_text)

#             response = self.sendgrid_client.send(message)

#             if response.status_code in [200, 201, 202]:
#                 logger.info(f"✅ SendGrid: Email sent to {to_email}")
#                 return True
#             else:
#                 logger.error(f"❌ SendGrid failed with status {response.status_code}")
#                 return False

#         except Exception as e:
#             logger.error(f"❌ SendGrid error: {str(e)}")
#             return False

#     async def send_email_brevo(
#         self,
#         to_email: str,
#         subject: str,
#         template_name: str,
#         template_body: Dict[str, Any]
#     ) -> bool:
#         """Send email via Brevo using fastapi-mail"""
#         try:
#             conf = await self._get_brevo_config()
#             message = MessageSchema(
#                 subject=subject,
#                 recipients=[to_email],
#                 template_body=template_body,
#                 subtype=MessageType.html
#             )
#             fm = FastMail(conf)
#             await fm.send_message(message, template_name=template_name)
#             logger.info(f"✅ Brevo: Email sent to {to_email}")
#             return True
#         except Exception as e:
#             logger.error(f"❌ Brevo error: {str(e)}")
#             return False

#     def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
#         """Render email template"""
#         try:
#             template = self.jinja_env.get_template(template_name)
#             return template.render(**context)
#         except Exception as e:
#             logger.error(f"Template rendering error: {e}")
#             return ""

#     async def send_email(
#         self,
#         to_email: str,
#         subject: str,
#         template_name: str,
#         template_data: Dict[str, Any],
#         use_sendgrid: bool = True
#     ) -> bool:
#         """
#         Send email with automatic fallback

#         Args:
#             to_email: Recipient email
#             subject: Email subject
#             template_name: Template file name (e.g., 'emails/welcome.html')
#             template_data: Data to pass to template
#             use_sendgrid: Try SendGrid first (falls back to Brevo if fails)
#         """
#         # Add current year to all templates
#         template_data.setdefault('current_year', datetime.utcnow().year)
#         template_data.setdefault('app_url', settings.APP_URL)

#         # Try SendGrid first if enabled
#         if use_sendgrid and self.sendgrid_enabled:
#             html_content = self._render_template(template_name, template_data)
#             if html_content:
#                 success = await self.send_email_sendgrid(to_email, subject, html_content)
#                 if success:
#                     return True
#                 logger.warning("SendGrid failed, falling back to Brevo...")

#         # Fallback to Brevo
#         return await self.send_email_brevo(to_email, subject, template_name, template_data)


# # ================================================
# # EMAIL FUNCTIONS (Compatible with existing code)
# # ================================================

# # Global email service instance
# email_service = EmailService()


# async def send_password_reset_email(email: str, reset_link: str):
#     """Send password reset link to a user or organization."""
#     return await email_service.send_email(
#         to_email=email,
#         subject="Reset Your TeamIQ Password",
#         template_name="emails/password_reset.html",
#         template_data={"reset_link": reset_link}
#     )


# async def send_invitation_email(email_to: str, invitation_link: str, invited_by: str = "your organization"):
#     """Send invitation link for user onboarding."""
#     return await email_service.send_email(
#         to_email=email_to,
#         subject="You've Been Invited to Join TeamIQ!",
#         template_name="emails/invitation.html",
#         template_data={
#             "invitation_link": invitation_link,
#             "invited_by": invited_by
#         }
#     )


# async def send_organization_signup_email(email_to: str, organization_name: str):
#     """Send success confirmation when an organization signs up."""
#     return await email_service.send_email(
#         to_email=email_to,
#         subject="Welcome to TeamIQ — Your Organization Account is Ready",
#         template_name="emails/organization_signup.html",
#         template_data={"organization_name": organization_name}
#     )


# async def send_onboarding_complete_email(email_to: str, organization_name: str):
#     """Send email when organization completes onboarding."""
#     return await email_service.send_email(
#         to_email=email_to,
#         subject="🎉 Your TeamIQ Onboarding Is Complete",
#         template_name="emails/onboarding_complete.html",
#         template_data={"organization_name": organization_name}
#     )


# async def send_daily_digest(email_to: str, summary: str, name: str):
#     """Send summary of user or organization activity."""
#     return await email_service.send_email(
#         to_email=email_to,
#         subject="Your TeamIQ Daily Digest",
#         template_name="emails/daily_digest.html",
#         template_data={
#             "summary": summary,
#             "name": name
#         }
#     )


# async def send_generic_email(subject: str, email_to: str, content: str):
#     """Fallback email function for system notices or plain announcements."""
#     try:
#         conf = await email_service._get_brevo_config()
#         message = MessageSchema(
#             subject=subject,
#             recipients=[email_to],
#             body=content,
#             subtype="plain"
#         )
#         fm = FastMail(conf)
#         await fm.send_message(message)
#         return True
#     except Exception as e:
#         logger.error(f"Failed to send generic email: {e}")
#         return False






"""
Unified Email Service for Team IQ
Prioritizes Brevo API (Primary) with SendGrid as Fallback
"""
import logging
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # --- Brevo API Setup (Primary) ---
        self.brevo_enabled = bool(settings.BREVO_API_KEY)
        if self.brevo_enabled:
            try:
                configuration = sib_api_v3_sdk.Configuration()
                configuration.api_key['api-key'] = settings.BREVO_API_KEY
                self.brevo_api = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))
                logger.info("✅ Brevo API client initialized (Primary)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Brevo: {e}")
                self.brevo_enabled = False

        # --- SendGrid Setup (Fallback) ---
        self.sendgrid_enabled = bool(settings.SENDGRID_API_KEY)
        if self.sendgrid_enabled:
            try:
                self.sendgrid_client = SendGridAPIClient(settings.SENDGRID_API_KEY)
                self.sg_from = Email(settings.SENDGRID_FROM_EMAIL, settings.SENDGRID_FROM_NAME)
                logger.info("✅ SendGrid client initialized (Fallback)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize SendGrid: {e}")
                self.sendgrid_enabled = False

        # --- Template Setup ---
        self.BASE_DIR = Path(__file__).resolve().parent
        self.TEMPLATE_FOLDER = str(self.BASE_DIR / "templates")
        self.jinja_env = Environment(loader=FileSystemLoader(self.TEMPLATE_FOLDER))

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            logger.error(f"❌ Template rendering error: {e}")
            return ""

    async def send_email_brevo(self, to_email: str, subject: str, html_content: str) -> bool:
        if not self.brevo_enabled: return False
        try:
            sender = {"name": settings.SENDGRID_FROM_NAME, "email": settings.MAIL_FROM}
            to = [{"email": to_email}]
            send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
                to=to,
                html_content=html_content,
                sender=sender,
                subject=subject
            )
            self.brevo_api.send_transac_email(send_smtp_email)
            return True
        except ApiException as e:
            logger.error(f"❌ Brevo API error: {e}")
            return False

    async def send_email_sendgrid(self, to_email: str, subject: str, html_content: str) -> bool:
        if not self.sendgrid_enabled: return False
        try:
            message = Mail(
                from_email=self.sg_from,
                to_emails=To(to_email),
                subject=subject,
                html_content=Content("text/html", html_content)
            )
            response = self.sendgrid_client.send(message)
            return response.status_code in [200, 201, 202]
        except Exception as e:
            logger.error(f"❌ SendGrid error: {e}")
            return False

    async def send_email(self, to_email: str, subject: str, template_name: str, template_data: Dict[str, Any]) -> bool:
        template_data.setdefault('current_year', datetime.utcnow().year)
        template_data.setdefault('app_url', settings.APP_URL)

        html_content = self._render_template(template_name, template_data)
        if not html_content: return False

        # 1. Try Brevo First
        if self.brevo_enabled:
            if await self.send_email_brevo(to_email, subject, html_content):
                logger.info(f"📧 Email sent via Brevo to {to_email}")
                return True
            logger.warning("⚠️ Brevo failed, attempting SendGrid fallback...")

        # 2. Try SendGrid Fallback
        if self.sendgrid_enabled:
            if await self.send_email_sendgrid(to_email, subject, html_content):
                logger.info(f"📧 Email sent via SendGrid to {to_email}")
                return True

        return False

email_service = EmailService()

# --- Helper Functions ---

async def send_password_reset_email(email: str, reset_link: str):
    return await email_service.send_email(
        to_email=email,
        subject="Reset Your TeamIQ Password",
        template_name="emails/password_reset.html",
        template_data={"reset_link": reset_link}
    )

async def send_invitation_email(email_to: str, invitation_link: str, invited_by: str = "your organization"):
    return await email_service.send_email(
        to_email=email_to,
        subject="You've Been Invited to Join TeamIQ!",
        template_name="emails/invitation.html",
        template_data={"invitation_link": invitation_link, "invited_by": invited_by}
    )

async def send_organization_signup_email(email_to: str, organization_name: str):
    return await email_service.send_email(
        to_email=email_to,
        subject="Welcome to TeamIQ — Your Organization Account is Ready",
        template_name="emails/organization_signup.html",
        template_data={"organization_name": organization_name}
    )

async def send_onboarding_complete_email(email_to: str, organization_name: str):
    return await email_service.send_email(
        to_email=email_to,
        subject="🎉 Your TeamIQ Onboarding Is Complete",
        template_name="emails/onboarding_complete.html",
        template_data={"organization_name": organization_name}
    )
async def send_daily_digest(email_to: str, summary: str, name: str):
    """Send summary of user or organization activity."""
    return await email_service.send_email(
        to_email=email_to,
        subject="Your TeamIQ Daily Digest",
        template_name="emails/daily_digest.html",
        template_data={
            "summary": summary,
            "name": name
        }
    )

async def send_generic_email(subject: str, email_to: str, content: str):
    """Simple HTML wrapper for generic notices"""
    html = f"<html><body><p>{content}</p></body></html>"
    # Try primary SendGrid first
    if await email_service.send_email_sendgrid(email_to, subject, html):
        return True
    return await email_service.send_email_brevo(email_to, subject, html)