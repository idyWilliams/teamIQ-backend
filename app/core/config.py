from dotenv import load_dotenv
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL") #connects with the postgresql database in .env
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-for-jwt")
    GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID")
    GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET")
    GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
    MICROSOFT_CLIENT_ID = os.getenv("MICROSOFT_CLIENT_ID")
    MICROSOFT_CLIENT_SECRET = os.getenv("MICROSOFT_CLIENT_SECRET")
    GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "replace-with-your-secret")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    
    SMTP_SERVER: str
    SMTP_PORT: int
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_FROM: str
    SLACK_WEBHOOK_URL: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    
    
    class Config:
        fields = {
            'SMTP_SERVER': {'env': 'MAIL_SERVER'},
            'SMTP_PORT': {'env': 'MAIL_PORT'},
            'SMTP_USERNAME': {'env': 'MAIL_USERNAME'},
            'SMTP_PASSWORD': {'env': 'MAIL_PASSWORD'},
            'SMTP_FROM': {'env': 'MAIL_FROM'},
        }

settings = Settings()